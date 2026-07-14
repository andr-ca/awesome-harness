---
date: 2026-07-14
status: approved
topic: project-bootstrap-policy
purpose: Design the modular bootstrap, capability profiling, and deterministic enforcement subsystem.
related-harness: tools/setup/harness-link.sh, patterns/profiles/, .github/hooks/
---

# Project bootstrap and deterministic policy design

## Status

This design was approved interactively on 2026-07-14. It defines the
implementation scope; it does not claim that the subsystem exists yet.

The first release builds an extensible plugin framework and proves it with one
production-grade Python plugin. It also makes documentation and changelog
quality first-class requirements. Production plugins for other languages are
deliberately deferred until the contract has been proven by real use.

## Problem

agentharness currently has two different quality stories:

- The harness repository itself runs a broad, hardcoded set of checks through
  `tools/check.sh` and its CI workflow.
- Consumer repositories receive conventions and partial profile enforcement,
  but they do not get one capability inventory, one editable requirements
  profile, or one policy compiled consistently into commit, push, CI, and agent
  completion gates.

The result is useful guidance without a deterministic project-level contract.
Different tools can enforce different subsets, a missing integration can look
like a pass, and an agent can claim completion without machine-readable
evidence tied to the exact revision and requirements it was asked to satisfy.

The new subsystem must bootstrap a project on first use, discover what already
exists, ask the user what should be required, recommend missing capabilities,
and enforce the accepted result consistently. Requirements must be easy to
add, remove, inspect, and modify without making them easy to weaken silently.

## Goals

1. Start bootstrap automatically on first interactive use.
2. Fail clearly in non-interactive CI when bootstrap is incomplete.
3. Inventory linting, logging, observability, configuration, unit testing,
   mutation testing, documentation, and changelog practices.
4. Preserve detected existing checks as the mandatory initial baseline.
5. Recommend improvements without silently turning recommendations into
   requirements.
6. Store accepted requirements in one committed, schema-validated profile.
7. Allow safe machine-local execution overrides without allowing policy
   weakening.
8. Compile the same profile into commit, push, CI, merge, and agent-completion
   enforcement.
9. Protect requirement reductions through repository-host review policy.
10. Emit fresh, machine-readable evidence for every verification decision.
11. Make the language and capability model extensible through plugins.
12. Bootstrap and enforce agentharness itself as the first end-to-end proof.

## Non-goals for the first release

- Production language plugins other than Python.
- Replacing a functioning project tool merely to standardize preferences.
- A hosted control plane, dashboard, or policy service.
- An external policy language such as Rego.
- Perfect semantic proof that an application has good logs or useful traces.
  The harness can verify explicit, evidence-backed requirements; it must not
  overstate what static discovery proves.
- Making local Git hooks impossible for the machine owner to bypass. Remote CI
  and protected-branch policy are the authoritative controls.
- Automatic merging of the initial bootstrap proposal or later policy changes.
- Cross-host protection automation. GitHub is the first remote adapter.

## Approved product decisions

| Area | Decision |
|---|---|
| Ownership | Detect and run existing tools, and generate defaults where capabilities are missing. |
| Enforcement audience | Apply to agents, local Git activity, CI, and protected merges. |
| Unbootstrapped default | `strict`; also implement selectable `warn` and `grace` modes. |
| Configuration | Commit `.agentharness-policy/profile.yaml`; allow a gitignored `.agentharness.local.yaml` with non-policy presentation/performance overrides only. The namespace deliberately avoids the existing `.agentharness/` submodule path. |
| Initial ecosystem | Build the plugin framework and a complete Python plugin first. |
| First-use behavior | Start automatically in an interactive local session; fail fast with remediation in non-interactive CI. |
| Initial requirements | Detected existing checks become required automatically; new recommendations require acceptance. |
| Requirement reductions | Require a designated reviewer through `CODEOWNERS` and branch protection. |
| GitHub setup | Apply protection automatically after profile confirmation; fall back to a preview-and-confirm/resume flow when automatic application cannot complete. |
| Expensive checks | Use layered gates: fast at commit, broader at push, complete in CI and at agent completion. |
| Documentation | Documentation and changelog are first-class, diff-aware requirement modules. |

## Terminology

- **Capability:** A project practice the harness can detect or recommend, such
  as linting, structured logging, or mutation testing.
- **Finding:** A discovery result with evidence and a confidence level.
- **Requirement:** A user-accepted, machine-verifiable policy statement.
- **Recommendation:** A proposed addition or migration that is not binding
  until accepted.
- **Gate:** An enforcement point: `commit`, `push`, `ci`, or `completion`.
- **Evidence:** A result bound to the exact inputs, tools, profile, and gate
  that produced it.
- **Reduction:** Removing a requirement, lowering a threshold, narrowing its
  scope, or removing it from a gate.
- **Bootstrap proposal:** The initial profile and generated integration changes
  before they have reached the default branch and remote protection is active.
- **Plugin:** A trusted executable extension that detects capabilities,
  supplies schema, proposes requirements, and verifies them.

## Architecture

The subsystem is a Python core behind the existing `agentharness` command.

```text
bin/cli.js (npm/npx distribution shim)
              |
              v
      Python bootstrap core
       |       |        |
       |       |        +--> remote adapters (GitHub first)
       |       +-----------> policy compiler and verifier
       +-------------------> plugin registry
                                  |
                                  +--> Python plugin
                                  +--> core capability plugins
                                  +--> future language plugins
```

The core owns:

- Project-root and environment detection.
- Bootstrap state and resumable transactions.
- Interactive questions and non-interactive failure behavior.
- Profile schema validation and migrations.
- Plugin discovery, trust, compatibility, and contract validation.
- Recommendation resolution and user confirmation.
- Policy compilation and evidence handling.
- Git hook, CI, completion, and remote-protection adapters.
- Drift detection and repair planning.

Plugins own:

- Capability-specific discovery.
- Evidence-backed findings and confidence.
- Capability-specific bootstrap questions.
- Requirement schema fragments and defaults.
- Generated configuration proposals.
- Gate commands and verification logic.
- Human-readable explanations and remediation.

### Distribution boundary

The npm package and `npx agentharness-toolkit` remain the low-friction entry
point. `bin/cli.js` remains a thin launcher, but invokes the packaged Python
entry point for new commands. Existing Bash lifecycle commands can delegate to
the new core during migration; they must not become a second policy engine.

The packaged runtime must be self-contained and reproducible. The implementation
plan must choose and test one concrete packaging method, such as a Python
zipapp containing pinned pure-Python runtime dependencies. Bootstrap must not
silently run an unpinned `pip install` on a consumer machine. Both a Git checkout
and an npm tarball must execute the same core and schema version.

Every bootstrapped project commits
`.agentharness-policy/runtime.lock`, containing:

