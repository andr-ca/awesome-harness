# AGENTS.md

Generated from this repo's own `CLAUDE.md` and `.claude/skills/` catalog
by `tools/generate-agents-md.sh` — do not hand-edit; regenerate instead
(`tools/generate-agents-md.sh --output AGENTS.md`). A CI check keeps this
file in sync with its source (see `.github/workflows/ci.yml`'s
`content-quality` job).

Codex has no on-demand skill-loading mechanism — everything below is
always in context, not loaded on demand the way Claude Code loads a
matching skill. Content is otherwise identical to what a Claude Code
session reads from `CLAUDE.md` and `.claude/skills/*/SKILL.md`.

**This adapter has not been verified against a real Codex CLI session —
best-effort until someone tests it. See `README.md`'s "Supported
clients" section.**

---

## agentharness – Agent Router

This file is loaded into every session that touches this repo. Keep it
short — everything else is one link away. Full index: [MANIFEST.md](MANIFEST.md).
Planned-but-not-built: [ROADMAP.md](ROADMAP.md).

### 🤖 Agent Workflow Completion

**Default (no publish authority): verify and stage, then stop.**

1. ✅ **Verify all work is done** — tests pass, coverage meets the applicable rigor tier (see `.github/CODING_GUIDELINES.md#rigor-tiers`), lint passes, no TODOs
2. ✅ **Create atomic commits locally** — one logical unit per commit, clear message explaining WHY
3. 🛑 **Stop before pushing, opening a PR, or auto-implementing recommendations.** Present a summary of what's staged and ask the user to confirm before publishing anything.

**Full publish authority (commit → push → PR, same as before) applies only when either is true:**
- `.agentharness-publish-mode` exists at this repo's root (a local,
  gitignored, per-operator flag — see "Publish authority" below), **or**
- The user has explicitly granted standing authorization for this session
  or task in the current conversation. This always overrides the flag in
  either direction — explicit instructions in the request outrank a
  standing file the same way rigor-tier precedence already works (see
  `patterns/profiles/README.md#precedence-order`).

Under full publish authority, the original mandate applies as written:
push to remote with tracking, create a PR with `gh pr create`, and never
leave verified work uncommitted-and-unpushed — an agent claiming work is
"complete" while it's only staged locally is incomplete.

**Never merge a PR on CI status alone — wait for review comments, then
address them, before merging.** A green CI run says nothing about
feedback left on the diff itself (human or automated, e.g. GitHub
Copilot's code review). Before merging:
1. Give automated review time to post (its own check, separate from CI,
   e.g. "Copilot Code Review") — don't merge the instant CI turns green.
2. Fetch *both* comment types — issue-level (`gh pr view <n> --json
   comments`) and inline review comments (`gh api
   repos/<owner>/<repo>/pulls/<n>/comments`); the first call alone misses
   inline findings entirely.
3. Verify each finding against current code before acting on it — an
   automated reviewer's claim can be stale (already fixed by a later
   commit) or simply wrong; confirm the premise, don't implement a "fix"
   on faith.
4. Fix what's real and in scope per the Recommendation Assessment
   mandate below (scoped/low-risk directly; larger findings get scoped
   and confirmed like any other recommendation); note explicitly why
   anything is skipped rather than silently ignoring it.

**Never report a push/merge as done while CI is still running or red —
watch it through to an actual, current green before moving on or telling
the user it's finished.** "I pushed" and "CI passed" are different
claims; only the second one means the work is safe. This applies to
every CI-triggering push this mandate covers: opening a PR, pushing more
commits to one, and merging into `main`.
1. After any such push, poll the run (`gh run watch --exit-status`, or an
   equivalent poll loop) until it reaches a terminal state — `queued` and
   `in_progress` are not outcomes, and reporting either as "done" is the
   exact mistake this rule exists to prevent.
2. On failure, read the actual log for the failed job(s)
   (`gh run view <run-id> --log-failed`) before deciding what to do next
   — don't guess from the job name.
