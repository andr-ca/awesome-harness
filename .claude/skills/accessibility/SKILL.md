---
name: accessibility
description: Use when building or reviewing web UIs for accessibility — WCAG 2.2 Level AA compliance, semantic HTML over ARIA, keyboard navigation, color contrast, screen reader patterns, and testing approach.
metadata:
  type: skills
  complexity: medium
  languages: [typescript, javascript]
---

# Accessibility

This skill is self-contained for day-to-day use. Deeper reference (needs
the full harness checkout): `patterns/accessibility/README.md` (full
examples including ARIA live regions and APG patterns). External
canonical sources: [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and the
[WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/).

**Target: WCAG 2.2 Level AA.**

## The first rule: don't use ARIA if a native element exists

A native `<button>`, `<a href>`, `<input>`, `<label>`, `<nav>`, or
`<table>` brings keyboard behavior, focus management, and the correct
role/state for free. `role="button"` + `tabindex` + keyboard handler is
a liability you now own forever.

```html
<!-- Good: browser handles focus, Enter, Space, and role automatically -->
<button type="button" onclick="save()">Save</button>

<!-- Avoid: you must re-implement everything the native button provides -->
<div role="button" tabindex="0" onclick="save()" onkeydown="handleKey(event)">Save</div>
```

## Perceivable

- **Text alternatives.** Meaningful images: `alt` describing *purpose*.
  Decorative images: `alt=""`. Icon-only controls: `aria-label` or
  visually-hidden text.
- **Contrast.** Body text ≥ **4.5:1** against background. Large text
  (≥ 24px, or ≥ 18.66px bold) and UI components/graphics ≥ **3:1**.
  Verify computed colors — don't eyeball.
- **Color alone is not enough.** A red border *and* an error text/icon —
  not red alone.

## Operable

- **Keyboard.** All interactive elements must be reachable by Tab, in
  logical order, with no keyboard trap. `tabindex="0"` for natural order;
  `tabindex="-1"` for programmatic-only focus; never positive values.
- **Visible focus.** Never `outline: none` without a clearly visible
  replacement. Keyboard users navigate by it.
- **Skip link.** First focusable element on pages with repeated
  navigation: `<a href="#main">Skip to main content</a>`.
- **Target size.** Interactive targets ≥ **24×24 px** (WCAG 2.2 §2.5.8),
  with adequate spacing if smaller.

## Understandable

- **Label every input.** `<label for>` or `aria-labelledby`. Placeholder
  text is not a label — it disappears when the user starts typing.
- **Errors in text.** On validation failure: describe what's wrong and
  how to fix it; associate via `aria-describedby`; set
  `aria-invalid="true"` on the field.
- **Consistent, predictable behavior.** Focus doesn't jump unexpectedly;
  forms don't submit on focus change.

## Robust

- **Name, Role, Value** for every custom widget. Follow the matching
  [ARIA APG pattern](https://www.w3.org/WAI/ARIA/apg/patterns/) exactly —
  its roles, states, and keyboard interactions. A half-implemented ARIA
  widget is worse than a native element.
- **Announce dynamic changes.** Content that updates without a page load
  (toasts, async results, validation) needs an `aria-live` region
  (`polite` for status updates, `assertive` only for urgent/time-sensitive
  changes) or `role="alert"`.

```html
<!-- Status message that updates asynchronously -->
<div aria-live="polite" aria-atomic="true" class="sr-only" id="status">
  <!-- Updated by JS: "3 items saved." -->
</div>
```

## Testing: automated is not enough

Automated tools (`axe-core`, Lighthouse) catch ~30–50% of WCAG issues —
contrast, missing labels/alt, invalid ARIA. The rest requires manual
testing:

1. **Tab through every interactive element** — confirm logical order,
   visible focus, no traps.
2. **Run a screen reader** (NVDA + Firefox, VoiceOver + Safari) on each
   flow. Hear, don't just read, what's announced.
3. **Check at 200% browser zoom** — layout must not break or lose content.
4. Run `axe-core` in CI as a smoke test, not a complete audit.

## Pitfalls to catch in review

```tsx
// Missing alt — screen reader announces the file path
<img src="/hero.png" />  // WRONG
<img src="/hero.png" alt="Developer reviewing code" />  // RIGHT

// Form input with no label
<input type="email" placeholder="you@example.com" />  // WRONG
<label htmlFor="email">Email</label>
<input type="email" id="email" placeholder="you@example.com" />  // RIGHT

// Click handler on non-interactive element — keyboard users can't trigger
<div onClick={handleSave}>Save</div>  // WRONG
<button type="button" onClick={handleSave}>Save</button>  // RIGHT

// outline: none without a replacement focus style
button:focus { outline: none; }  // WRONG
button:focus-visible { outline: 2px solid #005fcc; outline-offset: 2px; }  // RIGHT
```
