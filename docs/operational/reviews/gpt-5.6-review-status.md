# GPT-5.6 repository review — completion validation

**Timestamp:** 2026-07-12T15:47:00Z
**Source:** `gpt-5.6-review.md`
**Assessment:** completed, implementation not complete
**Snapshot:** `43604a73432816c7dfcb1983dba7e9cff1951e9c` on `chore/add-remaining-components`
**Remote:** PR #4 at the same SHA; six of six hosted checks green
**Default branch:** `main` at `61b60b0`; latest hosted run failed
**Release:** `v0.1.0` is 35 commits behind this snapshot

## Verdict

No: the original review was **partially actioned, not completed**.

- **1 of 30 backlog items is verified complete.**
- **12 are partial.**
- **17 are not done.**
- **0 of 12 release gates is fully satisfied.**
- Updated overall score: **5.2/10**, up from **4.5/10**.
- Product status remains **internal alpha / no-go for a stable release**.

The branch is materially better than the reviewed `b4622da` snapshot. PR CI is
green, the inert pre-commit installation was repaired, the installer tests now
exercise the real script, a sample consumer is checked in CI, the logging loader
has better interpolation and CLI tests, and several immediately broken snippets
were fixed. Those are real improvements.

They do not close the review's core product and trust gaps: default policies
still self-authorize edits and remote publication, the installer is not safe or
portable, the manifest check still provides false assurance, the shipped
logging quick start still fails, runnable examples are not systematically
tested, skills break their references in a blank consumer, and there is no
profile/lifecycle/release model.

## Snapshot and verification boundary

This audit distinguishes three states that previous status notes sometimes
mixed together:

1. **Current feature branch:** clean and pushed at `43604a7`; all six PR checks
   are green for that exact SHA.
2. **Default branch:** `main` remains at `61b60b0`; its latest hosted CI run is
   red (`shellcheck`). Green feature-branch CI is not green `main`.
3. **Release:** `v0.1.0` predates 35 commits and has no matching current
   compatibility, migration, or upgrade record.

The original requested file, `docs/gpt-5.6-sol.md`, was filed as
`docs/operational/reviews/gpt-5.6-review.md`. This document is its completion
status report.

## What was genuinely completed

### P0-01 — PR #4 green for the right core behaviors

Verified complete for the core gate:

- Hosted PR checks at `43604a7`: `shellcheck`, `hook-tests`, `python-tests`,
  `markdown-links`, `manifest-verify`, and `sample-project-integration` all
  succeeded.
- `tools/tests/harness-link.bats` derives the script path from the test file,
  tests the implemented per-skill link contract, and no longer masks assertions
  with `|| true`.
- CI now runs Python coverage and includes all three hook entrypoints in
  ShellCheck.

Installer safety and consumer behavior are not counted here; they remain open
under P0-02, P0-08, and P1-05.

## Newly found or still release-blocking

### 1. The new consumer-installed pre-push hook tests agentharness, not the consumer

`tools/setup/harness-link.sh --with-hook` points a consumer's
`core.hooksPath` at this repository. The new `.github/hooks/pre-push` then
derives `REPO_ROOT` from the hook file's own directory and runs
agentharness's Bats and logging-loader suites (`pre-push:23-25,44-75`).

A real blank consumer push produced:

```text
consumer_push_exit=1
Running pre-push checks (test suite + 80%+ coverage)...
bats not installed — cannot run shell test suites.
pytest: patterns/logging/test_config_loader.py (>=80% coverage required)
Pre-push checks failed. Push blocked.
remote_refs=0
```

This is a regression in portability and profile semantics. It can block an
unrelated Prototype or Internal Tool repository because agentharness lacks a
tool or test, and it imposes the Production 80% threshold regardless of the
consumer's selected rigor tier.

### 2. The sample integration job is a shallow positive check

`examples/sample-project/verify.sh:14-29` checks one skill symlink, the text of
`core.hooksPath`, and the existence of `.github/CLAUDE.md`. It does not make a
real commit or push, preserve an existing hook manager, resolve skill
references, verify agent discovery, or test update/uninstall behavior.

