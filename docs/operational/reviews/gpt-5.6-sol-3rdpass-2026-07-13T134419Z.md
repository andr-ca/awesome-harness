# agentharness repository review — GPT-5.6 third pass

- **Timestamp:** 2026-07-13T13:44:19Z
- **Date:** 2026-07-13
- **Reviewer:** GPT-5.6 / Codex
- **Snapshot:** `9d32ddcc75e5df115c5237bce24b9b2f84385a49` on
  `docs/require-ci-green-before-done`
- **Scope:** product idea, positioning, documentation, implementation,
  tests/CI, safety, release/distribution, GPT-5/Codex fit, and practical
  usefulness
- **Method:** assessment only. Current files and behavior were checked
  directly; prior review/status checkmarks were not trusted. No product fixes
  are included in this report.

## Executive verdict

agentharness is now a **credible early product**, not the unreliable internal
alpha described in the first GPT-5.6 review. The central idea remains strong:
portable, versioned engineering policy can reduce cross-repository instruction
drift, and the repository now has real product shape around that idea. The
lifecycle CLI, generated manifest, rigor profiles, tested agent loop, logging
loader, consumer fixtures, pinned CI, release path, and explicit trust model are
substantial improvements.

It is not yet a product I would recommend teams adopt broadly without caveats.
The largest problem has shifted from “many advertised paths do not work” to
“the working pieces do not yet form one safe, coherent consumer experience.” In
particular:

1. The lifecycle CLI can delete a consumer's pre-existing hook configuration
   after previously refusing to overwrite it.
2. The `npx` fast path defaults to symlinks into an npm package/cache location,
   while lifecycle state remains tied to that potentially ephemeral source.
3. The installer's “coverage hooks” do not enforce consumer coverage; the
   consumer pre-push hook intentionally no-ops and profile enforcement is a
   separate manual command.
4. The Codex adapter is based on an outdated assumption for this GPT-5/Codex
   environment: it eagerly injects all skills into an 880-line, 33.7 KB
   `AGENTS.md`, even though the running client exposes a skill catalog and can
   load matching `SKILL.md` instructions on demand.
5. Documentation has started drifting again after the rapid v0.2 follow-up,
   including contradictory release, profile-enforcement, and trust-model text.
6. There is still no real baseline-versus-treatment agent evaluation or
   non-fixture dogfooding evidence proving that the harness improves outcomes.

**Overall score: 7.3/10** (previous re-audit: 7.0/10; original review:
4.5/10). The implementation is much stronger, but new integration evidence
exposes a few high-leverage defects that the broad green suite does not catch.

## What was verified

### Repository and release state

- 152 tracked files and about 18.7k lines at the reviewed snapshot.
- `v0.2.0` exists at merge commit `538b6cb`; the reviewed snapshot is 14
  commits ahead of it.
- The working tree was clean before this report was created.
- The repository was reviewed on the user's active feature branch rather than
  silently switching or modifying `main`.
- Registry availability was not independently rechecked because package-network
  access was unavailable. The repository's current docs say the first manual
  npm publish was completed.

### Verification evidence

The repository's full local check was rerun in a disposable clone under `/tmp`
so Git metadata, the Go build cache, npm materialization cleanup, and local
submodule operations were writable. With `GOCACHE` redirected and the local
clone allowed as the submodule transport:

- ShellCheck passed.
- **86 Bats tests passed** across hooks, install/lifecycle behavior, generators,
  package symlink materialization, publish authority, and profiles.
- Ruff passed.
- mypy passed for all seven configured source files.
- **73 pytest cases passed**:
  - logging loader: 37, 99.45% branch-aware coverage;
  - agent loop: 9, 100%;
  - eval scorer/orchestrator: 15, 87.30%;
  - content-quality unit tests: 12.
- Generated-manifest and filesystem verification passed.
- `tools/verify-content-quality.py` passed in the shared checkout.
- `git diff --check` passed.
- The final `npx markdownlint-cli2` step could not complete because it waited
  for unavailable package-network access. It was stopped rather than reported
  as passed.

The initial shared-worktree run failed for environmental reasons, not code
reasons: Git metadata was read-only, normal Go cache was read-only, and GitHub
network access was unavailable for submodule tests. That run did reveal a test
isolation weakness discussed below.

## Scorecard

