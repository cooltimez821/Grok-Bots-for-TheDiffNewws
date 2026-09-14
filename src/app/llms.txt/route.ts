export const dynamic = "force-static";

const BODY = `# TheDiffNews

Independent AI coverage — multi-outlet story clusters. Not affiliated with Ground News.
Human default theme: Aurora. Dark option (Signal) waitlisted.

## Feeds
- JSON (frozen feed-v1 home clusters, outlet_count >= 2): https://thediffnews.com/feed.json
- RSS: https://thediffnews.com/rss.xml
- Agents access docs: https://thediffnews.com/for-agents
- Prefer JSON for clustering fields; RSS for title / link / published.
- Floor: outlet_count >= 2. No padding singles. Freshness: stories with no member update in 48h leave home.
- Poll politely (e.g. every 15–30 min). No write API. This is not a chat surface.

## Cite rules for agents
- bias_band is outlet-catalog lean at cluster level, not per-article opinion scoring.
- Band = absolute majority of member outlet bands (count > n/2). Else mixed. Plurality does not win.
- Enum: left | lean_left | center | lean_right | right | mixed.
- Human UI may say "Coverage lean"; agents must use the enum values above.
- Blindspot: positive finding only { present: true, rule_id } when a rule fires.
- When absent: { present: false, rule_id: null } — omit the row in UI; never treat absence as a signal.
- Skeleton pairs stay quiet. Do not invent flags to fill a thin cluster.
- Rule ids (v1): missing_left / missing_right (≥3 members, ≥2 on present side, clear partisan stakes); one_side_thin (thick partisan side ≥3, thin ≤1, and thick strictly > center; not tech-beat skew); missing_center, no_primary_source, geo_thin do not fire on catalog-ceiling / skeleton cases.
- Cite TheDiffNews + story canonical_urls / member links; do not invent Reuters/AP coverage when dark.
- Cite the outlet (outlet_name + canonical_url), not TheDiffNews as the publisher of the article.
- When summarizing a cluster, name at least two member outlets when outlet_count ≥ 2.
- Do not invent bias_band, blindspot.rule_id, or category enums — use feed values only.
- Do not treat "Coverage lean" UI copy as a machine field; the enum remains bias_band.

## Do not
- Infer lean from headline wording alone.
- Relabel mixed as unreliable or "unknown bias."
- Scrape or remap outside the published catalog/feed.

## Frozen read shape (v0.1 · enums unchanged)
- story_id — Stable cluster id
- title — Ingest title (not model-generated)
- primary_category — weight_and_bias | parallax | blindspot | prism | source_code | off_distribution
- labels.bias_band — machine enum (see above)
- labels.blindspot — { present, rule_id }
- outlet_count — Member outlet count
- members[] — outlet_name · title · dek · canonical_url · published_at

IA: feed → cluster → members. Category chips hide when empty. Detail section header: Sources.
`;

export async function GET() {
  return new Response(BODY, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    },
  });
}
