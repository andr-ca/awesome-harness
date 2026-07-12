# agentharness repository review and improvement plan

**Reviewer:** GPT-5.6 · **Date:** 2026-07-11 · **Scope:** idea, positioning, documentation, implementation, tests, safety, maintainability, distribution, and practical usefulness

- **Reviewed:** 2026-07-11 (America/Toronto)
- **Snapshot:** `b4622da` on `chore/add-remaining-components`
- **Remote status at review time:** [PR #4](https://github.com/andr-ca/agentharness/pull/4) open; `shellcheck` and `hook-tests` failing; `markdown-links` and `manifest-verify` passing

> Filed by Claude (Fable 5) on 2026-07-12 from an untracked working file
> (`docs/gpt-5.6-sol.md`) into the operational-docs convention. The current
> implementation was independently validated in
> [`gpt-5.6-review-status.md`](gpt-5.6-review-status.md).

## Executive verdict

The core idea is good: a versioned, reusable set of coding-agent policies, skills, conventions, and workflow helpers can reduce instruction drift across repositories. The repository also has several good primitives already: a lean agent router, on-demand Claude Code skills, rigor tiers, an integration guide, a manifest/roadmap split, CI structure, and a permissive license.

The current repository is nevertheless an **internal alpha, not a reliable reusable harness**. It is useful today as Andrey's opinionated reference library, but the installation path, enforcement claims, runnable examples, and release signals are not dependable enough for team or production adoption. The highest-risk problem is trust: the project tells agents and users that policies are installed and verified when several of those paths are currently inert or failing.

**Recommendation:** continue the project, but pause breadth expansion and stabilize the product contract, installer, examples, and verification layer before adding more languages, frameworks, or patterns.

### Directional scorecard

These scores are diagnostic, not scientific.

| Dimension | Score | Assessment |
|---|---:|---|
| Problem / idea | 8/10 | Real pain point; centralized, versioned agent guidance is valuable |
| Product focus / differentiation | 5/10 | Useful concept, but currently split between policy library, installer, and agent-runtime guidance |
| Documentation readability | 7/10 | Generally clear, navigable, and concrete |
| Documentation correctness | 4/10 | Inventory, commands, policies, and examples have material drift |
| Implementation quality | 3/10 | Small readable scripts, but critical integration paths are broken |
| Tests and CI | 3/10 | Good job structure; current PR is red and important behavior is not tested |
| Safety and trust model | 3/10 | Remote-write mandates and mutable instruction delivery are unsafe defaults |
| Usefulness today | 5/10 | Helpful personal playbook; unreliable as a portable team harness |
| Release readiness | 2/10 | No-go until the P0 items below are resolved |
| **Overall** | **4.5/10** | **Strong concept, uneven alpha implementation** |

## Current status

At the reviewed snapshot:

- The worktree and pushed feature branch were aligned at `b4622da` and clean.
- `main` was at `61b60b0`.
- The repository contained 57 tracked files and roughly 13.3k lines, including 43 Markdown files and five Claude Code skills.
- Ten commits existed after the `v0.1.0` tag without an `Unreleased` changelog section.
- The branch grew repeatedly during this audit: logging code, TypeScript/Go guides, two pattern guides, and two skills were added in quick succession. That pace explains some drift, but it also shows that breadth is outpacing validation.
- PR #4's hosted CI confirmed the local audit: six of seven harness-link Bats tests failed, and ShellCheck failed on `tools/verify-manifest.sh`.

### Readiness by surface

| Surface | Status | Why |
|---|---|---|
| Personal reference library | Usable with caution | Several guides are helpful, but examples and universal mandates need judgment |
| Claude Code skill collection | Alpha | Valid skill layout, but installed skills contain unresolved harness-root references and unsafe defaults |
| Setup / integration tool | Pre-alpha | Test suite and hook installation are broken; no rollback, state, or uninstall |
| Team policy distribution | Not ready | Mutable absolute symlinks, no pinning/override model, and over-authorizing instructions |
| Logging utility | Not ready | Shipped example cannot load or configure Python logging as documented |
| Agentic-loop guidance | Not ready | "Production" sample is non-runnable and references a deprecated OpenAI API |
| Stable public release | No-go | Red CI, false enforcement claims, stale inventory, and no proven consumer fixture |

## What is already good

1. **The problem statement is concise and credible.** `README.md:3-12` explains the cost of duplicated agent instructions without fabricated impact claims.
2. **The target architecture has the right broad layers.** Universal rules, patterns, languages, frameworks, and project overrides are a sensible mental model.
3. **The router-plus-skills direction is correct.** Keeping `CLAUDE.md` relatively short and loading specialized guidance on demand is better than injecting thousands of tokens into every session.
4. **Rigor tiers are a valuable correction.** Prototype, internal-tool, and production expectations should differ; `.github/CODING_GUIDELINES.md:10-30` establishes the right concept.
5. **The integration guide explains trade-offs.** The symlink, copy, and submodule comparison is helpful even though several commands need repair.
6. **The hook logic itself is reasonable when installed under the correct filename.** Directly installing it as `pre-commit` correctly blocks an unborn `main` commit.
7. **The scripts are small and readable.** `tools/setup/harness-link.sh` uses strict Bash mode, quotes paths, and avoids overwriting non-symlink skill directories.
8. **The project has healthy transparency primitives.** MIT license, changelog, roadmap, historical review, PR template, CODEOWNERS, and separated CI jobs are a good base.
9. **The prior Fable review produced real improvements.** Phantom inventory, fabricated metrics, the oversized router, and several broken snippets were addressed. The right next step is preventing regressions, not another breadth push.

## Release-blocking findings

### 1. PR #4 is red, and the new integration tests test a different program

`tools/tests/harness-link.bats` hard-codes `/home/andrey/projects/awesome-harness` at every invocation. GitHub runners do not have that path, so hosted CI cannot execute the script. The remote `hook-tests` job reported six failures out of seven.

Even after fixing the path, three core assertions contradict `tools/setup/harness-link.sh`:

- `tools/tests/harness-link.bats:28-34` expects `.claude/skills` itself to be a symlink; the script creates a real directory containing one symlink per skill (`tools/setup/harness-link.sh:91-119`).
- `tools/tests/harness-link.bats:37-43` expects `.github/hooks` to be a symlink; the script never creates it.
- `tools/tests/harness-link.bats:59-65` expects a configured hook after calling the installer without `--with-hook` and before initializing Git.
- The help test at line 19 uses `command || true | grep`, so a successful command bypasses the intended output assertion.
- The idempotency test contains `... || true`, allowing the behavior assertion to be skipped.

The ShellCheck job also fails because `tools/verify-manifest.sh` triggers SC2016 in six places. Some single quotes are intentional, but CI still treats the findings as failures; the code or a narrowly justified suppression must make that explicit.

**Impact:** the branch cannot merge under its own quality policy, and the new test suite creates false confidence locally because its expectations were not derived from the implementation contract.

### 2. The advertised trunk-protection installation does not install a Git hook

`MANIFEST.md:19`, `docs/INTEGRATION.md:109-123`, `.claude/skills/branching/SKILL.md:17-20`, and `tools/setup/harness-link.sh:157-160` configure:

```bash
git config core.hooksPath .github/hooks
```

Git looks for a hook named `pre-commit` inside that directory. The repository contains `.github/hooks/prevent-trunk-commit`, so nothing runs.

Fresh temporary-repository checks produced:

- Documented `core.hooksPath` + commit on `main`: exit `0`; commit created.
- `harness-link.sh <repo> --with-hook` + commit on `main`: exit `0`; commit created.
- Copying the same script to `.git/hooks/pre-commit`: exit `1`; commit correctly blocked.

The installer also overwrites an existing `core.hooksPath`, which can silently disable Husky, pre-commit, Lefthook, or a consumer's custom hooks.

**Impact:** the strongest enforcement claim in the project is false, including in this repository's own checkout.

### 3. Agent instructions grant themselves authority the user may not have given

`CLAUDE.md:7-17`, `.github/COMMITTING_GUIDELINES.md:12-28`, and the committing skill require every agent task to end with commit, push, and PR creation. `CLAUDE.md:19-45` goes further: when asked to review or look into recommendations, an agent must implement every recommendation it considers net-positive, regardless of effort.

This conflates four distinct permissions:

1. inspect and report;
2. edit local files;
3. create commits;
4. write to a remote service or contact other people through a PR.

A review request is not authorization for implementation, and a local edit is not authorization for publication. These rules will fail in forks, offline environments, read-only tasks, dirty worktrees, repos without `gh`, and organizations with different merge policies. More importantly, they can cause scope expansion and external changes the user never requested.

**Impact:** this is a trust and adoption blocker for any reusable agent harness.

### 4. The logging feature is not runnable as shipped

The repository calls `patterns/logging/logging.yaml.example` ready to copy and documents two Python quick starts. Neither works.

Observed behavior:

- Loading the default file through `patterns/logging/config_loader.py` exits `1` on missing `GCP_PROJECT_ID`, even though the cloud backend defaults to disabled.
- Interpolation happens after YAML parsing, so defaults such as `false`, `true`, `4317`, and `0.1` become strings rather than booleans or numbers.
- The regular expression stops at the first `}`, turning `${LOG_FILENAME:-app-{date}.log}` into `app-{date.log}`.
- `logging.config.dictConfig(config["logging"])` raises `ValueError: dictionary doesn't specify a version`; the custom YAML schema is not a Python `dictConfig` schema.
- `patterns/logging/README.md:96-108` skips interpolation entirely and also passes the custom schema to `dictConfig`.
- `--show-env-vars` prints resolved environment-variable values and the CLI prints the fully resolved config. Tokens and credentials referenced by the template can therefore be exposed in terminal output or logs.
- The 17 unit tests pass, but none loads the repository's real example or follows the documented `dictConfig` path.
- Python dependencies (`PyYAML`, `pytest`, and typing stubs) are not declared, and CI does not run the Python tests.

**Impact:** a centerpiece example is both unusable and capable of disclosing secrets.

### 5. The manifest and inventory checks provide false assurance

`MANIFEST.md:3-5` claims to index every real asset, and the README tells users to trust it over prose. At the snapshot, 19 of 57 tracked files were absent from its path cells, including the CI workflow, both Bats suites, `tools/verify-manifest.sh`, `LICENSE`, and most component READMEs.

The verifier is one-directional: it checks whether selected manifest paths exist but never detects unlisted tracked assets. It also has parsing false negatives:

- top-level paths without `/` are skipped;
- `grep -v 'Asset\|Path\|Type'` drops valid rows containing text such as `hooksPath` or `TypeScript`;
- the printed check and final count use different pipelines;
- dead `found`/`missing` counters run in a subshell and are never used.

Controlled checks removed one file at a time from a temporary archive:

| Removed manifest entry | Verifier result |
|---|---|
| `README.md` | exit `0`, "All manifest entries exist" |
| `.github/hooks/prevent-trunk-commit` | exit `0`, "All manifest entries exist" |
| `languages/typescript/CONVENTIONS.md` | exit `0`, "All manifest entries exist" |
| `patterns/logging/config_loader.py` | exit `1`, correctly detected |

The manifest itself also has a malformed table row at `MANIFEST.md:59` with no closing pipe.

**Impact:** a green `manifest-verify` check currently proves much less than its name and documentation imply.

### 6. "Working" and "production" examples contain immediate failures

The new content violates the repository's own rule that additions include real runnable examples (`README.md:75`). Examples include:

- `patterns/agentic-loops/README.md:34-38` writes `last_result` and returns nonexistent `state["result"]`.
- The "Production Loop" omits `Callable`, requires `messages`, and constructs `AgentState(task=task)` without it (`:46-71`). It never puts the task into model input.
- Reflection code accesses an uninitialized iteration field (`:238-258`).
- Tool outputs are represented as user messages rather than provider-specific tool results, tool arguments are not schema-validated, and no call ID is preserved.
- The further-reading section points to the deprecated OpenAI Assistants API. OpenAI recommends the Responses API and has scheduled the Assistants API sunset for August 26, 2026; use the official [Responses migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses).
- `patterns/error-handling/README.md:137-156` uses `backoff_base ** attempt` with a default base of `1.0`, producing a constant delay; `max_attempts=0` eventually attempts to raise `None`.
- Error classification later passes a string to a retry function that expects a callable and uses bare `raise` outside an active exception (`patterns/error-handling/README.md:284-309`).
- The error-handling examples log rejected raw JSON, contradicting the repository's own sensitive-data rules.

**Impact:** agents are likely to reproduce invalid or unsafe patterns precisely because the files present them as canonical.

### 7. The security model ignores the highest-impact asset: instructions

`SECURITY.md:3-6` says there is no attack surface beyond a script being wrong. In an agent harness, Markdown instructions and skills are effectively executable policy: a malicious or accidental instruction can cause commands, file reads, remote writes, or secret exposure.

The recommended symlink mode automatically changes every consuming project when the harness checkout changes. That is convenient for one person's local projects, but it is an instruction-supply-chain risk for teams and production repositories. No signature, reviewed pin, compatibility contract, or update approval is required.

The new agentic skill also demonstrates unrestricted file reads and tool execution without approvals, sandbox boundaries, prompt-injection handling, budgets, cancellation, or idempotency guidance.

**Impact:** the project understates its real threat model and recommends its least stable update mode as the default.

## Detailed review

### Idea and positioning

The strongest version of this project is not "a big folder of best-practice Markdown." It is a **portable, versioned engineering-policy kit for coding agents**, with explicit profiles, safe installation, drift detection, and tested client adapters.

Today the actual user is narrower than the name and architecture suggest: a Claude Code user managing several Python, TypeScript, or Go repositories. There are no implemented framework packs, no Codex adapter, no stable cross-agent contract, and no portable team install.

The repository also mixes three products:

- a reference library of engineering opinions;
- a policy installer/enforcer;
- a guide to building agent runtimes.

Those can coexist, but one must be primary. The recommended primary job is: **select a profile, install a small set of versioned agent policies, and audit whether a project still conforms.** Language and runtime guides should support that job rather than dominate it.

A current direct benchmark, [netresearch/agent-harness-skill](https://github.com/netresearch/agent-harness-skill), already emphasizes verify-first behavior, bootstrap/audit modes, maturity levels, CI enforcement, and portable installation. agentharness should not copy it blindly, but it needs a sharper differentiator: cross-agent policy profiles plus evidence that those profiles improve coding-agent outcomes.

The name `agentharness` is better than `awesome-harness`, but "agent harness" can also imply an execution or evaluation runtime. A clear subtitle such as **"portable engineering policies for coding agents"** is more important than another rename.

### Documentation and onboarding

The prose is usually readable, but correctness and source-of-truth discipline are not yet strong enough:

- README still shows only Python, three skills, and testing/logging; the tree now contains TypeScript, Go, five skills, error handling, and agentic loops.
- ROADMAP still lists TypeScript, Go, agentic loops, error handling, Dependabot, and CODEOWNERS as unbuilt.
- `docs/README.md`, `.github/README.md`, `.claude/README.md`, and the category READMEs are similarly stale.
- `CHANGELOG.md` has no `Unreleased` section despite ten post-tag commits.
- The operational index still describes the logging loader as pending even though the branch calls it implemented.

Several onboarding commands are wrong:

- The quoted heredoc at `docs/INTEGRATION.md:48-53` writes the literal text `$(git -C ~/agentharness rev-parse --short HEAD)` instead of a revision.
- The fresh submodule path does not create `.claude/` before linking `.claude/skills` (`:61-65`).
- Copy commands assume `docs/` and `config/` exist (`:101-104`).
- The guide claims every command is tested (`:4-5`), which is false.
- Skill discovery is documented through `/help`; current Claude Code documentation exposes `/skills` and recommends `${CLAUDE_SKILL_DIR}` for bundled resources. See the official [Claude Code skills documentation](https://code.claude.com/docs/en/slash-commands).
- `.github/pull_request_template.md:38` resolves links through `.github/.github/...`.
- `.github/README.md:114-115` uses owner `andrey` instead of `andr-ca` and omits `/blob/main/`.
- Hook docs use obsolete Husky setup commands and claim automatic teammate setup without adding the required package script.
- The root README gives only an SSH clone command, no prerequisites, no supported platforms, no preview of modified files, and no uninstall instructions.

The documentation corpus is also too repetitive. Roughly 11.8k of 13.3k tracked lines are Markdown. Testing and logging requirements are restated across routers, README files, policies, checklists, guides, and skills. This makes drift inevitable and consumes agent context when skills load. The repository should own decisions and runnable examples; stable language/framework facts should often link to authoritative upstream documentation.

### Policy consistency

Rigor tiers are intended to be the single applicability policy, but component guides still use universal language:

- `patterns/testing/TDD.md:15-17` says 80% is mandatory for all code.
- `patterns/testing/README.md` repeats universal TDD, coverage, edge-case, and inherited-failure mandates.
- `patterns/testing/COVERAGE_REQUIREMENTS.md` includes all utilities and agents.
- `patterns/logging/README.md:3-55` mandates a full multi-backend logging stack for all code.

Other rules are too absolute for reuse:

- "Fix inherited failures" conflicts with narrow task scope and can turn a small change into unrelated repair work.
- "No skipped tests" ignores legitimate platform- or capability-conditioned tests.
- A fixed 80% repository-wide coverage threshold is a management choice, not a universal engineering truth. Risk, mutation score, critical-path behavior, and changed-line coverage may be more informative.
- Every production UI test requiring a screenshot is slow and brittle; visual snapshots should cover selected stable surfaces, while behavior, accessibility, and responsive checks use the most appropriate test layer.
- Requiring file, console, cloud, and OTEL backends for every production service is excessive and may increase cost, privacy risk, and operational complexity.
- Global UI title-casing rules and global function-style preferences should defer to the product's design system and formatter.

The correct precedence model should be explicit:

1. current user request and safety constraints;
2. consuming repository's local rules;
3. selected agentharness profile;
4. language/framework add-ons;
5. generic defaults.

Projects also need a documented way to override or disable individual policies without forking the whole harness.

### Installer and distribution

`tools/setup/harness-link.sh` is a useful prototype, but it is not yet a product installer:

- Absolute symlinks break when the harness moves and are unsuitable for teammates or CI with different paths.
- The installer does not record the harness version, selected skills, or integration mode.
- There is no `--dry-run`, status/doctor, update, rollback, or uninstall path.
- It silently skips unknown skills and returns success.
- `--skills` accepts traversal such as `../../patterns`, allowing a destination outside `.claude/skills` and a source outside the skill directory.
- A Git worktree has a `.git` file, not a directory, so the current `[ -d "$TARGET/.git" ]` test rejects valid worktrees.
- Hook installation can partially fail while the script still prints `Done.`.
- Merging a comprehensive multi-language `.gitignore` by sorting exact lines discards comments and can break order-sensitive negation rules.
- Installed skills reference harness-root files such as `.github/BRANCHING_STRATEGY.md` and `languages/python/CONVENTIONS.md`, but those paths are not installed into the consumer. Official Claude skills support `${CLAUDE_SKILL_DIR}`; references should be self-contained or resolve through an installed, versioned bundle.

Symlink mode should be described as **local, unpinned development mode**, not the default for teams. Copy or a pinned submodule/package should be the reproducible mode.

### CI, testing, and maintainability

The CI decomposition is a good start, but coverage is incomplete and supply-chain choices are weak:

- Python loader tests, lint, typing, coverage, and the actual sample integration are absent from CI.
- CI clones the latest Bats default branch, then runs its installer with `sudo`.
- GitHub Actions use mutable major tags and the workflow does not declare least-privilege `permissions: contents: read`.
- Dependabot configures `gomod` despite no `go.mod`, but there is no Python dependency manifest to update.
- There is no `git diff --check`, Markdown style/frontmatter validation, example-snippet validation, or action workflow lint.
- `git diff --check origin/main...HEAD` reports 79 trailing-whitespace defects across five newly added files.
- The logging loader's tests mutate `os.environ` directly and do not cover the shipped template, typed values, brace-containing defaults, CLI redaction, or schema integration.
- The manifest verifier itself has no tests.

The `v0.1.0` tag also predates later CI repairs, while current unreleased work adds substantial content. Releases should be cut from green `main`, with an explicit compatibility and migration policy.

### Content correctness

The content expansion needs a technical editing pass, not just copy editing.

**TypeScript guide**

- Calls underscore-prefixed private members "deprecated" (`languages/typescript/CONVENTIONS.md:82-85`), which is not a TypeScript deprecation.
- Uses `Map<string, any>` while the universal policy says to avoid `any` (`:91`).
- Treats `null` over `undefined` as a universal preference despite optional properties naturally producing `undefined` (`:268-288`).
- Claims a small regex follows RFC 5322 (`:323-332`), which it does not.
- Catches and logs asynchronous failures without rethrowing, potentially converting failure into apparent success (`:373-394`).
- Mixes framework-specific React policy into the language guide rather than a composable React add-on.

**Go guide**

- Marks `defaultTimeout` as wrong because it "should be camelCase," although it already is (`languages/go/CONVENTIONS.md:59-62`).
- Uses deprecated `ioutil.ReadFile` rather than `os.ReadFile` (`:246-255`).
- Defines methods on `*UserRepository` after presenting `UserRepository` as an interface (`:83-86`, `:132-139`, `:339`, `:364`); that example cannot compile.
- Uses rigid function-length limits and broad "avoid abbreviations" advice that conflict with idiomatic Go names.

**Error handling**

- Logs raw rejected input and user data.
- Retry examples omit jitter, deadlines, `Retry-After`, and idempotency guidance.
- The circuit breaker is labeled as a reusable pattern but is not concurrency-safe and treats every exception as a downstream service failure.
- Cache fallback treats cache miss as an exception and can return `None` as a successful cached value.
- Guide and skill duplicate large blocks, ensuring future drift.

**Agentic loops**

- "Production" examples are pseudocode with missing imports/state.
- No model/provider adapter, JSON Schema validation, tool-call ID, or correct tool-result protocol is shown.
- No approval boundary, sandbox, cancellation, time/token/cost budget, retry/idempotency model, prompt-injection defense, untrusted-output handling, persistence/resume, or evaluation strategy is covered.
- Naive majority-vote "multi-agent consensus" can amplify correlated errors and should not be presented as validation.

Content should be version-scoped, source-backed, tested where runnable, and clearly labeled as policy, example, or pseudocode.

### Security

Immediate security issues:

- Remove or redact `patterns/logging/config_loader.py --show-env-vars`; never print resolved secret values.
- Do not dump fully resolved production configuration by default.
- Stop logging raw invalid JSON and raw tool errors/results without a redaction boundary.
- Validate `--skills` against a basename-safe grammar and confirm resolved source/destination containment.
- Preserve an existing hook manager instead of overwriting `core.hooksPath`.
- Pin reviewed installer and action revisions; do not execute an unpinned default branch with `sudo`.
- Add an instruction-supply-chain threat model and recommend pinned consumption for shared repositories.
- Add a private security contact if the project becomes publicly consumed; instruction poisoning can warrant coordinated disclosure even without a hosted service.

## Prioritized actionable backlog

### P0 — restore trust before merging or releasing

#### P0-01 — Make PR #4 green for the right reasons

**Files:** `tools/tests/harness-link.bats`, `tools/setup/harness-link.sh`, `tools/verify-manifest.sh`, `.github/workflows/ci.yml`

**Actions:**

- Derive `HARNESS_DIR` from `BATS_TEST_FILENAME`; remove every workstation path.
- Rewrite tests from the installer's documented contract, including filtered skills, existing files, unknown skills, idempotency, and error exits.
- Remove `|| true` from assertions.
- Resolve or narrowly document the ShellCheck SC2016 cases.
- Run Bats and ShellCheck locally and in hosted CI.

**Acceptance:** all four PR checks pass; the test suite fails if the installer is reverted to any of the currently broken behaviors.

#### P0-02 — Install a real, composable `pre-commit` hook

**Files:** `.github/hooks/`, `tools/setup/harness-link.sh`, hook tests, integration docs, manifest, branching skill

**Actions:**

- Provide an executable `.github/hooks/pre-commit` entrypoint or install/copy `prevent-trunk-commit` under that name.
- Detect an existing hook manager and refuse, chain, or give explicit integration instructions; never silently replace it.
- Detect Git repositories through `git -C "$TARGET" rev-parse --git-dir`, including worktrees.
- Test a real commit on every protected branch and a real allowed feature-branch commit.

**Acceptance:** after installation, an unborn `main` commit fails, a feature-branch commit succeeds, existing hooks remain active, and worktrees are supported.

#### P0-03 — Replace self-authorized remote workflow rules

**Files:** `CLAUDE.md`, committing/branching skills, committing and coding guidelines

**Actions:**

- Make review/report tasks read-only unless the user explicitly asks for implementation.
- Treat commit, push, PR creation, tagging, and repository settings as separate permissions.
- Move automatic publish behavior into an opt-in `strict-publish` profile.
- Replace "implement every positive recommendation" with prioritize, propose, obtain scope approval, then implement selected items.

**Acceptance:** a consumer can use the default profile for a local review without any implied edit or remote write.

#### P0-04 — Fix or withdraw the logging quick start

**Files:** logging YAML, loader, tests, both logging guides, dependency metadata, CI

**Actions:**

- Choose one contract: a custom portable schema with real adapters, or Python `dictConfig`. Do not claim both.
- Make the shipped default load with zero environment variables.
- Preserve boolean/number types, brace-containing defaults, and disabled-provider semantics.
- Remove secret-printing behavior and redact config dumps.
- Add schema validation and actionable errors.
- Test the actual example through the documented setup path.

**Acceptance:** one copy-paste Python example configures logging, emits a record, and exits successfully in CI without cloud credentials.

#### P0-05 — Establish one generated inventory source

**Files:** new `assets.yaml` or `manifest.json`, generated `MANIFEST.md`, README current tree, ROADMAP, docs indexes, changelog

**Actions:**

- Define a structured schema: path, kind, status, client, language/framework, version, dependencies, and validation command.
- Generate the human manifest and current-state sections from it.
- Make CI bidirectional: listed paths must exist and in-scope tracked assets must be listed.
- Explicitly define excluded files rather than relying on parser accidents.

**Acceptance:** deleting a top-level file, hook, TypeScript guide, or loader fails the same check; adding an unlisted asset also fails.

#### P0-06 — Validate every claimed runnable example

**Files:** agentic loops, error handling, language guides, integration guide, logging docs

**Actions:**

- Extract runnable snippets into fixtures/tests or use a snippet-testing tool.
- Label incomplete fragments `pseudocode` and remove "production"/"complete working" claims.
- Add source versions and dependencies to every runnable example.

**Acceptance:** all examples labeled runnable execute in CI; pseudocode is visually and textually unmistakable.

#### P0-07 — Rewrite the agentic-loop material around a safe current protocol

**Files:** agentic guide and skill

**Actions:**

- Use the current Responses API or a provider-neutral adapter; remove Assistants API guidance.
- Validate tool arguments with JSON Schema, preserve call IDs, and return provider-correct tool outputs.
- Cover approval policies, sandboxing, untrusted tool output, prompt injection, time/token/cost budgets, cancellation, retries, idempotency, persistence, and evals.
- Make one minimal implementation genuinely runnable; keep the skill concise and link to tested support files.

**Acceptance:** a fixture performs one tool call and one final response, rejects malformed arguments, enforces a budget, and records an auditable trace.

#### P0-08 — Close immediate security leaks

**Files:** config loader, installer, logging/error/agentic examples, SECURITY.md

**Actions:**

- Remove raw secret output and raw rejected-input logging.
- Reject traversal and unknown skill names with nonzero exits.
- Add instruction poisoning and mutable-symlink risks to the threat model.
- Recommend pinned copy/submodule/package modes for shared repos.

**Acceptance:** security tests prove secret values are absent from stdout/stderr and installer writes cannot escape intended target directories.

### P1 — turn the alpha into a dependable product

#### P1-01 — Define product contract, users, and non-goals

Add README sections for target users, supported clients, supported platforms, what is installed, what is advisory versus enforced, and what the project deliberately does not do. Position the current release as Claude-first until other adapters are tested.

#### P1-02 — Introduce profiles and precedence

Create `prototype`, `internal`, and `production` profiles that select policies rather than merely describing them. Document override/disable mechanics and the precedence order between user request, local repo, profile, language/framework add-on, and generic default.

#### P1-03 — Make skills self-contained and portable

Use `${CLAUDE_SKILL_DIR}` for bundled resources, or package referenced files with each skill. Validate every skill reference after installation in a blank consumer. Keep `SKILL.md` focused; move detailed examples to support files as recommended by the official Claude Code skill docs.

#### P1-04 — Replace `harness-link.sh` with an explicit lifecycle CLI

The first version can remain Bash, but should expose:

- `init --profile ... --mode copy|link|submodule`;
- `plan`/`--dry-run`;
- `status`/`doctor`;
- `audit`;
- `update` with diff and confirmation;
- `uninstall`/rollback.

Record selected assets, source revision, mode, and local overrides in a state file. Fail atomically or provide rollback instructions.

#### P1-05 — Add consumer fixtures

Keep tiny blank/Python/TypeScript/Go consumers in test fixtures. In CI, install each supported mode, discover the skills, resolve every reference, verify the hook, run a representative policy check, update, and uninstall.

#### P1-06 — Add a reproducible development toolchain

Add root project metadata for Python test dependencies, a lock or pinned dependency strategy, and one documented `make`, `just`, or script entrypoint for all checks. Run pytest, Ruff, typing, coverage, sample integration, Bats, ShellCheck, link validation, and manifest validation in CI.

#### P1-07 — Harden CI supply chain and permissions

Pin Actions and Bats to reviewed revisions, avoid an unpinned `sudo` installer, declare `permissions: contents: read`, add timeouts, and add an action-workflow lint check. Let Dependabot/Renovate propose controlled pin updates.

#### P1-08 — Add a content-quality gate

Run `git diff --check`, Markdown lint, YAML/frontmatter schema validation, duplicate-policy detection, and snippet tests. Schedule online external-link validation separately from the fast offline PR check.

#### P1-09 — Technically edit the new language guides

Correct the TypeScript and Go defects listed above, scope guidance by supported language versions, link to official sources, and separate React into a framework add-on. Prefer project formatter/linter configuration over universal style preferences.

#### P1-10 — Rationalize testing and logging policy

Make rigor profiles the sole applicability source. Replace universal percentages and tool mandates with risk-based defaults and project-owned thresholds. Keep one short policy document; turn long guides into optional references.

#### P1-11 — Repair onboarding end to end

Add HTTPS clone instructions, prerequisites, platform support, an exact file-change preview, safe hook-manager paths, working copy/submodule commands, `/skills` verification, troubleshooting, and uninstall/update instructions. Test every command in a clean container.

#### P1-12 — Establish release discipline

Add `Unreleased`, release and migration checklists, supported harness/client versions, and a compatibility policy. Cut releases only from green `main`; demonstrate pin, upgrade, rollback, and breaking-change handling in a consumer fixture.

#### P1-13 — Fix repository policy contradictions

Align the root `.gitignore` with the committed-lock policy, repair branch naming syntax/examples, update operational statuses, and remove stale target-directory commands from category READMEs.

#### P1-14 — Expand governance and security reporting

Document maintainer/reviewer responsibilities, add contribution commands, and define a private disclosure channel once external consumers exist. For high-impact instruction changes, require review from someone other than the author when the contributor base permits it.

### P2 — create differentiated usefulness and adoption

#### P2-01 — Make `agentharness audit` the signature capability

Audit unresolved references, stale pins, conflicting policies, missing validation commands, unsafe remote-write rules, and drift from the selected profile. Default to read-only and provide machine-readable plus human output.

#### P2-02 — Support the Agent Skills ecosystem from one source

Generate or package tested adapters for Claude Code, Codex/`AGENTS.md`, and other selected clients from one canonical policy catalog. Do not claim a client until a clean consumer fixture proves discovery and reference resolution.

#### P2-03 — Add a low-friction distribution path

After the installer is safe, publish a Claude plugin/marketplace package or a standard skill installation path. Keep git clone/submodule available for transparent pinned use.

#### P2-04 — Prove value with evaluations

Run a small repeatable task set with and without each profile. Measure task success, policy adherence, introduced defects, tool calls, token/context overhead, time, and false-positive interventions. Publish results and methodology; do not invent productivity claims.

#### P2-05 — Dogfood before list submissions

Use a pinned release in two or three real repositories, including at least one different language and one teammate/external user. Record setup time, drift found, overrides required, and update/rollback experience.

#### P2-06 — Reduce the generic encyclopedia

Retain decisions, trade-offs, runnable templates, and failure lessons. Link upstream language/tool documentation for generic facts. This lowers maintenance and makes the unique product easier to see.

#### P2-07 — Improve public project hygiene

Add `CONTRIBUTING.md`, a compact code of conduct if accepting community work, issue templates, status/version/license badges, a 90-second demo, and a small architecture decision record for major policy choices.

#### P2-08 — Clarify positioning before renaming again

Use the subtitle "portable engineering policies for coding agents," add "Why not just CLAUDE.md?", and show a before/after consumer example. Reconsider the name only if real user interviews still reveal confusion.

## Recommended execution sequence

### Milestone 0 — stabilize the current branch

Complete P0-01 through P0-06, remove or repair unsafe examples, update current inventory, and get PR #4 green. Do not add more content categories during this milestone.

### Milestone 1 — trusted `v0.2`

Complete P0-07/P0-08 plus P1-01 through P1-08. Release from green `main` with one pinned consumer fixture and a tested upgrade/rollback path.

### Milestone 2 — productize

Complete the profile system, portable lifecycle CLI, technical content editing, release policy, and two or three dogfood integrations.

### Milestone 3 — distribute and differentiate

Ship audit/drift detection, selected cross-agent adapters, marketplace/package distribution, and published evaluation evidence. Only then pursue broad awesome-list inclusion.

## Proposed release gate for the next version

Do not call the next version stable unless all of the following are true:

- [ ] `main` and the release tag have green hosted CI.
- [ ] A real installed hook blocks `main` and preserves existing hook tooling.
- [ ] Every documented quick-start command runs in a clean environment.
- [ ] All runnable examples execute; all pseudocode is labeled.
- [ ] Manifest/catalog drift is checked in both directions.
- [ ] Default agent policies do not imply edits, commits, pushes, or PRs without authorization.
- [ ] Shared-repo installation is version-pinned and portable.
- [ ] Installer supports preview, status, and uninstall/rollback.
- [ ] Logging example loads without credentials and emits a record through its documented adapter.
- [ ] Skills resolve all references from a blank consumer.
- [ ] Security checks prove secrets are not printed or logged.
- [ ] Changelog, compatibility notes, and upgrade instructions match the tag.

## Verification evidence

| Check | Observed result at `b4622da` |
|---|---|
| Worktree status | Clean |
| PR #4 checks | `shellcheck` failure; `hook-tests` failure; links and manifest success |
| Hosted harness-link tests | 1/7 reported `ok`, 6/7 failed; the one `ok` was not meaningful because missing executable was accepted as a nonzero result |
| Shell syntax (`bash -n`) | Passed for shell entrypoints |
| Python loader tests | 17 passed locally |
| Default logging sample | Exit `1`, missing `GCP_PROJECT_ID` |
| Interpolated types | `false` and `4317` returned as `str` |
| Documented Python `dictConfig` path | Exit `1`, missing dictionary `version` |
| Documented installed hook on `main` | Commit exit `0`; hook did not run |
| Direct hook copy as `pre-commit` | Commit exit `1`; hook correctly blocked |
| Manifest check | Exit `0` despite 19 unlisted tracked files |
| Controlled manifest deletions | Failed to detect missing README, hook, and TypeScript guide |
| `git diff --check origin/main...HEAD` | Exit `2`; 79 trailing-whitespace findings |
| Git integrity | `git fsck --no-dangling` passed |

Local `bats`, `shellcheck`, `actionlint`, and `yamllint` binaries were unavailable during the review. Their local success is not claimed; hosted failure logs were inspected through GitHub.

## Bottom line

agentharness is worth continuing. The idea is stronger than the current implementation, and the repository already contains the right seeds: profiles, on-demand skills, a catalog, an installer, and verification. The best next move is not more content. It is to make one narrow promise true end to end:

> A user can choose a policy profile, preview and install a pinned harness safely, verify exactly what is active, and remove or update it without surprises.

Once that works in clean fixtures and real consuming repositories, the language/framework catalog becomes leverage. Before that, every new guide increases surface area faster than usefulness.
