---
name: rest-api-conventions
description: Mandatory REST API design conventions for Production-tier HTTP services — resource naming, HTTP semantics, error response shapes, versioning, pagination, and authentication
complexity: medium
applies_to: all HTTP APIs at Production tier
---

# REST API Conventions

The canonical reference for HTTP API design in Production-tier services.
The on-demand skill at `.claude/skills/api-design/SKILL.md` summarises
this doc for day-to-day use. This doc is the source of truth.

---

## Resource naming

Use nouns, not verbs. Collections are plural. Use `kebab-case` for
multi-word path segments. Identifiers go in the path; filters and
pagination go in the query string.

```
# Collections and members
GET    /users                      → list users
POST   /users                      → create a user
GET    /users/{id}                 → get a single user
PATCH  /users/{id}                 → partial update (send only changed fields)
PUT    /users/{id}                 → full replace (send the entire resource)
DELETE /users/{id}                 → delete

# Nested resources (ownership relationship)
GET    /users/{id}/posts           → posts belonging to a user
POST   /users/{id}/posts           → create a post for a user

# Actions that don't map cleanly to CRUD
POST   /users/{id}/activate        → trigger a state transition
POST   /payments/{id}/refund       → trigger a business process
```

**Path naming rules:**
- `kebab-case` for path segments: `/user-profiles`, not `/user_profiles`
  or `/userProfiles`
- `camelCase` for JSON field names: `{"userId": "abc"}`, not
  `{"user_id": "abc"}` (consistent with most JS/TS clients; choose one
  and enforce it with a serialiser, not case-by-case)
- Never encode the HTTP method in the URL: `POST /users/create` is wrong;
  `POST /users` is right

---

## HTTP methods and status codes

### Methods

| Method | Idempotent | Safe | Use for |
|---|---|---|---|
| `GET` | Yes | Yes | Retrieve; never mutates state |
| `POST` | No | No | Create, or trigger a non-idempotent action |
| `PUT` | Yes | No | Full replacement of a resource |
| `PATCH` | No | No | Partial update; send only changed fields |
| `DELETE` | Yes | No | Delete a resource |

### Status codes — use them precisely

| Code | Use for |
|---|---|
| 200 OK | Successful GET, PATCH, PUT |
| 201 Created | Successful POST that created a resource; `Location` header points to the new resource |
| 204 No Content | Successful DELETE or action with no response body |
| 400 Bad Request | Client sent syntactically invalid data |
| 401 Unauthorized | Not authenticated (missing or invalid credentials) |
| 403 Forbidden | Authenticated but not permitted for this resource |
| 404 Not Found | Resource does not exist (or is hidden for auth reasons) |
| 409 Conflict | Duplicate creation attempt; optimistic lock failure |
| 422 Unprocessable Entity | Syntactically valid but semantically invalid input (e.g. email format wrong, age negative) |
| 429 Too Many Requests | Rate limit exceeded; include `Retry-After` header |
| 500 Internal Server Error | Unexpected server failure; never expose internal details |

**Common mistakes:**
- `200` with `{"success": false, "error": "..."}` in the body —
  use a `4xx` status code instead; the HTTP layer communicates the outcome
- `404` for auth failures — use `401`/`403`; a `404` on a protected
  resource can leak existence
- `500` for business logic failures — pick the appropriate `4xx`

---

## Error response shape

All `4xx` and `5xx` responses must use the
[RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457) format.
`Content-Type: application/problem+json`.

```json
{
  "type": "https://api.example.com/errors/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "detail": "The submitted form contains invalid values.",
  "instance": "/requests/f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "errors": [
    {
      "field": "email",
      "message": "must be a valid email address",
      "code": "invalid_format"
    },
    {
      "field": "age",
      "message": "must be a positive integer",
      "code": "out_of_range"
    }
  ]
}
```

**Field rules:**
- `type` — a stable URI identifying the error class. It does not need to
  resolve, but should if possible.
- `title` — a stable, human-readable label for the error class. Does not
  change between occurrences.
- `status` — the HTTP status code (redundant with the response code, but
  useful for clients that read the body before the status line).
- `detail` — a human-readable description specific to this occurrence.
  May change for each error. Safe to show to the user.
- `instance` — a URI identifying this specific error occurrence. Use a
  request ID or correlation ID.
- `errors` — (extension) field-level validation failures. Include `field`
  (JSON path from the request root), `message` (human-readable), and `code`
  (machine-readable, stable identifier).

**Never include in error responses:**
- Stack traces or exception class names
- Raw database error messages
- Internal identifiers, file paths, or server hostnames
- Any field that differs between `development` and `production` builds
  (unless gated by a non-user-facing flag)

