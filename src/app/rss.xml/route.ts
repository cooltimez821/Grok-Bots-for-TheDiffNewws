import { getFeedStories } from "@/lib/feed";

export const dynamic = "force-static";

const SITE = "https://thediffnews.com";

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/** Home clusters as RSS 2.0 — same floor as /feed.json (outlet_count >= 2). */
export async function GET() {
  const stories = getFeedStories();
  const lastBuild =
    stories
      .map((s) => s.last_updated_at)
      .filter(Boolean)
      .sort()
      .at(-1) ?? new Date().toISOString();

  const items = stories
    .map((story) => {
      const link = `${SITE}/story/${story.story_id}`;
      const pubDate = story.last_updated_at ?? story.first_seen_at ?? "";
      const outlets = story.members.map((m) => m.outlet_name).join(", ");
      const description = escapeXml(
        `${story.outlet_count} outlets (${outlets}). bias_band=${story.labels.bias_band}. Category: ${story.primary_category}.`,
      );
      return `    <item>
      <title>${escapeXml(story.title)}</title>
      <link>${escapeXml(link)}</link>
      <guid isPermaLink="true">${escapeXml(link)}</guid>
      ${pubDate ? `<pubDate>${escapeXml(new Date(pubDate).toUTCString())}</pubDate>` : ""}
      <description>${description}</description>
      <category>${escapeXml(story.primary_category)}</category>
    </item>`;
    })
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>TheDiffNews</title>
    <link>${SITE}</link>
    <description>Independent AI coverage — multi-outlet story clusters.</description>
    <language>en-us</language>
    <lastBuildDate>${escapeXml(new Date(lastBuild).toUTCString())}</lastBuildDate>
${items}
  </channel>
</rss>
`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=300, stale-while-revalidate=600",
    },
  });
}
