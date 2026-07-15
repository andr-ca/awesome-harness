# Harness Ideation Note — Disposition (2026-07-15)

**Timestamp:** 2026-07-15T23:00:51Z
**Source:** an external ideation note (2026-07-15) on intent-first
harness design: intent/context gates before implementation, request
classification and routing, per-work-type workflow catalogues, and a
repository-readiness/bootstrap gate. The note references material
internal to its author's employer; none of that content is reproduced
in this repo — only the generalizable ideas were assessed.
**Requested by:** user — "is it worth adding to our roadmap? in what
format, please filter out and add what makes sense."
**Outcome:** six filtered items added to `ROADMAP.md` as the
**Ideation Backlog (I-01…I-06)**, documentation-only (no implementation
authorized). Everything else rejected, deferred, or blocked below.
**PR:** _added in this PR — see the PR that introduced this file._

## Assessment method

Each idea was mapped against what agentharness already ships (skills,
rigor tiers, patterns, the bootstrap-policy program on PR #47) under
two repo rules: one source of truth per rule (extend, don't duplicate),
and the 2026-07-15 over-engineering finding on PR #47 (prefer the
cheapest thing that serves the actual user; no new subsystems without a
demonstrated need).

## Accepted → ROADMAP.md I-XX backlog

| ID | Idea (filtered form) | Why it fits |
|----|----------------------|-------------|
| I-01 | Evidence-classified intent contract | Extends the existing `requirements-clarification` skill; the genuinely new part is classifying statements as fact/inference/assumption/unknown so unknowns can't silently become decisions |
| I-02 | Risk-adaptive discovery depth | The note's task-type table is the existing rigor-tiers idea applied to discovery instead of testing — one table in the existing source of truth |
| I-03 | Read-only investigation mode | Cheap, high-value rule: a question authorizes analysis, never edits |
| I-04 | Reclassification checkpoint | The note's strongest safeguard ("a defect that matches requirements is a feature request — stop") kept as a rule, without the router around it |
| I-05 | `patterns/refactoring/` | The one work-type genuinely missing from `patterns/` (characterization tests, behavior-preservation contract) |
| I-06 | Repository context contract | **Blocked on the PR #47 scope decision** — overlaps the in-flight policy-bootstrap program; only the provenance vocabulary (verified/inferred/declared/unknown) is independently adoptable now |

## Rejected

| Idea | Rationale |
|------|-----------|
| Two-level classification router, routing-envelope schemas, workflow registry | Machinery disproportionate to this repo's audience; skill trigger descriptions already route on-demand content, and rigor tiers already encode risk adaptivity. I-02/I-04 capture the residual value at doc cost |
| Persona-agent fleet (Intent Analyst, Context Scout, Solution Planner, Plan Validator, independent validators) | Duplicates existing brainstorming/planning/review skills and subagents; adds orchestration surface with no demonstrated need — the exact ratchet the PR #47 over-engineering assessment warned about |
| Full per-work-type workflow catalogue (defect/feature/prototype/ modernization as separate subsystems) | Debugging, planning, and prototype-vs-production rigor are already covered by existing skills and rigor tiers; only refactoring lacked a home (I-05) |
| Legacy modernization workflow | Enterprise-specific; no audience among this repo's consumers |
| Employer-internal content (systems, colleagues, meeting references) | Must not be committed to this repo in any form; excluded from all artifacts including this one |

## Deferred (not rejected)

| Idea | Rationale |
|------|-----------|
| Hard edit-blocking hooks gated on schema-validated plan artifacts | Revisit only if the soft gates (I-01/I-02) demonstrably fail in practice; the `.claude/hooks/` roadmap entry is the natural home if ever justified. Enforcement-before-evidence is how harnesses become bureaucracy |
| Whole-task eval metrics | Not a new item — folded into the existing P2-01 entry as a metrics refinement (measure through accepted PR, not first generation) |