- The exact `agentharness-toolkit` package version, never a range or tag.
- The registry and published tarball integrity digest.
- The exact core, schema, bundled-plugin, and compatibility-provider versions.
- The approved acquisition source or an integrity-equivalent mirror.

Generated CI uses a small standard-library bootstrapper stored under
`.agentharness-policy/bootstrap/`. For pull requests, the workflow loads that
bootstrapper and the authoritative lock from the base commit, not from the
untrusted head tree. The bootstrapper:

1. Fetches the exact tarball URL without invoking npm lifecycle or package code.
2. Computes and compares the committed SHA-512 integrity before extraction.
3. Rejects absolute paths, traversal, links escaping the extraction root, and
   unexpected archive layout.
4. Extracts into an isolated temporary directory.
5. Launches the verified entry point with the lock and gate request.

`npm exec` is convenient for interactive installation, but is explicitly not
the authoritative CI acquisition path because it can execute package code
before the launched CLI performs a self-check. The verified CLI still checks its
internal core/plugin/schema identity after launch as defense in depth.

The bootstrapper, lock, workflow namespace, and acquisition settings are
protected policy surfaces. The one-time initial bootstrap proposal uses the
already confirmed installer runtime because no base bootstrapper exists yet;
that trust-establishment exception ends once the first profile is active.

An unavailable or mismatched artifact is an error in strict mode, not a skip or
an implicit upgrade. Offline CI requires a configured mirror/cache whose
artifact matches the committed digest. Runtime upgrades use dual verification:
the base-locked runtime remains authoritative for the upgrade PR, while the
candidate artifact is independently fetched, digest-checked, and runs the full
contract/migration suite. A breaking schema upgrade first lands a
backward-compatible runtime, then changes schema in a later PR; the repository
never depends on a candidate that the base runtime cannot assess.

Consumer enforcement always follows the lock, even when skills and guidance are
installed through link or submodule mode. A source-checkout development runtime
is allowed only for agentharness's own tests, where CI proves that its built
artifact and declared version match the lock.

The public command name is the existing `agentharness` binary. Examples in this
document use that canonical name.

## Bootstrap lifecycle

### Entry behavior

`agentharness init` installs the harness and immediately begins bootstrap when
the session is interactive. For an already-installed project, the first normal
mutating or enforcement command notices that
`.agentharness-policy/profile.yaml` is absent and routes to bootstrap.
Diagnostic commands such as `status` report the unbootstrapped state and offer
the bootstrap command without hiding their requested output.

The following commands remain available while strict bootstrap is incomplete:

- `agentharness bootstrap`
- `agentharness bootstrap --resume`
- `agentharness plan`
- `agentharness status`
- `agentharness doctor`
- `agentharness plugins list`
- Read-only `agentharness profile show|explain|validate`

Other project-mutating commands and normal verification gates are blocked in
`strict` mode. CI never opens a questionnaire. An absent profile means strict
by default and exits non-zero with the exact local bootstrap command, except for
the narrowly defined initial bootstrap proposal below. An invalid confirmed
profile always fails. A valid confirmed `warn` profile reports findings but does
not fail capability checks; `grace` does the same until its deterministic
deadline or budget is exhausted.

### State machine

```text
unbootstrapped
      |
      v
discovering --> questioning --> proposed --> applying-local
                                              |
                                              v
                                      pending-default-branch
                                              |
                                              v
                             verifying-default-branch-ci
                                              |
                                              v
                                      applying-remote
                                              |
                         +--------------------+------------------+
                         |                                       |
                         v                                       v
                  active-and-verified                  drifted-or-incomplete
                                                                 |
                                                                 v
                                                              resume
```

Temporary transaction state lives in the gitignored
`.agentharness-local/bootstrap-state.json`. It contains no secrets and is not a
policy source. The committed profile becomes authoritative after confirmation;
`active` is a computed state, not a mutable field in that profile. It requires a
valid confirmed profile on the default branch, a successful full CI result for
that exact revision/profile/runtime, and verified remote protection. Bootstrap
writes files through a staged plan and recovery journal so an interruption can
resume without guessing which steps succeeded.

The initial bootstrap PR is detected only when the base branch has no profile,
the PR adds a confirmed profile/runtime lock/generated integration, and the diff
contains no unrelated product changes. Its dedicated bootstrap-proposal CI mode
runs schema, runtime, profile, and all locally executable capability checks, but
reports remote activation as `pending` rather than failing. After that proposal
merges, bootstrap waits for default-branch CI, applies protection, reads it back,
and computes the project as active without requiring a second status-changing
commit. A second initial-proposal exception is rejected.

### Bootstrap modes

The same discovery and verification logic powers all modes.

- `strict`: only bootstrap and diagnostic operations are allowed until the
  policy is active. This is the default for a newly linked project.
- `warn`: normal activity continues, but every unmet requirement and missing
  enforcement layer is visible and recorded as advisory.
- `grace`: normal activity continues until the earlier of a committed UTC
  deadline or commit allowance. The profile records `anchor_sha`, `started_at`,
  `expires_at`, and `max_new_commits`. The count is the non-merge commits in
  `anchor_sha..effective_head`; staged commit checks include the proposed tree,
  and remote gates use the tested head SHA. The protected default branch forbids
  force pushes. An unreachable anchor, shallow history that cannot prove the
  count, or an expired deadline fails strict. CI time is authoritative; local
  clock evaluation can warn earlier but cannot extend grace.

Changing from strict to a weaker mode after the initial profile is active is a
requirement reduction and follows protected-policy review.

### Bootstrap phases

1. **Locate:** Resolve the project root, install state, Git repository, default
   branch, remotes, CI provider, and interactive/non-interactive context.
2. **Discover:** Run trusted plugins in read-only mode and collect findings.
3. **Preserve:** Convert runnable existing checks into mandatory proposed
   requirements with evidence showing where each check came from.
4. **Recommend:** Rank missing capabilities by compatibility, rigor tier,
   benefit, cost, and migration risk.
5. **Question:** Ask only questions that discovery cannot answer safely.
6. **Resolve:** Show detected requirements, accepted additions, deferred
   recommendations, generated files, gate cost, and remote changes separately.
7. **Confirm:** Require explicit confirmation of the complete profile.
8. **Apply locally:** Write the profile and generated integrations atomically,
   then verify them.
9. **Publish proposal:** When publication is authorized, create the bootstrap
   branch/PR through the normal repository workflow. Without publish authority,
   stop at a verified local proposal and report the required next action.
10. **Activate:** After the bootstrap proposal reaches the default branch,
    wait for its full default-branch CI result, apply GitHub protection
    automatically, read it back, and compute the project as active.

The initial bootstrap proposal is a necessary trust-establishment exception:
remote policy cannot protect a profile and workflow that do not yet exist on
the default branch. The proposal may be committed and pushed for review, but no
agent may call bootstrap complete until the profile is on the default branch,
remote protection is verified, and the full activation check passes.

