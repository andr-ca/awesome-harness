---
date: 2026-07-17
status: draft
topic: existing-surface-integration
purpose: Design how harness installation integrates with a consumer project's pre-existing skills, agents, and instructions files instead of skipping them.
related-harness: tools/setup/harness-link.sh, docs/INTEGRATION.md, tools/generate-*.sh
---

# Existing-surface integration design

## Status

Draft, designed interactively on 2026-07-17. Implementation has not
started; nothing in this document claims to exist yet.

## Problem

`harness-link.sh init` is safely non-destructive after F-03: any
pre-existing consumer file (an `AGENTS.md`, a `.cursor/rules/` file, a
same-named skill) is skipped with a message unless `--force` is given.
But non-destructive currently means non-integrating: on a project that
already has its own Claude/Codex/Gemini/Cursor surfaces (Recalium is the
live example), harness content never reaches the files those clients
actually read. The consumer's `CLAUDE.md` is never touched at all —
INTEGRATION.md tells the operator to hand-append a block, which is
exactly the manual, forgettable step this harness exists to eliminate.

## Design

### 1. Managed reference blocks (single-file surfaces)

For each instructions file the consumer already has — `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md` — `init`
inserts one clearly-marked block:

```markdown
<!-- agentharness:begin id=core-instructions version=0.2.1 -->
…rendered content…
<!-- agentharness:end id=core-instructions -->
```

The `id` is the **stable match key** across upgrades; `version` is
informational. Matching semantics are formal:

| Blocks found for an id | Action |
|---|---|
| zero | insert |
| exactly one, well-formed | replace |
| multiple | hard fail |
| unmatched begin or end | hard fail |
| nested markers | hard fail |

Insertion point: end of file, one blank line before the block, block
ends with a trailing newline, and the file's existing final-newline
convention is respected.

Block contents, rendered from harness state at install time:

- one short paragraph: what agentharness is, where the installed
  router/policy content lives in this repo;
- the precedence statement (section 3);
- the list of installed skills and where they are;
- the completion-gate and publish-authority rules in one line each,
  linking to the full text.

Rules:

- **Idempotent**: re-running `init`/`update` replaces marker-to-marker
  only. Content outside the markers is treated as opaque bytes and
  preserved byte-for-byte. If the resulting file would be byte-identical,
  no write happens at all (mtime preserved).
- **Reversible**: `uninstall` deletes exactly the block. The state file
  (`.agentharness-state.json`) records which files carry blocks.
- **Drift-checked**: `update` re-renders every recorded block from
  current harness content; `doctor` flags a block whose content differs
  from what the installed version would render (same discipline the
  harness applies to its own generated adapters).
- If the file does not exist, it is created wholesale via the existing
  `generate-clients` code path (already marked with provenance headers)
  and recorded in state as harness-created rather than block-managed.
- **`init` and `update` invoke this machinery themselves** — that is
  the point of the design; no manual `generate-clients` step remains
  for the covered surfaces. The standalone `generate-clients`
  subcommand stays available and unchanged for ad-hoc use. (This is
  the "larger managed-block part" of P1-01 that ROADMAP.md notes as
  not yet wired; it is in scope here.)

**Uninstall semantics, defined precisely:**

- Block-managed files: `uninstall` removes marker-to-marker only.
  Consumer edits outside the markers are preserved by construction; no
  backup is needed or taken for these files.
- Harness-created and overwritten files: `uninstall` compares the
  current file hash to the recorded `written_sha256`. If unchanged,
  the file is deleted (harness-created) or the `.pre-agentharness`
  backup is restored (overwritten). If the consumer has edited the
  file since, `uninstall` leaves it in place and prints the backup
  path with a warning — never clobbering post-install user edits,
  the same caution F-05 applies to `core.hooksPath`.

The begin/end marker-pair machinery is **new infrastructure**, not a
reuse of the existing gitignore handling: the gitignore path appends
marker-tagged lines, which cannot preserve arbitrary content around a
replaceable region. The gitignore code is precedent for the *idea* of
marked harness-owned regions and state-tracked mutations, but planners
should treat block insert/replace/remove as a fresh, tested component.

**Filesystem discipline** for every mutated file: regular files only;
mode bits preserved; newline convention (CRLF/LF) and final-newline
state preserved where practical; symlinked instructions files are a
hard fail by default (never silently followed); write-to-temp + atomic
rename per file.

**State schema additions** (`.agentharness-state.json`):

