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
If both share the **same** event key and `|Δt| ≤ 48h` → density path (Jaccard not required) **only if** both titles share a named event anchor (softfix 2026-09-29); otherwise the legacy path below applies.
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
3. ~~**Density fallback (pair-level)**~~ **REMOVED 2026-09-29 (softfix).** A shared `event_key` (e.g. `amodei_call`) is never an anchor: `amodei_call` fires on generic "slow down / slowdown" phrasing and cannot stand in for a named event. See "Softfix (2026-09-29)" below.

Blocked edges are counted in `cluster-summary.json` → `edges_removed_event_anchor`.

Regression (3:01 PM ET refresh, 2026-09-28): WaPo "Trump dined with the Anthropic CEO who called for AI slowdown" {dinner, meeting} was merged with CNBC "Anthropic launches cheaper AI model…" {launch, product:sonnet 5.5} at 0.40 via `amodei_call` + `anthropic`. That edge is now removed and both are held single-outlet. The Amodei dinner story (all members share `dinner`) and Meta/MongoDB (`hire`) are unchanged. Test: `.venv/bin/python debug/test_event_anchor.py`.

### Softfix (2026-09-29): density path needs a shared named event in both titles

Regression (9:09 AM ET refresh, 2026-09-29): home card `6B6BA0C8DAA617B2675D4FC1C6` joined WaPo "Trump dined with the Anthropic CEO who called for AI slowdown" with The Verge "Will Chinese AI companies slow down? A top House Democrat wants answers" (Khanna/China treaty) at title Jaccard 0.08. Path: both titles map to `event_key` = `amodei_call` (WaPo: "Anthropic" + "slowdown"; Verge: "AI companies" + "slow down"), so the **density path** skipped the Jaccard ≥ 0.55 / shared-entity / 18h checks; the anchor gate then passed on `meeting`, which came only from the two **deks** ("first one-on-one meeting with Dario Amodei" vs "as Trump prepares to meet tech and AI CEOs") — two different meetings. The pair-level `event:amodei_call` fallback was not used in this edge but is the same "slowdown glue" and is removed too.

Rules now (`soft_merge_ok` / `_anchor_gate` in `cluster_v0.py`):

* **Every edge** passes `_anchor_gate`: shared class/product anchor from title + dek; **no event_key fallback**.
* **Density path** (both titles share the same `event_key`, Δt ≤ 48h): additionally requires a shared class/product anchor in **both titles** (`event_anchors(title_a) ∩ event_anchors(title_b)`); a dek-only overlap is not enough. If that fails, the pair may still link only via the **strict legacy path** (Jaccard ≥ 0.55, ≥1 shared entity, Δt ≤ 18h, anchor gate). Density-path blocks are counted in `edges_removed_event_anchor` (`blocked_detail = density_path_no_shared_title_event`).
* Other code paths do not create edges: exact dedupe (URL/content hash) only collapses identical articles, the transitive-evidence loop only reads `soft_merge_ok` evidence, and stable-ID carry-forward only renames clusters.

Effect on the 2026-09-29 data: `6B6BA0C8` splits; the Verge China piece keeps `6B6BA0C8DAA617B2675D4FC1C6` (stable-ID tie-break at Jaccard 0.5: smaller sorted member key `the_verge|…` < `wapo|…`), WaPo gets a new id; both are held single-outlet and the card leaves home. All other multi-outlet stories are unchanged (`4A6939A5` OpenAI Astra oc=3, `4A68FCAA` Anthropic IPO, `FFD1E514` Nvidia, `FFD1731A` Meta, `FFD17FFE` Amodei oc=3). `edges_removed_event_anchor` 3 → 4. Tests (`debug/test_event_anchor.py`): WaPo dinner vs Verge China slowdown no link on any path (synthetic + real articles, end-to-end), WaPo/CNBC Sonnet still split, Meta pair / Nvidia pair / OpenAI Astra trio still link; the old fallback test now asserts that two slow-down-only titles do **not** link. `debug/test_stable_ids.py` fixtures now name a shared event ("summit"/"unveils") because the key alone no longer links them.

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

## Carry-forward of in-window articles (2026-09-29)

Some feeds only return their latest N items (e.g. `wash_examiner` returns 10), so an article still inside the 48h home window could vanish on the next reseed and silently shrink a story. Regression (9:09 AM ET refresh, 2026-09-29): Amodei `FFD17FFE5AB8D613465F8F94F3` fell from 5 outlets to 3 (lost The Information and Washington Examiner), which also flipped its `primary_category` to `blindspot`.

Rule (`debug/seed_feeds.py`, `carry_forward()`), applied before `out/articles.jsonl` is overwritten:

* Load the previous `out/articles.jsonl`. A prior row is **carried** iff neither its `url_hash` nor its member key (`outlet_id|normalized canonical_url`, same as `cluster_v0.member_key`) is in the current fetch, it was not `dropped` (policy/non_article), its **original `published_at` is within 48h of the run time**, and its outlet is still in the catalog.
* Carried rows keep their original `article_id`, URL and every field, plus `carried_forward: true`. `published_at` is never rewritten, so expiry is always **original `published_at` + 48h**, never measured from the carry date; a row past 48h is never carried again.
* The clusterer and freshness treat carried rows exactly like fetched rows (same `is_fresh` 48h rule, same dedupe, same stable-ID member keys). Bias band / blindspot / `assign_category` are unchanged.
* Reporting: `seed-summary.json` gets `articles_carried_forward` and a `carry_forward` block (`stats`, `carried_article_ids`, `in_window_losses`, `story_member_losses`). `cluster-summary.json` gets `articles_carried_forward`, `members_carried_forward` (home-feed members that are carried rows), `members_carried_forward_all_stories`, `in_window_member_loss_warnings` (prior home/held story members still inside 48h whose member key is no longer in `articles.jsonl`) and `seed_carry_forward` (copy of the seed block).
* Warnings: any prior in-window article that is neither re-fetched nor carried (e.g. its outlet left the catalog) and any story whose member keys disappear while still inside 48h.
* Tests: `.venv/bin/python debug/test_carry_forward.py` (47h carried / 49h not; carried twice still expires by original `published_at`; latest-10 feed keeps older in-window items; re-fetched article not duplicated; outlet removed from catalog is not carried and warns).
* One-time restore (2026-09-29 ~9:20 AM ET): The Information "Anthropic's Amodei to Dine With Trump at White House" (published Sep 27 2:47 PM ET, expires Sep 29 2:47 PM ET) and Washington Examiner "Trump to have dinner with Anthropic CEO Dario Amodei at White House: Report" (published Sep 27 3:19 PM ET, expires Sep 29 3:19 PM ET) were restored from `out/_pre_variant2_20260928-170618/` with original ids and `carried_forward: true`. Amodei is back to 5 outlets, same id, `weight_and_bias`.