| Dimension | First review | Prior re-audit | Third pass | Assessment |
|---|---:|---:|---:|---|
| Problem / idea | 8.0 | 8.0 | **8.5** | Real, recurring problem; the policy-as-versioned-product framing is useful. |
| Product focus / differentiation | 5.0 | 7.0 | **7.2** | Lifecycle/audit/profile surfaces clarify the product, but installation still exposes disconnected pieces. |
| Documentation readability | 7.0 | 7.5 | **8.0** | Strong orientation, product contract, demo, architecture, and release guide. |
| Documentation correctness | 4.0 | 7.0 | **6.5** | Several post-v0.2 contradictions and overstatements have reappeared. |
| Implementation quality | 3.0 | 7.5 | **7.0** | Good small utilities and strong defensive work; hook state/uninstall and npm lifecycle have serious gaps. |
| Tests and CI | 3.0 | 8.5 | **8.5** | Broad and meaningful suite; isolation, negative lifecycle transitions, and real-client tests remain weak. |
| Safety and trust model | 3.0 | 5.5 | **6.5** | Publish authority is fixed, but mutable default links and destructive uninstall behavior remain. |
| Usefulness today | 5.0 | 7.5 | **7.2** | Useful for the author's Claude-first workflow; team portability still takes manual glue and judgment. |
| Release readiness | 2.0 | 5.0 | **6.5** | v0.2/package machinery exists; tag publishing is not independently gated and npx defaults are fragile. |
| GPT-5 / Codex fit | — | — | **4.5** | Best-effort adapter is unverified, context-heavy, and built around a false current-client assumption. |
| **Overall** | **4.5** | **7.0** | **7.3** | **A strong early foundation with three concrete consumer-path blockers.** |

## What is working especially well

1. **The idea and positioning are finally concrete.** `README.md` explains
   the cross-project drift problem, target users, support boundary, installed
   assets, advisory/enforced distinction, and non-goals.
2. **The project is honest about many boundaries.** Claude-first support,
   unverified Codex behavior, unimplemented live eval calls, unsupported
   profile runners, and Windows status are usually named rather than hidden.
3. **The lifecycle CLI is a meaningful differentiator.** `plan`, `status`,
   `doctor`, `audit`, `update`, `uninstall`, three install modes, state, and
   drift reporting are much more useful than a one-shot symlink script.
4. **The trust-model correction was important.** Remote publication now
   requires explicit authorization or a local flag; review no longer implies
   push/PR authority.
5. **The test investment is real.** Tests exercise worktrees, hook conflicts,
   lifecycle operations, all install modes, fixtures in three languages,
   profile thresholds, package symlink materialization, and generated-file
   drift.
6. **The repository has better self-verification than most policy repos.** The
   structured manifest, generated `AGENTS.md`, content checks, pinned actions,
   ShellCheck, Ruff, mypy, coverage, and offline link validation meaningfully
   reduce silent drift.
7. **The reference implementations are appropriately bounded.** The logging
   loader and agent loop now have executable behavior, budgets, validation,
   redaction-aware traces, and high coverage instead of aspirational snippets.
8. **The documentation hierarchy is navigable.** README → manifest/roadmap →
   architecture/integration/releasing is a sensible route, and prior reviews
   provide useful historical accountability.

## Findings and actionable improvements

### P0 — fix before presenting the lifecycle/distribution path as safe

#### P0-01 — Preserve hook ownership through the full lifecycle

**Finding:** `init --with-hook` refuses to overwrite a different existing
`core.hooksPath`, but still records `with_hook: true`. `doctor` only checks that
*some* hook path exists, so it accepts the unrelated path. `uninstall` then
unconditionally unsets `core.hooksPath`, despite telling the user it will do so
only “if still pointing at agentharness.”

**Direct reproduction:** a scratch repo started with
`core.hooksPath=preexisting/hooks`; init preserved it, doctor passed, and
uninstall changed it to unset.

**Impact:** data/configuration loss in a consuming repository. This violates
the lifecycle CLI's central reversibility promise.

**Action:** record the exact previous hook path and the exact installed hook
path; set `with_hook` only when installation succeeds; have `doctor` compare the
actual value to the recorded expected value; have uninstall restore the prior
value only when the current value still equals the value installed by the
harness. Add transition tests for conflict, `--force`, later user changes, and
uninstall.

**Acceptance:** every state transition preserves a hook manager the harness did
not install, and uninstall is idempotent.

#### P0-02 — Make the npm/npx install mode durable

**Finding:** `npx agentharness-toolkit init <project>` uses the CLI's default
`--mode link`. Those links and `.agentharness-state.json` point into the npm
package location used for that invocation. An npx cache is not a durable,
user-managed harness checkout. A later cache cleanup/move can break every
installed skill. `update` also follows the *recorded old source path*, so a new
`npx agentharness-toolkit update` invocation does not naturally update from the
new package version.

