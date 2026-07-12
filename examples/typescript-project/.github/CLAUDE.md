# typescript-project (fixture)

This project uses agentharness for shared conventions.

## Overrides

- **Rigor tier**: Internal Tool (see `.github/CODING_GUIDELINES.md#rigor-tiers`
  in the harness) — not all Production-tier mandates apply.

## How to Use Harness

- Committing: `.claude/skills/committing/SKILL.md`
- Branching: `.claude/skills/branching/SKILL.md`
- TypeScript conventions: `languages/typescript/CONVENTIONS.md` in the
  harness checkout — not bundled as a skill, so it's only reachable in
  `--mode submodule` (via `.agentharness/languages/...`) or by referencing
  the harness checkout directly, not in `--mode link`/`copy`, which only
  install `.claude/skills/`. See the harness's README "Product Contract"
  for what each mode actually installs.