---

## Versioning

### URL versioning (recommended for public APIs)

```
/v1/users     → current stable version
/v2/users     → new version with breaking changes
```

**What is a breaking change:**
- Removing a field, endpoint, or HTTP method
- Changing a field's type (e.g. `string` → `integer`)
- Changing a field's semantics (e.g. `status` values change meaning)
- Making a previously optional field required
- Changing the error response shape

**What is NOT a breaking change:**
- Adding a new optional field to a response
- Adding a new endpoint
- Adding a new optional query parameter
- Adding new values to an extensible enum (if clients use `default` cases)

**Deprecation:**
- Give at least 6 months' notice before removing a version.
- Add a `Deprecation` response header on the deprecated version's responses:
  `Deprecation: Tue, 31 Dec 2026 00:00:00 GMT`
- Add a `Sunset` header for the removal date:
  `Sunset: Tue, 31 Dec 2026 00:00:00 GMT`
- Document the migration path from the old version to the new one.

---

## Pagination

Use **cursor-based pagination** for any list endpoint that may return more
than 100 items or where the dataset changes frequently. Offset pagination
is simpler but breaks under concurrent writes (items can be skipped or
duplicated as pages shift).

### Cursor-based (preferred)

```http
GET /users?cursor=eyJpZCI6MTAwfQ&limit=20

{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTIwfQ",
    "prev_cursor": "eyJpZCI6MTAxfQ",
    "has_more": true,
    "total": null
  }
}
```

**Rules:**
- The cursor is opaque to the client — base64-encode the internal state;
  do not expose a parseable format.
- `has_more: false` on the last page; omit `next_cursor` or set it `null`.
- `total` is `null` unless you can compute it cheaply; don't run a
  `COUNT(*)` for every paginated request.
- Server enforces a maximum `limit` (e.g. 100); clients may request fewer.

### Offset-based (simple cases only)

```http
GET /users?page=3&per_page=20

{
  "data": [...],
  "pagination": {
    "page": 3,
    "per_page": 20,
    "total_pages": 15,
    "total_items": 297
  }
}
```

Use offset only for small, static datasets where the count query is
cheap and concurrent writes don't occur during a paginated session.

---

## Authentication and authorization

### Token delivery

- **Bearer tokens** in the `Authorization` header:
  `Authorization: Bearer <token>`
- **API keys** in a custom request header: `X-Api-Key: <key>`
- **Never** in URL query parameters — they appear in server logs, browser
  history, and referrer headers

### Status code semantics

- `401 Unauthorized` — credentials are missing, invalid, or expired.
  Include `WWW-Authenticate` header: `WWW-Authenticate: Bearer realm="api"`
- `403 Forbidden` — credentials are valid but the caller lacks permission
  for this specific resource or operation

### Resource scoping

Every endpoint that returns user-owned data must verify that the
authenticated caller owns or is permitted to access the requested resource:

```python
# WRONG: fetches any record; no ownership check
def get_document(doc_id: str) -> Document:
    return db.get(Document, doc_id)

# RIGHT: scopes to the authenticated user
def get_document(doc_id: str, current_user: User) -> Document:
    doc = db.query(Document).filter_by(
        id=doc_id, owner_id=current_user.id
    ).first()
    if not doc:
        raise NotFoundError()
    return doc
```

---

## Request/response headers

Always set:
- `Content-Type: application/json` on responses with a JSON body
- `Content-Type: application/problem+json` on error responses
- `Cache-Control: no-store` on responses containing user-specific data

On responses that vary by client headers:
- `Vary: Accept-Encoding` (if you gzip)
- `Vary: Accept` (if you serve multiple formats)

For CORS (if needed):
- Be explicit — `Access-Control-Allow-Origin: *` is only acceptable for
  fully public, non-credentialed endpoints
- Prefer an allowlist of known origins for credentialed endpoints

---

## Review checklist

- [ ] Resources are nouns; collections are plural; `kebab-case` paths
- [ ] `GET` does not mutate state
- [ ] Correct status codes for each operation (201 for created, 204 for no-body delete)
- [ ] All `4xx`/`5xx` responses use RFC 9457 format; no stack traces in responses
- [ ] Breaking changes bump the API version; additive changes do not
- [ ] List endpoints are paginated; cursor-based for large/volatile datasets
- [ ] Auth tokens in headers only (not URL query params)
- [ ] Ownership check on every resource that belongs to a user
- [ ] `Deprecation` and `Sunset` headers on deprecated endpoints
