# TheDiffNews ingest contract v0.1

Owner: Data. Consumers: Eng (read APIs), Bias (outlet join + scoring fields), Bee (cluster QA).
Rule: no silent drops. Every rejected or un-clustered article keeps a reason.

## Objects

### `outlet`
Stable source identity. Bias rates this, we do not store scores here.

| field | type | notes |
|---|---|---|
| `outlet_id` | string | slug, stable forever (`reuters`, `the-guardian`) |
| `name` | string | display name |
| `homepage_url` | url | |
| `feed_url` | url? | RSS/Atom if we have one |
| `domain` | string | registrable domain, join key for Bias |
| `country` | string | ISO-3166-1 alpha-2 |
| `language` | string | BCP-47, default feed language |
| `active` | bool | false = paused, not deleted |

### `article`
One URL, one row. Duplicates point at a survivor; they are never deleted.

| field | type | notes |
|---|---|---|
| `article_id` | ulid | |
| `outlet_id` | string | required |
| `canonical_url` | url | tracking params stripped |
| `url_hash` | hex | sha256 of canonical_url |
| `title` | string | |
| `dek` | string? | feed summary / standfirst, not a model rewrite |
| `authors` | string[] | |
| `language` | string | BCP-47 |
| `published_at` | datetime | publisher time, UTC |
| `ingested_at` | datetime | when we first saw it |
| `content_hash` | hex? | sha256 of normalized title+dek; exact-dupe key |
| `status` | enum | `fetched` `dropped` `deduped` `clustered` |
| `drop_reason` | enum? | `paywall_empty` `non_article` `duplicate` `lang_filter` `fetch_fail` `policy` |
| `duplicate_of` | ulid? | survivor article_id |
| `story_id` | ulid? | set only when clustered |
| `raw_ref` | string | pointer to stored feed payload |

### `story`
A cluster of articles about the same event. Conservative on v0: precision over recall.

| field | type | notes |
|---|---|---|
| `story_id` | ulid | |
| `title` | string | taken from earliest high-trust outlet, not generated; feed items use fresh (≤48h) members only |
| `first_seen_at` | datetime | min(article.published_at) |
| `last_updated_at` | datetime | last article attach |
| `article_count` | int | survivors only |
| `outlet_count` | int | distinct outlets |
| `cluster_version` | int | bumps on split/merge |
| `primary_category` | enum | one of `weight_and_bias` `parallax` `blindspot` `prism` `source_code` `off_distribution` |
| `status` | enum | `open` `frozen` `split` |

### `story_member`
Why this article is in this story. This is the debug table.

| field | type | notes |
|---|---|---|
| `story_id` | ulid | |
| `article_id` | ulid | |
| `method` | enum | `canonical_url` `content_hash` `title_entity` `manual` |
| `score` | float? | 0-1; null for exact methods |
| `evidence` | object | `{shared_entities?, title_overlap?, time_delta_hours?}` |
| `assigned_at` | datetime | |


`primary_category` is one tag per cluster (Bias framing map). Written at cluster time from those rules; multi-tag waits. Not six products.

## Clustering rules (v0)

1. Exact: same `url_hash` or `content_hash` → dedupe, not a new story member.
2. Soft merge: same calendar day UTC (±18h), Jaccard(title tokens) ≥ 0.55, **and** ≥ 1 shared entity (person/org/place). All three required.
3. Never merge across a contradiction entity (different primary org or place) just because titles overlap.
4. Split > merge. Bee can flag a bad merge; we split and write `cluster_version++` plus a `story_member` row with `method=manual`.

## Bias join

We emit `outlet_id` + `domain` + `country` + `language` on every article and story rollup.
Bias owns ratings. We never copy a lean/score onto `article` or `story`.
Story coverage rollup for Eng is computed at read time: members × Bias rating.

## SLAs (v0)

- Ingest lag p95 < 20 min from `published_at` for live RSS.
- Silent drop rate = 0. `dropped` always has `drop_reason`.
- Cluster explain: every `story_member` has `method` + `evidence`. "Why is this one story?" is a query, not a guess.
- No article overwrite that loses the first `ingested_at` or the original `raw_ref`.

## Out of v0

Full text body, embeddings, generated story titles, multi-tag categories, paywall unlock, social shares.

## Read API v0.1 (frozen — TheDiffNews)

`GET` cluster feed item:

```
story
  story_id, title, first_seen_at, last_updated_at, article_count, outlet_count
  primary_category   # one of the six section tags
  members[]
    title
    canonical_url
    published_at
    outlet_id
    outlet_name
    dek          # Bias "lede"
  labels         # attached by Bias at read time, not stored on the story
    bias_band     # left|lean_left|center|lean_right|right|mixed
    blindspot { present, rule_id }   # absent => { present: false, rule_id: null }
    # trust: off
```

`dek` is the RSS description / standfirst. Author and body are out of v0.1.

v1 home feed: emit only stories with `outlet_count >= 2`. Single-outlet clusters stay in storage, not the feed.

## Bias v1 pack (2026-09-11)

Blindspot `rule_id`: `missing_left` | `missing_right` | `missing_center` | `one_side_thin` | `no_primary_source` | `geo_thin`.
Seed RSS only from `catalog/v1-outlets.json` (36 named ids, including `platformer`).
Cluster `bias_band` = majority of member outlet bands, else `mixed`. Lean stays on the catalog, not the article row.


