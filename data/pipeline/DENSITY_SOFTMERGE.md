# Density soft-merge (durable)

Owner: Data. Locks from Bias / Bob / Foreman (2026-09-14).
Implements durable multi-outlet density so scheduled refresh does not collapse the Amodei cycle into 1–2 feed stories.

## Why

Title Jaccard ≥ 0.55 alone is too brittle across outlets (same event, different wording). After refresh, density dropped from ~8 feed stories to 2. Soft-merge must recover density **without** smashing distinct Amodei-cycle satellites into one mega-story.

## Event keys (`event_key` in `cluster_v0.py`)

Title-primary (dek intentionally ignored for routing — standfirsts cross-mention adjacent events).

| event_key | Meaning | Keep separate from |
|---|---|---|
| `amodei_call` | Amodei / CEOs “pace the frontier” / slowdown call | all rows below |
| `trump_reject` | Trump (or Vance) rejects / brushes off slowdown | `amodei_call` |
| `china_reject` | China / Beijing rejects “fearmongering” | `amodei_call` |
| `ai_stocks_fall` | AI/tech stocks fall / slide / tumble | `amodei_call`, `zai_fundraise` |
| `openai_ipo` | OpenAI IPO delay / ill-advised / rules out | `amodei_call` (own story when titles are about IPO) |
| `microsoft_caution` | Microsoft caution / “people matter” / limits | `amodei_call` |
| `zai_fundraise` | Z.ai fundraising / shares | `ai_stocks_fall` |
| `obama_safeguards` | Obama AI safeguards / Dems plan | `amodei_call` |

If both articles have event keys and they **differ** → never soft-merge (satellite-split).
If both share the **same** event key and `|Δt| ≤ 18h` → soft-merge (density path; Jaccard not required).
Otherwise → legacy path: Jaccard ≥ 0.55 **and** ≥1 shared entity **and** `|Δt| ≤ 18h`, plus contradiction checks.

## Product locks (must hold)

1. **bias_band** = absolute majority of member outlet bands (`count > n/2`), else `mixed`. Never plurality.
2. **Satellite-split** via event tokens (table above). Entity+title contradiction still applies for primary org/place.
3. **Unique `outlet_id` per story members** — `dedupe_members_by_outlet` keeps earliest; extras become `deduped`.
4. **Blindspots** (positive finding only; default `{present:false, rule_id:null}`):
   - `missing_left` / `missing_right`: ≥3 outlets, ≥2 on present side, **partisan stakes** (`PARTISAN_STAKES`, not bare Trump name-drop).
   - `no_primary_source` / `geo_thin`: quiet on skeleton pairs (`outlet_count < 3`) **and** catalog-ceiling (Reuters/AP feeds failed).
5. **Feed** only `outlet_count >= 2`. No padding. No inventing Reuters/AP.
6. **Write** feed + cluster-summary to:
   - `/workspace/news-pipeline/out/feed-v1.json`
   - `/workspace/thediffnews/data/feed-v1.json`
   - (plus `cluster-summary.json` beside each)

## Routine

```bash
python3 /workspace/news-pipeline/debug/cluster_v0.py
# expects feed_stories ≥ 8 when Amodei-cycle articles are present (~27 hits in fetch)
```

Do not git push. Do not invent outlets. Catalog (`catalog/v1-outlets.json`) is source of truth.


## Bias tighten (2026-09-14)

Do **not** fire `one_side_thin` when `center` already holds absolute majority (`count > n/2`). That is catalog/beat skew, not a contested spectrum imbalance.


## Freshness (2026-09-14)

Home feed drops stories with **no member `published_at` in the last 48 hours**. Aged members drop off the cluster first; `bias_band` is recomputed (absolute majority) on who remains. If `outlet_count` falls below 2, the story leaves home (held). No padding.


## Same-cycle Amodei (2026-09-14)

Same `event_key` (`amodei_call`) merges across the **48h freshness window**, not 18h. 18h forked Sep-12 vs Sep-13/14 into two home cards — that's a bug. Satellites (Trump/China/stocks) still never share `amodei_call`.


## one_side_thin (2026-09-14 evening)

Thick partisan side must **strictly outnumber center** (`thick > center`) and be ≥3 vs ≤1. Tied with center stays quiet (Trump 3ll/3c/1rr is beat skew).


## one_side_thin beat-skew (2026-09-15)

Stay quiet when the thin side is **only `nypost`** and the thick side has ≥2 tech-beat outlets (`the_verge`, `wired`, `techcrunch`, `ars_technica`). Catalog AI-press lean ≠ a spectrum hole.


## Stable story_id (2026-09-28)

`cluster_v0.py` reuses the previous run's `story_id` when outlet+URL member-key Jaccard ≥ 0.5 (highest overlap wins, ties → smaller id, one claim per prior id). State lives in `out/story_id_map.json`; do not delete it between seed and cluster. See CONTRACT.md "story_id stability". Test: `.venv/bin/python debug/test_stable_ids.py`.


## Shared event anchor (2026-09-28)