```json
"schema_version": 2,
"managed_blocks": [
  {"file": "AGENTS.md", "block_id": "core-instructions",
   "rendered_version": "0.2.1", "rendered_sha256": "…"}
],
"overwritten_files": [
  {"file": ".cursor/rules/x.mdc",
   "backup": ".cursor/rules/x.mdc.pre-agentharness.a1b2c3",
   "written_sha256": "…"}
],
"collision_decisions": [
  {"item": ".cursor/rules/testing.mdc", "kind": "whole-file",
   "choice": "keep-existing", "existing_sha256": "…", "decided_at": "…"}
]
```

A persisted decision is honored only while `existing_sha256` still
matches the file on disk; if the underlying object changed materially,
`update` re-prompts (interactive) or re-reports (non-interactive).
Schema versioning and migration follow the policy tracked as F-12 in
the disposition backlog — this spec adds fields under that policy, not
a second one.

`rendered_sha256`/`written_sha256` are what `doctor` compares against to
detect drift and what `uninstall` uses for its safety check (below).

### 2. Directory-style surfaces

`.cursor/rules/`, `.kilo/rules/`, and per-skill directories already
coexist file-by-file with provenance headers and F-03 skip/`--force`
semantics. No blocks needed; behavior unchanged except for the
collision-choice flow in section 4.

### 3. Precedence: enforcement wins by construction, text defers

Conflicts between consumer instructions and harness policy resolve at
two different layers:

- **Mechanically enforced behavior** (trunk-protection hooks, completion
  gate, push locks) fires regardless of prose. The escape hatches are
  explicit mechanisms — `.agentharness-publish-mode`, `--force`,
  `uninstall` — never a contradicting sentence in an instructions file.
  Stated precisely: harness-enforced constraints cannot be *weakened*
  by prose, and independent project enforcement (the consumer's own
  hooks, CI rules) may impose *additional* constraints — composition is
  strictest-wins, not harness-wins.
- **Textual guidance** (conventions, style, workflow prose): project-
  local instructions win on conflict, stated explicitly inside every
  managed block. The harness supplies defaults; the consumer knows
  their context.

The boundary requires no judgment call from an agent: *is it a
hook/gate, or is it prose?* The precedence text lives in exactly two
places — the block template and one canonical section in
INTEGRATION.md — honoring one-source-of-truth.

### 4. Collision handling: the user chooses, never silently

**A normal pre-existing supported instructions file is NOT a
collision — it receives a managed block (section 1).** Whole-file
overwrite is never offered merely because `AGENTS.md` exists; that
would undermine the design's central safety property.

A path is a collision only when:

- it already contains ambiguous or malformed harness markers
  (→ hard fail, see Error handling — not a prompt);
- it is not a regular writable file (→ hard fail);
- the path is occupied by an incompatible object (→ hard fail);
- or it is a **whole-file generated surface** with no block mechanism —
  a directory-style asset such as a `.cursor/rules/*.mdc` or
  `.kilo/rules/` file that the harness would generate but a consumer
  file already occupies (→ user chooses, below).

Shadowed skills are the separate case (b) and bypass prompts entirely
(see below).

**What exists today vs. what this section adds:** today's behavior is
skip-with-message plus a global `--force` (the F-03 fix in
`generate-clients`), and nothing is recorded about the decision. The
interactive prompt flow, the `--keep-existing` flag, per-item decision
recording in state, and the `.pre-agentharness` backup discipline are
all **new** in this design; only the `--force` semantic is carried over
(and extended from generate-clients to the whole install flow).

Prompt UX (interactive):

```text
.cursor/rules/testing.mdc exists and is not harness-generated.
  [o]verwrite (backs up to .cursor/rules/testing.mdc.pre-agentharness.<install-id>)
  [k]eep yours (the harness version of this rule will not be installed)
  [a]ll — overwrite this and every remaining collision
  [n]one — keep yours for every remaining collision
```

- **Interactive (TTY)**: prompt per item — `overwrite / keep yours /
  all / none`. Every answer is recorded in the state file so `update`
  does not re-ask decided questions.
- **Flags**: `--force` overwrites all collisions (warning per file —
  the existing generate-clients semantic, applied uniformly);
  `--keep-existing` skips all without prompting (today's default
  behavior, made explicit); `--dry-run` previews the collision list.
- **Non-interactive and unflagged** (CI, agent sessions): skip and
  report, exiting with the collision list. An agent surfaces the choice
  to its operator; it does not make it. This matches the file-placement
  policy's ask-first rule. Non-interactive skips are **not** recorded
  as decisions — a later interactive run prompts for them; only
  explicit answers (prompt or flag) persist to `collision_decisions`.
