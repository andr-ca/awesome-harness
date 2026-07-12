# Release Discipline

How a tag gets cut, what a version number means to a consuming project,
and how to move a consumer between versions (pin, upgrade, roll back).
See [CHANGELOG.md](../CHANGELOG.md) for the history this policy governs.

## Versioning

Tags are `vMAJOR.MINOR.PATCH`. While the repo is `0.x` (current: `v0.1.0`):

- No stability guarantee. Any release may rename or remove a skill,
  change `harness-link.sh`'s CLI shape, or change
  `.agentharness-state.json`'s schema.
- `MINOR` bumps signal "content or CLI surface changed, check the
  changelog before updating a pinned consumer." `PATCH` bumps are
  docs/test-only changes with no behavior change for a consumer.
- Once a `1.0.0` is cut, `MAJOR` bumps are reserved for breaking changes
  as defined below, and `MINOR`/`PATCH` follow normal semver.

**Breaking change**, for this repo, means any of:

- A skill directory under `.claude/skills/` is renamed or removed.
- A `harness-link.sh` subcommand, flag, or `--mode` value is renamed or
  removed (adding a new one is not breaking).
- `.agentharness-state.json`'s schema changes in a way `doctor`/`status`
  on an older harness checkout can no longer read.
- A convention doc's guidance changes in a way that would fail a
  consumer's existing CI gate (for example, tightening
  `COVERAGE_REQUIREMENTS.md`'s default without a tier escape hatch).

A rename/removal like this should have a deprecation note in
`CHANGELOG.md`'s `Unreleased` section before it ships, so consumers
running `harness-link.sh audit` see it coming.

## Release Checklist

1. `main`'s latest CI run is green — check with
   `gh run list --branch main --limit 1`, not just that the merging PR
   was green (a later push to `main` itself, e.g. a direct hotfix, can
   still break it). Do not tag from a red `main`.
2. Move `CHANGELOG.md`'s `## [Unreleased]` content under a new
   `## [x.y.z] - YYYY-MM-DD` heading; leave a fresh empty `Unreleased`
   section above it.
3. Decide the version bump using the breaking-change definition above.
4. Tag the exact commit that produced the green run from step 1:
   `git tag -a vX.Y.Z -m "vX.Y.Z" <sha> && git push origin vX.Y.Z`.
5. Confirm the tag is reachable and current:
   `git merge-base --is-ancestor <tag> origin/main` should exit 0, and
   `git log --oneline <tag>..origin/main` should be empty (or every
   commit since the tag should be accounted for as "not yet released,
   goes in the next Unreleased section").

## Pin, Upgrade, Rollback

These are the same three operations for every install mode; only how a
consumer moves their pinned reference differs.

| | Pin | Upgrade | Rollback |
|---|---|---|---|
| **link** | Not pinned — always reads the harness checkout's current working tree. "Pin" means pin the harness checkout itself to a tag (`git -C ~/agentharness checkout vX.Y.Z`). | `git -C ~/agentharness pull` (or checkout a newer tag), then `harness-link.sh update` to pick up added/removed skills. | `git -C ~/agentharness checkout <older-tag-or-sha>`, then `harness-link.sh update`. |
| **copy** | The copy itself is the pin — `harness-link.sh init --mode copy` records the source revision it copied from. | `harness-link.sh update` diffs the copy against the *current* source checkout and applies only changed files, after confirmation. | Restore the copied files from version control history (they're committed in the consumer's own repo) or re-run `init --mode copy` against an older harness checkout. |
| **submodule** | `harness-link.sh init --mode submodule` adds `.agentharness` pinned to the harness's exact commit at install time — not the remote's mutable default branch. | `git -C <project> submodule update --remote .agentharness` moves the pin forward, then `harness-link.sh update` re-syncs skill symlinks to match. | `git -C <project>/.agentharness checkout <older-sha>` moves the pin back; skill symlinks resolve correctly with no further action, since they point into the submodule's working tree rather than a specific blob. |

`tools/tests/harness-lifecycle.bats`'s `"--mode submodule supports pin,
rollback, and re-upgrade against real history"` test exercises the
submodule row above end-to-end (real `git checkout` against this repo's
actual commit history, not a simulated one) as a standing regression
check, and `doctor` is asserted healthy at every step.

**Breaking-change handling in practice:** if an upgrade removes a skill
your project used, `harness-link.sh doctor` fails with a clear "skill
directory no longer exists" error (see
`"doctor fails when a skill directory is deleted out from under it"` in
the same test file) instead of leaving a silently-broken symlink; `audit`
surfaces removed/added skills before you run `update` at all.

## Supported Harness / Client Versions

See the README's "Product Contract" section for supported clients and
platforms — that contract doesn't change per-release. This doc only
governs *this repo's own* version history, not what it supports.