A soft-merge edge needs more than shared entities plus similar wording: **both articles must name the same event** (`event_anchors` / `_anchor_gate` in `cluster_v0.py`). This applies to every edge, on both the density path and the legacy Jaccard path. Anchors come from **title + dek**, are deterministic, and never include named entities or generic words (`ai`, `ceo`, `model`, `company`):

1. **Event classes** from a closed lexicon, via the event-word normalization map (see below): `dinner`, `meeting`, `launch`, `lawsuit`, `acquisition`, `hire`, `ipo`, `funding`, `investigation`, `hack`, `ban`.
2. **Product/version names**: a capitalized word followed by a version number (`Sonnet 5.5` → `product:sonnet 5.5`, `GPT-5`). The word is ignored if it is a known entity, a month, or a counter word (Top/Phase/Round/…).
3. **Density fallback (pair-level)**: a shared title `event_key` (e.g. `amodei_call`) counts as the anchor **only when at least one of the two articles has no class/product anchor of its own**. If both name explicit events, those events must overlap. A "CEO who called for a slowdown" backstory clause cannot bridge a dinner story and a model launch.

Blocked edges are counted in `cluster-summary.json` → `edges_removed_event_anchor`.

Regression (3:01 PM ET refresh, 2026-09-28): WaPo "Trump dined with the Anthropic CEO who called for AI slowdown" {dinner, meeting} was merged with CNBC "Anthropic launches cheaper AI model…" {launch, product:sonnet 5.5} at 0.40 via `amodei_call` + `anthropic`. That edge is now removed and both are held single-outlet. The Amodei dinner story (all members share `dinner`) and Meta/MongoDB (`hire`) are unchanged. Test: `.venv/bin/python debug/test_event_anchor.py`.

### Event-word normalization map (2026-09-28 PM)

`EVENT_CLASS_WORDS` → `EVENT_WORD_CANON` in `cluster_v0.py` maps every listed inflection/synonym to one of the 11 canonical classes by **exact lowercase word lookup** (no fuzzy stemming):

| class | words |
|---|---|
| `dinner` | dinner, dinners, dine, dines, dined, dining |
| `meeting` | meeting(s), meet(s), met, summit(s) |
| `launch` | launch(es/ed/ing), release(s/d/releasing), unveil(s/ed/ing), debut(s/ed/ing), introduces, introduced |
| `lawsuit` | lawsuit(s), sue(s/d), suing, litigation |
| `acquisition` | acquisition(s), acquire(s/d), acquiring, buyout, takeover, merger, buy(s), bought, buying |
| `hire` | hire(s/d), hiring, taps, tapped, tapping, appoint(s/ed/ing), appointment, poach(es/ed/ing) |
| `ipo` | ipo(s) |
| `funding` | fundraise(s/d), fundraising, raises |
| `investigation` | investigation(s), investigate(s/d), investigating, probe(s/d), probing, subpoena(s/ed) |
| `hack` | hack(s/ed/ing), breach(ed), cyberattack(s) |
| `ban` | ban(s), banned, banning |

Multi-word phrases (`EVENT_PHRASE_CANON`, anchors only, title + dek): `to lead` → `hire`; `names/named/naming <…up to 6 words…> <role>` (ceo, cto, cfo, coo, chief, president, chair(man/woman), head, leader, director) → `hire` (so "a startup named X" is not a hire); `met with` → `meeting`; `roll(s/ed/ing) out` → `launch`; `go/goes/going/went public` → `ipo`; `funding round`, `raised $N` → `funding`.

Where the map applies:

* **Anchor gate** (`event_anchors`): **all** classes are normalized, including `dinner`.
* **Title similarity** (`tokenize_title` → title Jaccard): every class is normalized (`taps`/`hires` → `hire`, `unveils`/`launches` → `launch`, …) **except `dinner`** (`TITLE_CANON_EXCLUDE = {"dinner"}`); dinner words fall back to plain `stem_token`. Why: normalizing dine/dined/dinner in title similarity lifts TechCrunch "Anthropic's CEO is about to have dinner with President Trump" vs WaPo "Trump dined with the Anthropic CEO who called for AI slowdown" to 0.57 and creates a **duplicate satellite dinner card** next to the main Amodei dinner card (`FFD17FFE5AB8D613465F8F94F3`). The two stay separate, single-outlet, until satellite-folding is designed (pending proposal); revisit this exclusion then.

Regression that motivated it (5:02 PM ET refresh, 2026-09-28): Meta/MongoDB `FFD1731A8EB8FF60DD10788911` fell apart once its Bloomberg text article (the bridge) left the feed. TechCrunch "Meta launches enterprise AI platform, hires MongoDB CEO to lead new initiative" vs The Information "Meta Taps MongoDB CEO to Lead New Enterprise AI Division" scored title Jaccard 0.5455 < 0.55 (`taps` ≠ `hire`). With the map they score 0.70, share `hire`, and re-form as `FFD1731A8EB8FF60DD10788911` (stable ID carried forward). The WaPo/CNBC Sonnet edge is still blocked (`edges_removed_event_anchor` = 1). Tests in `debug/test_event_anchor.py`: normalization, Meta pair links (sim ≥ 0.55, shares `hire`), TechCrunch "about to have dinner" and WaPo "dined with" stay separate, WaPo/CNBC Sonnet still don't link, end-to-end.