The sample's own instructions also contradict the installer:

- `examples/sample-project/.github/CLAUDE.md:7-12` says the whole skills and
  hooks directories are symlinked; the installer creates individual skill
  links and no hooks symlink.
- It references a nonexistent consumer-side
  `.github/CODING_GUIDELINES.md` (`:35,56`).
- It invents an Internal Tool threshold of 50% (`:37-40`); the actual rigor
  table does not define that percentage, while the new pre-push hook forces
  80%.

### 3. The manifest verifier is neither generated nor reliably one-way

There is no structured catalog or generator. `tools/verify-manifest.sh` only
attempts listed-path-to-file checks and never detects unlisted assets. Worse,
its row filter `grep -v 'Asset\|Path\|Type'` drops legitimate rows whose prose
contains those words—for example the pre-commit row contains `hooksPath`, and
the TypeScript row contains `TypeScript`. Controlled deletions of
`README.md`, `.github/hooks/pre-commit`, and
`languages/typescript/CONVENTIONS.md` all returned success. Adding an unlisted
skill also returned success.

### 4. The shipped logging quick start still fails

- With a clean environment, the real example exits on missing
  `GCP_PROJECT_ID` (`logging.yaml.example:94`) even though that provider is
  disabled by default; Azure has the same design at line 109.
- Interpolated `${...:-false}` and `${...:-4317}` values remain strings, not
  booleans/numbers.
- `patterns/logging/README.md:98-108` still passes the custom schema directly
  to `logging.config.dictConfig()`, which raises because no dictConfig
  `version` exists.
- `--show-config` intentionally prints resolved secrets. Explicit debug output
  may be acceptable, but it does not satisfy the review's stronger redacted
  dump/security acceptance criterion.

### 5. Installer containment and composition remain unsafe

Manual end-to-end tests found:

- An installed hook blocks an unborn `main` commit and allows a feature-branch
  commit—this part works.
- An existing `core.hooksPath` is overwritten, and the old hook no longer runs.
- A Git worktree is reported as “not a git repo” because the installer checks
  for a `.git` directory rather than using `git rev-parse`.
- `--skills ../../patterns` exits successfully and creates a symlink outside
  `.claude/skills` in the target.
- An unknown skill is skipped with exit 0 rather than failing atomically.

### 6. Installed skills are not self-contained

A blank consumer receives absolute symlinks to `.claude/skills/*`, but the
skills reference consumer-root paths that are not installed, including
`.github/COMMITTING_GUIDELINES.md`, `.github/BRANCHING_STRATEGY.md`,
`languages/python/CONVENTIONS.md`, and several `patterns/` guides. All tested
targets were missing in the consumer.

### 7. The default authorization model is unchanged

`CLAUDE.md:7-45`, `.github/COMMITTING_GUIDELINES.md:12-28`, and the committing
skill still require commit, push, and PR creation after every task and require
agents to implement recommendations they judge positive. This conflicts with
the new audit-follow-up skill's correct instruction to assess without fixing.
A review request still implies local and remote writes under the default
profile.

## Backlog disposition

Legend: **✅ verified complete**, **⚠️ partial**, **❌ not done**.

### P0 — restore trust before merging or releasing

| Item | Status | Evidence-based disposition |
|---|---|---|
| P0-01 Green PR for the right reasons | ✅ | Six hosted checks green at exact current SHA; original test/path failures repaired. |
| P0-02 Real composable pre-commit | ⚠️ | Dispatcher and trunk block work; existing hook managers are overwritten, worktrees are skipped, and real consumer behavior is not covered. |
| P0-03 Remove self-authorized remote workflow | ❌ | Mandatory edit/commit/push/PR and recommendation auto-implementation rules remain unchanged. |
| P0-04 Fix or withdraw logging quick start | ⚠️ | Loader, adapter, brace handling, redaction defaults, and tests improved; shipped no-credential quick start and typed interpolation still fail. |
| P0-05 Generated bidirectional inventory | ❌ | Hand-written Markdown plus a lossy one-way parser; controlled missing and unlisted assets pass. |
| P0-06 Validate every runnable example | ⚠️ | Several immediate defects fixed; no snippet extraction/gate, version metadata, or consistent pseudocode labeling. Known broken snippets remain. |
| P0-07 Safe current agent-loop protocol | ❌ | Still a generic `model.complete` sketch with no provider-correct tool-result protocol, call IDs, schema validation, approvals, budgets, sandboxing, or eval fixture. |
| P0-08 Close immediate security leaks | ⚠️ | Default CLI output is safer; traversal, raw rejected-input/error logging, mutable symlinks, hook replacement, and instruction-supply-chain risks remain. New pre-push behavior regresses consumer safety. |

