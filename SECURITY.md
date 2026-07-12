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

The executables that get installed into a consuming project are
`.github/hooks/{prevent-trunk-commit,pre-commit,pre-push}` and
`tools/setup/harness-link.sh` (see [MANIFEST.md](MANIFEST.md) for the
complete current list, including this repo's own `tools/check.sh`,
`tools/verify-manifest.sh`, and `tools/verify-content-quality.py`, which
never leave this repo). None has elevated privileges, and only
`harness-link.sh --mode submodule` ever reaches the network (to add the
submodule) — but a bug in any of them could still do the wrong thing to
a repo it's installed into (e.g. blocking legitimate commits, or
mis-merging a `.gitignore`). Open an issue or PR; there's no formal
disclosure process needed for a repo at this scale — just fix it and
add a test to `.github/hooks/tests/` or `tools/tests/` covering the case
that broke.

## The instruction attack surface

Executables aren't the only thing a consuming project trusts from this
repo. `CLAUDE.md`, every `.claude/skills/*/SKILL.md`, and the
`languages/`/`patterns/`/`frameworks/` guides are *instructions* an
agent reads and acts on directly — a symlinked or copied project picks
them up automatically, with no review step of its own. A malicious or
merely careless change here (e.g. a skill instructing an agent to
exfiltrate `.env` contents, silently disable a safety hook, or always
`git push --force`) is a supply-chain risk to every consumer, not just a
bug in a script.

Mitigations today: everything in `.claude/skills/` and `CLAUDE.md` goes
through the same branch-protected PR review as code (see
[.github/CODEOWNERS](.github/CODEOWNERS)); the
[Recommendation Assessment](CLAUDE.md#-agent-recommendation-assessment-mandatory)
mandate requires escalating high-risk changes instead of auto-applying
them; `tools/verify-content-quality.py` validates skill frontmatter
structurally (not semantically — it can't tell a *malicious* instruction
from a benign one, only a malformed one). There's no automated
semantic review of instruction content today; a careful PR reviewer is
the actual control.

## Reporting

Open an issue, or a PR with the fix if you have one.

**Maintainer responsibilities today:** this repo has a single maintainer
(`@andr-ca`, per [.github/CODEOWNERS](.github/CODEOWNERS)), who reviews
and merges every PR. There's no separate private disclosure channel —
nothing in this repo handles user data or runs as a service, so there's
no class of vulnerability that needs coordinated, embargoed disclosure;
a public issue is fine even for a security bug.

**If that changes** — once this repo has external consumers depending
on it in a way where a public issue could be actively exploited before a
fix ships, or once the contributor base grows past one maintainer:
- Add a private reporting channel (e.g. GitHub's private vulnerability
  reporting, or a maintainer email) and document it here.
- Require review from someone other than the author for changes to
  `CLAUDE.md` or any `SKILL.md` (see "The instruction attack surface"
  above) — a single-maintainer repo can't have an independent reviewer,
  but a multi-maintainer one should.
Neither condition holds yet; this section exists so the trigger is
written down instead of decided ad hoc when it does.
