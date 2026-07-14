---
name: dependency-audit
description: Use when adding dependencies, reviewing a project's dependency tree, or checking for known vulnerabilities — covers pip-audit, npm audit, govulncheck, lock file hygiene, and update policy.
metadata:
  type: skills
  complexity: low
  languages: [python, typescript, javascript, go]
---

# Dependency Audit

Checking and managing third-party dependencies for known vulnerabilities
and supply-chain risks. This operationalises OWASP A06 (Vulnerable and
Outdated Components) at the dependency level.

---

## When to run an audit

- Before shipping a new feature or release.
- When adding a new dependency.
- When a CVE advisory mentions a package you use.
- On a scheduled basis (weekly or monthly, via CI).

---

## Python — pip-audit

```bash
# Install
pip install pip-audit

# Audit current environment
pip-audit

# Audit against a requirements file
pip-audit -r requirements.txt

# Exit non-zero on any vulnerability (CI gate)
pip-audit --strict
```

Fix: upgrade the package (`pip install --upgrade <package>`) or pin to
a patched version in `requirements.txt`. If no fix is available, document
the accepted risk in a comment near the pin.

---

## Node / TypeScript — npm audit

```bash
# Audit and show summary
npm audit

# Show only high and critical
npm audit --audit-level=high

# Fix automatically (updates package-lock.json)
npm audit fix

# Fix including semver-major bumps (review carefully)
npm audit fix --force
```

For CI, prefer `npm audit --audit-level=high` so the exit code gates
the build on high/critical findings:

```bash
npm audit --audit-level=high || { echo "High/critical vulnerabilities found"; exit 1; }
```

Or use `audit-ci` for more control:

```bash
npx audit-ci --high          # fail on high+
npx audit-ci --config .audit-ci.json   # custom config for allowlist
```

---

## Go — govulncheck

```bash
# Install
go install golang.org/x/vuln/cmd/govulncheck@latest

# Audit the module
govulncheck ./...

# JSON output for CI parsing
govulncheck -json ./...
```

`govulncheck` only reports vulnerabilities in code paths that are actually
reachable — it doesn't flag packages you import but never call.

---

## Lock files — never skip them

| Language | Lock file | Commit it? |
|---|---|---|
| Python | `requirements.txt` (pinned) or `uv.lock` / `poetry.lock` | Yes |
| Node | `package-lock.json` or `yarn.lock` or `pnpm-lock.yaml` | Yes |
| Go | `go.sum` | Yes |

**Always commit lock files.** They guarantee reproducible builds. Running
`npm install` (without `npm ci`) on a system without a lock file can
silently pull in newer, potentially vulnerable versions.

In CI, use the install command that respects the lock file:
- Python: `pip install -r requirements.txt` (pinned versions) or `uv sync`
- Node: `npm ci` (not `npm install`)
- Go: `go build ./...` (go.sum is always respected)

---

## Version pinning policy

| Scenario | Recommendation |
|---|---|
| Direct production dependencies | Pin to exact version or narrow range |
| Dev/test tools | Minor-range pinning (`^1.2.0`) is acceptable |
| Transitive dependencies | Managed via lock file; don't pin manually |
| `latest` tag | Never use in production |

---

## What to do with a finding

1. **Check severity.** CRITICAL/HIGH: fix before shipping. MEDIUM: fix
   within the sprint. LOW/INFO: schedule or accept with documentation.
2. **Check if the vulnerable code path is actually called.** `govulncheck`
   does this for Go; for Python/Node you may need to trace manually.
3. **Upgrade or patch.** Pin to the patched version in the lock file.
4. **If no fix exists:** document the accepted risk as a comment in the
   lock/requirements file, create a tracking issue, and set a review date.
5. **Never just silence the audit.** Suppressions require documented
   justification.

---

## Review checklist

- [ ] Lock file committed and up to date
- [ ] `npm ci` / `pip install -r requirements.txt` / `go build` used in CI
- [ ] Audit run before this release (`pip-audit`, `npm audit`, `govulncheck`)
- [ ] No HIGH or CRITICAL open CVEs
- [ ] New dependencies justified (do you need a whole library for this?)
- [ ] No `latest` version tags in dependency files