**Impact:** the lowest-friction advertised path is the least lifecycle-stable.
The package CI test checks the links immediately but never removes/moves the
unpacked package and re-runs `doctor`.

**Action:** make the npm shim default to `--mode copy`, or install a versioned
durable source under the consumer before linking. Make package-driven update
explicitly use the currently executing package as the new source. Add an E2E
test that installs, deletes the package extraction/cache, runs `doctor`, upgrades
from a second package version, and uninstalls.

**Acceptance:** an npx-installed consumer remains healthy after the original
process and package directory disappear.

#### P0-03 — Stop advertising consumer coverage enforcement that does not occur

**Finding:** README, integration docs, CLI output, and `--with-hook` describe
“trunk-protection + coverage hooks.” In a consumer repo, the shared pre-push hook
intentionally no-ops. Real profile enforcement lives in a separate,
explicitly-invoked `enforce-profile` command and is not wired into the hook.

**Impact:** users can reasonably believe `--with-hook` mechanically enforces
their test/coverage profile when it only enforces trunk protection.

**Action:** choose one honest contract:

- rename consumer installation to “trunk-protection hook” and state that
  coverage is not installed; or
- generate a consumer-owned, profile-aware pre-push hook that calls
  `enforce-profile`, with an explicit opt-in and compatibility handling for
  existing hook managers.

**Acceptance:** a fixture below threshold fails a real consumer push when the
product says coverage is enforced; otherwise no consumer-facing text calls it a
coverage hook.

#### P0-04 — Fail invalid requested installs atomically

**Finding:** `--skills definitely-not-a-skill` prints a warning, exits 0,
creates `.gitignore` and state with an empty `skills` list, and `doctor` reports
“all checks passed.” Path traversal is likewise “skipped” rather than rejected
with a failure status. This behavior was reported in the original review and
remains by design in the current tests.

**Impact:** typos produce a successful but useless installation; automation
cannot distinguish success from partial/no-op setup.

**Action:** validate all requested names before mutation, reject invalid or
unknown names nonzero, and require at least one resolved skill unless the user
explicitly requests `--skills none`. Add rollback for any later init failure.

**Acceptance:** a typo leaves the target byte-for-byte unchanged and exits
nonzero.

#### P0-05 — Make release publication verify the artifact, not only the version

**Finding:** `.github/workflows/release.yml` checks only that tag and
`package.json` versions match, then publishes. It does not run the package E2E
test, content checks, or verify that the tagged commit is the green `main`
commit. The written release checklist is a human control, not a workflow gate.

**Impact:** an accidentally placed or malicious matching tag can publish a
broken artifact even if PR/main CI was never run for that commit.

**Action:** have release call a reusable verification workflow or at minimum
pack/unpack/run the CLI and check the tagged commit's ancestry. Publish using
npm provenance and a protected release environment when practical.

**Acceptance:** a matching version on an unverified/broken tag cannot publish.

#### P0-06 — Replace the current Codex adapter assumption with a tested GPT-5 contract

**Finding:** `tools/generate-agents-md.sh`, its tests, `AGENTS.md`, and
`docs/INTEGRATION.md` assert that Codex has no on-demand skill-loading mechanism
and must receive every skill in one file. In this actual Codex session, a skill
catalog is provided and matching `SKILL.md` files can be read on demand.
`AGENTS.md` is consequently 880 lines / 33.7 KB and front-loads six skill bodies
into every task, including unrelated Python, error-handling, and agent-loop
material.

**Impact:** unnecessary context cost, lower instruction salience, duplicated
skill systems, and a client adapter whose foundational premise is false for the
environment it is intended to support.

**Action:** run a real Codex integration study and choose the native path:

- a concise `AGENTS.md` containing only repo-wide rules and routing;
- installable Codex skills/plugin assets for on-demand behavior; or
- a generated adapter variant keyed to the detected Codex version/capability.

Delete the test that enshrines “no on-demand skill loading” and replace it with
behavioral tests: discovery, trigger matching, path resolution, and context
size. Keep Claude and Codex outputs generated from a shared structured policy
source, not by concatenating one client's rendered documents.

**Acceptance:** a real GPT-5/Codex session discovers and uses one relevant skill
without receiving every unrelated skill body, and the repo publishes measured
context size before/after.

### P1 — make the product coherent and maintainable

#### P1-01 — Install a usable client entry point, not only skill directories

`harness-link.sh init` installs skills, gitignore entries, optional hooks, a
profile file, and state. It does not install/generate a project `CLAUDE.md` or
`AGENTS.md`, nor does it wire language/framework/pattern guides. The fast path
therefore does not, by itself, deliver the full “portable engineering policies”
value proposition.

