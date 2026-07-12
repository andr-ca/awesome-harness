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

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"


def materialize() -> None:
    for link in sorted(SKILLS_DIR.rglob("*")):
        if link.is_symlink():
            target = link.resolve()
            link.unlink()
            shutil.copy2(target, link)


def restore() -> None:
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
