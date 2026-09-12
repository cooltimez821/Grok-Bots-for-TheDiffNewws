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
| `title` | string | taken from earliest high-trust outlet, not generated |
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
