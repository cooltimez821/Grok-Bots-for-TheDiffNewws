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
