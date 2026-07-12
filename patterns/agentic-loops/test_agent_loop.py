#!/usr/bin/env python3
"""
Tests for agent_loop.py — the one tested agentic-loop implementation.

Covers the review's acceptance bar: one tool call + one final response,
rejecting malformed arguments, enforcing a budget, and an auditable
trace that never leaks raw tool output.
"""

import sys
import time
from pathlib import Path

import pytest

# agent_loop.py lives alongside this test file, which isn't on sys.path
# when pytest is invoked from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_loop import Budget, ToolSpec, run_agent_loop  # noqa: E402

ADD_SCHEMA = {
    "type": "object",
    "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
    "required": ["x", "y"],
}


def _scripted_model(responses):
    """A model_fn stub that returns each response in `responses` in
    order, ignoring the messages it's called with — a real adapter
    calls an actual provider instead."""
    it = iter(responses)

    def model_fn(messages):
        return next(it)

    return model_fn


class TestOneToolCallOneFinalResponse:
    def test_calls_tool_once_then_returns_final_response(self):
        calls = []

        def add(x, y):
            calls.append((x, y))
            return {"sum": x + y}

        tool = ToolSpec(name="add", fn=add, parameters_schema=ADD_SCHEMA)
        model_fn = _scripted_model(
            [
                {"content": None, "tool_calls": [{"id": "call_1", "name": "add", "arguments": {"x": 2, "y": 3}}]},
                {"content": "The sum is 5.", "tool_calls": None},
            ]
        )

        result = run_agent_loop(
            model_fn, {"add": tool}, messages=[{"role": "user", "content": "add 2 and 3"}]
        )

        assert result["status"] == "complete"
        assert result["final_content"] == "The sum is 5."
        assert calls == [(2, 3)]
        assert result["iterations"] == 2

        tool_result_messages = [m for m in result["messages"] if m.get("role") == "tool"]
        assert len(tool_result_messages) == 1
        assert tool_result_messages[0]["tool_call_id"] == "call_1"
        assert tool_result_messages[0]["content"] == {"sum": 5}

    def test_unknown_tool_name_is_rejected_without_raising(self):
        model_fn = _scripted_model(
            [
                {"content": None, "tool_calls": [{"id": "call_1", "name": "nonexistent", "arguments": {}}]},
                {"content": "done", "tool_calls": None},
            ]
        )

        result = run_agent_loop(model_fn, {}, messages=[{"role": "user", "content": "go"}])

        assert result["status"] == "complete"
        rejected = [t for t in result["trace"] if t["event"] == "tool_rejected"]
        assert len(rejected) == 1
        assert rejected[0]["detail"] == "unknown tool"

    def test_tool_exception_is_caught_and_fed_back_as_string(self):
        def broken():
            raise RuntimeError("db connection string: postgres://user:pass@host/db")

        tool = ToolSpec(name="broken", fn=broken, parameters_schema={"type": "object", "properties": {}})
        model_fn = _scripted_model(
            [
                {"content": None, "tool_calls": [{"id": "call_1", "name": "broken", "arguments": {}}]},
                {"content": "handled", "tool_calls": None},
            ]
        )

        result = run_agent_loop(model_fn, {"broken": tool}, messages=[{"role": "user", "content": "go"}])

        assert result["status"] == "complete"
        failed = [t for t in result["trace"] if t["event"] == "tool_call" and t["success"] is False]
        assert len(failed) == 1
        # The trace records the exception *type*, not its message (which
        # can embed sensitive detail like the connection string above).
        assert failed[0]["detail"] == "RuntimeError"
        assert "postgres://" not in str(result["trace"])


class TestMalformedArguments:
    def test_rejects_malformed_arguments_without_calling_the_tool(self):
        calls = []

        def add(x, y):
            calls.append((x, y))
            return {"sum": x + y}

        tool = ToolSpec(name="add", fn=add, parameters_schema=ADD_SCHEMA)
        model_fn = _scripted_model(
            [
                {"content": None, "tool_calls": [{"id": "call_1", "name": "add", "arguments": {"x": "not-a-number"}}]},
                {"content": "Sorry, couldn't complete that.", "tool_calls": None},
            ]
        )

        result = run_agent_loop(model_fn, {"add": tool}, messages=[{"role": "user", "content": "add"}])

        assert calls == []  # the underlying tool function was never invoked
        rejected = [t for t in result["trace"] if t["event"] == "tool_rejected"]
        assert len(rejected) == 1
        assert rejected[0]["detail"] == "schema validation failed"

        tool_result_messages = [m for m in result["messages"] if m.get("role") == "tool"]
        assert "invalid arguments" in tool_result_messages[0]["content"]["error"]


