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
<!-- agentharness:begin v<version> -->
…rendered content…
<!-- agentharness:end -->
```

Block contents, rendered from harness state at install time:

- one short paragraph: what agentharness is, where the installed
  router/policy content lives in this repo;
- the precedence statement (section 3);
- the list of installed skills and where they are;
- the completion-gate and publish-authority rules in one line each,
  linking to the full text.

Rules:

- **Idempotent**: re-running `init`/`update` replaces marker-to-marker
  only. Content outside the markers is never read, parsed, or modified.
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

**State schema additions** (`.agentharness-state.json`):

```json
"managed_blocks": [
  {"file": "AGENTS.md", "version": "0.2.1", "rendered_sha256": "…"}
],
"overwritten_files": [
  {"file": ".cursor/rules/x.mdc", "backup": ".cursor/rules/x.mdc.pre-agentharness",
   "written_sha256": "…"}
],
"collision_decisions": [
  {"item": "skill:testing", "choice": "keep-existing", "decided_at": "…"}
]
```

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
- **Textual guidance** (conventions, style, workflow prose): project-
  local instructions win on conflict, stated explicitly inside every
  managed block. The harness supplies defaults; the consumer knows
  their context.

The boundary requires no judgment call from an agent: *is it a
hook/gate, or is it prose?* The precedence text lives in exactly two
places — the block template and one canonical section in
INTEGRATION.md — honoring one-source-of-truth.

### 4. Collision handling: the user chooses, never silently

Collisions are (a) a pre-existing instructions file that would otherwise
be generated, and (b) a consumer skill whose name shadows a harness
skill.

**What exists today vs. what this section adds:** today's behavior is
skip-with-message plus a global `--force` (the F-03 fix in
`generate-clients`), and nothing is recorded about the decision. The
interactive prompt flow, the `--keep-existing` flag, per-item decision
recording in state, and the `.pre-agentharness` backup discipline are
all **new** in this design; only the `--force` semantic is carried over
(and extended from generate-clients to the whole install flow).

Prompt UX (interactive):

```text
AGENTS.md exists and is not harness-generated.
  [o]verwrite (backs up to AGENTS.md.pre-agentharness)
  [k]eep yours (harness content will not reach this surface)
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
  `--force` is first backed up to `<name>.pre-agentharness`, recorded
  in state, and restored on `uninstall` — the same treatment F-05 gives
  `core.hooksPath`.
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

## Error handling

- A malformed block (begin without end, nested markers) fails `init`/
  `update` for that file with a precise message; nothing is written.
- Files the process cannot parse safely are treated as collisions
  (user chooses), never best-effort edited.
- All mutations per file are write-to-temp + atomic rename.

## Testing

- bats: block insert/replace/remove idempotency; uninstall restores
  byte-identical pre-install files (both block removal and
  `.pre-agentharness` restore); collision prompt paths via stdin
  scripting; non-interactive default = skip + nonzero with list;
  shadowed-skill reporting in doctor/audit.
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
