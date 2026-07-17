---
applyTo: "*.rs"
description: "Rust-specific naming conventions, style, and best practices"
---

Generated from `languages/rust/CONVENTIONS.md` by
`tools/generate-copilot-instructions.sh`
(https://github.com/andr-ca/agentharness) — do not hand-edit; regenerate
instead. Only applied by Copilot when editing a file matching
`*.rs`.

---

## Rust Conventions & Best Practices

Naming (`snake_case` for functions/variables/modules, `PascalCase` for
types/traits/enum-variants, `SCREAMING_SNAKE_CASE` for consts/statics),
module layout, and the borrow-checker mechanics are all standard Rust
community convention — see the
[Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) and
[RFC 430 naming](https://github.com/rust-lang/rfcs/blob/master/text/0430-finalizing-naming-conventions.md)
for the parts not worth restating here. `rustfmt` (formatting) and
`clippy` (lints) are the non-negotiable baseline — run both in CI; don't
hand-argue formatting. Below are the places this repo makes an actual
decision.

### `unwrap()`/`expect()` is a rigor-tier decision, not a habit

`.unwrap()` and `.expect()` turn a `None`/`Err` into a panic. That's fine
at the Prototype tier and in tests, but at the Internal and Production
tiers library and request-path code must propagate errors with `?`
instead — a panic in a request handler takes down more than the request.
Reserve `expect()` for genuine invariants that cannot fail, and when you
use it, make the message state *why* it can't fail, not *what* failed:

```rust
// Good: the message documents the invariant.
let port = env::var("PORT").expect("PORT is set by the launcher before exec");

// Bad in Internal/Production code: propagate instead.
let config = load_config()?; // not load_config().unwrap()
```

See [`.github/CODING_GUIDELINES.md`](../../.github/CODING_GUIDELINES.md)'s
rigor tiers for which tier applies.

### Error types: `thiserror` for libraries, `anyhow` for binaries

- **Libraries** expose a concrete, matchable error enum
  (`#[derive(thiserror::Error)]`) so callers can handle specific cases —
  don't leak `Box<dyn Error>` across a public API.
- **Binaries / application code** can use `anyhow::Result` with `.context()`
  to add human-readable context at each boundary, since the top-level
  handler only needs to report, not match.

```rust
#[derive(thiserror::Error, Debug)]
pub enum StoreError {
    #[error("item {0} not found")]
    NotFound(String),
    #[error("backend unavailable")]
    Backend(#[from] std::io::Error),
}
```

### `unsafe` needs a written justification

Every `unsafe` block carries a `// SAFETY:` comment stating the invariant
that makes it sound. No `unsafe` for convenience, and none at all in code
that has a safe equivalent. This is the one place clippy's default lints
aren't enough — the reasoning is what's being reviewed, not the syntax.

### Borrow before you clone

Prefer `&T` / `&str` / `&[T]` in function signatures over owned `T` /
`String` / `Vec<T>` when the callee only needs to read. A `.clone()` in a
hot path to satisfy the borrow checker is a smell — restructure ownership
first; clone deliberately, not reflexively.

### Tests live next to the code

Unit tests go in a `#[cfg(test)] mod tests` block in the same file;
integration tests go in `tests/`. Use `#[should_panic(expected = "...")]`
for panic paths and `Result`-returning tests (`-> Result<(), E>`) so `?`
works inside the test body.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adds() {
        assert_eq!(add(2, 3), 5);
    }
}
```