**Action:** add `--client claude|codex|both` and generate a small repo-local
router with stable relative references. Track it in state/update/doctor/uninstall
without overwriting user-owned project instructions; use marked managed blocks
or a dedicated included file.

#### P1-02 — Complete profile enforcement for mainstream projects

Python and Node's built-in runner are enforced; Go and the most common JS/TS
runners (Vitest/Jest/Mocha) exit 0 as unsupported. That is honest but too narrow
for a product whose examples include Go and TypeScript.

**Action:** define runner adapters with explicit commands and machine-readable
results, starting with Go and one mainstream JS runner. Add `--strict` so CI can
fail on “unsupported” instead of treating it as success. Never parse decorative
console output when a tool offers JSON/coverage files.

#### P1-03 — Fix profile and workflow documentation drift

Current contradictions include:

- `.github/CODING_GUIDELINES.md` says profile mechanical enforcement is “none
  yet — advisory only,” while `patterns/profiles/README.md` and the CLI enforce
  Python/Node projects.
- The same coding guide still points to a universal “commit → push → PR” rule,
  while the default trust model is verify/commit locally then request publish
  authority.
- `docs/DEMO.md` calls P0-03's authority model an “open question,” although the
  decision is settled.
- `docs/RELEASING.md` says the current release is `v0.1.0`, while `v0.2.0`
  exists.
- `docs/DECISIONS.md` says npm publishing is “in progress,” then describes the
  first publish as completed.
- The v0.2 changelog says npm was not published, conflicting with the current
  release documentation. If intentionally historical, it needs a dated
  follow-up note rather than silently disagreeing with current status.

**Action:** create a generated current-capabilities table (client × install mode
× enforcement × distribution × verification) and link prose to it. Add
targeted contradiction tests for release version, profile status, and authority
mode; numeric-only duplicate detection cannot catch these semantic conflicts.

#### P1-04 — Make package materialization independent of writable Git metadata

`materialize-skill-symlinks.py restore` uses `git checkout`. The real-worktree
test mutates tracked files and relies on Git for cleanup. In a restricted or
non-Git source package this fails and can leave file-type changes behind.

**Action:** test materialization in an isolated fixture and restore from an
in-memory/on-disk backup created by `materialize`, not from Git. The packaging
script should be transactional and usable from an exported source tree.

#### P1-05 — Make tests hermetic by default

`tools/check.sh` includes submodule lifecycle tests that clone the checkout's
configured `origin`; in the shared checkout that meant a live SSH GitHub
dependency. The Go scorer assumes the default Go cache is writable. Markdown
lint may invoke `npx` network resolution.

**Action:** use a local bare fixture remote for submodule tests, set temporary
language caches inside the test harness, and vendor/pin or preflight every
required executable. Split `check.sh` into `check:offline` and explicitly named
network checks if any are truly needed.

#### P1-06 — Test lifecycle transitions, not only happy-state snapshots

The suite is broad, but the hook-loss defect survived because tests check init
and uninstall separately, not sequences where external state changes between
them.

**Action:** add model/state-machine tests for install → user modification →
doctor → update → uninstall across hook conflict, moved source, partial install,
removed skill, profile edit, package upgrade, and repeated uninstall.

#### P1-07 — Make update previews match the documentation

Docs say copy-mode update “shows a diff.” Current output lists changed skill
names (`~ content changed upstream`) but does not show the content diff.

**Action:** provide `update --diff`/`plan` with bounded file diffs or change
summaries and make confirmation operate on the exact previewed plan. Detect
consumer-local edits separately from upstream changes to avoid overwriting both
under one generic “changed” label.

#### P1-08 — Reconcile universal policies with language/product reality

The supposedly universal coding guide mandates camelCase functions/methods,
global UI capitalization rules, and JavaScript-specific arrow-function style
while the repo also ships Python and Go conventions. These are preferences, not
universal safety/quality invariants, and can conflict with consuming projects'
formatters and design systems.

**Action:** reduce universal policy to cross-language invariants; move naming,
UI copy, function style, testing frameworks, and logging stack choices into
language/framework/profile modules. Add explicit precedence and conflict
examples.

#### P1-09 — Give managed state a compatibility/migration contract

The state file has `version: 1`, but there is no migration machinery or test
matrix showing a newer CLI can read/update/uninstall older released state.

**Action:** keep state fixtures from every release, add forward migration and
clear unsupported-version errors, and exercise v0.1/v0.2 → current update and
uninstall in CI.

#### P1-10 — Consolidate operational review history

The review/status chain is valuable but now long, repetitive, and easy to read
out of chronological context. Several current docs link deep into old status
reports for present behavior.

