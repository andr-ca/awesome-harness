# typescript-project (fixture)

A tiny, realistic TypeScript project used to CI-verify harness
integration against non-trivial pre-existing content — specifically a
`.gitignore` with real Node/TypeScript entries, which must survive
`harness-link.sh`'s merge untouched. See `../sample-project/README.md`
for the blank/generic fixture and the full method-by-method walkthrough;
this one only adds what's different for a TypeScript consumer.

```bash
~/agentharness/tools/setup/harness-link.sh init . --mode link --with-hook
bash verify.sh
```

There is no TypeScript-specific *skill* today — `languages/typescript/
CONVENTIONS.md` is a guide, not a bundled skill, so it isn't installed
by any mode (see `.github/CLAUDE.md` in this fixture for the exact
caveat by mode).

Exercised in CI across all three install modes (link/copy/submodule) by
the `fixture-matrix` job in `.github/workflows/ci.yml`, which also runs
`doctor`, `update`, and `uninstall` against it.
