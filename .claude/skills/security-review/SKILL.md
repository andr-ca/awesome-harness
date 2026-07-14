---
name: security-review
description: Use when reviewing code for security vulnerabilities, performing a security audit, or checking for OWASP Top 10 issues — covers injection flaws, broken access control, cryptographic failures, secrets exposure, dependency vulnerabilities, and language-specific pitfalls for Python, TypeScript/JavaScript, and Go.
metadata:
  type: skills
  complexity: medium
  languages: [python, typescript, javascript, go]
---

# Security Review

This skill operationalises the OWASP mandate in this harness's own
instructions: "Ensure your code is free from security vulnerabilities
outlined in the OWASP Top 10." Work through this checklist for every
production-tier code review; prioritise findings as P0 (must fix before
merge) or P1 (fix within the sprint).

External reference: [OWASP Top 10 (2021)](https://owasp.org/Top10/).

---

## A01 — Broken Access Control

**What to look for:** Missing authentication checks, insecure direct
object references (IDOR), privilege escalation paths, CORS misconfiguration.

```python
# WRONG: fetches any record by ID — no ownership check
def get_document(doc_id: int) -> Document:
    return db.query(Document).filter_by(id=doc_id).first()

# RIGHT: scope to the authenticated user
def get_document(doc_id: int, current_user: User) -> Document:
    doc = db.query(Document).filter_by(id=doc_id, owner_id=current_user.id).first()
    if doc is None:
        raise NotFoundError()
    return doc
```

**Checklist:**
- Every route/handler checks that the caller owns or is permitted to
  access the resource it requests.
- Admin/privileged endpoints require an explicit role check, not just
  authentication.
- CORS `Access-Control-Allow-Origin: *` is not set on endpoints that
  return sensitive data.

---

## A02 — Cryptographic Failures

**What to look for:** Hardcoded secrets, weak algorithms (MD5, SHA-1,
DES), HTTP instead of HTTPS for sensitive data, secrets logged.

```python
# WRONG: hardcoded API key and weak hashing
API_KEY = "sk-12345abcde"
password_hash = hashlib.md5(password.encode()).hexdigest()

# RIGHT: key from environment; use bcrypt/argon2 for passwords
import os, bcrypt
API_KEY = os.environ["OPENAI_API_KEY"]
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

**Checklist:**
- No credentials, tokens, or private keys in source code or committed
  config files. Use `.env` + `.env.sample` pattern.
- Password storage uses bcrypt, argon2, or scrypt — never MD5/SHA-1.
- Sensitive data transmitted only over TLS; no HTTP fallback for auth.

---

## A03 — Injection

**What to look for:** SQL injection via string formatting, command
injection via `subprocess` with `shell=True`, template injection,
NoSQL injection.

```python
# WRONG: SQL injection via f-string
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")

# RIGHT: parameterised query
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))

# WRONG: shell injection
subprocess.run(f"convert {filename}", shell=True)

# RIGHT: list form — no shell interpretation
subprocess.run(["convert", filename])
```

```typescript
// WRONG: XSS via dangerouslySetInnerHTML or innerHTML
element.innerHTML = userInput;
// RIGHT: use text content
element.textContent = userInput;
```

**Checklist:**
- All database queries use parameterised statements or an ORM that
  handles escaping.
- `subprocess` / `child_process.exec` never uses `shell=True` / `{shell: true}`
  with user-controlled input.
- No direct HTML string construction from user data.

---

## A05 — Security Misconfiguration

**What to look for:** Debug mode in production, default credentials,
verbose error messages exposing stack traces, unnecessary features/endpoints
enabled, permissive file permissions.

```python
# WRONG: debug=True in a production deploy
app.run(debug=True)

# RIGHT: read from environment
app.run(debug=os.environ.get("DEBUG", "false").lower() == "true")
```

**Checklist:**
- Debug mode, verbose logging, and internal error details are disabled
  in production (controlled by environment variable, not a code constant).
- Default passwords and example credentials are not shipped; `.env.sample`
  uses placeholder values only.
- API endpoints that exist for development/testing are not deployed to
  production.

---

## A06 — Vulnerable and Outdated Components

**What to look for:** Known CVEs in dependencies; unpinned versions.

```bash
# Python
pip-audit                     # install: pip install pip-audit

# Node / TypeScript
npm audit                     # built-in; use --audit-level=high for CI gate
npx audit-ci --high           # CI-friendly exit-code variant

