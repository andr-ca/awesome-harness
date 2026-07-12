---
name: agentic-loops
description: Use when building multi-turn agents, tool-calling systems, agent orchestration, or autonomous workflows — covers loops, tool calling, branching, reflection patterns.
metadata:
  type: skills
  scope: ["Python", "JavaScript", "TypeScript"]
  when: "Before implementing agent loops; when designing tool calling; when building autonomous systems"
---

# Agentic Loops: Agents, Tools, Workflows

Structured patterns for building multi-turn agents that reason, act, and observe.

An **agentic loop** is:
1. **Think**: Agent reasons about task → decides action
2. **Act**: Call tools / take action
3. **Observe**: Get result, update state
4. **Repeat**: Loop until task complete

---

## Minimal Loop — use the tested implementation, don't hand-roll this

Don't write a bespoke think/act/observe loop from scratch — it's easy to
get the tool-result protocol wrong (feeding a tool's result back as a
plain `"user"` message loses the call binding and looks like human input
to the model, instead of `{"role": "tool", "tool_call_id": ..., ...}`),
easy to leave out a budget (infinite loop if the model never stops
calling tools), and easy to skip argument validation (a malformed tool
call reaches your tool function instead of being rejected).

`agent_loop.py`, bundled alongside this file (a symlink back to
`patterns/agentic-loops/agent_loop.py`, so it resolves whether you
installed the whole harness or only this one skill), is a minimal, tested
(100% coverage), provider-neutral implementation that gets these right:
JSON-Schema-validated arguments, provider-correct tool-result messages, an
iteration + wall-clock budget, an optional approval hook, and an auditable
trace that never logs raw tool output. See
`patterns/agentic-loops/README.md` in the full harness checkout for the
complete usage example and what it does *not* cover (sandboxing,
prompt-injection handling, real cost accounting, cancellation,
retries/idempotency, persistence, evals) — that guide isn't bundled with
this skill since it's documentation, not something the skill needs to
function.

```python
# Run from this skill's own directory, or add it to sys.path — see
# test_agent_loop.py (also bundled here) for a runnable example.
from agent_loop import Budget, ToolSpec, run_agent_loop

tool = ToolSpec(name="add", fn=add, parameters_schema={...})  # JSON Schema
result = run_agent_loop(
    model_fn=my_provider_adapter,  # translates to/from your provider's native shape
    tools={"add": tool},
    messages=[{"role": "user", "content": "What is 2 + 3?"}],
    budget=Budget(max_iterations=5, max_seconds=30),
)
```

---

## Tool Definition

```python
class Tool:
    def __init__(self, name: str, fn, description: str):
        self.name = name
        self.fn = fn
        self.description = description

    def call(self, **kwargs):
        """Call tool and return result as JSON string."""
        try:
            result = self.fn(**kwargs)
            return json.dumps(result) if not isinstance(result, str) else result
        except TypeError as e:
            return json.dumps({"error": f"Invalid arguments: {e}"})

# Define tools
def search_web(query: str) -> dict:
    """Search the web for information."""
    # Implementation
    return {"results": [...]}

def read_file(path: str) -> str:
    """Read a file's contents."""
    with open(path) as f:
        return f.read()

# Registry
tools = {
    "search_web": Tool("search_web", search_web, "Search the web"),
    "read_file": Tool("read_file", read_file, "Read file contents"),
}
```

---

## Patterns

### Pattern 1: Reflection
Agent observes its own results and corrects course.

```python
def run_with_reflection(agent, task):
    """Agent reflects on each step."""
    state = {"task": task, "iteration": 0}

    for i in range(5):
        # Execute action
        action = agent.decide(state)
        result = execute(action)

        # Reflect on result
        reflection = agent.reflect(state, action, result)

        if reflection["progress"]:
            state["iteration"] += 1
        else:
            # Adjust strategy based on reflection
            state["strategy"] = reflection["new_strategy"]

    return state
```

