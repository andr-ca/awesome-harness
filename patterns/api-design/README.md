# API Design

Index for this directory — each doc is the single source of truth for
its topic; this file routes to them and states what applies where.

Applies in full at **Production tier**. See
`.github/CODING_GUIDELINES.md#rigor-tiers` for what changes at
Prototype/Internal tiers.

The quick reference is the on-demand skill at
`.claude/skills/api-design/SKILL.md` — load it for day-to-day decisions.
The docs below are the canonical source the skill summarises.

| Doc | Covers |
|---|---|
| [REST_CONVENTIONS.md](./REST_CONVENTIONS.md) | Resource naming, HTTP methods + status codes, error shapes (RFC 9457), versioning, pagination, authentication |

**Read REST_CONVENTIONS.md first.** It is the mandatory standard for all
REST/HTTP APIs in Production-tier harness-linked projects. GraphQL-specific
guidance lives in the relevant skill (`.claude/skills/api-design/SKILL.md`)
until traffic justifies a dedicated doc.