## Discovery and recommendation model

Discovery is read-only. A plugin may inspect tracked files, declared
dependencies, configuration, scripts, source usage, CI definitions, and Git
metadata. It may run commands explicitly classified as diagnostic and free of
project mutation. Commands with side effects belong in the confirmed apply or
verification phase.

Every finding contains:

```yaml
capability: lint
plugin: python
state: configured
confidence: high
evidence:
  - kind: file
    path: pyproject.toml
    selector: tool.ruff
  - kind: ci-command
    path: .github/workflows/ci.yml
    value: ruff check .
```

Allowed capability states are `absent`, `detected`, `configured`, `executed`,
and `enforced`. These states prevent the harness from equating an installed
package with a working gate. Confidence is `high`, `medium`, or `low`; only a
high-confidence, runnable check becomes mandatory automatically. Lower
confidence findings become questions or recommendations.

Recommendations include:

- The proposed tool or approach.
- Why it fits the detected project.
- Alternatives considered.
- Files and dependencies it would change.
- Expected runtime at each gate.
- Benefits, migration risk, and operational cost.
- The exact requirement that acceptance would create.

The recommendation engine prefers the smallest coherent improvement. It keeps
a functioning Flake8 setup rather than silently replacing it with Ruff, for
example. Consolidation can be recommended, but migration is never inferred
from a preference alone.

## Bootstrap questions

Questions are generated from findings, but the core guarantees coverage of:

1. Project rigor tier and any path-specific exceptions.
2. Bootstrap mode and, for grace mode, deadline or commit allowance.
3. Which detected commands are intentional and should remain required.
4. Which proposed missing capabilities the user accepts.
5. Thresholds, scope, and gate placement for accepted requirements.
6. Documentation surfaces and which change types require updates.
7. Changelog strategy and which change types require entries.
8. Protected code owners and the repository-wide total approval count for
   policy reductions.
9. Agent completion and publication expectations.
10. Remote protection changes and the GitHub repository to configure.

Existing runnable checks are selected by default and become binding without an
extra opt-in. The user can challenge a false-positive detection before final
confirmation; removing a check after activation is a protected reduction.

## Committed profile

`.agentharness-policy/profile.yaml` is the single project policy source. It is
versioned, schema-validated, human-readable, and editable through both normal
text review and CLI operations.

```yaml
schema_version: 1

runtime:
  lock: .agentharness-policy/runtime.lock

project:
  name: example
  rigor: production

bootstrap:
  mode: strict
  confirmed_at: 2026-07-14T00:00:00Z
  existing_checks_are_required: true

plugins:
  python:
    enabled: true
    version: 1.0.0
    config: {}

requirements:
  lint:
    provider: python
    enabled: true
    tool: ruff
    command: [ruff, check, .]
    gates: [commit, push, ci, completion]

  logging:
    provider: python
    enabled: true
    standard: structured
    checks: [central_config, context_fields, redaction]
    gates: [ci, completion]

  observability:
    provider: python
    enabled: true
    checks: [health_check, error_reporting]
    gates: [ci, completion]

  configuration:
    provider: core
    enabled: true
    checks: [env_sample, secret_scan, schema_validation]
    gates: [commit, ci, completion]

  unit_testing:
    provider: python
    enabled: true
    command: [pytest]
    minimum_coverage: 80
    gates: [push, ci, completion]

  mutation_testing:
    provider: python
    enabled: true
    tool: mutmut
    command: [mutmut, run]
    minimum_score: 70
    gates: [ci, completion]

  documentation:
    provider: core
    enabled: true
    checks: [readme_present, internal_links_valid, public_changes_documented]
    gates: [ci, completion]

  changelog:
    provider: core
    enabled: true
    strategy: fragments
    required_for: [feature, fix, breaking_change]
    gates: [ci, completion]

workflow:
  reviews:
    expected_signals:
      - type: check
        name: Copilot Code Review
        allowed_conclusions: [success, neutral]
    timeout_seconds: 900
    stabilization_seconds: 60
  completion:
    require_clean_tree: true
    require_committed_changes: true
    publication: follow_publish_authority
    require_current_ci: true
    require_resolved_reviews: true

protection:
  provider: github
  default_branch: main
  requirement_reductions:
    codeowners: ["@project-maintainers"]
    require_codeowner_approval: true
    minimum_total_approvals: 1
  waivers:
    require_expiry: true
    require_reason: true
```

### Schema rules

- Unknown top-level keys fail validation unless namespaced to a registered
  plugin extension point.
- `runtime.lock` resolves to exact compatible core, schema, bundled-plugin, and
  compatibility-provider identities.
- Every requirement declares its provider, enabled state, verifiable settings,
  and at least one gate.
- A requirement cannot name a plugin that is disabled or incompatible.
- Strict CI and completion gates cannot depend on manual-only attestations.
- Thresholds have plugin-defined ranges and comparison semantics.
- Gate names are closed in schema version 1.
- Timestamps use UTC ISO 8601.
- Commands are argument arrays, not shell strings, unless a plugin explicitly
  declares and validates shell execution.
- The profile never stores credentials or tokens.

### Local overrides

`.agentharness.local.yaml` is gitignored and uses a separate restrictive schema.
Version 1 allows only presentation and performance hints: concurrency, output
format, color, and a verifier-bounded local timeout. It does not allow executable
substitution, command arguments, tool versions, arbitrary environment values,
cache locations/results, or network result substitution. A timeout can turn a
run into an error, never a pass. It may not alter requirements, thresholds,
gates, bootstrap mode, protection, waivers, or completion policy.

Validation computes the effective profile and rejects any local value outside
the operational allowlist. It does not attempt a generic merge followed by a
best-effort comparison; the schema makes weakening fields unrepresentable.

### Profile operations

```text
agentharness profile show
agentharness profile explain <requirement>
agentharness profile add <capability>
agentharness profile remove <capability>
agentharness profile set <path> <value>
agentharness profile validate
agentharness profile diff
```

Every mutating command defaults to a preview and accepts an explicit apply
action. Direct edits remain supported, because the schema and gates—not the
editor—provide safety. Removing or weakening policy creates a reduction
proposal and explains the required review path.

### Provenance and history

Questionnaire answers, discovery evidence, recommendation dispositions, and
policy-change rationales are stored separately under
`.agentharness-policy/history/`. The active profile remains concise. History
files are committed, contain no secrets, and identify the profile hash they
produced.

The history is an audit record, not a second source of active requirements.
Changing it never changes enforcement.

### Migration from `.agentharness-profile`

The existing one-line rigor selector is an input to bootstrap, not a permanent
parallel policy source. Bootstrap imports its tier into the proposed YAML
profile and shows the resolved requirements.