**Action:** add one maintained `docs/STATUS.md` or `KNOWN_LIMITATIONS.md` with
current capabilities and open gaps. Archive completed review cycles under dated
directories, keeping immutable historical evidence but removing it from the
normal onboarding route.

### P2 — prove usefulness and improve adoption

#### P2-01 — Run real baseline/treatment GPT-5 evaluations

The deterministic scorer is good infrastructure, not evidence that the harness
helps. Implement a pluggable live runner outside the core package, pin model and
prompt versions, run multiple seeds, record cost/turns/context/test score, and
publish raw results. Add tasks that test policy adherence and instruction
conflicts, not only final code correctness.

#### P2-02 — Dogfood in real repositories

Adopt a pinned release in at least two non-fixture repos with different stacks
and one user other than the author. Track install time, overrides, false
positives, update friction, context cost, and abandoned features. Use this
evidence to decide whether link mode, hook enforcement, and profile breadth are
worth expanding.

#### P2-03 — Measure instruction quality, not just file correctness

Add evals for: correct skill triggering, irrelevant-skill avoidance, rule
precedence, refusal to publish without authority, existing-hook preservation,
and resistance to malicious instruction changes. This is the product's actual
differentiator.

#### P2-04 — Add a policy provenance model

For each normative rule, record owner/source, rationale, applicability,
enforcement mechanism, and last review date in structured data. Generate the
human guides from or validate them against that catalog. This is the semantic
equivalent of the successful structured manifest work.

#### P2-05 — Provide composable presets instead of one global opinion set

Offer a minimal safety core plus opt-in modules such as `git-safe`,
`python-production`, `typescript-node`, `observability`, and
`agent-runtime-reference`. Let teams adopt one useful slice without inheriting
UI capitalization, publication workflow, or unrelated language preferences.

#### P2-06 — Improve distribution fit for agent ecosystems

Evaluate a native Claude plugin and native Codex skill/plugin distribution
against npm. npm is convenient as a launcher but unusual as a delivery channel
for Markdown policies and requires Node plus Bash plus Python. Choose channels
based on measured onboarding success, not ubiquity alone.

#### P2-07 — Add telemetry-free local adoption diagnostics

Extend `audit --json` to report client adapter freshness, managed router state,
unsupported profile runner, broken/stale package source, hook ownership, and
state-schema version. Keep it local and deterministic; no remote telemetry is
needed.

#### P2-08 — Publish a concise comparison and migration story

Explain when to use agentharness versus a single `CLAUDE.md`/`AGENTS.md`, a
native agent plugin, dotfiles, a submodule of policy docs, or an organization
template. Include the smallest migration from one existing project and the
ongoing maintenance cost.

## Recommended sequence

### Phase 1 — restore consumer safety

1. Fix hook state/doctor/uninstall ownership (P0-01).
2. Make invalid installs atomic (P0-04).
3. Make npx durable and test cache removal/upgrades (P0-02).
4. Correct the coverage-hook contract (P0-03).
5. Gate release publication on the built artifact (P0-05).

### Phase 2 — make the client product coherent

6. Redesign and test the Codex/GPT-5 adapter (P0-06).
7. Add managed client routers and stable guide references (P1-01).
8. Add Go plus one mainstream JS runner and strict unsupported behavior
   (P1-02).
9. Add lifecycle transition/state migration tests (P1-06, P1-09).
10. Fix current docs and generate a capability matrix (P1-03).

### Phase 3 — prove value before adding breadth

11. Run the existing eval pilot with GPT-5 baseline/treatment conditions.
12. Dogfood a pinned release in two real repositories.
13. Use the evidence to choose native distribution channels and module
    boundaries.
14. Only then expand languages, frameworks, profiles, or agent runtimes.

## Suggested next release gate

A v0.3 candidate should not be called broadly team-ready until all of these are
true:

- uninstall cannot delete consumer-owned configuration;
- a typo cannot produce a healthy empty install;
- npx installs survive deletion of the invoking package/cache;
- consumer-facing hook claims match a real push test;
- release CI tests the exact artifact before publishing;
- current documentation contains no known profile/release/authority
  contradictions;
- one real Codex/GPT-5 session passes skill discovery and context-size checks;
- at least one baseline/treatment eval and one non-fixture adoption report are
  published with limitations.

## Bottom line

The project is worth continuing. Its best assets are no longer just ideas:
there is real tooling, testing, lifecycle management, and an increasingly clear
trust model. The next gain will not come from adding more convention pages. It
will come from making one installation path safe end to end, adapting to the
actual GPT-5/Codex skill model, and producing evidence that agents using the
harness behave better than agents given a small project-local instruction file.
