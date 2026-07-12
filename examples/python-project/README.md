# python-project (fixture)

A tiny, realistic Python project used to CI-verify harness integration
against non-trivial pre-existing content — specifically a `.gitignore`
with real Python entries, which must survive `harness-link.sh`'s merge
untouched. See `../sample-project/README.md` for the blank/generic
fixture and the full method-by-method walkthrough; this one only adds
what's different for a Python consumer.

```bash
~/agentharness/tools/setup/harness-link.sh init . --mode link --with-hook
bash verify.sh
```

Exercised in CI across all three install modes (link/copy/submodule) by
the `fixture-matrix` job in `.github/workflows/ci.yml`, which also runs
`doctor`, `update`, and `uninstall` against it.