Python projects migrate to the Python plugin. Existing Go, Node test, and Vitest
enforcement is preserved by a bundled, version-pinned compatibility provider
that runs the current supported checks as a mandatory composite requirement
under the new core and evidence model. This provider is not a second CLI or
policy engine: gate selection, result semantics, runtime locking, and evidence
remain owned by the new core. It is removed only after an equivalent production
plugin has migrated that project successfully.

An ecosystem the new core cannot migrate enters a schema-defined
`legacy-deferred` compatibility state. Bootstrap still writes the YAML profile
for core capabilities, but declares the legacy selector's path/hash and the
locked legacy command as a mandatory compatibility requirement. The old file is
a material input, normal commands no longer treat the project as
unbootstrapped, and `status` reports exactly which language enforcement remains
deferred. This is the only valid coexistence state; it preserves behavior while
keeping the new core responsible for gates and evidence.

When migration can preserve every enforced check, the old file is removed in
the same proposal. If both files exist outside an active migration transaction
or declared `legacy-deferred` requirement, validation fails rather than
guessing precedence. `enforce-profile` delegates to the locked core/provider
after migration.

Bootstrap also audits the current precedence sources. It imports recognized
path-specific exceptions from repository instructions into structured profile
scopes. Free-form or conflicting exceptions block confirmation and require the
user to resolve them explicitly. After activation, explicit session
instructions may strengthen the committed profile. Weakening it requires a
protected profile change or waiver; generated agent instructions reference this
rule so prose and mechanical policy cannot silently disagree.

## Plugin contract

Each plugin publishes metadata and implements a versioned contract resembling:

```python
class HarnessPlugin(Protocol):
    metadata: PluginMetadata

    def detect(self, context: DiscoveryContext) -> list[Finding]: ...
    def questions(self, findings: list[Finding]) -> list[Question]: ...
    def recommend(self, context: RecommendationContext) -> list[Recommendation]: ...
    def schema(self) -> dict[str, object]: ...
    def plan(self, requirements: dict[str, object]) -> ChangePlan: ...
    def verify(self, request: VerificationRequest) -> list[CheckResult]: ...
    def explain(self, result: CheckResult) -> Remediation: ...
```

The final names may change during implementation, but these responsibilities
and boundaries are part of the design.

Plugin metadata declares:

- Stable identifier and display name.
- Plugin version and compatible core/schema range.
- Capabilities provided.
- Detection permissions and possible command execution.
- Generated file ownership and merge strategies.
- Runtime dependencies.
- Whether the plugin is bundled or third-party.

Plugins return data; they do not directly edit the project during discovery or
planning. The core owns confirmation, transactions, file conflict handling,
redaction, and evidence persistence.

### Trust model

Bundled plugins are trusted as part of the pinned harness release. Third-party
plugins execute project-level code and therefore require explicit trust by
identifier and version. CI refuses an unpinned or newly introduced plugin until
the committed profile records it and the policy-change review succeeds.

Plugin discovery does not import arbitrary modules found in the consumer
repository. Installation and trust are explicit operations.

### Generated files

Each generated change declares one of these strategies:

- `create`: fail if an unfamiliar file already exists.
- `managed-block`: edit only a clearly marked harness-owned region.
- `structured-merge`: modify owned keys in a parsed format and preserve
  unrelated data.
- `proposal-only`: produce a patch for manual resolution.

Unknown content is never overwritten. A conflict pauses apply and leaves the
confirmed plan resumable.

## First production plugin: Python

The Python plugin must cover the complete approved capability set rather than
only lint and tests.

| Capability | Discovery examples | Verification/recommendation scope |
|---|---|---|
| Project environment | `pyproject.toml`, `setup.py`, requirements files, uv, Poetry, Pipenv, tox, nox | Identify authoritative dependency and task entry points. |
| Lint/format | Ruff, Black, Flake8, Pylint, isort, CI and task commands | Preserve runnable checks; recommend the smallest coherent missing baseline. |
| Type checking | mypy, Pyright, configured strictness | Record actual command and scope; do not infer strictness from dependency presence. |
| Logging | standard `logging`, structlog, Loguru, configuration, context propagation, unsafe ad-hoc output | Distinguish package presence from centralized, tested configuration; recommend by rigor and application type. |
| Observability | OpenTelemetry, Sentry, metrics, traces, health checks, error reporting | Record evidence and confidence separately; avoid claiming semantic coverage from imports alone. |
| Configuration | environment loading, typed settings, `.env.sample`, schema validation, secret scanning | Prefer an existing settings system; propose safe defaults only when absent. |
| Unit testing | pytest, unittest, coverage, test layout, CI commands | Capture the real runner and threshold; recommend pytest only when no established runner exists. |
| Mutation testing | mutmut, Cosmic Ray, exclusions, baseline, CI use | Run only at configured expensive gates; explain runtime cost and surviving mutants. |
| Documentation | README, docstrings, MkDocs, Sphinx, link checks, API/public-change coverage | Use diff-aware triggers and existing documentation tooling. |
| Changelog | `CHANGELOG.md`, Towncrier or similar fragments, release conventions | Preserve the established strategy or recommend fragments for concurrent work. |

Detection must recognize task indirection such as Make, tox, nox, and package
scripts. The mandatory requirement should invoke the project's stable public
task where one exists instead of bypassing it with a guessed raw command.

For every indirect command, discovery records material policy inputs: the task
definition, tool configuration, dependency lock, included scripts, and the
resolved underlying tool/effect when it can be proven. Policy integrity hashes
those inputs. A change to an opaque task or a change that weakens the resolved
tool/effect is a protected reduction even when the command string is unchanged.
Where the plugin can safely unwrap the task, verification also confirms the
expected underlying tool and material arguments rather than trusting a target
name such as `lint`.

Generated defaults are proposals. Typical options may include Ruff, mypy or
Pyright, pytest with coverage, mutmut or Cosmic Ray, standard-library structured
logging, OpenTelemetry, typed settings, MkDocs or Sphinx, and changelog
fragments. The plugin explains trade-offs and does not declare one stack best
for every Python project.

## Core capability plugins

Language-independent core plugins cover:

- Repository and Git policy.
- Configuration hygiene and secret scanning integration.
- Documentation structure and link validation.
- Changelog strategy and diff-aware entry requirements.
- Existing composite commands, such as this repository's `tools/check.sh`.

Logging and observability requirements can combine a core policy vocabulary
with language-plugin verification. This keeps the accepted meaning stable while
allowing Python, Go, or TypeScript to collect different evidence later.

### Documentation policy

Documentation requirements are change-aware. Bootstrap asks which paths and
change classifications correspond to public behavior, architecture, operations,
and APIs. A requirement can then verify, for example, that a public feature
change updates an owned documentation surface or carries an approved exemption.

The module also supports deterministic checks such as required entry points,
internal-link validation, snippet validation, generated-document drift, and
documentation build commands.

It must not require a meaningless documentation edit for every refactor. If the
diff classifier cannot decide confidently, it asks for an explicit change
classification in the PR rather than guessing.

