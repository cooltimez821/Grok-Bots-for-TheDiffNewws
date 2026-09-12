# TheDiffNews v1 — wireframe spec notes

Owner: Dee (UX). Consumers: Eng (implementation), Bias (label display). Lo-fi only.

## What ships

One product, one layout. Home is a feed of AI **story clusters**. Category is a **filter chip**, not a section product. Tap a card → cluster detail with member sources. No auth gate.

Chrome: **TheDiffNews** wordmark + category nav (All + six). Same chrome on home and detail.

## Fields rendered (read API v0.1)

Cluster card / detail head

- `title`
- `primary_category` → chip using display labels below (enum, one tag)
- `labels.bias_band` → L/C/R bar + counts
- `labels.blindspot` → `{ present, rule_id }`
- `outlet_count`

Member row

- `outlet_name`, `title`, `dek`, `canonical_url` (link affordance), `published_at`

If `blindspot` is missing, null, or `{ present: false }`, the card **must not break**. Show nothing (Prism card) or muted “no blindspot” (Parallax / Source Code cards). Both treatments are valid; Eng may pick one.

## Category display labels

| id | label | helper (tooltip only — not a layout) |
|---|---|---|
| weight_and_bias | Weight & Bias | outlet lean distribution |
| parallax | Parallax | same facts, divergent framing |
| blindspot | Blindspot | spectrum side missing |
| prism | Prism | multi-angle non-partisan split |
| source_code | Source Code | primary docs vs commentary |
| off_distribution | Off-Distribution | under-covered angles |

## Acceptance sample

Home card + detail for “OpenAI releases GPT-5…” (`weight_and_bias`): 5 outlets, `bias_band` L2·C2·R1, `blindspot.present=true` / `rule_id=right_underrepresented`.

## Out of v1 — do not draw

Auth, search, personalization, trust labels, multi-tag categories, per-category custom chrome, share/save, generated titles, author/body.

## Screens

1. **Home feed** — mobile 390×844, desktop 1440×900. All + six filters. Cards show chip, title, bias_band, optional blindspot, outlet count.
2. **Cluster detail** — same chrome. Category + bias_band + blindspot. Member list. Back to feed. No login wall.
3. **Empty / missing blindspot** — Parallax card uses muted “no blindspot”; Prism card omits the row.

## Assumptions

- Cluster `title` is the story title from ingest (earliest high-trust outlet), not model-generated.
- `bias_band` visualization is a simple L/C/R meter; Bias owns the numbers. Wireframe counts are dummy.
- `rule_id` shown as secondary text so Eng can bind it; product copy can hide the raw id later.
- Category filter is additive on one feed (All = unfiltered). Selecting a chip does not change layout.
- `canonical_url` is an outbound affordance, not an in-app reader.
- Desktop is the same information architecture as phone: no extra rails that invent v2 features (the detail aside is spec notes, not product UI).
