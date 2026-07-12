#!/usr/bin/env python3
"""
Minimal, provider-neutral, tested single-tool-call agent loop.

This is the one genuinely runnable implementation referenced by
README.md — everything else in that file is labeled pseudocode. It
demonstrates the concrete, testable parts of a safe agentic loop:

  - JSON Schema validation of tool arguments before execution
  - provider-correct tool-result messages (role="tool", tool_call_id
    preserved — not a plain "user" message, which loses the call
    binding and looks like human input to the model)
  - an iteration + wall-clock budget so a model that never stops
    calling tools can't loop forever
  - an optional approval hook for tool calls
  - an auditable trace that records what happened without ever
    recording raw tool output (tool results can contain file contents,
    API responses, or credentials — see patterns/error-handling and
    patterns/logging for why that matters)

model_fn is a provider-neutral seam: a real integration writes a thin
adapter that turns a provider's native response into this shape
{"content": str | None, "tool_calls": [{"id", "name", "arguments"}] |
None} and turns the tool-result messages this loop produces back into
that provider's native tool-result format before sending them on.
"""

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

try:
    import jsonschema
except ImportError as e:  # pragma: no cover — defensive; jsonschema is a required dependency
    raise ImportError(
        "jsonschema is required for agent_loop. Install with: pip install jsonschema"
    ) from e


@dataclass
class ToolSpec:
    """A callable tool plus the JSON Schema its arguments must satisfy."""

    name: str
    fn: Callable[..., Any]
    parameters_schema: Dict[str, Any]


@dataclass
class Budget:
    """Caps how long a loop may run — the concrete, enforceable stand-in
    for the fuller token/cost budgeting a real deployment needs (which
    depends on provider-specific usage accounting this loop doesn't have
    access to)."""

    max_iterations: int = 10
    max_seconds: float = 30.0


def run_agent_loop(
    model_fn: Callable[[List[Dict[str, Any]]], Dict[str, Any]],
    tools: Dict[str, ToolSpec],
    messages: List[Dict[str, Any]],
    budget: Optional[Budget] = None,
    require_approval: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
) -> Dict[str, Any]:
    """
    Run the loop: the model proposes tool calls or a final response;
    validated, approved tool calls are executed and fed back; repeat
    until the model returns a final response or the budget runs out.

    `messages` is the actual conversation so far — the caller seeds it
    (system/user turns); this loop only appends to it, it never invents
    a task string the way the old pseudocode's `AgentState(task=task)`
    did without threading `task` into `messages` at all.

    Returns a dict with `status` ("complete" | "budget_exceeded"),
    `final_content`, `iterations`, `messages` (the full transcript,
    including tool results — those go to the model on purpose), and
    `trace` (an audit log of what happened, deliberately excluding raw
    tool output).
    """
    budget = budget or Budget()
    trace: List[Dict[str, Any]] = []
    start = time.monotonic()
    iteration = 0

    while True:
        iteration += 1
        if iteration > budget.max_iterations:
            trace.append(_trace_entry(iteration, "budget_exceeded", detail="max_iterations"))
            return _result("budget_exceeded", messages, trace, iteration - 1)
        if time.monotonic() - start > budget.max_seconds:
            trace.append(_trace_entry(iteration, "budget_exceeded", detail="max_seconds"))
            return _result("budget_exceeded", messages, trace, iteration - 1)

        response = model_fn(messages)
        messages.append(
            {
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": response.get("tool_calls"),
            }
        )

        tool_calls = response.get("tool_calls")
        if not tool_calls:
            trace.append(_trace_entry(iteration, "final", success=True))
            return _result(
                "complete", messages, trace, iteration, final_content=response.get("content")
            )

        for call in tool_calls:
            _handle_tool_call(call, tools, messages, trace, iteration, require_approval)


def _handle_tool_call(
    call: Dict[str, Any],
    tools: Dict[str, ToolSpec],
    messages: List[Dict[str, Any]],
    trace: List[Dict[str, Any]],
    iteration: int,
    require_approval: Optional[Callable[[str, Dict[str, Any]], bool]],
) -> None:
    call_id = call["id"]
    tool_name = call["name"]
    arguments = call.get("arguments", {})

    tool = tools.get(tool_name)
    if tool is None:
        messages.append(_tool_result_message(call_id, {"error": f"unknown tool: {tool_name}"}))
        trace.append(
            _trace_entry(iteration, "tool_rejected", tool=tool_name, success=False, detail="unknown tool")
        )
        return

    try:
        jsonschema.validate(instance=arguments, schema=tool.parameters_schema)
    except jsonschema.ValidationError as e:
        messages.append(
            _tool_result_message(call_id, {"error": f"invalid arguments: {e.message}"})
        )
        trace.append(
            _trace_entry(
                iteration, "tool_rejected", tool=tool_name, success=False, detail="schema validation failed"
            )
        )
        return

    if require_approval is not None and not require_approval(tool_name, arguments):
        messages.append(_tool_result_message(call_id, {"error": "tool call denied by approval policy"}))
        trace.append(_trace_entry(iteration, "tool_denied", tool=tool_name, success=False))
        return

    try:
        result = tool.fn(**arguments)
        messages.append(_tool_result_message(call_id, result))
        trace.append(_trace_entry(iteration, "tool_call", tool=tool_name, success=True))
    except Exception as e:
        messages.append(_tool_result_message(call_id, {"error": str(e)}))
        trace.append(
            _trace_entry(
                iteration, "tool_call", tool=tool_name, success=False, detail=type(e).__name__
            )
        )


def _tool_result_message(call_id: str, content: Any) -> Dict[str, Any]:
    """Provider-correct tool-result shape: role="tool" with the call ID
    preserved, matching the OpenAI/Anthropic tool-result convention —
    not a plain "user" message, which the old pseudocode used and which
    loses the binding between a call and its result."""
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def _trace_entry(
    iteration: int,
    event: str,
    tool: Optional[str] = None,
    success: Optional[bool] = None,
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    """An audit-trail entry. Deliberately has no field for raw tool
    output/arguments — see the module docstring."""
    return {
        "iteration": iteration,
        "event": event,
        "tool": tool,
        "success": success,
        "detail": detail,
        "timestamp": time.time(),
    }


def _result(
    status: str,
    messages: List[Dict[str, Any]],
    trace: List[Dict[str, Any]],
    iterations: int,
    final_content: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "final_content": final_content,
        "iterations": iterations,
        "messages": messages,
        "trace": trace,
    }
