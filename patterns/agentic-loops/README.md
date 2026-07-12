# Agentic Loop Patterns

Structured patterns for building multi-turn agent interactions, tool calling loops, and agentic workflows.

An **agentic loop** is a cycle where an agent:
1. Receives a task or state
2. Plans / reasons about next steps
3. Calls tools or takes actions
4. Observes outcomes
5. Repeats until done

This pattern appears in LLM-powered systems, AI orchestrators, and automated workflows.

---

## Basic Loop Structure

### Minimal Loop

```python
def agentic_loop(task: str, max_iterations: int = 10):
    """Minimal agent loop: think → act → observe → repeat."""
    state = {"task": task, "iteration": 0}
    
    while state["iteration"] < max_iterations:
        # 1. Think: decide next action
        action = agent.plan(state)
        
        # 2. Act: execute action
        result = execute_action(action)
        
        # 3. Observe: update state
        state["iteration"] += 1
        state["last_result"] = result
        
        # 4. Check: are we done?
        if is_complete(state):
            return state["result"]
    
    raise TimeoutError("Agent did not complete within max iterations")
```

### Production Loop

```python
import json
from typing import Any, Dict, List
from dataclasses import dataclass

@dataclass
class AgentState:
    task: str
    messages: List[Dict[str, str]]  # Conversation history
    current_action: str = None
    iteration: int = 0
    max_iterations: int = 10
    tools_called: List[str] = None
    
    def __post_init__(self):
        if self.tools_called is None:
            self.tools_called = []

class Agent:
    def __init__(self, model, tools: Dict[str, Callable], logger):
        self.model = model
        self.tools = tools
        self.logger = logger
    
    def run(self, task: str) -> Dict[str, Any]:
        """Run agent loop with error handling and observability."""
        state = AgentState(task=task)
        
        try:
            while state.iteration < state.max_iterations:
                state.iteration += 1
                
                # 1. Think: LLM generates next action
                self.logger.info(f"Iteration {state.iteration}", 
                               extra={"task": task})
                
                response = self.model.complete(
                    messages=state.messages,
                    tools=list(self.tools.keys()),
                )
                
                # 2. Parse: extract action from response
                state.messages.append({
                    "role": "assistant",
                    "content": response["content"]
                })
                
                action = response.get("tool_call")
                if not action:
                    # Agent decided it's done
                    return {
                        "status": "complete",
                        "result": response["content"],
                        "iterations": state.iteration,
                    }
                
                state.current_action = action["name"]
                
                # 3. Act: call tool
                try:
                    tool_fn = self.tools.get(action["name"])
                    if not tool_fn:
                        raise ValueError(f"Unknown tool: {action['name']}")
                    
                    tool_result = tool_fn(**action["arguments"])
                    state.tools_called.append(action["name"])
                    
                except Exception as e:
                    self.logger.error(f"Tool error", extra={
                        "tool": action["name"],
                        "error": str(e),
                        "iteration": state.iteration,
                    })
                    tool_result = f"Error: {str(e)}"
                
                # 4. Observe: add result to conversation
                state.messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "tool": action["name"],
                        "result": tool_result,
                    })
                })
                
                self.logger.info("Tool executed", extra={
                    "tool": action["name"],
                    "iteration": state.iteration,
                })
        
        except Exception as e:
            self.logger.error("Agent loop failed", extra={
                "task": task,
                "iteration": state.iteration,
                "error": str(e),
            })
            return {
                "status": "error",
                "error": str(e),
                "iterations": state.iteration,
            }
        
        # Max iterations reached without completion
        return {
            "status": "max_iterations_reached",
            "last_action": state.current_action,
            "iterations": state.iteration,
            "tools_called": state.tools_called,
        }
```

---

## Tool Calling

### Tool Definition

```python
from typing import Callable, Dict, Any
import inspect

class Tool:
    def __init__(self, name: str, fn: Callable, description: str):
        self.name = name
        self.fn = fn
        self.description = description
        self.schema = self._extract_schema(fn)
    
    def _extract_schema(self, fn: Callable) -> Dict[str, Any]:
        """Extract parameter schema from function signature."""
        sig = inspect.signature(fn)
        params = {}
        
        for param_name, param in sig.parameters.items():
            # Use type hints and docstring to build schema
            params[param_name] = {
                "type": param.annotation.__name__,
                "description": f"Parameter: {param_name}",
            }
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": list(params.keys()),
                }
            }
        }
    
    def call(self, **kwargs) -> str:
        """Call tool and return result."""
        try:
            result = self.fn(**kwargs)
            return json.dumps(result) if not isinstance(result, str) else result
        except TypeError as e:
            return f"Invalid arguments: {str(e)}"

# Define tools
def search_web(query: str) -> Dict[str, Any]:
    """Search the web for information."""
    # Implementation
    return {"results": [...]}

def read_file(path: str) -> str:
    """Read a file and return its contents."""
    with open(path) as f:
        return f.read()

def write_file(path: str, content: str) -> Dict[str, str]:
    """Write content to a file."""
    with open(path, 'w') as f:
        f.write(content)
    return {"status": "written", "path": path}

# Registry
tools = {
    "search_web": Tool("search_web", search_web, "Search the web"),
    "read_file": Tool("read_file", read_file, "Read a file"),
    "write_file": Tool("write_file", write_file, "Write to a file"),
}
```