3. If the failure is transient infrastructure (runner provisioning,
   `Service Unavailable`/network errors resolving actions, a flaky step
   unrelated to this diff — not a real test/lint/type failure), rerun
   the failed jobs (`gh run rerun <run-id> --failed`) and re-poll. Retry
   up to 5 times; if it's still failing after that, stop and surface it
   to the user rather than silently retrying forever.
4. If the failure reflects the actual change (a real test/lint/build
   failure), fix it like any other bug per the Recommendation Assessment
   mandate below, push the fix, and re-verify CI from a clean state —
   don't rerun a failing job hoping it passes the second time.
5. A merge to `main` is not finished until `main`'s own resulting CI run
   (the run the merge commit itself triggers, not just the PR's
   pre-merge run) is confirmed green — a PR's checks passing before
   merge doesn't guarantee the post-merge run on `main` will, and only
   the post-merge run reflects what's actually deployed/tagged from.

#### Publish authority

`touch .agentharness-publish-mode` at this repo's root grants standing
push/PR/auto-implement authority for every session that reads this file,
until the flag is removed. It's gitignored (never committed) because
it's a per-operator/per-machine authorization, not a repo-wide policy —
see `docs/DECISIONS.md` for why this replaced the old always-on default,
and `docs/INTEGRATION.md` for how to create/remove it.

### 🔍 Agent Recommendation Assessment

**When an agent is asked to address/review/look into recommendations:**

1. **Assess each item** — evaluate positive vs. negative impact (complexity, effort, risk, benefit)
2. **Scoped, low-risk fixes** — a bug fix, a correctness/security fix with one
   clear resolution, closing a gap in something already built:
   - ✅ Implement directly, regardless of effort — don't ask permission to
     *fix* it. Whether the fix gets **published** still follows the
     Agent Workflow Completion default above (verify + stage, or full
     publish if authorized).
3. **Anything larger** — a new subsystem, a product-direction decision
   (target users, supported clients, distribution model), an architecture
   change, or a recommendation batch that amounts to a roadmap rather than
   a fix:
   - 🛑 **Present a scoped summary and get explicit confirmation on scope
     before implementing.** A review file recommending something is not
     the same as the user authorizing a multi-session build-out. Once
     scope is confirmed, that confirmation covers the agreed batch — don't
     re-ask item-by-item within it, but do re-check before expanding past
     what was agreed.
4. **If potential outcome is NEGATIVE or HIGH-RISK regardless of size:**
   - 🚨 **Escalate to user immediately** — do not implement
   - Include: specific concern, risk analysis, request guidance
5. **Report status in `<recommendations>-status.md`** with:
   - Timestamp (ISO 8601: `2026-07-11T14:30:00Z`)
   - Summary of what was implemented (and, for a confirmed larger batch,
     what scope was agreed)
   - Rationale for positive/negative aspects of each recommendation
   - Link to PR(s)

**This applies to:**
- Recommendations from reviews, audits, or assessments
- All work on this repository (agentharness)
- All harnesses and projects consuming this harness

**Rationale:** Recommendations only improve systems when they're acted on
deliberately. Complexity is not a reason to decline a scoped fix — but
silently treating an unbounded backlog as blanket authorization turns
"assess recommendations" into unrequested product decisions the user
never actually signed off on. The same logic applies one level up: a
mandate that grants an agent standing remote-write authority by default
is itself a product-direction decision the user should make explicitly,
not inherit silently from a template — see "Publish authority" above.

---

### What This Repo Is

A single source of truth for git conventions, coding guidelines, testing
standards, and (eventually) on-demand skills, so they're written once and
referenced everywhere instead of drifting across projects. Full rationale:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Where To Look

| Need | Read |
|---|---|
| Full asset index | [MANIFEST.md](MANIFEST.md) |
| Git workflow (branches, commits, secrets) | `.github/BRANCHING_STRATEGY.md`, `.github/COMMITTING_GUIDELINES.md` |
| Coding standards + rigor tiers | `.github/CODING_GUIDELINES.md` |
| Testing (TDD, coverage, Playwright) | `patterns/testing/` |
| Logging | `patterns/logging/` |
| Python conventions | `languages/python/` |
| Integrating this repo into a project | `docs/INTEGRATION.md`, or just run `tools/setup/harness-link.sh` |
| What's planned but not built | [ROADMAP.md](ROADMAP.md) |