# Go
govulncheck ./...              # install: go install golang.org/x/vuln/cmd/govulncheck@latest
```

**Checklist:**
- Run the appropriate command above before every production release.
- Pin direct dependencies to exact or narrow version ranges; don't use
  `*` or `latest`.
- Known HIGH/CRITICAL CVEs block merge; MEDIUM CVEs are tracked and
  scheduled.

---

## A07 — Identification and Authentication Failures

**What to look for:** Weak session tokens, missing rate limiting on
login endpoints, passwords in URLs or logs, JWTs without expiry.

**Checklist:**
- Session tokens are cryptographically random (≥ 128 bits), never
  derived from user data.
- Login and password-reset endpoints have rate limiting.
- JWTs have a short `exp` claim (≤ 1 hour for access tokens); refresh
  token rotation is implemented.
- Passwords never appear in URL query parameters or log output.

---

## A08 — Software and Data Integrity Failures

**What to look for:** Deserialising untrusted data with `pickle` (Python)
or `eval`/`Function()` (JS), unsigned package installs, CI/CD with
untrusted actions.

```python
# WRONG: pickle deserialises arbitrary code
data = pickle.loads(untrusted_bytes)

# RIGHT: use JSON or a schema-validated format
data = json.loads(untrusted_bytes)
```

**Checklist:**
- Never deserialise with `pickle`, `marshal`, or `yaml.load` (use
  `yaml.safe_load`) from untrusted sources.
- Third-party CI actions are pinned to a full commit SHA, not a mutable
  tag (`uses: actions/checkout@v4` can be silently replaced).

---

## A10 — Server-Side Request Forgery (SSRF)

**What to look for:** HTTP requests to URLs controlled by user input,
fetching files by user-provided path, webhooks without allowlisting.

```python
# WRONG: fetches any URL the user provides
response = requests.get(user_provided_url)

# RIGHT: validate against an allowlist before fetching
ALLOWED_HOSTS = {"api.partner.com", "cdn.example.com"}
parsed = urllib.parse.urlparse(user_provided_url)
if parsed.hostname not in ALLOWED_HOSTS:
    raise ValueError("URL not allowed")
response = requests.get(user_provided_url)
```

**Checklist:**
- Outbound HTTP calls from the server use an explicit allowlist of
  hosts/schemas; reject anything else.
- Metadata endpoints (AWS `169.254.169.254`, GCP `metadata.google.internal`)
  are blocked at the network level and guarded in code.

---

## Secrets scanning

Run before every push:

```bash
# trufflehog (open source, high signal)
trufflehog git file://. --since-commit HEAD~1 --only-verified

# gitleaks (config-driven, fast)
gitleaks detect --source . --log-opts="HEAD~1..HEAD"
```

GitHub's built-in secret scanning fires automatically; check the
"Security" tab on every repo.

---

## Language-specific quick-reference

### Python

| Risk | Wrong | Right |
|---|---|---|
| SQL | `f"... {val}"` | `cursor.execute(q, (val,))` |
| Shell | `shell=True` + var | list form |
| Deserialise | `pickle.loads` | `json.loads` |
| Hash password | `hashlib.md5` | `bcrypt` / `argon2-cffi` |
| Secret source | hardcoded | `os.environ["KEY"]` |

### TypeScript / JavaScript

| Risk | Wrong | Right |
|---|---|---|
| XSS | `innerHTML = input` | `textContent = input` |
| Eval | `eval(code)` / `new Function(code)` | never; use a safe parser |
| Prototype pollution | merge from user JSON without schema | validate schema first |
| Secret source | hardcoded | `process.env.KEY` |
| HTTPS | `http://` internal call | `https://` always |

### Go

| Risk | Wrong | Right |
|---|---|---|
| SQL | `fmt.Sprintf` in query | `db.Query(q, args...)` |
| Shell | `exec.Command("sh", "-c", input)` | `exec.Command("cmd", arg)` |
| SSRF | `http.Get(userURL)` | allowlist check first |
| Error leak | `http.Error(w, err.Error(), 500)` | generic message, log internally |
| Secret source | hardcoded const | `os.Getenv("KEY")` |

---

## Review checklist (summary)

Before approving a PR, confirm:

- [ ] No secrets, tokens, or credentials in source code or config
- [ ] All DB queries parameterised; no string-interpolated SQL
- [ ] `subprocess`/`exec` uses list form; no user input in shell strings
- [ ] XSS: no raw user content in HTML; Content-Security-Policy header set
- [ ] Auth checks on every sensitive endpoint; IDOR not possible
- [ ] Dependency audit run; no HIGH/CRITICAL open CVEs
- [ ] Debug mode, verbose errors off in production
- [ ] Outbound HTTP from server uses an allowlist
- [ ] Secrets scanning clean (`gitleaks` or `trufflehog`)