- **Reversibility**: any consumer file overwritten via prompt or
  `--force` is first backed up, recorded in state, and restored on
  `uninstall` — the same treatment F-05 gives `core.hooksPath`.
  **Backups are collision-safe**: if an existing backup is state-owned
  and hash-verified, it is reused (it already holds the true
  pre-harness content); otherwise a unique `.pre-agentharness.<install-id>`
  is created. No existing backup is ever overwritten or deleted, under
  any flag. Uninstall edge cases have defined outcomes: backup missing
  → warn, leave target; target deleted post-install → note and clean
  state; backup edited (hash mismatch) → warn, leave both; target
  became a directory/symlink → hard fail with instructions.
- **Shadowed skills** bypass the prompt flow entirely — they are never
  overwritten, prompted about, or affected by `--force`; the shadowing
  is recorded in state and reported by `doctor`/`audit` ("local skill X
  shadows harness skill X") so coexistence is a visible, deliberate
  choice. Replacing a local skill with the harness one is a manual act
  (delete yours, re-run `update`), not an install-time option.

The one surface with no overwrite choice is the inside of a managed
block: marker-to-marker content is harness-owned by definition and
always re-rendered.

### 5. Documentation updates

- INTEGRATION.md: the hand-append suggestion is replaced by an
  "existing agent surfaces" section describing blocks, precedence, and
  the collision flow.
- MANIFEST.md (via `manifest.yaml`): no new assets beyond what lands in
  `harness-link.sh` itself; the subcommand help text is the primary
  reference.
- The block template carries the harness version so a reader of any
  consumer repo can tell which harness release rendered it.

### 6. Preflight and crash consistency

`init`/`update` are **two-phase**:

```text
discover → validate → resolve decisions → construct plan → apply plan → commit state
```

All validation failures and all prompts happen before the first write;
a run that will fail must fail with zero mutations. `--dry-run` prints
the complete mutation plan (every block insert/replace, file creation,
overwrite, and skip), not only the collisions.

Crash consistency: before the apply phase, the full plan and prior
file hashes are journaled to `.agentharness-state.pending.json`; the
journal is deleted only after the state file commits. `doctor` detects
a leftover journal, reports what was in flight, and explains recovery.
Concurrent `init`/`update` runs are excluded by a repo-level install
lock held across the apply phase.

## Error handling

Three distinct failure classes — overwrite is never an escape hatch
from uncertainty about file structure:

- **Malformed existing harness markers** (unmatched, nested, duplicate
  blocks): hard failure for that run, nothing written — the harness may
  already own an unknown region, so overwriting is unsafe.
- **Unsupported whole-file surface**: collision decision (section 4).
- **Unreadable, unwritable, symlinked, or special files**: hard
  failure, never an overwrite prompt.

## Testing

- bats: block insert/replace/remove idempotency; uninstall restores
  byte-identical pre-install files (both block removal and backup
  restore); collision prompt paths via stdin scripting; non-interactive
  default = skip + nonzero with list; shadowed-skill reporting in
  doctor/audit.
- Preflight/transaction: an all-collisions run produces zero mutations;
  crash between file mutation and state commit is recoverable via the
  journal; two simultaneous `init`/`update` runs are excluded by the
  install lock; `uninstall` called twice is a no-op the second time.
- Block edge cases: duplicate complete blocks fail; an old-version
  marker is matched by id and upgraded; a user edit *inside* the block
  is overwritten on update (by contract) while an edit *outside*
  survives byte-for-byte; unchanged output does not rewrite the file
  (mtime preserved).
- Filesystem: CRLF and no-final-newline files preserved; symlinked
  instructions file hard-fails; pre-existing backup path never
  clobbered.
- State: a stale collision decision (file replaced after
  "keep-existing") triggers re-prompt/re-report; a shadowed skill that
  disappears and later reappears is re-reported.
- Fixture matrix: extend the existing `examples/*-project` CI fixtures
  with one fixture that pre-seeds an `AGENTS.md`, a `.cursor/rules/`
  file, and a same-named skill, asserting coexistence and clean
  uninstall.

## Out of scope

- Semantic merging of consumer and harness prose (rejected: not
  idempotent, not reversible).
- Side-by-side harness-only files as the primary mechanism (rejected:
  leaves the canonical-file gap this design exists to close).
- Any change to the bootstrap policy core (`src/agentharness/`); this
  is entirely `harness-link.sh` + docs + tests.
