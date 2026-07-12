# Agentic Loop Patterns

Structured patterns for building multi-turn agent interactions, tool calling loops, and agentic workflows.

An **agentic loop** is a cycle where an agent:
1. Receives a task or state
2. Plans / reasons about next steps
3. Calls tools or takes actions
4. Observes outcomes
5. Repeats until done

This pattern appears in LLM-powered systems, AI orchestrators, and automated workflows.

> **What's actually runnable here.** Only [`agent_loop.py`](agent_loop.py) +
> [`test_agent_loop.py`](test_agent_loop.py) are tested, executable code —
> run `pip install -r requirements.txt && pytest test_agent_loop.py --cov=agent_loop
> --cov-fail-under=80` from this directory to verify it yourself. Every other
> code block below is explicitly labeled **pseudocode**: it illustrates a
> concept, it is not something to copy into production without filling in
> the missing pieces (a real model adapter, real tool implementations, a
> real approval/sandbox layer).

---

## Tested Reference Implementation

[`agent_loop.py`](agent_loop.py) is a minimal, provider-neutral, single-tool-call
agent loop covering the concrete parts of a safe loop that can actually be
tested:

- **JSON Schema validation** of tool arguments before execution — a
  malformed call is rejected and fed back to the model as an error, the
  underlying tool function is never invoked.
- **Provider-correct tool-result messages** — `{"role": "tool",
  "tool_call_id": ..., "content": ...}`, preserving the call ID, not a
  plain `"user"` message (which loses the call binding and looks like
  human input to the model — a bug in an earlier version of this doc).
- **A budget** (`max_iterations` and `max_seconds`) so a model that never
  stops calling tools can't loop forever.
- **An optional approval hook** (`require_approval(name, arguments) ->
  bool`) — a tool call is skipped, not executed, if the hook returns
  `False`.
