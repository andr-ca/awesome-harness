#!/usr/bin/env python3
"""npm prepack/postpack hook.

npm tarballs don't preserve symlinks (git does), and a few skills bundle
resources as relative symlinks back into patterns/ (e.g.
.claude/skills/agentic-loops/agent_loop.py -> ../../../patterns/
agentic-loops/agent_loop.py) rather than duplicating the file. Left
alone, `npm pack`/`npm publish` would silently drop those files from the
published tarball. 'materialize' replaces each such symlink with a real
copy of its target just before packing; 'restore' puts the symlinks back
afterward via `git checkout` so the working tree stays exactly what git
tracks.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"


def materialize() -> None:
    for link in sorted(SKILLS_DIR.rglob("*")):
        if not link.is_symlink():
            continue
        target = link.resolve()
        # Every bundled-resource symlink this repo actually uses points
        # back into the repo itself (e.g. patterns/agentic-loops/). A
        # symlink resolving outside the repo root is either a mistake or
        # something worse — not a file `npm pack` should ever copy into
        # a published tarball — so refuse rather than blindly follow it.
        if not target.is_relative_to(REPO_ROOT):
            raise ValueError(
                f"{link} resolves outside the repo root ({target}) — refusing to materialize"
            )
        if not target.is_file():
            raise ValueError(f"{link} resolves to {target}, which isn't a regular file")
        # Copy before unlinking: if copy2() fails partway (disk full, a
        # permissions error), the symlink is still there to retry/restore
        # from, instead of leaving neither a symlink nor a real file.
        shutil.copy2(target, link.with_name(link.name + ".materializing"))
        link.unlink()
        link.with_name(link.name + ".materializing").rename(link)


def restore() -> None:
    """Restore symlinks via git checkout.

    In a bare git repository (or any context where git requires a work tree),
    git checkout -- will fail. In that case, log a warning and skip — the
    materialized files will remain, which is acceptable for local dev; the
    prepack/postpack cycle is intended for npm pack in CI (a normal clone).
    """
    is_work_tree = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    ).stdout.strip() == "true"
    if not is_work_tree:
        print(
            "materialize-skill-symlinks.py restore: not inside a work tree "
            "(bare repo?); skipping git checkout. Materialized files remain.",
            file=sys.stderr,
        )
        return
    subprocess.run(["git", "checkout", "--", str(SKILLS_DIR)], check=True)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "materialize":
        materialize()
    elif action == "restore":
        restore()
    else:
        print(
            "usage: materialize-skill-symlinks.py {materialize|restore}",
            file=sys.stderr,
        )
        sys.exit(1)