v1 blindspot tighten (Bias 2026-09-11): `missing_left` / `missing_right` require ≥3 members and ≥2 on the present side, plus clear partisan stakes. Skeleton pairs stay `{ present: false, rule_id: null }`.

## story_id stability (2026-09-28)

`story_id` stays a ULID string, but is **stable across refreshes**: a re-clustered story keeps its prior id instead of minting a new one.

- Member key = `outlet_id` + normalized `canonical_url` (https, lowercase host without `www.`, no fragment/trailing slash, tracking params like `utm_*` dropped). Article ids are not used (seed re-mints them).
- Before minting, the clusterer loads the previous run's full story set (all clusters, incl. held/aged-off) from `out/story_id_map.json` (`story_id → member keys, last_seen_at`). If the map is missing it bootstraps from `stories.jsonl` / `story_members.jsonl` / `articles.jsonl` / `feed-v1.json` / `held-single-outlet.json`.
- New cluster reuses a prior `story_id` when **Jaccard(member keys) ≥ 0.5**. Highest overlap wins; ties go to the lexicographically smaller (older) `story_id`. Greedy by descending overlap; each prior id is claimed by at most one new cluster. Otherwise a new ULID is minted.
- Unclaimed prior ids stay in the map for 7 days (`STORY_ID_RETAIN_HOURS`), so a story that drops out for a refresh or two gets its id back.
- Feed shape, bands, blindspots, freshness and `outlet_count >= 2` are unchanged. Test: `.venv/bin/python debug/test_stable_ids.py`.


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

## Title and category from fresh members (2026-09-29)

The feed item's `title` and `primary_category` are derived from its **fresh (in-window, ≤48h) members** only — the same unique-by-outlet `members` list the card shows after the 48h freshness trim. Rules are unchanged; only the input set changed:

* `title`: best trust tier (`trust_rank`: center non-provisional, then center provisional, then other), then earliest `published_at`, then `article_id` (`pick_title_member` in `cluster_v0.py`).
* `primary_category`: existing `assign_category` rules (Bias-owned, untouched), applied to the fresh members.
* Applies to `feed-v1.json` home items and to single-outlet held items (they share the same item builder). `stories.jsonl` and `aged_out` held rows keep the all-member title/category (story-level record; an aged_out row has no fresh members). `cluster-summary.json` `by_category` still counts `stories.jsonl`.
* Unchanged: members, `story_id` / `story_id_map`, `outlet_count`, `bias_band`, blindspot (still passed the story-level category), freshness, carry-forward, anchors, edges.
* Regression: Amodei dinner `FFD17FFE5AB8D613465F8F94F3` showed the expired axios headline "Scoop: Anthropic's Dario Amodei to have White House dinner with Trump" while its fresh members were only wash_examiner, nyt and ft; it now shows FT "Trump hosts Anthropic boss Dario Amodei at White House dinner" (category unchanged, `weight_and_bias`). No other story changed on the 2026-09-29 data.
* Test: `.venv/bin/python debug/test_title_fresh.py`.

## IPO/funding anchor tightening (2026-09-29)

`ipo` and `funding` are broad event classes: one company can have several unrelated IPO/funding stories on the same day. An edge whose shared event anchors are **only** `ipo` and/or `funding` (`WEAK_ANCHOR_CLASSES`) now also needs corroboration beyond the company/org entity:

* a shared **normalized $ figure** in title + dek (`money_figures`: "$30 billion" == "$30bn"; units trillion/tn, billion/bn, million/mn; bare prices don't count), **or**
* title Jaccard ≥ **0.5** (`WEAK_ANCHOR_TITLE_JACCARD_MIN`). This floor comes from the data: every genuine ipo-only edge seen so far scores ≥ 0.5556 (Anthropic S-1 filing: ft/semafor 0.5556, ft/guardian 0.625), and the bad pair scores 0.1667.

Any other shared class (dinner, meeting, launch, lawsuit, acquisition, hire, investigation, hack, ban) or a product/version anchor still passes on its own, as before. The check lives in `_anchor_gate`, so it applies to both paths. The density path's "shared event in both titles" check applies the same rule: a titles-only overlap made up of just ipo/funding needs the same corroboration. Blocked edges get `blocked_detail = weak_anchor_uncorroborated` and are counted in `edges_removed_event_anchor`.

The legacy path already requires Jaccard ≥ 0.55, so in practice this only affects the density path.

Regression (5:03 PM ET refresh): home card `8CB12CAD93C59FE88B0D10B4D8` merged The Information "OpenAI in Early Talks to Raise $30 Billion Before an IPO" (a pre-IPO round) with Bloomberg "Altman Says OpenAI Investors Patient on IPO Amid Safety Focus" (IPO timing). They linked via density key `openai_ipo` plus a shared `ipo` anchor, at Jaccard 0.17 with no shared figure. After the fix:

* The pair splits. Bloomberg keeps `8CB12CAD93C59FE88B0D10B4D8`; The Information gets a new id. Both are held as single-outlet stories, and home goes from 8 to 7.
* No other story changed. The Anthropic IPO card `4A68FCAAA9EA182B279B288E78` (ft/guardian/semafor) is unchanged.
* `edges_removed_event_anchor` 8 → 9.
* Test: `.venv/bin/python debug/test_ipo_anchor.py`.