### Changelog policy

Bootstrap detects monolithic changelogs and fragment-based systems. The user
chooses the change classes that require entries, such as features, fixes, and
breaking changes. Internal refactors and test-only changes can be excluded.

For a monolithic changelog, the verifier checks the expected file. For fragment
workflows, it checks for a valid fragment and delegates release aggregation to
the project's existing tool. An approved `no-changelog` classification is
auditable and cannot be an undocumented skip flag.

### Canonical change range and classification

Diff-aware requirements use an explicit base and head:

- `commit`: `HEAD` to the proposed staged tree.
- `push`: the remote-reported old SHA to new SHA for each updated ref; a new
  branch uses its merge base with the configured default branch.
- Pull-request CI: the event's immutable base SHA/merge base and head SHA.
- Default-branch CI: the push event's before and after SHAs.
- `completion`: the current PR base/head when a PR exists; otherwise the
  upstream merge base and local head. If no unique authoritative base exists,
  completion fails with a command to select one explicitly.

The evidence record includes both SHAs, the merge-base algorithm/version, and a
canonical hash of the classified change set. The hash is SHA-256 over sorted,
NUL-delimited tuples of path, change/rename status, old/new mode, and old/new
blob object ID. All paths under `.agentharness-policy/changes/` are excluded
from this tuple stream so a classification record never hashes itself. No other
path or field is omitted. The classification files remain bound separately by
the head commit and effective-policy hash. Rebasing, changing either endpoint,
or changing any non-classification blob invalidates the classification.

The authoritative classification is a committed
`.agentharness-policy/changes/<change-id>.yaml` record, not a mutable PR label or
free-form body. It declares change classes, affected requirements, and any
`no-documentation` or `no-changelog` disposition with reason and required
approver. CI binds it to the computed diff hash. PR metadata can improve UX, but
cannot replace the committed record. A missing or stale classification fails
when the profile requires one.

## Policy compilation and gates

Every enforcement layer calls the same verifier:

```text
agentharness verify --gate commit
agentharness verify --gate push
agentharness verify --gate ci
agentharness verify --gate completion
```

Hooks and workflows contain invocation plumbing, not copied requirements.

### Commit gate

The commit gate operates on the staged tree and runs requirements assigned to
`commit`, normally formatting/linting, configuration validation, secret checks,
and targeted fast tests. It reports unstaged dependencies that would make the
staged result misleading.

The input fingerprint uses the staged tree object plus the effective profile,
plugin versions, tool versions, and relevant environment—not merely the current
HEAD commit.

### Push gate

The push gate operates on each outgoing revision range and normally runs broader
linting, typing, unit tests, coverage, and profile-integrity checks. It fails if
the required CLI/runtime is missing rather than silently skipping a configured
requirement.

### CI gate

The CI gate is authoritative for merge protection. It runs the complete
applicable profile, including expensive mutation, documentation, changelog, and
repository-policy requirements. Independent jobs may execute in parallel, but
their result set is assembled and evaluated against one profile hash.

Stable, repository-unique GitHub check names include at least an overall policy
check and a policy-integrity check. No other workflow may reuse those job names.
Branch protection requires them after their first successful run establishes
the contexts and pins the expected GitHub App source where the API supports it.

Because all GitHub Actions workflows share that App identity, App pinning alone
is not an identity boundary. The base-locked policy-integrity verifier parses
the complete `.github/workflows/` namespace and rejects any duplicate required
job name. CODEOWNERS protects that entire namespace plus local actions,
bootstrapper code, and scripts/configuration capable of producing or changing a
required result. GitHub uses the base branch's CODEOWNERS for the PR, so a head
workflow that emits a colliding success still cannot merge without the protected
review. Where an organization plan supports a ruleset-required workflow pinned
to a protected source repository/ref, the adapter prefers that stronger
identity. If neither required-workflow identity nor enforceable ownership of all
status-producing inputs is available, strict remote activation fails rather
than claiming an unspoofable gate.

### Completion gate

The completion gate runs the full applicable policy and then checks workflow
state configured under `workflow.completion`:

- Working tree and index state.
- Whether requested changes are committed.
- Whether publication is authorized and, if so, current.
- Current CI for the exact revision.
- Required PR approvals that apply to the current head SHA, with stale
  approvals dismissed when the profile requires it.
- No blocking `CHANGES_REQUESTED` or pending required review.
- No unresolved inline review thread.
- An auditable assessment reply for every issue-level PR comment and inline
  review comment in scope.
- Fresh evidence for every required capability.

Before enumerating reviews or comments, completion waits for every configured
`workflow.reviews.expected_signals` entry to reach an allowed terminal state for
the current PR/head. Signals can name a check run, review author, or installed
review App. After the final signal/comment, the gate re-fetches after the
configured stabilization interval and requires no new review activity. Missing,
pending, failed, or timed-out expected review is an error with remediation, not
evidence that there were zero findings. A protected waiver is required to
proceed when an expected reviewer is unavailable.

Top-level PR comments have no native resolved state. The harness therefore
tracks acknowledgement, not resolution: `agentharness review acknowledge`
posts a reply containing a stable hidden marker for the source comment ID plus
the assessment and action/commit. Inline comments use GitHub's direct reply
relationship and the same marker. Completion fetches both comment APIs and
review-thread state for the current PR, correlates every comment with a later
acknowledgement, and rejects stale acknowledgements whose claimed action no
longer applies to the current head. This implements the repository's existing
reply-to-every-comment policy instead of treating conversation resolution as a
substitute.

Acknowledgement replies, harness-generated status comments, superseded bot
status updates, and comments by the current actor on its own PR are excluded by
explicit typed rules so acknowledgement does not recurse. Review findings from
humans or automated reviewers are never excluded merely because their author is
a bot.

When exact-commit CI evidence already covers every full-profile requirement,
the completion gate may consume that authoritative evidence instead of rerunning
expensive mutation checks locally. It still evaluates publication, review, and
working-tree state itself.

The completion gate never grants publication authority. It follows the existing
explicit-request or `.agentharness-publish-mode` policy. Without authority it
can report `verified locally; publication awaiting authorization`, but an agent
must not misreport that state as published completion.

## Evidence model

Each check produces a structured record containing:

- Profile and effective-policy hashes.
- Staged-tree fingerprint or commit SHA, as appropriate.
- Gate and requirement identifier.
- Plugin, core, and tool versions.
- Command arguments or non-command evidence type.
- Start/end timestamps and duration.
- Result: pass, fail, warn, not-applicable, or error.
- Redacted diagnostic summary and remediation.

Local evidence is stored under the gitignored
`.agentharness-local/evidence/` directory. CI publishes the same schema as
build artifacts and check output. Evidence is not accepted when the code
fingerprint, comparison base, classification, policy, runtime, plugin, tool
version, or material input set changes.

