import Link from "next/link";
import { categoryLabel } from "@/lib/categories";
import { formatRelativeUpdated } from "@/lib/format";
import type { Story } from "@/lib/types";
import { BiasMeter } from "./BiasMeter";
import { BlindspotRow } from "./BlindspotRow";

type StoryCardProps = {
  story: Story;
};

export function StoryCard({ story }: StoryCardProps) {
  return (
    <Link
      href={`/story/${story.story_id}`}
      className="block rounded-sm border border-[var(--border)] bg-[var(--surface)] p-3.5 text-inherit no-underline shadow-[var(--shadow-card)] transition-[border-color,box-shadow] hover:border-[var(--accent-ring)]"
      style={{
        background:
          "linear-gradient(180deg, var(--surface-raised) 0%, var(--surface) 100%)",
      }}
    >
      <span className="mb-2 inline-block rounded-sm border border-[var(--accent-ring)] bg-[var(--accent-soft)] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.1em] text-[var(--accent)]">
        {categoryLabel(story.primary_category)}
      </span>
      <h3 className="mb-2 text-[15px] font-semibold leading-snug tracking-tight text-[var(--ink)]">
        {story.title}
      </h3>
      <BiasMeter band={story.labels.bias_band} />
      <BlindspotRow blindspot={story.labels.blindspot} />
      <div className="mt-2 flex items-center justify-between border-t border-[var(--border)] pt-2 text-[11px] text-[var(--faint)]">
        <span className="font-semibold text-[var(--muted)]">
          {story.outlet_count} outlet{story.outlet_count === 1 ? "" : "s"}
        </span>
        <span>{formatRelativeUpdated(story.last_updated_at)}</span>
        <span className="font-semibold text-[var(--accent)]">Open cluster →</span>
      </div>
    </Link>
  );
}
