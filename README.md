# TheDiffNews

Independent AI-news site. Home is a feed of multi-outlet **story clusters**; category is a filter chip, not a separate product surface.

## This ships (v1)

- Home feed of clusters with `outlet_count >= 2` from fixture `data/feed-v1.json`
- Cluster cards: `primary_category` chip, `bias_band` L/C/R meter, optional blindspot row
- Blindspot row **only** when `labels.blindspot.present === true` (omitted when false — never muted “no blindspot”)
- Quiet line on a short feed: “Showing multi-outlet stories”
- Category nav: All + six categories, one layout, client-side filter
- Cluster detail route with member list (`outlet_name`, `title`, `dek`, `published_at`, link via `canonical_url`)
- Wordmark **TheDiffNews** in chrome (home + detail)

## This waits

- Auth, search, personalization, trust labels
- Live ingest / read API (fixtures only)
- Invented outlets, stories, or Bias labels
- Multi-tag categories, share/save, in-app reader

## Frozen shape (Read API v0.1)

```
story
  story_id, title, outlet_count, primary_category
  members[]
    title, canonical_url, published_at, outlet_name, dek
  labels
    bias_band     # left|lean_left|center|lean_right|right|mixed
    blindspot { present, rule_id }
```

Category display labels:

| id | label |
|---|---|
| weight_and_bias | Weight & Bias |
| parallax | Parallax |
| blindspot | Blindspot |
| prism | Prism |
| source_code | Source Code |
| off_distribution | Off-Distribution |

Fixtures (copied, not invented):

- `data/feed-v1.json` ← news-pipeline `out/feed-v1.json`
- `data/bias/v1-outlet-catalog.json`, `data/bias/v1-blindspot-rules.json`
- `docs/CONTRACT.md`, `docs/schema-v0.1.json`, `docs/SPEC.md`

## Run

```bash
cd /workspace/thediffnews-app
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

```bash
npm run build   # production build
npm start       # serve production build
```

## Notes

- Name in UI/docs is **TheDiffNews** only (never TheDiffNewws).
- Bias owns lean/blindspot rules; Eng only displays fields already on the feed fixture.
