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

## npm distribution

This repo is distributed as `agentharness-toolkit` on npm. If you believe a published version contains a supply-chain vulnerability (e.g. malicious code injected into the package), report it by opening an issue on this repository. Do not install untrusted versions from unofficial mirrors.

**Integrity verification.** The consumer's committed `runtime.lock` file records the SHA-512 digest of the shipped Python zipapp under the `zipapp.sha512` key. The dependency-free bootstrapper verifies this digest before executing the zipapp. If you observe a mismatch between the published artifact and the lock file, treat the artifact as potentially tampered and report it.

**What consumers install.** `harness-link.sh --mode npm` copies the tarball into a durable directory inside the consumer's repo (`.agentharness-pkg/`). This copy does not execute arbitrary code on its own — but if the install used `--with-hook`, git's `core.hooksPath` may point at a hooks directory inside the durable copy, meaning hooks (trunk protection, pre-commit checks) run from the copy on every git operation. Hooks inside the copy are fixed at install time; they don't change without an explicit `harness-link.sh update`. The npm lifecycle scripts (`prepack`/`postpack`) only run during publishing and packaging on the harness maintainer's machine; they never run on a consumer's machine.

## git config mutations

Several harness commands write to a consumer's git configuration:

- `harness-link.sh --with-hook` sets `core.hooksPath` in the consumer. The exact path depends on the install mode: `link`/`submodule`/`npm` installs point to the shared `.github/hooks` directory inside the harness source; `copy` and `--with-coverage-hook` installs write real files into the consumer's own `.github/hooks/` and point there.
- `harness-link.sh uninstall` restores the previous `core.hooksPath` value (recorded in `.agentharness-state.json`).

**Trust boundary.** These mutations are opt-in (`--with-hook` is a flag, not the default) and documented. The harness never sets config values outside the consumer's own repository.

**What could go wrong.** A bug in `uninstall` that fails to restore `core.hooksPath` would redirect the consumer's git hooks to the (now-removed) harness path — silently disabling trunk protection, pre-commit checks, etc. This is tracked as F-05 in the project's readiness plan; the fix (recording and restoring the previous value) was shipped in `v0.2.0`.

If you find a case where `uninstall` leaves the consumer's git config in an unexpected state, report it as a bug issue. The mitigation is to run `git config --unset core.hooksPath` in the consumer and re-install.

## GitHub branch protection changes

The Python core's `agentharness github protection apply` command writes to a consumer repo's branch protection settings via the GitHub REST API. `harness-link.sh generate-clients` does **not** make GitHub API calls — it only writes local files. The `protection apply` command:

- Requires an explicit `--repo owner/repo` argument and a GitHub token with `repo: admin` scope.
- Sets `required_pull_request_reviews`, `required_status_checks`, `enforce_admins`, and `restrictions` on the target branch.
- Reads back the settings after writing to verify they match the declared plan.

**Trust boundary.** The command is never invoked automatically. It requires an explicit user invocation with an API token. The harness does not store or transmit tokens.

**Least-privilege recommendation.** Use a fine-grained personal access token scoped to the specific repository and the `administration: write` permission, not a classic token with broad org access.

## Supported boundary

The following are **in scope** as security bugs:

- A hook script that modifies files outside the targeted repository.
- A skill instruction that could cause an agent to exfiltrate secrets, disable safety checks, or run destructive commands.
- A harness-link subcommand that mutates git config or file system state without restoring it on uninstall.
- A supply-chain issue with the published npm package or Python zipapp.

The following are **out of scope** (by design):

- The agent following a harness instruction in a way the user didn't intend — agents are non-deterministic; the skill instructions are guidance, not a sandbox.
- A consumer project's own CI or branch rules that happen to conflict with what the harness suggests.
- Vulnerabilities in tools the harness recommends (ruff, mypy, bats, etc.) — report those upstream.

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
