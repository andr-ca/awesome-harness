# Gemini Review - 2026-07-13

## 1. Idea
The concept of `agentharness` is brilliant and addresses a very real pain point: the drift of LLM coding conventions (like `CLAUDE.md`, testing standards, and git hooks) across multiple projects. By extracting these rules into a centralized, referenceable, and version-controlled repository, it establishes a single source of truth for coding agents. It shifts agent instructions from ad-hoc, project-local files to shared engineering policies.

## 2. Documentation
The documentation is phenomenal. The separation of concerns between `MANIFEST.md` (what exists), `ROADMAP.md` (what is planned), `STATUS.md` (what works today), and `KNOWN_LIMITATIONS.md` (known gaps) is incredibly disciplined. 
- The product contract is clearly stated.
- `ARCHITECTURE.md` perfectly outlines the layered design.
- The use of `CLIENT_COMPATIBILITY.md` brings transparency regarding what has been dogfooded versus what is just passively covered. 
There is very little ambiguity about the state of the repository.

## 3. Implementation
The implementation is solid and heavily relies on bash scripts (`harness-link.sh`), bats testing, and Python for content verification (`verify-content-quality.py`).
- **Strengths:** The lifecycle CLI (`init`, `status`, `update`, `uninstall`) supports multiple modes (link, copy, submodule, npm). The repo leverages GitHub hooks (`pre-push`, `prevent-trunk-commit`) effectively. Client generation scripts for non-Claude platforms are already scaffolded out.
- **Weaknesses/Gaps:** Profile enforcement (`enforce-profile`) is fragmented (supports Python, Go, Node test, but misses Jest/Mocha) and is not automatically wired into git hooks. Additionally, client adapter generations (e.g., Gemini, Copilot, Cursor) are manually generated rather than seamlessly integrated into the `init` lifecycle.

## 4. Overall Usefulness
Highly useful for organizations or individuals running multiple projects with AI agents. It acts as an orchestrator of engineering standards. Its current usefulness peaks for Claude Code users (since it's dogfooded there), but it promises massive utility for users of other agents (Codex, Gemini, Cursor) once real-world dogfooding and lifecycle wiring are completed.

## 5. Actionable Feedback & Next Steps
Here is an itemized list of what can be improved:

1. **Dogfooding Across Other Platforms:** Run live sessions with Gemini CLI, GitHub Copilot, and Cursor to validate the generated adapters (`GEMINI.md`, `.cursor/rules/`, etc.). Currently, this is listed as a known limitation; live testing is required to verify actual agent adherence.
2. **Wire Client Generation into Lifecycle:** Integrate the `harness-link.sh generate-clients` command directly into `init` and `update` commands. Track these generated files in `.agentharness-state.json` via managed blocks to allow for clean `uninstall` and `update` without overwriting user customizations.
3. **Automate Profile Enforcement:** Wire `enforce-profile` into the `.github/hooks/pre-push` hook so that test coverage rules (e.g., Python's 80% coverage) are physically enforced during git pushes, rather than requiring manual invocation.
4. **Expand JS/TS Runner Support:** Add support for Jest and Mocha to `enforce-profile` so that a broader range of JS/TS projects can benefit from the rigor tiers.
5. **Decouple Package Materialization from Git:** Update `materialize-skill-symlinks.py restore` to use an on-disk backup instead of `git checkout`. This will prevent failures in restricted or non-Git source packages (e.g., npm tarball deployments).
6. **Implement State Migration Contract:** Add forward-migration logic for `.agentharness-state.json` to ensure seamless upgrades (e.g., from v1 to v2) without bricking existing consumer integrations.
7. **Instruction-Quality Evals:** Advance the `tools/eval/` suite to measure policy adherence (e.g., does the agent actually respect the `prevent-trunk-commit` rule?) instead of just deterministic code correctness.
8. **Expand Framework & Language Content:** Begin fleshing out the missing `frameworks/` (Vue, Angular, Django) and `languages/` (Java) to increase the harness's addressable market.
