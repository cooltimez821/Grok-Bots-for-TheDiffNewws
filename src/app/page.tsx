import { HomeFeed } from "@/components/HomeFeed";
import { SiteHeader } from "@/components/SiteHeader";
import { getFeedStories } from "@/lib/feed";

export default function HomePage() {
  const stories = getFeedStories();

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-4 md:px-8 md:py-6">
      <SiteHeader />
      <HomeFeed stories={stories} />
    </main>
  );
}
