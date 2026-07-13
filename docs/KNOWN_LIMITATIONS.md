# Known Limitations

The current, honest list of **what to expect *not* to work yet**, in one
place — the companion to [STATUS.md](./STATUS.md) (what *does* work).
This is a curated summary of open gaps; the full planned-vs-built
breakdown, with proposals and this-review's numbering, lives in
[ROADMAP.md](../ROADMAP.md). Where a gap is tracked there, the label is
noted — resolve any label against the review filename cited next to it in
[ROADMAP.md](../ROADMAP.md), since two review rounds reused the same
`P1-xx`/`P2-xx` numbers.

## Verification & evidence

- **Not verified against live tool sessions (except Claude Code).** Every
  generated adapter (`AGENTS.md`, `GEMINI.md`,
  `.github/copilot-instructions.md`, `.cursor/rules/`, `.kilo/rules/`)
  and every custom-agent port is implemented against each tool's
  *published* behavior, not dogfooded end-to-end. See
  [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md)'s intro and
  [DECISIONS.md](./DECISIONS.md)'s "Claude-first client scope".
- **No real-world dogfood yet.** The harness is exercised only by its own
  CI fixtures (`examples/*-project/`), not pinned into a real, non-fixture
  project with a different stack and a user other than the author.
  → ROADMAP "P2-05 (real dogfood) has no target" / P2-02.
- **Evals are infrastructure, not evidence.** `tools/eval/` is a
  deterministic runner + scorer, but no baseline/treatment run has shown
  the harness improves agent behavior. → ROADMAP P2-01, P2-03.

## Enforcement

- **Profile enforcement is partial.** `harness-link.sh enforce-profile`
  gates for real on Python, Go, and `node --test`/Vitest JS/TS projects;
  Jest/Mocha and unrecognized project types are advisory (exit 0, or fail
  under `--strict`). It is also **not wired into the pre-push hook** — it
  ships as an explicitly-invoked subcommand. → ROADMAP P1-02.

## Client integration

- **Client-adapter generation isn't wired into `init`/`update` yet.**
  `harness-link.sh generate-clients <project> --client all` now produces
  the router/instruction files in one command, but generation is still a
  separate step from `init`/`update`, and generated files aren't tracked
  in state for `doctor`/`uninstall` via managed blocks. → ROADMAP P1-01
  (first increment shipped; managed-block lifecycle integration open).
- **Custom sub-agent tool/permission scoping is not ported.** The
  agent generators carry `name`/`description`/`model` and the body
  verbatim, but not Claude Code's `tools:` allow-list or any target
  tool's own permission vocabulary — re-specify those by hand per
  platform. See [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md)'s
  custom-agent table.

## Content coverage

- **Languages:** Python, TypeScript, Go, and Rust. Java and others are
  not started. → ROADMAP "Planned Components".
- **Frameworks:** only React. Vue/Angular/Django/Express/etc. are not
  started.
- **Patterns:** no API-design pattern yet. → ROADMAP "Planned Components".

## Maintenance & robustness

- **Review history isn't archived yet.** This file and
  [STATUS.md](./STATUS.md) are the first step of consolidating the long
  dated review chain under [docs/operational/reviews/](./operational/reviews/);
  moving completed cycles into dated archive directories is still open.
  → ROADMAP P1-10.
- **Managed state has no migration contract.** `.agentharness-state.json`
  declares `version: 1` with no forward-migration machinery or
  cross-version test matrix. → ROADMAP P1-09.
- **Tests aren't fully hermetic.** Some lifecycle tests reach the network
  (submodule clone of the configured `origin`, `npx` resolution, Go
  cache). → ROADMAP P1-05 (3rd-pass).
- **Package materialization is coupled to writable Git metadata.**
  `materialize-skill-symlinks.py restore` uses `git checkout`, so it
  fails in a restricted/non-Git source package. → ROADMAP P1-04.
