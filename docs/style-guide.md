# Someday — Design System & Style Guide

> This document is the source of truth for all UI decisions.
> Before adding any colour, component, or visual treatment, check here first.
> If something isn't in this guide, define it here before using it.

---

## 1. Typography

| Role | Family | Weight | Size (mobile) |
|---|---|---|---|
| Display / headings | Lora (serif) | 500–600 | 18–30px |
| Display italic (emotional moments) | Lora italic | 400–500 | 26–34px |
| Body / UI text | DM Sans | 400–600 | 12–15px |
| Labels / caps | DM Sans | 500–600 | 10–11px, 0.09–0.14em tracking |

**Rules:**
- Circle names, intent titles, greeting text, payoff headline → Lora
- Buttons, chips, badges, metadata, labels → DM Sans
- Notes / quote fields → Lora italic
- Never introduce a third typeface

---

## 2. Colour Tokens

All colours must be consumed via CSS variables — never hardcoded hex values in components.

### 2a. Base Palette

| Token | Light | Dark |
|---|---|---|
| `--bg-a / --bg-b / --bg-c` | Warm off-white tones (#F3EEF9 → #EBF6F1 → #F9EDF3) | Pure charcoal (#101010 → #131313 → #0E0E0E) |
| `--txt` | #1C1525 | #EEEEEE |
| `--txt-m` | #5A4E72 | #888888 |
| `--txt-l` | #9B90B4 | #444444 |

**Dark mode rule:** Background and surface tokens must be neutral grey/charcoal — zero colour tint. The only colour allowed in dark backgrounds is the accent on interactive elements.

### 2b. Accent (Primary Interactive)

| Token | Light | Dark |
|---|---|---|
| `--acc` | #5B4B8A | #9B8DC4 |
| `--acc-m` | #8B78C0 | #BDB0E0 |
| `--acc-l` | rgba(91,75,138,.10) | rgba(155,141,196,.11) |
| `--acc-glow` | rgba(91,75,138,.22) | rgba(155,141,196,.14) |

**This is the only gradient colour.** Every filled CTA button uses `linear-gradient(135deg, var(--acc), var(--acc-m))`.

### 2c. Per-Circle Identity Colours

Each circle gets one of three colour identities. These appear **only** in:
- The left-border accent stripe on circle cards
- The icon background tint inside circle cards
- The count badge on circle cards
- Member dot colours for that circle's members

| Token | Light | Dark | Usage |
|---|---|---|---|
| `--cp` (pink/coral) | #FF4B6E | #E8607A | Personal/friendship circles |
| `--cg` (green) | #00B87A | #2DBF8A | Group/gang circles |
| `--cb` (blue) | #4A68F0 | #6B8FFF | Trip/event circles |

**These colours must not appear on buttons, backgrounds, or any UI chrome outside the above three contexts.**

### 2d. Status Badge Colours

Status badges are the only place status-specific colour appears.

| Status | Background token | Text token |
|---|---|---|
| Saved | `--ss` | `--ss-t` |
| Interested | `--si` | `--si-t` |
| Planned | `--sp` | `--sp-t` |
| Done | Same as Saved, reduced opacity | — |

---

## 3. Glass Surface System

The app uses a layered glass system. Choose the right layer — don't mix them arbitrarily.

| Class | Usage |
|---|---|
| `.gcrd` | Standard card surface (circle cards, intent cards, info sections) |
| `.gcrd-hi` | Elevated surface (modals, detail view, top card in a stack) |
| `--glass-nav` | Sticky navigation bars only |
| `--glass-lo` | Subtle fills (chips, inactive buttons, nested sub-rows) |

**Implementation:** always pair with `backdrop-filter: blur(18px) saturate(155%)` and include the `@supports` fallback for non-supporting browsers (solid `--glass-hi` background).

**Dark mode:** Glass in dark mode is charcoal-tinted (`rgba(22,22,22, .80)`) — no colour bleed from the surface.

---

## 4. Buttons

There are exactly **two** button variants. No others.

### Primary CTA
```css
background: linear-gradient(135deg, var(--acc), var(--acc-m));
color: #fff;
border: none;
border-radius: var(--r);   /* 20px */
box-shadow: var(--shb);
font-family: 'DM Sans'; font-weight: 600;
```
Use for: Save, Confirm, Payoff CTA, Mark as Planned, any single primary action per screen.

### Secondary / Ghost
```css
background: var(--glass);
border: 1px solid var(--brd-h);
color: var(--txt) or var(--txt-m);
border-radius: var(--r);
backdrop-filter: blur(10px);
```
Use for: Spin the Wheel, Cancel, Leave, secondary actions alongside a primary.

**Rules:**
- One primary CTA per screen maximum
- Never use circle identity colours (`--cp`, `--cg`, `--cb`) on buttons
- Never create a one-off button colour for a "special" action (e.g. green for "Planned") — use primary CTA style
- Destructive actions (Delete, Leave) use secondary style with `color: var(--cp)` text only — never a red filled button in the POC

---

## 5. Icons

All icons use the SVG sprite system defined in `components/Sprite.tsx`.

```html
<svg class="icon icon-md"><use href="#i-name"/></svg>
```

| Class | Size |
|---|---|
| `.icon-sm` | 13px |
| `.icon-md` | 16px (default) |
| `.icon-lg` | 22px |
| `.icon-xl` | 38px (intent card preview headers) |

**Rules:**
- Stroke-based only (fill:none, stroke:currentColor) — except `.icon-fill` for filled variants (star selected, heart filled)
- stroke-width: 1.8, stroke-linecap: round, stroke-linejoin: round — never change these per-icon
- Never use emoji as UI elements. Emoji are user-generated content only (circle names, notes)
- Icon colour inherits from parent (`currentColor`) — never set a fixed colour on an icon directly

### Icon map

| Context | Icon id |
|---|---|
| Back navigation | `i-arrow-left` |
| Personal/friendship circle | `i-eye` |
| Group circle | `i-users` |
| Trip circle | `i-globe` |
| Watch category | `i-film` |
| Eat category | `i-utensils` |
| Visit category | `i-map-pin` |
| Read category | `i-book-open` |
| Play category | `i-gamepad` |
| Trip category | `i-plane` |
| Shortlist tab | `i-star` |
| Done tab / status | `i-check` |
| Boost | `i-zap` |
| Best Pick / Payoff | `i-target` |
| Spin | `i-shuffle` |
| React / Interested | `i-heart` |
| Add / New | `i-plus` |
| Theme: dark | `i-moon` |
| Theme: light | `i-sun` |
| Time / age | `i-clock` |
| External link | `i-link` |
| Delete | `i-trash` |
| Copy to clipboard | `i-copy` |
| Settings / gear | `i-settings` |
| Email / magic link | `i-mail` |
| Sign out | `i-log-out` |
| Dismiss / close | `i-x` |
| Comment / note | `i-message-circle` |
| Overflow menu | `i-more` |
| Edit / pencil | `i-pencil` |
| Notifications bell | `i-bell` |
| Navigate forward | `i-chevron-right` |

---

## 6. Spacing & Radius

| Token | Value | Usage |
|---|---|---|
| `--r` | 20px | Cards, buttons, modals |
| `--rs` | 12px | Chips, badges, inputs, smaller cards |
| Standard screen padding | 22px left/right | All screen content |
| Card internal padding | 17–18px | Circle cards |
| Intent card body padding | 13–15px | Intent card text area |
| Section gap | 12–14px | Gap between cards in a list |

---

## 7. Shadows

| Token | Usage |
|---|---|
| `--shc` | Standard card shadow (circle cards, intent cards) |
| `--shb` | Button shadow (primary CTA only) |

Never add custom `box-shadow` values to components — use the tokens.

---

## 8. What is NOT in the design system

If you find yourself reaching for any of the following, stop and reread this guide:

- ❌ A third font
- ❌ A hardcoded hex colour on any element
- ❌ A green/red/yellow filled button
- ❌ Any emoji in navigation, buttons, labels, or badges
- ❌ `border-radius` values other than `--r` or `--rs`
- ❌ A new gradient colour
- ❌ Blue/purple tints in dark mode backgrounds or dark glass surfaces
- ❌ A custom icon drawn outside the sprite system
