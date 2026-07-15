# Project Bootstrap Policy Acceptance and Evidence Matrix

This matrix is the release ledger for the 31 acceptance criteria in
`docs/superpowers/specs/2026-07-14-project-bootstrap-policy-design.md`.
Implementation commits update `Status` and replace planned evidence with exact
test IDs, CI artifact URLs, or remote read-back records. A checkmark without
reproducible evidence is invalid.

## Status vocabulary

| Status | Meaning |
|---|---|
| `planned` | Mapped to implementation and tests, but no passing evidence exists. |
| `implemented` | Code exists and focused tests pass locally. |
| `partial` | Some owning code exists and passes focused tests, but a required part of the criterion is not yet implemented or provable. Never sufficient for release. |
| `verified` | Required integration/E2E evidence passes for the release candidate. |
| `blocked` | External capability or unresolved design constraint prevents proof. |

## Matrix

| ID | Acceptance outcome | Slice | Owning implementation | Automated proof | Release evidence | Status |
|---:|---|---:|---|---|---|---|
| AC-01 | First interactive project use launches bootstrap. | 1 | `src/agentharness/cli.py`, `bootstrap/state.py` | `tests/integration/test_first_use.py` | Packed-artifact transcript from clean fixture | implemented |
| AC-02 | Unbootstrapped CI fails with exact remediation. | 1 | `bootstrap/state.py`, `cli.py` | `tests/integration/test_first_use.py::test_unbootstrapped_ci_fails_with_remediation` | CI fixture result JSON | implemented |
| AC-03 | Initial proposal uses honest one-time CI mode and activates after default-branch proof without a status commit. | 1, 5 | `bootstrap/state.py`, `remote/github/protection.py` | `tests/integration/test_activation.py`; `tests/e2e/test_activation.py` | Sandbox PR/default-branch run and protection read-back | planned |
| AC-04 | Discovery covers every approved capability category. | 2, 4 | Python and core bundled plugins | `tests/contract/test_capability_coverage.py`; `tests/unit/plugins/` | Contract report enumerating all capability IDs | implemented |
| AC-05 | High-confidence runnable existing checks bind with provenance. | 2 | Python detectors and compatibility provider | `tests/unit/plugins/python/`; `tests/integration/test_legacy_migration.py` | Profile finding/requirement provenance snapshot | implemented |
| AC-06 | New recommendations remain optional until accepted. | 1, 2 | `bootstrap/questions.py`, `bootstrap/transaction.py` | `tests/unit/bootstrap/test_questions.py`; `tests/integration/test_confirmation.py`; `tests/unit/plugins/python/test_recommend.py` | Confirmed-plan history fixture | implemented |
| AC-07 | User reviews the final profile before binding. | 1 | `bootstrap/questions.py`, `bootstrap/transaction.py` | `tests/integration/test_confirmation.py` | Apply transcript containing plan hash and confirmation | implemented |
| AC-08 | Strict, warn, and grace modes are deterministic from committed fields. | 1, 3 | `profile/loader.py`, `policy/modes.py` | `tests/unit/policy/test_modes.py` | Mode matrix JSON | implemented |
| AC-09 | Local overrides cannot weaken policy or substitute executables/caches. | 1 | `profile/loader.py`, `profile/reduction.py` | `tests/unit/profile/test_loader.py`; `tests/unit/profile/test_reduction.py` | Negative-test report | implemented |
| AC-10 | Profile operations support preview, apply, validate, and explain. | 1 | `cli.py`, `profile/history.py` | `tests/integration/test_profile_commands.py` | CLI JSON-schema snapshots | implemented |
| AC-11 | All four gates compile from one profile. | 3 | `policy/compiler.py`, `gates/` | `tests/integration/test_gate_compilation.py` | Four plans with identical effective-policy hash | implemented |
| AC-12 | Missing verifier or runtime fails closed in strict mode. | 1, 3 | launcher, `policy/verifier.py` | `tests/integration/test_fail_closed.py` | Failure result and remediation snapshots | implemented |
| AC-13 | Fresh CI verifies exact artifacts from base-trusted code before execution. | 1, 3 | `templates/bootstrap/verify-runtime.mjs` | hostile archive/digest Bats tests; `tests/integration/test_base_trust.py` | Packed-artifact CI trace | planned |
| AC-14 | Evidence invalidates after every specified relevant input change. | 3 | `policy/fingerprint.py`, `policy/evidence.py` | `tests/unit/policy/test_fingerprint.py`; `tests/integration/test_evidence_inputs.py` | Invalidation coverage report with all input classes | implemented |
| AC-15 | Indirect-check no-op weakening is detected. | 2, 3 | task detector, `profile/reduction.py` | `tests/unit/policy/test_classification.py` | Before/after reduction report | implemented |
| AC-16 | Go, Node test, and Vitest enforcement survives migration. | 1, 2 | compatibility provider | `tests/integration/test_legacy_migration.py`; `tools/tests/harness-lifecycle.bats` | Migrated profile snapshots and gate passes | implemented |
| AC-17 | Mutation runs only at configured expensive gates. | 2, 3 | Python testing detector, compiler | `tests/unit/plugins/python/test_mutation.py`; `tests/unit/policy/test_compiler.py` | Gate plan and CI artifact | implemented |
| AC-18 | Docs/changelog use canonical ranges and self-excluding diff-bound classifications. | 4 | `policy/classification.py`, core plugins | `tests/integration/test_classification_ranges.py` | Commit/push/PR/rebase/default/completion matrix | implemented |
| AC-19 | Python plugin passes contract and fixture matrix. | 2 | `plugins/python/` | `tests/contract/`; `tests/fixtures/python/` | Contract JUnit and fixture matrix artifacts | implemented |
| AC-20 | Reductions require one matching code owner plus configured total approvals; CODEOWNERS protects itself. | 5 | GitHub protection/review adapters | `tests/integration/test_reductions.py` | Sandbox API read-back and merge-block proof | planned |
| AC-21 | Waivers are scoped, expiring, reasoned, and protected. | 3, 5 | `profile/waivers.py`, protection adapter | `tests/unit/profile/test_waivers.py` | Waiver lifecycle report | partial |
| AC-22 | GitHub settings apply minimally and read back, or bootstrap stays resumably incomplete. | 5 | `remote/github/protection.py` | `tests/integration/test_github_reconcile.py` | Before/plan/after sanitized API snapshots | partial |
| AC-23 | Partial bootstrap operations recover or reconcile safely. | 1, 5 | transactions and GitHub reconciliation | `tests/integration/test_local_recovery.py`; fault-injection integration tests | Recovery transcript for each mutation boundary | partial |
| AC-24 | Completion blocks on expected review, stale CI, blocking/pending review, unresolved thread, or unacknowledged comments. | 5 | `remote/github/completion.py`, `reviews.py` | `tests/integration/test_completion.py` | Exact-head completion report | partial |
| AC-25 | Publication checks never broaden publish authority. | 3, 5 | completion gate authority reader | `tests/integration/test_publish_authority.py` | Authorized/unauthorized result matrix | implemented |
| AC-26 | Decommission uses protected three-PR transaction and leaves no orphan required context. | 5 | `remote/github/decommission.py` | `tests/unit/remote/github/test_slice5_tasks.py`; sandbox E2E pending | Three PRs plus final protection read-back | partial |
| AC-27 | Agent instructions change only through canonical source and generators. | 4, 6 | `integrations/agents.py` | `tests/integration/test_agent_generation.py` | Clean generated-client verification | implemented |
| AC-28 | agentharness passes its generated policy through a real PR. | 6 | committed `.agentharness-policy/` | dogfood script and actual PR | PR URL, exact-head CI, review and completion evidence | planned |
| AC-29 | Packed npm artifact bootstraps/verifies a clean Python project without source checkout. | 1, 6 | packaging, launcher, templates | `tools/acceptance/run-packed-artifact.sh` | Clean environment transcript and artifact digests | planned |
| AC-30 | Policy namespace coexists with link, copy, npm, and `.agentharness/` submodule mode. | 1, 6 | lifecycle migration and paths | `tests/integration/test_npm_mode_coexistence.py` | Four-mode install/bootstrap/update/uninstall report | implemented |
| AC-31 | Duplicate/modified workflow cannot spoof required contexts; strict activation fails without identity boundary. | 3, 5 | integrity verifier and protection adapter | spoof integration tests and sandbox rules | Protected-input review proof or strict refusal record | planned |