class TestBudgetEnforcement:
    def test_stops_at_max_iterations_instead_of_looping_forever(self):
        call_count = {"n": 0}

        def always_call_tool(messages):
            call_count["n"] += 1
            return {"content": None, "tool_calls": [{"id": f"call_{call_count['n']}", "name": "noop", "arguments": {}}]}

        tool = ToolSpec(name="noop", fn=lambda: "ok", parameters_schema={"type": "object", "properties": {}})

        result = run_agent_loop(
            always_call_tool,
            {"noop": tool},
            messages=[{"role": "user", "content": "loop forever"}],
            budget=Budget(max_iterations=3, max_seconds=10),
        )

        assert result["status"] == "budget_exceeded"
        assert result["iterations"] == 3
        assert call_count["n"] == 3

    def test_stops_at_wall_clock_budget(self):
        def slow_model(messages):
            time.sleep(0.05)
            return {"content": None, "tool_calls": [{"id": "call_x", "name": "noop", "arguments": {}}]}

        tool = ToolSpec(name="noop", fn=lambda: "ok", parameters_schema={"type": "object", "properties": {}})

        result = run_agent_loop(
            slow_model,
            {"noop": tool},
            messages=[{"role": "user", "content": "loop forever"}],
            budget=Budget(max_iterations=1000, max_seconds=0.12),
        )

        assert result["status"] == "budget_exceeded"
        assert result["iterations"] < 1000


class TestAuditableTrace:
    def test_trace_records_events_without_leaking_raw_tool_output(self):
        def fetch_secret():
            return {"api_key": "sk-should-not-appear-in-trace"}

        tool = ToolSpec(name="fetch_secret", fn=fetch_secret, parameters_schema={"type": "object", "properties": {}})
        model_fn = _scripted_model(
            [
                {"content": None, "tool_calls": [{"id": "call_1", "name": "fetch_secret", "arguments": {}}]},
                {"content": "done", "tool_calls": None},
            ]
        )

        result = run_agent_loop(
            model_fn, {"fetch_secret": tool}, messages=[{"role": "user", "content": "go"}]
        )

        assert "sk-should-not-appear-in-trace" not in str(result["trace"])
        # ...but the real result is still in `messages`, since the model
        # genuinely needs it to respond — only the audit trace redacts.
        assert "sk-should-not-appear-in-trace" in str(result["messages"])

        first_call_trace = [t for t in result["trace"] if t["event"] == "tool_call"][0]
        assert first_call_trace["tool"] == "fetch_secret"
        assert first_call_trace["success"] is True
        assert "timestamp" in first_call_trace


class TestApprovalBoundary:
    def test_denies_tool_call_when_approval_callback_rejects(self):
        calls = []

        def dangerous():
            calls.append(1)
            return "done"

        tool = ToolSpec(name="dangerous", fn=dangerous, parameters_schema={"type": "object", "properties": {}})
        model_fn = _scripted_model(
            [
                {"content": None, "tool_calls": [{"id": "call_1", "name": "dangerous", "arguments": {}}]},
                {"content": "ok, skipped", "tool_calls": None},
            ]
        )

        result = run_agent_loop(
            model_fn,
            {"dangerous": tool},
            messages=[{"role": "user", "content": "go"}],
            require_approval=lambda name, args: False,
        )

        assert calls == []
        denied = [t for t in result["trace"] if t["event"] == "tool_denied"]
        assert len(denied) == 1

    def test_approves_tool_call_when_approval_callback_accepts(self):
        calls = []

        def safe_tool():
            calls.append(1)
            return "done"

        tool = ToolSpec(name="safe_tool", fn=safe_tool, parameters_schema={"type": "object", "properties": {}})
        model_fn = _scripted_model(
            [
                {"content": None, "tool_calls": [{"id": "call_1", "name": "safe_tool", "arguments": {}}]},
                {"content": "done", "tool_calls": None},
            ]
        )

        result = run_agent_loop(
            model_fn,
            {"safe_tool": tool},
            messages=[{"role": "user", "content": "go"}],
            require_approval=lambda name, args: True,
        )

        assert calls == [1]
        assert result["status"] == "complete"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