`not-applicable` is valid only when the profile's scope expression excludes the
current change. `error` never becomes a pass. In strict mode, a verifier that
cannot run fails closed with a precise remediation.

The first release does not need cryptographic signing for local evidence.
GitHub's association of CI results with an immutable commit is the authoritative
remote binding. A future remote backend may add attestations without changing
the result schema.

## Policy changes, reductions, and waivers

### Additions

Adding or strengthening a requirement is a normal reviewed policy change. Its
new checks must pass in the proposing PR before merge unless the change uses an
explicit staged-activation date.

### Reductions

A semantic diff classifies these as reductions:

- Disabling or deleting a requirement.
- Lowering a threshold.
- Removing a gate.
- Narrowing scope or adding an exclusion.
- Weakening bootstrap, completion, protection, or waiver rules.
- Replacing a verifier with one that supplies weaker evidence.
- Changing the runtime lock, plugin/provider identity, material task
  definition, tool configuration, dependency lock, generated enforcement
  workflow, or canonical agent-policy source in a way that weakens evidence.
- Weakening ownership of `.github/CODEOWNERS` or any protected policy surface.

The CLI labels the proposal and identifies required code owners. Version 1 uses
the semantics GitHub actually provides: at least one approval from any matching
code owner, plus a separately configured minimum number of total approving
reviews. It does not claim that GitHub requires multiple approvals from a
specific owner set. A future trusted approval-validation check is required
before offering that stronger policy. Direct profile edits receive the same
semantic classification in CI.

A reduction proposal must be committable and pushable so it can be reviewed.
This is a narrow exception to normal failing policy: the diff may contain only
the profile/runtime/history/change record, registered material task definitions
and tool/dependency configuration, protected workflows/CODEOWNERS/canonical
agent-policy source, and deterministic generated outputs required by those
changes. It must identify its rationale and cannot satisfy the completion gate
or merge until protected approval and all non-reduced requirements pass.
Unregistered product/source changes or unrelated cleanup cannot hide inside the
exception.

### Waivers

There is no general `--skip`, secret environment variable, or local bypass that
satisfies strict CI. A waiver is committed policy data containing:

- Requirement and scope.
- Reason and owner.
- Creation and expiry timestamps.
- Approver required by protection policy.
- Optional tracking issue.

Expired, malformed, overly broad, or unapproved waivers fail policy integrity.
Emergency repository-host administrator bypasses remain visible in host audit
logs and are outside what local software can prevent.

## GitHub protection adapter

After the profile confirmation and initial policy PR reaches the default
branch, the adapter attempts automatic setup through authenticated GitHub APIs.
It manages only the settings in its confirmed plan:

- Required status checks.
- Pull-request review requirements.
- Required code-owner review for protected policy paths.
- Direct-push restrictions on the default branch.
- Conversation-resolution requirements when supported.
- `CODEOWNERS` entries for the profile, runtime lock, history, change
  classifications, schemas, plugins/providers, material task/configuration
  inputs, canonical agent-policy source, the entire `.github/workflows/`
  namespace, local Actions/status-producing scripts, enforcement integration,
  and `.github/CODEOWNERS` itself.