### Rules That Apply Regardless of What You're Working On

- **Rigor tiers.** Not all mandates apply to all code — see
  `.github/CODING_GUIDELINES.md#rigor-tiers` before assuming 80% coverage
  or full Playwright suites apply to a prototype or one-off script.
- **One source of truth per rule.** If you find the same number/rule
  stated differently in two files, that's a bug — fix the duplicate, don't
  add a third version.
- **`.env.sample` not `.env.example`.** Never hardcode secrets; always
  provide a sanitized sample file.
- **Never commit to `main` directly.** Branch protection enforces this for
  everyone except repo admins; agents should never rely on the admin
  bypass.

### Operational Documents

Temporary/working docs (research notes, agent logs, planning) go in
`docs/operational/`, tracked in git like everything else. See
`docs/operational/README.md` for the promote/archive/delete workflow.

---

## Skills (always included — see note above)

### Skill: agentic-loops

## Agentic Loops: Agents, Tools, Workflows

Structured patterns for building multi-turn agents that reason, act, and observe.

An **agentic loop** is:
1. **Think**: Agent reasons about task → decides action
2. **Act**: Call tools / take action
3. **Observe**: Get result, update state
4. **Repeat**: Loop until task complete

### Minimal Loop — use the tested implementation, don't hand-roll this

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

### Tool Definition

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

### Patterns

#### Pattern 1: Reflection
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

#### Pattern 2: Tool Chaining
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

#### Pattern 3: Branching
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

#### Pattern 4: Multi-Agent Consensus
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

### Common Pitfalls

| Pitfall | Cause | Fix |
|---------|-------|-----|
| Infinite loops | Agent repeats same action | Add iteration limit |
| Token explosion | Long message history | Summarize old messages |
| Tool errors ignored | No error handling | Catch exceptions, feed back to agent |
| No observability | Can't debug | Log every action, decision, tool call |
| Silent failures | Errors don't propagate | Always return results to agent |

### Observability

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

### Checklist

