# Security

This is a personal documentation/tooling repository — instructions,
conventions, and a couple of scripts. There's no running service, no
user data, and no attack surface beyond "a script in here could be
wrong." Still, two things are worth stating explicitly.

## If you find a secret committed to this repo's history

1. **Assume it's compromised**, even if you're about to remove it —
   public git history can be cached, forked, or scraped before you catch
   it.
2. **Rotate the secret first**, then clean history. Cleaning history
   without rotating leaves the actual exposure window unchanged; you've
   just made it harder to find, not harder to use.
3. **Clean history** with [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
   (preferred) or `git filter-repo` (fallback) — see
   `.github/BRANCHING_STRATEGY.md#if-you-accidentally-committed-secrets`
   for the exact commands. Don't use `git filter-branch`; it's slow and
   easy to misuse, and only rewrites the branch you're on, not every
   branch that has the secret.
4. **Tell anyone with a clone to re-clone**, not pull — a force-pushed
   history rewrite doesn't merge cleanly with an existing clone.

## If you find a bug in the hook script or setup script

`.github/hooks/prevent-trunk-commit` and `tools/setup/harness-link.sh`
are the only executables in this repo. Neither has elevated privileges
or network access, but a bug in either could still do the wrong thing to
a repo it's installed into (e.g. blocking legitimate commits, or
mis-merging a `.gitignore`). Open an issue or PR; there's no formal
disclosure process needed for a repo at this scale — just fix it and
add a test to `.github/hooks/tests/` covering the case that broke.

## Reporting

Open an issue, or a PR with the fix if you have one. There's no separate
private disclosure channel — nothing in this repo handles user data or
runs as a service, so there's no class of vulnerability that needs
coordinated, embargoed disclosure.
