---
name: file-placement-policy
description: Protocol governing where agents may create files — guarded root directories, config files, and docs/ — and how to request permission before creating anything in an established project structure.
complexity: low
scope: [all]
---

# File Placement Policy

Agents must **not** create new files or directories in guarded locations
without first receiving explicit user permission.

## What is guarded

The guarded locations for a project are defined in
`.agentharness-guarded-paths.json` at the project root. If that file
does not exist, no restrictions apply.

The typical guarded locations in an established project:

| Location | Example paths |
|---|---|
| Root-level items | Any new file/dir at `./` depth |
| Source code | `src/`, `lib/`, `app/`, `pkg/` |
| Tests | `tests/`, `test/`, `spec/` |
| Documentation | `docs/`, `doc/` |
| Config/runtime | `conf/`, `config/`, `logs/` |
| Root config files | `.gitignore`, `package.json`, `Dockerfile`, etc. |

## Before creating a file: check

```bash
# Check if a location is guarded
python3 tools/analyze_structure.py . | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(json.dumps(d.get('guarded_dirs', []), indent=2))
"

# Or: load .agentharness-guarded-paths.json directly
python3 -c "import json; print(json.load(open('.agentharness-guarded-paths.json')))"
```

## When you need to create a guarded file: ask first

1. Tell the user where you want to create the file and why.
2. Wait for explicit approval (`"yes"`, `"ok"`, `"go ahead"`, etc.).
3. Add the approved path to `.agentharness-allowed-additions.txt` so the
   pre-commit hook doesn't block it.
4. Create the file.
5. Commit it — the hook will read the allowed-additions list.

**One standing exception:** `docs/operational/harness-feedback.md` — the
harness-feedback skill already carries its own standing authorization
to create this exact file without asking (see that skill's "no
ask-the-user step for logging" rule), which would otherwise directly
contradict this policy's ask-first default for any consumer with a
guarded `docs/`. `tools/check-file-placement.sh` exempts this one path
outright rather than requiring every consumer to remember to pre-seed
`.agentharness-allowed-additions.txt` (issue #110). Nothing else under
`docs/operational/` gets this exemption.

## For new projects: recommend structure first

If `.agentharness-guarded-paths.json` does not exist, the project may
be new. Before creating files, run the analyzer:

```bash
python3 tools/analyze_structure.py . --recommend
```

If the project is early-stage, present the recommendations to the user
and get approval before creating the structure.

## Init-time generation

The guarded-paths config is generated automatically during
`agentharness init` by calling the analyzer. To regenerate it:

```bash
python3 tools/analyze_structure.py <project-root> \
    --output .agentharness-guarded-paths.json
```

## Enforcement

The pre-commit hook runs `tools/check-file-placement.sh` before every
commit. It blocks staged files in guarded paths unless those paths are
listed in `.agentharness-allowed-additions.txt`.