GitHub's code-owner rule is modeled precisely: one matching code-owner approval
is sufficient, while the branch-level approval count is a total-review count.
The adapter validates that configured owners have the required repository
access and that the base branch's CODEOWNERS file is syntactically active before
reporting protection as verified. This follows GitHub's documented
[CODEOWNERS and branch-protection semantics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners#codeowners-and-branch-protection).

The adapter reads current settings first, computes a minimal diff, applies it,
then reads the settings back. It never replaces unrelated branch rules merely
because they were not in the harness profile.

If `gh` is unauthenticated, the caller lacks administration permission, the
remote is not GitHub, or the API cannot express the policy, bootstrap records
the exact incomplete step and falls back to the approved preview-and-confirm
flow. It shows the remote diff and remediation, then resumes automatic apply
after credentials or permissions are corrected. Strict bootstrap remains
incomplete until read-back proves enforcement is active.

GitHub tokens are never written to the profile, history, logs, or evidence.

## Generated integrations

The policy compiler generates or manages:

- Thin pre-commit and pre-push dispatchers that invoke the installed CLI.
- A GitHub Actions workflow that invokes the CI gate.
- Stable check-context configuration.
- Managed `CODEOWNERS` entries.
- A managed block in the project's canonical agent-instruction source that
  invokes the completion gate.
- Gitignore entries for local state, overrides, caches, and evidence.

Generated artifacts carry the schema/core version and a content hash. `doctor`
can distinguish an intentional user edit from generated drift. Where a project
already has a hook dispatcher or CI workflow, the compiler uses a managed block
or proposal rather than replacing the file.

Generated agent outputs are never edited directly. Bootstrap identifies the
authoritative source (for this repository, `CLAUDE.md`), updates only its managed
policy block, then invokes the repository's existing generators for `AGENTS.md`,
Gemini, Copilot, Cursor, Kilo, and other adapters. A consumer with a different
canonical source records that source in the profile. If no safe source/generator
relationship can be proven, the compiler emits a proposal and keeps bootstrap
incomplete rather than editing multiple client files independently.

## Decommission and uninstall

Uninstalling an active policy is itself a protected reduction and uses a
resumable three-PR transaction:

1. `agentharness decommission plan` creates the protected intent PR **and**
   installs a pinned, minimal decommission workflow/provider. The normal policy
   checks remain required. The temporary producer runs successfully on that PR
   and again on the resulting default-branch commit; its job name, App source,
   runtime digest, and expected intent are read back before anything depends on
   it.
2. After PR 1 merges and the temporary context is proven, an authorized
   operator resumes. The adapter snapshots current remote settings and replaces
   the normal harness required contexts with the already-established temporary
   context while retaining ordinary PR review and direct-push protection.
3. PR 2 removes normal policy artifacts but deliberately keeps the temporary
   workflow/provider, base bootstrapper/runtime lock, and approved intent. The
   temporary check succeeds only for the expected removal diff; unrelated
   changes fail.
4. Immediately after PR 2 merges, resume removes the temporary required context
   and reads branch/ruleset protection back. Only after no rule references that
   context does PR 3 remove the temporary producer, lock/bootstrapper, and
   intent.
5. After PR 3 merges, resume verifies no deleted check remains required and
   removes local runtimes/state.

The transaction reports its unavoidable, audited protection transition
explicitly: disabling policy cannot be atomic with merging the commit that
removes its workflow through GitHub's separate APIs. The approved intent,
isolated diffs, retained general branch protection, proven temporary producer,
read-back, and minimal transition window are the safety boundary. Before PR 2
merges, rollback restores the remote snapshot and cancels the intent. After PR 2
merges, reinstall uses normal bootstrap rather than pretending removed artifacts
can be restored from local state.

## Commands and user experience

```text
agentharness bootstrap [--resume]
agentharness status [--json]
agentharness doctor [--repair]
agentharness recommend [--json]
agentharness profile <operation>
agentharness verify --gate <gate> [--json]
agentharness plugins list|inspect|trust|remove
agentharness protection plan|apply|verify
agentharness decommission plan|--resume
```

`status` separates four concepts instead of collapsing them into one pass/fail:

1. Discovered project capabilities.
2. Active requirements and gate placement.
3. Deferred recommendations.
4. Enforcement drift and evidence freshness.

`doctor` diagnoses invalid schemas, missing dependencies, plugin incompatibility,
hook drift, CI drift, GitHub-protection drift, stale evidence, and illegal local
overrides. `--repair` produces a plan first and applies only confirmed changes.

Machine-readable output uses stable result codes and JSON schemas. Human output
leads with the outcome and exact next action.

## Failure handling and recovery

Bootstrap is a resumable transaction, not one irreversible script:

- Discovery and planning do not mutate the project.
- Confirmation freezes a plan hash.
- Local writes use temporary files and atomic replacement where the platform
  supports it.
- Before modifying an existing file, the transaction records its hash and
  recovery content outside Git tracking.
- Remote operations record the request and read-back result without storing
  credentials.
- Resume verifies current state before continuing; it never assumes the last
  attempted action succeeded.
- A changed project invalidates the old plan and returns to review rather than
  applying stale edits.

Safe local failures roll back generated changes. Ambiguous remote failures are
reconciled by reading actual remote state. The CLI reports partial completion
honestly and never marks bootstrap active merely because an API request returned
success before read-back.

## Security requirements

- Execute commands as argument arrays by default.
- Treat project filenames, configuration, plugin output, and Git metadata as
  untrusted input.
- Redact tokens, credentials, environment values, and secret-like output from
  plans, logs, history, and evidence.
- Never upload source or findings to a hosted service in the first release.
- Pin the core, schema, and bundled plugin versions in the distributed runtime.
- Require explicit trust and version constraints for third-party plugins.
- Reject symlink/path traversal outside the project for generated writes unless
  the user explicitly selects a documented external path.
- Detect time-of-check/time-of-use changes before applying a plan.
- Keep remote mutations limited to the confirmed repository and branch.

## Dogfooding in agentharness

This repository is the first adoption target. Its bootstrap must preserve these
existing checks as mandatory requirements:

- `tools/check.sh` as a composite full verification command.
- ShellCheck and Bats suites.
- Ruff, mypy, pytest, and coverage.
- Markdown, YAML/frontmatter, snippet, generated-file, manifest, and skill-link
  checks.
- actionlint and existing GitHub workflow checks.

The Python plugin adds structured discovery for the repository's Python tools
and code. Core plugins account for shell, documentation, changelog, generated
content, and existing composite commands so limiting the first language plugin
to Python does not reduce current coverage.

Dogfooding is complete only when:

1. The committed profile represents the current requirements accurately.
2. Local hooks invoke compiled gates.
3. CI invokes the same verifier and profile.
4. GitHub protection is read back as active.
5. The completion gate works on a real PR lifecycle.
6. The existing full check remains green.
7. Setup from the packed npm artifact passes an integration fixture.

## Testing strategy

Implementation follows the repository's rigor tier and test-first rules.

### Core unit tests

- Schema validation and semantic reduction detection.
- Local-override allowlist and non-weakening guarantees.
- Bootstrap state transitions and resume decisions.
- Recommendation acceptance and detected-baseline preservation.
- Gate compilation and scope evaluation.
- Evidence fingerprints and invalidation.
- Redaction and path-boundary validation.
- Grace deadline and commit-budget evaluation.
- Runtime-lock identity and incompatible/missing artifact failure.
- Material task/configuration input weakening.
- Canonical diff-base and classification invalidation after rebase.

### Plugin contract tests

Every plugin runs against a shared compliance suite covering metadata,
side-effect-free discovery, schema composition, deterministic planning,
conflict reporting, result codes, redaction, and remediation quality.

The repository includes a minimal sample plugin showing the complete supported
contract without pretending to be another production language integration.

### Python fixture matrix

Fixtures cover representative combinations, including:

- `pyproject.toml` and legacy packaging.
- Existing Ruff, Flake8, Black, mypy, and Pyright setups.
- pytest and unittest projects with and without coverage.
- mutmut and Cosmic Ray configurations.
- Standard logging, structlog, and no logging configuration.
- OpenTelemetry/Sentry presence without enforcement, and complete setups.
- Typed and untyped configuration approaches.
- MkDocs, Sphinx, plain README, monolithic changelog, and fragment workflows.
- Task indirection through tox, nox, and Make.
- Conflicting or malformed configuration.

### Integration tests

- Interactive first use and question resolution.
- Non-interactive CI fail-fast behavior.
- Initial bootstrap-proposal CI, default-branch activation, and proof that no
  second status commit is required.
- Strict, warn, and grace modes.
- Real pre-commit and pre-push blocking in disposable repositories.
- Isolated reduction proposals versus mixed unrelated changes.
- Local override weakening attempts.
- Interrupted local apply and resume.
- Remote partial failure and reconciliation through a fake GitHub adapter.
- Generated-file conflict strategies.
- Python migration from `.agentharness-profile` and preservation of Go/Node
  test/Vitest enforcement through the locked compatibility provider.
- Exact code-owner plus total-review semantics and protection of CODEOWNERS.
- Base-trusted, pre-execution runtime digest verification and dual-runtime
  upgrade sequencing.
- Duplicate required-job spoof attempts from a second workflow and changes to
  every status-producing local Action/script.
- Review-thread resolution and marker-correlated acknowledgement of top-level
  and inline comments.
- Committed docs/changelog classifications across push, PR, rebase, default
  branch, and local completion ranges.
- Canonical agent-source updates followed by generated-client regeneration.
- Full protected three-PR decommission, rollback before removal, proof that the
  temporary producer succeeds before it becomes required, and proof that no
  deleted check context remains required afterward.
- npm pack, unpack, fresh-clone acquisition, bootstrap, and verify without
  repository-local dependencies, including unavailable/offline artifact errors.

### End-to-end GitHub verification

A dedicated test repository or explicitly authorized sandbox verifies real API
behavior for required checks, code-owner review, protection read-back, and
permission failure. Unit mocks alone are not sufficient evidence for the remote
adapter. Tests must not mutate production branch settings in this repository.

### Mutation testing

The new Python core and Python plugin dogfood the mutation-testing requirement
at the CI/completion layer once their test suite is stable. Mutation exclusions
must be explicit and reviewed.

## Delivery slices

### Slice 1: Core and schema

- Python command core and distribution path.
- Profile/local-override schemas and migrations.
- Bootstrap states, read-only discovery orchestration, and basic CLI UX.

### Slice 2: Plugin SDK and Python plugin

- Plugin metadata, trust, schema composition, and contract suite.
- Complete Python capability detection and recommendations.
- Sample plugin authoring reference.

### Slice 3: Policy compiler and evidence

- Gate planning and verification.
- Evidence schema, freshness, redaction, and result aggregation.
- Commit, push, CI, and completion adapters.

### Slice 4: Core quality modules

- Documentation, changelog, configuration, and repository-policy requirements.
- Diff classification and auditable no-doc/no-changelog dispositions.
- Generated integration and conflict strategies.

### Slice 5: GitHub protection

- Remote planning, automatic apply, read-back, and fallback/resume.
- Protected reductions, waivers, drift diagnosis, and decommission sequencing.
- Real sandbox verification.

### Slice 6: Dogfood and adoption documentation

- Bootstrap agentharness itself.
- Validate Git checkout and npm-packed distribution paths.
- Publish user, operator, plugin-author, migration, troubleshooting, and policy
  change documentation.
- Record measured bootstrap/gate runtime and usability findings.

Each slice must preserve a runnable, honest boundary. A partially implemented
adapter reports unsupported capability; it does not produce a false pass.

## Acceptance criteria

The first release is complete only when automated evidence demonstrates all of
the following:

1. First interactive project use launches bootstrap.
2. Unbootstrapped CI fails with a precise remediation command.
3. The isolated initial bootstrap proposal passes its dedicated CI mode without
   pretending remote activation is complete, and active state is computed after
   default-branch CI/protection without a second status commit.
4. Discovery covers all approved capability categories.
5. High-confidence runnable existing checks become mandatory with provenance.
6. New recommendations remain optional until accepted.
7. The final profile is reviewed before becoming binding.
8. Strict, warn, and grace modes behave deterministically from committed fields.
9. Local overrides cannot represent or produce weaker policy.
10. Profile changes are easy to preview, apply, validate, and explain.
11. Commit, push, CI, and completion gates compile from one profile.
12. A missing required verifier or locked runtime fails closed in strict mode.
13. Fresh CI uses base-trusted acquisition to verify exact runtime/plugin
    artifact identities before any package code executes.
14. Evidence becomes stale after relevant code, comparison base,
    classification, policy, runtime, plugin, tool, material task/configuration,
    or other input changes.
15. Changing an indirect check to a no-op is detected as a protected reduction.
16. Existing Go, Node test, and Vitest enforcement survives migration despite
    Python being the only new production language plugin.
17. Expensive mutation checks run only at their configured gates.
18. Documentation and changelog enforcement uses canonical ranges and committed,
    diff-bound classifications whose normalized hash excludes only the
    classification-record path set and cannot hash itself.
19. The Python plugin passes its contract and fixture matrix.
20. Requirement reductions require one matching code-owner approval plus the
    configured total approval count, and CODEOWNERS protects itself.
21. Waivers are scoped, expiring, reasoned, and protected.
22. GitHub settings are applied minimally and verified by read-back, or
    bootstrap remains honestly incomplete with a resumable fallback.
23. Partial bootstrap operations recover or reconcile safely.
24. Agent completion cannot pass before expected automated review reaches a
    configured terminal/stable state, or with stale CI, blocking reviews,
    unresolved review threads, or unacknowledged issue-level/inline comments.
25. Publication checks respect rather than broaden publish authority.
26. Decommission follows its protected three-PR transaction, proves the
    temporary producer before requiring it, and leaves no required context whose
    workflow was removed.
27. Agent instructions are changed through their canonical source and existing
    generators, never by hand-editing generated clients.
28. agentharness passes its own generated policy through a real PR lifecycle.
29. The packed npm artifact can bootstrap and verify a disposable Python
    project from a fresh clone without relying on the source checkout.
30. The committed policy namespace coexists with link, copy, npm, and the
    existing `.agentharness/` submodule install mode.
31. A second or modified GitHub Actions workflow cannot satisfy/spoof either
    required policy context without triggering protected workflow/material-input
    review, and strict activation fails if that identity boundary is unavailable.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Bootstrap becomes overwhelming | Ask only unresolved questions; group recommendations by impact and show a concise final policy diff. |
| Hooks are too slow | Layer gates, cache by valid fingerprints, and measure runtime during dogfooding. |
| Detection produces false confidence | Use capability states, evidence, and confidence; only high-confidence runnable checks auto-bind. |
| Generated configuration damages user files | Use declared merge strategies, hash checks, proposals, and resumable transactions. |
| Policy can be weakened in the same PR | Semantic reduction detection plus code-owner approval and isolated policy proposals. |
| GitHub automation overreaches | Confirm repository/branch, compute minimal diffs, preserve unrelated settings, and verify by read-back. |
| Python runtime complicates npm distribution | Ship one pinned self-contained runtime and test the packed artifact end to end. |
| Plugin ecosystem becomes a code-execution vector | Explicit trust, version constraints, metadata permissions, and no arbitrary project-module discovery. |
| Logging/observability checks overclaim quality | Separate presence/configuration/execution/enforcement states and document evidence limits. |
| The new profile regresses or duplicates the old tier mechanism | Migrate Python directly; preserve current Go/Node/Vitest behavior through one locked compatibility provider; remove the legacy selector only when every enforced check is represented. |

## Documentation deliverables

Slice 6 must provide permanent documentation for:

- First-time bootstrap and all three modes.
- Profile schema and safe local overrides.
- Requirement lifecycle, protected reductions, and waivers.
- Gate placement and evidence interpretation.
- GitHub permissions, automatic protection, and fallback recovery.
- Python detection/recommendation behavior.
- Documentation and changelog policies.
- Plugin authoring, trust, and contract tests.
- Migration from `.agentharness-profile` and existing hooks.
- Locked-runtime acquisition, upgrades, mirrors, and offline failure behavior.
- Troubleshooting and protected decommission/rollback behavior.

Release notes must distinguish designed, preview, and generally available
behavior. No documentation may describe a slice as enforced until its real
integration and dogfood acceptance criteria pass.

## Future extensions

After Python dogfooding proves the contract, additional language plugins can be
prioritized using real adoption evidence. TypeScript/JavaScript, Go, Rust, and
shell are likely candidates, but they require their own detection fixtures,
generated-default decisions, and runtime-cost measurements.

Future remote adapters can target other repository hosts. They must implement
the same plan/apply/read-back contract and must state honestly which protected
policy semantics the host cannot express.

Cryptographic attestations, organization-wide policy inheritance, and a hosted
dashboard remain separate product decisions, not implied follow-up work.

## Implementation planning handoff

The next step after review of this written specification is an implementation
plan that maps each delivery slice to concrete files, tests, migrations, and
verification commands. Planning must select the concrete self-contained Python
artifact build method that satisfies `runtime.lock` before implementation
starts, because distribution is an architectural dependency rather than release
cleanup.
