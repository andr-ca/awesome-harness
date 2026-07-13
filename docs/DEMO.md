# Demo: 5 Minutes With agentharness

A scripted walkthrough of what installing this harness actually does,
using real commands run against a scratch project — every command below
and its output was executed against this repo to write this doc (see
`docs/operational/reviews/gpt-5.6-completion-reaudit-status.md`, P2-07).
No video, no hosting decision needed: copy-paste and run it yourself
against a scratch directory if you want to see it live.

For the full command reference, see [docs/INTEGRATION.md](INTEGRATION.md).
This doc only walks the two things a first-time user actually asks:
"what does init put in my project?" and "what does the enforcement look
like?"

## 1. Install into a fresh project

```console
$ git init -q my-project && cd my-project
$ ~/agentharness/tools/setup/harness-link.sh init . --skills python-conventions,committing --with-hook
Initializing agentharness (/home/you/agentharness) into /home/you/my-project (mode: link)
  Linked skill: python-conventions
  Linked skill: committing
  Created .gitignore from template
  Installed trunk-protection + coverage hooks (core.hooksPath)
Done.
```

`--skills` picks which ones to install (omit it for all of them);
`--with-hook` additionally points `core.hooksPath` at this repo's
enforced hooks (see "Advisory vs. enforced" in the README — this step is
optional).

## 2. See what actually landed

```console
$ ls -la .claude/skills/
committing         -> /home/you/agentharness/.claude/skills/committing
python-conventions -> /home/you/agentharness/.claude/skills/python-conventions
```

Symlinks by default (`--mode link`) — Claude Code picks these up the
same way it would any other `.claude/skills/` entry, and they always
reflect the harness checkout's current state. `--mode copy` or
`--mode submodule` are the pinned alternatives; see
`docs/RELEASING.md`'s Pin/Upgrade/Rollback table.

```console
$ ~/agentharness/tools/setup/harness-link.sh status .
agentharness install status for /home/you/my-project
  mode:          link
  source path:   /home/you/agentharness
  source rev:    d4d2541988ea6bb5a02fd3161aef8fe31e9b0fbd
  source remote: git@github.com:andr-ca/agentharness.git
  skills:        python-conventions,committing
  with_hook:     true
  profile:       (none)
  installed_at:  2026-07-13T03:02:58Z
  updated_at:    2026-07-13T03:02:58Z
```

`.agentharness-state.json` (what `status` reads) is how `doctor`,
`audit`, and `update` know what's installed without re-deriving it.

## 3. The enforced part: trunk protection

`--with-hook` wires `.github/hooks/prevent-trunk-commit` in as this
project's `core.hooksPath` pre-commit hook. It's not advisory — it
refuses the commit outright:

```console
$ echo "change" >> README.md && git add README.md
$ git commit -m "edit readme"

╔════════════════════════════════════════════════════════════════╗
║          ✗ CANNOT COMMIT DIRECTLY TO TRUNK BRANCH              ║
╚════════════════════════════════════════════════════════════════╝

Current branch: master

This is a trunk/main branch and should only receive commits via pull requests.
```

(then prints the feature-branch instructions and exits non-zero — commit
does not happen)

The same change on a feature branch goes through normally:

```console
$ git checkout -b feature/demo-change
$ git commit -m "edit readme"
[feature/demo-change 9624754] edit readme
 1 file changed, 1 insertion(+)
```

The other enforced hook, `pre-push`, only ever tests *this*
(agentharness) repo's own suites when pushing to *this* repo — it no-ops
for every consuming project's own push, even though `--with-hook` wires
`core.hooksPath` to the same directory. See `.github/hooks/pre-push`'s
own comments, or `docs/operational/reviews/gpt-5.6-review-status.md`
finding 1 for the regression this design avoids.

## 4. Everything else is advisory, not enforced

`CLAUDE.md`, the skill files, and every guide under `languages/` and
`patterns/` are conventions an agent (or a human) is expected to follow
— nothing mechanically stops anyone from ignoring them. See the
README's "Advisory vs. enforced" section for the exact boundary, and
`docs/operational/reviews/gpt-5.6-completion-reaudit-status.md` (P0-03)
for the open question about how much default authority an agent gets
once it's read `CLAUDE.md`.