- [ ] Define tools clearly (name, description, parameters)
- [ ] Add iteration limit (prevent infinite loops)
- [ ] Log every action, tool call, result
- [ ] Handle tool errors explicitly
- [ ] Feed errors back to agent (don't hide)
- [ ] Test with small iteration limits first
- [ ] Trace IDs for debugging
- [ ] Monitor token usage (watch for message explosion)

### References

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

### Skill: audit-review-followup

## Audit Review Follow-up

Assess whether a past review's recommendations were genuinely implemented — not
just marked done — and re-score the repo. **This is an assessment task: report
findings, do not fix anything unless asked.**

### The Prompt (canonical form)

> Check the review and its status report in `docs/operational/reviews/`, then
> verify what was *actually* implemented against the current repo state — do
> not trust the status report's checkmarks. Did it close all the gaps? What
> gaps did the status report itself miss? What would you add next? Re-score
> using the original review's dimensions.

### Procedure

#### 1. Locate the documents
- Reviews live in `docs/operational/reviews/` as `<name>-review.md` (findings +
  scored verdict) and `<name>-review-status.md` (per-item disposition).
- If several review cycles exist, use the frontmatter datestamps (required per
  `docs/operational/README.md`) to pick the cycle in question — usually the
  newest.

#### 2. Read both documents fully
Extract: the item list (usually a numbered backlog), the claimed status of each
item, and the original scoring rubric/dimensions.

#### 3. Verify claims — never trust checkmarks
For each item marked done, check the repo itself. Typical checks:
- **Files claimed created/deleted**: `ls`, `test -e`, read key sections.
- **CI claimed added/passing**: `gh run list` — confirm green on the default branch, not just "workflow file exists".
- **Repo settings claimed changed** (branch protection, rename, tags): `gh api`, `git remote -v`, `git tag`, `git config core.hooksPath`.
- **"Removed everywhere" claims** (a phrase, a bad pattern): `grep -rn` across the repo — the sweep that was run may have missed non-link prose.
- **Fixed scripts**: read the fix and, where cheap, execute it.

Spot-check breadth over depth: every category of claim, not every single item.

#### 4. Hunt the missed instances (the highest-value step)
Status reports fail in *classes*, not one-offs. When you find one leftover, ask
what verification method produced it and where else that method is blind.
Example: a markdown *link* checker validates `[text](path)` but not prose
asserting a file exists — so grep for the claim text, not just dead links.

#### 5. Classify every item

| Bucket | Meaning |
|---|---|
| ✅ Verified done | Claimed done, confirmed against repo state |
| ⚠️ Partial (admitted) | Status report itself flags it incomplete |
| ❌ Missed gap | Marked done but you found a surviving instance |
| ⏸ Deferred | Explicitly deferred — check it's recorded in `ROADMAP.md`, not only in the status report |

#### 6. Suggest additions
Ideas the review didn't cover, ranked by leverage-per-effort. Prefer
*self-verifying* fixes (a CI check that prevents the failure class) over
one-time cleanups.

#### 7. Re-score
Use the **same dimensions and scale as the original review** so scores are
comparable. Present a before/after table with a one-line rationale per
dimension, then an overall score and what separates it from the next tier.

### Output shape

1. **TL;DR first**: closed or not, count of missed gaps, new score.
2. Verified-implemented (with how you verified).
3. Gaps: admitted vs. newly found (file:line for each).
4. Suggested additions, ranked.
5. Score table (was → now → why).
6. Offer to fix — but don't fix unprompted.

### Rules

- New review/status documents you write must carry ISO 8601 datestamps in
  frontmatter (see `docs/operational/README.md`).
- If asked to *implement* the findings afterwards, the repo's
  recommendation-assessment mandate in `CLAUDE.md` takes over (implement
  net-positive items, escalate high-risk ones).

### Skill: branching

## Branching

Full reference: `.github/BRANCHING_STRATEGY.md` (worktree deep-dive,
`.gitignore` policy, lifecycle walkthrough). This skill is the actionable
summary.

### The core rule

**Never commit directly to `main`/`master`/`trunk`/`develop`/`production`/
`release/*`.** Always: branch → commit → push → PR → merge. This repo
enforces it locally via `git config core.hooksPath .github/hooks`
(already set here) — don't rely on the admin bypass.

### Branch naming

`{type}/{description}`, lowercase, hyphens not underscores, short and
specific.

| Type | Purpose |
|---|---|
| `feature/` | New feature or enhancement |
| `fix/` | Bug fix |
| `refactor/` | No behavior change |
| `test/` | Testing improvements |
| `docs/` | Documentation only |
| `chore/` | Maintenance, deps, config |
| `perf/` | Performance improvement |
| `ci/` | CI/CD changes |

Good: `feature/user-authentication`, `fix/email-validation-crash`.
Bad: `update`, `Feature/UserAuth`, `fix_everything`.

### Worktrees

Use when you need two branches checked out simultaneously (comparing
versions, running tests on one branch while coding another). Skip for a
single quick edit. Keep them in `.worktrees/{branch-name}/`, one branch
per worktree directory, and `git worktree remove` when done.

### If a secret was committed

Act immediately — **rotate the secret regardless of whether history
cleanup succeeds**; treat anything that touched git history as
compromised.

1. Preferred: [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
   on a fresh mirror clone: `bfg --delete-files .env` then
   `git push --force`. See `.github/BRANCHING_STRATEGY.md` for the full
   command sequence.
2. Fallback: `git filter-repo --path .env --invert-paths` (the modern,
   maintained replacement for `filter-branch`).
3. Rotate the secret. Tell everyone with a clone to re-clone, not pull.

### Skill: committing

## Committing

Full reference: `.github/COMMITTING_GUIDELINES.md` (examples, git aliases,
commit template). This skill is the actionable summary.

### Before you commit

1. `git status` and `git diff` — know exactly what you're about to commit.
2. Stage specific files, not `git add .` / `git add -A` blind.
3. `git diff --cached` — review staged content one more time, scan for
   secrets (API keys, tokens, passwords).
4. Let hooks run. Never `--no-verify`, never `--no-gpg-sign`. If a hook
   fails, fix the underlying issue and re-stage — don't bypass it.

### Writing the commit

- **Atomic**: one logical change per commit. Don't mix a feature, a fix,
  and a refactor in one commit.
- **Message explains WHY, not WHAT** — the diff already shows what
  changed.
- Imperative mood summary ("Add X", not "Added X"), ideally under ~50
  chars, blank line, then body wrapped at ~72 chars if more explanation
  is needed.
- Reference issues (`Fixes #123`, `Relates to #456`) when applicable.

### What never gets committed

- Secrets: API keys, tokens, passwords, private credentials.
- `.env` and its variants — but DO commit `.env.sample` (sanitized
  template).
- Debug code: stray `console.log`/`print`, commented-out code, debugger
  statements.
- Build artifacts, `node_modules/`, and anything covered by
  `.github/.gitignore.template`.

### After the commit — mandatory for agents

This harness's `CLAUDE.md` mandates the full workflow: commit → push →
PR. Don't stop at the commit.

1. `git push -u origin <branch>` (first push) or `git push` (subsequent).
2. `gh pr create` with a real title, body, and test/verification notes.
3. Work is not "done" until the PR exists and its link has been given to
   the user. An agent claiming completion without a PR is incomplete —
   see `CLAUDE.md`'s "Agent Workflow Completion" section.

### If tests or hooks fail

Fix the underlying issue (lint error, failing test, secret detected).
Don't commit broken code planning to fix it "in the next commit."

### Skill: error-handling

## Error Handling & Recovery

Structured approaches to errors, recovery, and observability. **Never silently hide errors.**

### Core Patterns

#### 1. Explicit Errors (Always)
Return errors as values or raise them; never ignore them.

```python
# ✅ Good: Explicit handling
try:
    user = parse_user_data(raw)
except json.JSONDecodeError as e:
    # Never log the raw payload — it can carry passwords/PII. Log a
    # bounded, redaction-safe summary instead.
    logger.error("Invalid user JSON", extra={"error": str(e), "payload_length": len(raw)})
    return None

# ❌ Bad: Silent failure
try:
    parse_user_data(raw)
except:
    pass  # User data silently ignored
```

#### 2. Error Wrapping (Across Boundaries)
Add context as errors propagate—original error + where + why.

```python
# ✅ Python: Preserve cause
try:
    return repository.find(user_id)
except DatabaseError as e:
    raise UserNotFoundError(f"find user {user_id}") from e

# ✅ Go: Wrap with context
user, err := repo.Find(userID)
if err != nil {
    return nil, fmt.Errorf("find user %s: %w", userID, err)
}
```

#### 3. Error Classification
Decide recovery strategy based on error type.

```python
def classify_error(error):
    if isinstance(error, (ConnectionError, TimeoutError)):
        return "transient"  # Retry
    elif isinstance(error, (ValueError, KeyError)):
        return "validation"  # Reject, don't retry
    else:
        return "unknown"

# Transient → retry with backoff
# Validation → log and fail
# Fatal → panic
```

#### 4. Retry with Backoff (for Transient Errors)
Retry flaky operations; don't retry permanent failures.

```python
import time

def retry(func, max_attempts=3, backoff_base=2):
    """Retry with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return func()
        except (ConnectionError, TimeoutError) as e:
            if attempt < max_attempts - 1:
                wait_time = backoff_base ** attempt
                logger.warning(f"Retry {attempt + 1}/{max_attempts}, waiting {wait_time}s")
                time.sleep(wait_time)
            else:
                raise
        except (ValueError, KeyError):
            raise  # Don't retry validation errors

# Usage
user = retry(lambda: fetch_user(user_id), max_attempts=3)
```

#### 5. Circuit Breaker (for Cascading Failures)
Fail fast when a service is down; stop hammering it.

```python
class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = timeout
        self.state = self.CLOSED
        self.last_failure = None

    def call(self, func, *args, **kwargs):
        if self.state == self.OPEN:
            if time.time() - self.last_failure > self.timeout:
                self.state = self.HALF_OPEN
            else:
                raise RuntimeError("Circuit is OPEN")

        try:
            result = func(*args, **kwargs)
            self.failures = 0  # Success: reset
            self.state = self.CLOSED
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.threshold:
                self.state = self.OPEN
            raise
```

#### 6. Fallback (Default When Primary Fails)
Provide sensible default when operation fails.

```python
def get_user_with_fallback(user_id):
    """Try cache → database → guest fallback."""
    try:
        return cache.get(user_id)
    except CacheError:
        pass

    try:
        user = database.find(user_id)
        cache.set(user_id, user)  # Warm cache
        return user
    except DatabaseError as e:
        logger.error("Database down", extra={"error": str(e)})
        return User.guest()  # Fallback
```

#### 7. Structured Error Logging (Always)
Log errors with full context, not just the message.

```python
# ❌ Bad: Lost context
logger.error(str(error))

# ✅ Good: Full context
logger.error("Failed to fetch user", extra={
    "user_id": user_id,
    "operation": "fetch",
    "error_type": type(error).__name__,
    "error_message": str(error),
    "retry_count": attempt,
})
```

### Decision Tree

```
Error occurs
├─ Catch it?
│  ├─ Yes → Can recover?
│  │        ├─ Yes → Transient? (network, timeout, rate limit)
│  │        │        ├─ Yes → Retry with backoff + circuit breaker
│  │        │        └─ No → Fallback or fail fast
│  │        └─ No → Log + re-raise
│  └─ No → Let it propagate up
└─ Always wrap with context (where + why)
```

### Common Mistakes

| Mistake | Fix |
|---------|-----|
| Catching `Exception` broadly | Catch specific errors you can handle |
| Ignoring errors silently | Log errors with full context |
| No backoff on retry | Exponential backoff: 1s, 2s, 4s, 8s… |
| Retrying permanent errors | Classify errors first; don't retry 404, 401 |
| Lost error chain | Preserve cause: `from e` (Python), `%w` (Go) |

### References

This file is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout, not just this skill):
- Full guide: `patterns/error-handling/README.md`
- Logging: `patterns/logging/LOGGING_STANDARDS.md`

### Skill: python-conventions

## Python Conventions

This file is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout, not just this skill — these aren't bundled
here since they're documentation, not something this skill runs):
`languages/python/CONVENTIONS.md` (complete examples) and
`languages/python/COPILOT_INSTRUCTIONS.md` (general agent operating
principles for Python repos — inspect before changing, scope discipline,
never claim a command passed without running it).

### Naming

- `snake_case` — functions, variables. `PascalCase` — classes.
  `UPPER_SNAKE_CASE` — module-level constants.
- Single underscore prefix for private (`_internal`); avoid double
  underscore except for genuine name-mangling needs.
- Exceptions: `PascalCase` + `Error`/`Exception` suffix, specific not
  generic (`ValidationError`, not `BadThing`).

### Imports & structure

Standard library → third-party → local, each group separated by a blank
line. Absolute imports over relative. No `from module import *`.

### Type hints

Use them on function parameters and returns. Match syntax to the
project's minimum Python version — check `requires-python` in
`pyproject.toml` before using `list[str]` (3.9+), `X | None` (3.10+), or
`match/case` (3.10+). Don't silently raise the minimum version.

### Pitfalls to catch in review

```python
# Mutable default argument — persists across calls, shared state bug
def f(item, container=[]):  # WRONG
def f(item, container=None):  # RIGHT — default to None, create inside

# Bare/broad except — swallows KeyboardInterrupt, hides real errors
except:  # WRONG
except Exception:  # still too broad, usually
except ValueError as e:  # RIGHT — catch what you expect

# `is` for value comparison — checks identity, not equality
if user_id is 5:  # WRONG
if user_id == 5:  # RIGHT (== for values, `is` only for None/True/False)
```

### Testing

`tests/` directory, `test_*.py` files, `test_*` functions, pytest
fixtures for setup. See `patterns/testing/TDD.md` for the broader
methodology — this skill covers Python-specific structure only.

### Formatting & tooling

Defer to the project's `pyproject.toml` — don't impose Black/Ruff
defaults over an existing configured formatter/linter. If unconfigured:
Black or `ruff format` (88-char lines), `ruff check`, `mypy` for typing,
`pytest` for tests.