---

## Patterns & Best Practices

### Pattern: Reflection & Course Correction

Agent observes its own actions and corrects course if needed:

```python
def run_with_reflection(agent, task: str):
    """Run agent with per-iteration reflection."""
    state = {"task": task, "reflections": []}
    
    while state["iteration"] < 5:
        # Execute action
        action = agent.plan(state)
        result = execute(action)
        
        # Reflect on result
        reflection = agent.reflect(state, action, result)
        state["reflections"].append(reflection)
        
        if reflection["is_progress"]:
            state["iteration"] += 1
        else:
            # Try different approach
            state["message"] = f"Reflection: {reflection['advice']}"
    
    return state
```

### Pattern: Tool Chaining

One tool's output becomes the input to the next:

```python
def chain_tools(tools: List[str], initial_input: Any) -> Any:
    """Chain tools: output of one → input of next."""
    result = initial_input
    
    for tool_name in tools:
        tool = get_tool(tool_name)
        result = tool(result)
        logger.info(f"Chained {tool_name}", extra={"result": result})
    
    return result

# Usage
chain_tools(
    ["fetch_data", "transform_data", "save_data"],
    initial_input="/path/to/input"
)
```

### Pattern: Conditional Branching

Agent decides path based on outcomes:

```python
def run_with_branching(agent, task: str):
    """Agent branches logic based on intermediate results."""
    state = {"task": task, "branch": None}
    
    # First step: classify task
    classification = agent.classify(task)
    state["branch"] = classification  # "simple", "complex", "data_heavy"
    
    if state["branch"] == "simple":
        # Direct solution
        return agent.solve_simple(task)
    elif state["branch"] == "complex":
        # Multi-step reasoning
        return agent.solve_complex(task)
    elif state["branch"] == "data_heavy":
        # Fetch data first
        data = agent.fetch_data(task)
        return agent.solve_with_data(task, data)
```

### Pattern: Consensus / Voting

Multiple agents vote on next action:

```python
def multi_agent_consensus(agents: List[Agent], task: str):
    """Multiple agents propose actions; choose by vote."""
    proposals = []
    
    for agent in agents:
        action = agent.propose_action(task)
        proposals.append(action)
    
    # Vote on best proposal
    votes = {}
    for proposal in proposals:
        key = proposal["action"]
        votes[key] = votes.get(key, 0) + 1
    
    best_action = max(votes, key=votes.get)
    logger.info("Consensus reached", extra={
        "action": best_action,
        "votes": votes,
    })
    
    return execute(best_action)
```

---

## Common Pitfalls

| Pitfall | Problem | Fix |
|---------|---------|-----|
| Infinite loops | Agent stuck in repeat cycle | Add iteration limit + timeout |
| Token explosion | LLM runs out of context (long message history) | Summarize old messages, use sliding window |
| Tool errors ignored | Agent continues on tool failure | Catch and feed error back to agent |
| No observability | Can't debug what agent is doing | Log every action, tool call, and decision |
| Hard-coded actions | Agent can't adapt | Parameterize tools and strategies |

---

## Observability & Debugging

```python
class LoggingAgent(Agent):
    def run(self, task: str) -> Dict[str, Any]:
        """Run with comprehensive logging."""
        trace_id = generate_id()
        
        self.logger.info("Agent started", extra={
            "trace_id": trace_id,
            "task": task,
        })
        
        result = super().run(task)
        
        self.logger.info("Agent finished", extra={
            "trace_id": trace_id,
            "status": result["status"],
            "iterations": result.get("iterations"),
            "tools_called": result.get("tools_called"),
        })
        
        return result
```

---

## Further Reading

- OpenAI Assistants API: Tool use and function calling
- LangChain: Agent orchestration frameworks
- ReAct: Reasoning and Acting in Language Models (Yao et al.)
- Anthropic Agents: Building agentic systems with Claude