- **An auditable trace** — a list of `{iteration, event, tool, success,
  detail, timestamp}` entries that deliberately never includes raw tool
  arguments or output (see `patterns/error-handling` and `patterns/logging`
  for why raw tool output doesn't belong in logs).

```python
from agent_loop import Budget, ToolSpec, run_agent_loop

def add(x: int, y: int) -> dict:
    return {"sum": x + y}

tool = ToolSpec(
    name="add",
    fn=add,
    parameters_schema={
        "type": "object",
        "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
        "required": ["x", "y"],
    },
)

# model_fn is the provider-neutral seam: a real integration calls your
# actual provider and translates its response into {"content": ...,
# "tool_calls": [...]}, then translates the "tool" messages this loop
# appends back into that provider's native tool-result format before
# sending them on. This stub scripts two fixed turns so the example
# above runs standalone, with no API key or network access required.
_responses = iter([
    {"content": None, "tool_calls": [{"id": "call_1", "name": "add", "arguments": {"x": 2, "y": 3}}]},
    {"content": "2 + 3 is 5.", "tool_calls": None},
])
def model_fn(messages):
    return next(_responses)

result = run_agent_loop(
    model_fn=model_fn,
    tools={"add": tool},
    messages=[{"role": "user", "content": "What is 2 + 3?"}],
    budget=Budget(max_iterations=5, max_seconds=30),
    require_approval=None,  # or a callback for human-in-the-loop gating
)
assert result == {
    "status": "complete",
    "final_content": "2 + 3 is 5.",
    "iterations": 2,
    "messages": result["messages"],  # full transcript, including tool results
    "trace": result["trace"],        # audit log — no raw tool content
}
```

### What this does *not* cover

The acceptance bar for this file is a tool call, a final response, rejected
malformed arguments, an enforced budget, and an auditable trace — all
tested above. A production deployment needs more than that:

| Concern | What `agent_loop.py` gives you | What you still need |
|---|---|---|
| Approval / sandboxing | An approval hook that can veto a call | Actually running tools in a sandbox; a real approval UI/policy |
| Untrusted tool output | Nothing special | Treat tool output as untrusted input to the model — a compromised or malicious tool result can attempt prompt injection against the next turn |
| Prompt injection | Nothing special | Don't let tool output silently expand the model's permissions; consider a lower-trust message role or explicit boundary markers |
| Cost/token budget | Iteration count + wall-clock time | Real token/cost accounting from your provider's usage reporting |
| Cancellation | Nothing special | A cancellation token/event checked between iterations for long-running loops |
| Retries / idempotency | Tool exceptions are caught and fed back, not retried | Retry policy per tool; idempotency keys for tools with side effects (so a retried write doesn't double-apply) |
| Persistence / resume | `messages` and `trace` are returned to the caller | Durable storage if a loop needs to survive a process restart |
| Evals | Nothing | A test suite or eval harness that exercises your actual tools/model, not just this loop's control flow |

---

## Illustrative Pseudocode

Everything below is pseudocode — it shows a shape, not something that runs
as written. None of it has a model, tools, or an `execute()`/`agent.plan()`
implementation behind it.

### Minimal Loop (pseudocode)

```python
def agentic_loop(task: str, max_iterations: int = 10):
    """Pseudocode: think -> act -> observe -> repeat."""
    state = {"task": task, "iteration": 0, "last_result": None}

    while state["iteration"] < max_iterations:
        action = agent.plan(state)          # not defined here
        result = execute_action(action)     # not defined here

        state["iteration"] += 1
        state["last_result"] = result

        if is_complete(state):              # not defined here
            return state["last_result"]

    raise TimeoutError("Agent did not complete within max iterations")
```

### Tool Definition (pseudocode)

```python
from typing import Callable, Dict, Any
import inspect

class Tool:
    """Illustrates deriving a JSON-Schema-shaped description from a
    function signature. This is a simplification — `param.annotation
    .__name__` breaks on `Optional[str]`, `List[int]`, and other
    generics; a real implementation needs a proper type-to-schema
    mapping (or a library that already does this)."""

    def __init__(self, name: str, fn: Callable, description: str):
        self.name = name
        self.fn = fn
        self.description = description
        self.schema = self._extract_schema(fn)

    def _extract_schema(self, fn: Callable) -> Dict[str, Any]:
        sig = inspect.signature(fn)
        params = {
            name: {"type": param.annotation.__name__, "description": f"Parameter: {name}"}
            for name, param in sig.parameters.items()
        }
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": params, "required": list(params.keys())},
            },
        }
```

### Pattern: Reflection & Course Correction (pseudocode)

```python
def run_with_reflection(agent, task: str):
    """Pseudocode: agent observes its own actions and corrects course."""
    state = {"task": task, "iteration": 0, "reflections": []}

    while state["iteration"] < 5:
        action = agent.plan(state)
        result = execute(action)  # not defined here

        reflection = agent.reflect(state, action, result)
        state["reflections"].append(reflection)

        if reflection["is_progress"]:
            state["iteration"] += 1
        else:
            state["message"] = f"Reflection: {reflection['advice']}"

    return state
```

### Pattern: Tool Chaining (pseudocode)

One tool's output becomes the input to the next:

```python
def chain_tools(tools: List[str], initial_input: Any) -> Any:
    result = initial_input
    for tool_name in tools:
        tool = get_tool(tool_name)  # not defined here
        result = tool(result)
        # Never log a raw tool result — a tool can return file contents,
        # API responses, or credentials it fetched, none of which this
        # code has redacted. Log shape, not content.
        logger.info(f"Chained {tool_name}", extra={"result_type": type(result).__name__})
    return result
```

### Pattern: Conditional Branching (pseudocode)

```python
def run_with_branching(agent, task: str):
    classification = agent.classify(task)  # not defined here
    if classification == "simple":
        return agent.solve_simple(task)
    elif classification == "complex":
        return agent.solve_complex(task)
    elif classification == "data_heavy":
        data = agent.fetch_data(task)
        return agent.solve_with_data(task, data)
```

### Pattern: Consensus / Voting (pseudocode, use with caution)

Multiple agents propose an action; the majority wins:

```python
def multi_agent_consensus(agents: List[Agent], task: str):
    proposals = [agent.propose_action(task) for agent in agents]

    votes = {}
    for proposal in proposals:
        votes[proposal["action"]] = votes.get(proposal["action"], 0) + 1

    best_action = max(votes, key=votes.get)
    return execute(best_action)  # not defined here
```

**Caution:** majority vote is not independent validation. If the agents
share a model, prompt, or training data, their errors are correlated —
they can confidently agree on the same wrong answer. Treat this as a
way to reduce variance on tasks with diverse-enough proposers, not as a
correctness guarantee.

---

## Common Pitfalls

| Pitfall | Problem | Fix |
|---------|---------|-----|
| Infinite loops | Agent stuck in repeat cycle | Iteration limit + wall-clock budget — see `Budget` in `agent_loop.py` |
| Token explosion | LLM runs out of context (long message history) | Summarize old messages, use sliding window |
| Tool errors ignored | Agent continues on tool failure | Catch and feed the error back to the model (`agent_loop.py` does this) |
| Malformed tool calls | Agent calls a tool with invalid arguments | Validate against a JSON Schema before executing (`agent_loop.py` does this) |
| No observability | Can't debug what agent is doing | An auditable trace of events — without raw tool content, see above |
| Hard-coded actions | Agent can't adapt | Parameterize tools and strategies |
| Trusting tool output | A malicious/compromised tool result can try to steer the next turn | Treat tool output as untrusted input, not as trusted system instruction |

---

## Further Reading

- [OpenAI Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses) —
  the current API for tool use and function calling. The Assistants API is
  deprecated and scheduled for sunset (2026-08-26); don't build against it.
- Anthropic's [building effective agents](https://www.anthropic.com/research/building-effective-agents) —
  provider-neutral guidance on tool use, orchestration, and evaluation.
- ReAct: Reasoning and Acting in Language Models (Yao et al.) — the
  think/act/observe loop this pattern is based on.
- LangChain / other agent orchestration frameworks — useful for
  provider adapters and tool schemas at scale; still apply the same
  approval/sandbox/budget considerations above regardless of framework.
