import { getFeedStories } from "@/lib/feed";

export const dynamic = "force-static";

/** Field-for-field home clusters from data/feed-v1.json (outlet_count >= 2). */
export async function GET() {
  const stories = getFeedStories();
  return Response.json(stories, {
    headers: {
      "Cache-Control": "public, max-age=300, stale-while-revalidate=600",
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}
