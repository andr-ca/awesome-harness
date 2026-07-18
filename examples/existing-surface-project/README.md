# existing-surface-project (fixture)

A tiny project that already has its own `AGENTS.md` (with custom content)
and its own `.cursor/rules/testing.mdc` *before* harness install, used to
CI-verify the existing-surface integration
(docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md):
a managed block gets rendered into the pre-existing `AGENTS.md` without
disturbing its other content, and `uninstall` removes exactly that block
and nothing else. `.cursor/rules/testing.mdc` isn't one of the four
block-managed instructions files and isn't touched by `init`/`update` at
all — it's included here to verify the harness never reaches into files
outside its own managed set. It triggers no collision because Cursor-rule
generation (`generate-cursor-rules.sh`) is a separate, manual step from
`init`/`update`, not something the collision-handling flow currently
touches — see the Cursor section of `../../docs/INTEGRATION.md`. See
`../sample-project/README.md` for the
blank/generic fixture and the full method-by-method walkthrough; this one
only adds what's different for a project with pre-existing agent
instructions.

```bash
~/agentharness/tools/setup/harness-link.sh init . --mode link --with-hook
bash verify.sh
```

Exercised in CI across all three install modes (link/copy/submodule) by
the `fixture-matrix` job in `.github/workflows/ci.yml`, which also runs
`doctor`, `update`, and `uninstall` against it, with extra assertions
confirming the managed block is cleanly removed and the pre-existing
content and unrelated files survive uninstall untouched.
