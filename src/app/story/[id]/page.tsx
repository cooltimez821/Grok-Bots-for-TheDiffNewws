import Link from "next/link";
import { notFound } from "next/navigation";
import { BiasMeter } from "@/components/BiasMeter";
import { BlindspotRow } from "@/components/BlindspotRow";
import { CategoryNavStub } from "@/components/CategoryNavStub";
import { MemberList } from "@/components/MemberList";
import { SiteHeader } from "@/components/SiteHeader";
import {
  CATEGORY_HELPERS,
  categoriesInFeed,
  categoryLabel,
} from "@/lib/categories";
import { getAllStoryIds, getFeedStories, getStoryById } from "@/lib/feed";

type PageProps = {
  params: Promise<{ id: string }>;
};

export function generateStaticParams() {
  return getAllStoryIds().map((id) => ({ id }));
}

export default async function StoryDetailPage({ params }: PageProps) {
  const { id } = await params;
  const story = getStoryById(id);
  if (!story) notFound();

  const available = categoriesInFeed(getFeedStories());

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-4 py-4 md:px-8 md:py-6">
      <SiteHeader variant="detail" rightLabel="no auth gate" />
      <CategoryNavStub
        active={story.primary_category}
        available={available}
      />
      <div className="pt-2">
        <span className="mb-1.5 inline-block rounded-sm border border-[var(--accent-ring)] bg-[var(--accent-soft)] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.1em] text-[var(--accent)]">
          {categoryLabel(story.primary_category)}
        </span>
        <h1 className="mb-2 mt-2 text-[22px] font-bold leading-tight tracking-tight text-[var(--ink)] md:text-[28px]">
          {story.title}
        </h1>
        <p className="mb-3 text-[12px] text-[var(--muted)]">
          {categoryLabel(story.primary_category)} —{" "}
          {CATEGORY_HELPERS[story.primary_category]}. Helper copy only; this is
          not a different product surface.
        </p>
        <BiasMeter band={story.labels.bias_band} maxWidthClass="max-w-[240px]" />
        <BlindspotRow blindspot={story.labels.blindspot} />
        <MemberList members={story.members} outletCount={story.outlet_count} />
        <p className="mt-6 text-[12px]">
          <Link
            href="/"
            className="font-semibold text-[var(--accent)] hover:underline"
          >
            ← Back to feed
          </Link>
        </p>
      </div>
    </main>
  );
}