### Pattern 2: Tool Chaining
One tool's output → next tool's input.

```python
def chain_tools(tool_sequence: list, initial_input):
    """Execute tools in sequence."""
    result = initial_input
    for tool_name in tool_sequence:
        tool = tools[tool_name]
        result = tool(result)  # Output of one → input of next
    return result

# Usage
chain_tools(
    ["fetch_data", "transform_data", "save_data"],
    initial_input="/input"
)
```

### Pattern 3: Branching
Agent branches logic based on intermediate results.

```python
def run_with_branching(agent, task):
    """Agent chooses execution path."""
    # Classify task
    classification = agent.classify(task)

    if classification == "simple":
        return agent.solve_direct(task)
    elif classification == "complex":
        # Multi-step reasoning
        return agent.solve_step_by_step(task)
    elif classification == "data_heavy":
        # Fetch data first
        data = agent.gather_data(task)
        return agent.solve_with_data(task, data)
```

### Pattern 4: Multi-Agent Consensus
Multiple agents vote on best action.

```python
def consensus_decision(agents: list, task: str):
    """Multiple agents propose; choose by vote."""
    proposals = []

    for agent in agents:
        proposal = agent.propose(task)
        proposals.append(proposal)

    # Vote: most common proposal wins
    votes = {}
    for prop in proposals:
        key = prop["action"]
        votes[key] = votes.get(key, 0) + 1

    best = max(votes, key=votes.get)
    logger.info(f"Consensus: {best} (votes: {votes})")

    return execute(best)
```

**Caution:** this is not independent validation. Agents sharing a model,
prompt, or training data have correlated errors — they can confidently
agree on the same wrong answer. Use it to reduce variance on tasks with
genuinely diverse proposers, not as a correctness guarantee.

---

## Common Pitfalls

| Pitfall | Cause | Fix |
|---------|-------|-----|
| Infinite loops | Agent repeats same action | Add iteration limit |
| Token explosion | Long message history | Summarize old messages |
| Tool errors ignored | No error handling | Catch exceptions, feed back to agent |
| No observability | Can't debug | Log every action, decision, tool call |
| Silent failures | Errors don't propagate | Always return results to agent |

---

## Observability

```python
def run_with_logging(agent, task, logger):
    """Run agent with comprehensive logging."""
    trace_id = uuid.uuid4()
    logger.info("Agent start", extra={"trace_id": trace_id, "task": task})

    state = {"messages": []}
    for iteration in range(10):
        action = agent.decide(state)
        logger.info("Action", extra={
            "trace_id": trace_id,
            "iteration": iteration,
            "action": action["name"],
        })

        result = call_tool(action)
        logger.info("Result", extra={
            "trace_id": trace_id,
            "tool": action["name"],
            "success": result["status"] == "ok",
        })

        state["messages"].append({"role": "user", "content": json.dumps(result)})

    logger.info("Agent done", extra={"trace_id": trace_id, "iterations": len(state["messages"])})
    return state
```

---

## Checklist

- [ ] Define tools clearly (name, description, parameters)
- [ ] Add iteration limit (prevent infinite loops)
- [ ] Log every action, tool call, result
- [ ] Handle tool errors explicitly
- [ ] Feed errors back to agent (don't hide)
- [ ] Test with small iteration limits first
- [ ] Trace IDs for debugging
- [ ] Monitor token usage (watch for message explosion)

---

## References

- Tested implementation: `agent_loop.py` + `test_agent_loop.py`, bundled
  in this skill's own directory (works whether you installed the whole
  harness or only this skill).
- Full guide (usage example, what's not covered, pseudocode patterns) —
  needs the full harness checkout, not bundled here since it's
  documentation rather than something this skill runs:
  `patterns/agentic-loops/README.md`
- Error handling: `.claude/skills/error-handling/SKILL.md`
- [OpenAI Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses) —
  current tool-use API; the Assistants API is deprecated (sunset
  2026-08-26)