### P1 — turn the alpha into a dependable product

| Item | Status | Evidence-based disposition |
|---|---|---|
| P1-01 Product contract, users, non-goals | ❌ | README lacks target users, supported clients/platforms, advisory-vs-enforced boundaries, and non-goals. |
| P1-02 Selectable profiles and precedence | ❌ | Rigor tiers are descriptive prose only; no selectable assets, precedence, overrides, disable mechanism, or strict-publish opt-in. |
| P1-03 Self-contained portable skills | ❌ | Absolute links and unresolved consumer-root references remain; no `${CLAUDE_SKILL_DIR}` bundle. |
| P1-04 Lifecycle CLI | ❌ | Only target, `--skills`, and `--with-hook`; no plan, state, profile/mode, status, audit, update, uninstall, or rollback. |
| P1-05 Consumer fixtures | ⚠️ | One symlink-mode scratch sample is in CI; no blank/Python/TS/Go matrix, copy/submodule modes, real push, reference resolution, update, or uninstall. |
| P1-06 Reproducible toolchain | ⚠️ | CI now runs more checks and 100% loader coverage; no root dependency metadata/lock, unified check command, Ruff/typing in CI, or reproducible Bats install. |
| P1-07 CI supply-chain hardening | ⚠️ | Dependabot exists, but Actions use mutable major tags and CI clones an unpinned default branch before running its installer with `sudo`; no permissions, timeouts, or actionlint. |
| P1-08 Content-quality gate | ⚠️ | Offline link validation exists; no diff, Markdown style, frontmatter/schema, duplicate-policy, manifest-parser, or snippet gate. `git diff --check origin/main...HEAD` reports 154 lines of whitespace findings. |
| P1-09 Technical edit of TS/Go guides | ❌ | The specific TypeScript and Go defects in the review remain unchanged. |
| P1-10 Rationalize testing/logging policy | ⚠️ | Rigor tiers improved applicability, but universal logging text persists and the new consumer hook hard-codes 80%. |
| P1-11 End-to-end onboarding | ⚠️ | One fast path exists; prerequisites, platforms, preview, safe hook-manager flow, exact discovery check, lifecycle instructions, and clean-container validation do not. Several commands/claims are stale. |
| P1-12 Release discipline | ❌ | No `Unreleased`, compatibility/migration policy, release checklist, or tested upgrade/rollback; tag is 35 commits behind and `main` is red. |
| P1-13 Resolve policy/documentation contradictions | ⚠️ | Root lock-file ignore and some roadmap drift fixed; README/category trees, sample policy, integration inventory, and hook descriptions remain inconsistent. |
| P1-14 Governance and security reporting | ❌ | Existing CODEOWNERS/SECURITY files were not expanded into maintainer duties, contribution commands, private reporting, or independent instruction-change review. SECURITY understates the executable/instruction attack surface. |

### P2 — differentiated usefulness and adoption