## Cross-cutting quality evidence

| Evidence | Required threshold | Planned producer |
|---|---:|---|
| Core branch coverage | Meets the Production-tier floor in `patterns/testing/COVERAGE_REQUIREMENTS.md` | `pytest --cov=agentharness --cov-branch` |
| Security/policy mutation score | At least 90%, with every survivor dispositioned | `mutmut` CI artifact |
| Plugin contract | 100% bundled plugins pass | contract-suite JUnit artifact |
| Python fixture matrix | 100% expected outcomes; no unexpected skip | fixture-matrix JUnit artifact |
| False pass rate | 0 in adversarial suite | security integration report |
| Existing check preservation | 100% | `tools/check.sh` plus dogfood comparison |
| Commit gate warm latency | p95 at most 5 seconds | dogfood benchmark JSON |
| Push gate warm latency | p95 at most 30 seconds excluding configured mutation | dogfood benchmark JSON |
| Bootstrap task completion | At least 80% unassisted in usability sessions | dated release evaluation |
| Critical/high security findings | 0 open | release audit |

## Verification rule

`tools/acceptance/verify-matrix.py` must eventually parse this document or its
generated machine-readable companion and fail when a release-required row is
not `verified`, names a missing test, or lacks an evidence reference. Until that
tool is implemented in Slice 6, reviewers must treat every row as unverified.