| Item | Status | Evidence-based disposition |
|---|---|---|
| P2-01 Signature `agentharness audit` | ⚠️ | The read-only audit-follow-up skill is useful, but there is no installed-project CLI, profile-drift audit, or machine output. |
| P2-02 Cross-agent adapters from one source | ❌ | Claude-only; `.codex/` is explicitly unstarted and no tested `AGENTS.md`/other-client adapter exists. |
| P2-03 Low-friction distribution | ❌ | No plugin, marketplace, package, or standard skill installer; clone plus mutable local links remains the default. |
| P2-04 Evaluations | ❌ | No task set, baseline, method, results, or context/cost/adherence measurements. |
| P2-05 Real dogfood | ❌ | One scratch fixture is not pinned use in several real repos or by an external teammate; no adoption/update evidence. |
| P2-06 Reduce generic encyclopedia | ❌ | Generic long-form language, testing, logging, error, and agent-loop material remains; no reduction/source-linking pass. |
| P2-07 Public project hygiene | ❌ | No CONTRIBUTING, code of conduct, issue templates, badges, demo, or ADR. |
| P2-08 Clarify positioning | ❌ | No “portable engineering policies” subtitle, “Why not just CLAUDE.md?”, supported-client statement, or before/after consumer story. |

## Release-gate validation

None of the twelve gates is fully satisfied.

| Gate | Result | Blocking evidence |
|---|---|---|
| `main` and release tag have green hosted CI | ❌ | PR is green; `main` latest run is red and `v0.1.0` is 35 commits behind. |
| Installed hook blocks trunk and preserves hook tooling | ⚠️ | Trunk block works; existing hook path is replaced, worktrees are skipped, pre-push runs harness checks in consumers. |
| Every documented quick start runs cleanly | ❌ | Only sample Method 1 is CI-checked; logging and other integration claims fail or are untested. |
| Runnable examples execute; pseudocode is labeled | ⚠️ | Some fixes landed; no systematic gate and broken/unlabeled sketches remain. |
| Manifest drift checked both ways | ❌ | Neither generated nor bidirectional; parser misses listed paths too. |
| Default policies imply no unauthorized writes | ❌ | Default still mandates implementation, commit, push, and PR. |
| Shared installation is pinned and portable | ❌ | Default uses absolute mutable symlinks to a moving checkout. |
| Installer has preview/status/uninstall/rollback | ❌ | None exists. |
| Logging example loads without credentials and emits | ❌ | Adapter exists, but the shipped template fails before adapter use on missing cloud variables. |
| Skills resolve references in a blank consumer | ❌ | Referenced guidelines and patterns are absent after installation. |
| Security tests prove secrets are not printed/logged | ⚠️ | Default/show-env CLI cases are tested; explicit dump, raw-input examples, traversal, and broader redaction boundaries remain. |
| Changelog/compatibility/upgrade match release | ❌ | Changelog stops at 0.1.0; no compatibility or upgrade path for 35 later commits. |

## Updated scorecard

The same dimensions and scale as the original review are used.

| Dimension | Was | Now | Why |
|---|---:|---:|---|
| Problem / idea | 8.0 | 8.0 | The underlying cross-repo instruction-drift problem remains real. |
| Product focus / differentiation | 5.0 | 5.5 | Honest roadmap/sample improvements, but no product contract, profiles, audit CLI, or adoption proof. |
| Documentation readability | 7.0 | 7.0 | Generally readable and navigable; long encyclopedic sections and duplicated policy remain. |
| Documentation correctness | 4.0 | 5.0 | Several defects fixed, but the current tree, integration claims, sample policy, logging quick start, and examples still drift. |
| Implementation quality | 3.0 | 4.5 | Hook dispatcher, loader, and tests improved; installer containment/composition and consumer pre-push design are unsafe. |
| Tests and CI | 3.0 | 5.5 | Exact PR SHA is green with six jobs and loader coverage; `main` is red and major behavior/snippet/supply-chain gaps remain. |
| Safety and trust model | 3.0 | 3.0 | CLI defaults improved, but authorization, traversal, hook replacement, mutable instructions, and raw logging remain; pre-push adds risk. |
| Usefulness today | 5.0 | 5.5 | More useful as a personal Claude-first playbook; still unreliable as a portable team harness. |
| Release readiness | 2.0 | 2.5 | Green PR is progress, but zero release gates pass, `main` is red, and the release record is stale. |
| **Overall** | **4.5** | **5.2** | **A better-tested internal alpha, not a completed or stable product.** |

## Actionable next sequence

### Immediate — do before merging PR #4

1. **Remove the shared pre-push regression.** Do not install a
   repository-specific test runner through the same global `core.hooksPath` as
   trunk protection. Make project checks consumer-owned, profile-aware, and
   explicitly opt-in. Add a real blank-consumer push test.
2. **Fix the authorization defaults.** Reviews are read-only by default;
   editing, committing, pushing, opening PRs, tagging, and changing settings
   are separate permissions. Put publish automation behind an opt-in profile.
3. **Harden `harness-link.sh`.** Validate skill names with a basename-safe
   grammar, enforce source/destination containment, fail unknown names,
   recognize worktrees with `git rev-parse`, and preserve/refuse/chain an
   existing hook manager.
4. **Make the logging quick start real.** Disabled providers must not require
   credentials; preserve scalar types; choose and validate one schema; run the
   exact README quick start in CI and assert a log record is emitted.
5. **Replace the manifest parser.** Use a structured source, generate the human
   manifest/current-state sections, test both directions, and add mutation
   tests for top-level files, hooks, language guides, and unlisted assets.
6. **Add snippet verification.** Extract runnable examples into fixtures and
   label every other fragment as pseudocode. Start with logging, agent loops,
   error handling, TypeScript, Go, and integration commands.

### Next — trusted v0.2 foundation

7. Define target users, Claude-first support, platforms, advisory/enforced
   boundaries, non-goals, profiles, and precedence.
8. Package skills with self-contained references and test discovery/reference
   resolution in a blank consumer.
9. Add lifecycle operations: plan, init, status/doctor, audit, update with diff,
   and uninstall/rollback with recorded state and source revision.
10. Add reproducible root tooling and pin CI dependencies/actions; run Ruff,
    typing, coverage, diff/style/frontmatter/snippet/manifest checks from one
    documented command.
11. Technically edit TypeScript and Go, reconcile testing/logging policy, and
    repair stale README/category/sample/integration documentation.
12. Merge only after required checks protect `main`; add `Unreleased`,
    compatibility/migration policy, and a tested pin/upgrade/rollback path,
    then cut v0.2 from green `main`.

### Later — differentiation and adoption

13. Build the read-only `agentharness audit` capability and machine output.
14. Generate tested Claude/Codex/selected-client adapters from one catalog.
15. Dogfood a pinned release in several real repositories, publish evaluation
    methodology/results, then add distribution and public-project polish.

## Verification evidence

| Check | Result at audit snapshot |
|---|---|
| Worktree / origin | Clean; local HEAD and origin branch both `43604a7` |
| PR #4 hosted checks | 6/6 success at exact SHA |
| Latest `main` hosted run | Failure at `61b60b0` (`shellcheck`) |
| Loader unit tests | 26 passed |
| Loader coverage | 100%; 80% gate passed |
| Ruff | Passed |
| Mypy | Failed: no `types-PyYAML` dependency/stub strategy |
| Shell syntax | Passed for shell entrypoints |
| Local Bats / ShellCheck | Binaries unavailable; exact hosted jobs passed |
| Sample CI sequence | Passed after setup; direct `verify.sh` on an uninstalled checkout correctly fails |
| Real trunk / feature commits | Trunk blocked; feature commit allowed |
| Existing hook manager | Replaced; prior hook did not run |
| Worktree install | Hook skipped while command exited 0 |
| Traversal probe | Escaped `.claude/skills`; command exited 0 |
| Real blank-consumer push | Blocked by agentharness's own pre-push checks |
| Default logging template | Exit 1: missing `GCP_PROJECT_ID` |
| Documented logging README quick start | Exit 1: dict lacks `version` |
| Manifest mutation probes | Missing README/pre-commit/TypeScript and an unlisted skill all passed incorrectly |
| `git diff --check origin/main...HEAD` | Exit 2; 154 output lines |
| Git integrity | `git fsck --no-dangling` passed |

## Bottom line

The bug-fix pass was worthwhile and demonstrably improved the repository, but
it did not complete the GPT-5.6 review. Do not merge or release on the basis of
the green PR alone. The next milestone should make one narrow promise true end
to end: a user can preview and install a pinned, profile-selected harness in a
blank repository, verify exactly what is active, run only that repository's
checks, and update or remove it without losing existing tooling or granting
unrequested write authority.
