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
      className="block rounded-lg border border-[var(--border)] p-3.5 text-inherit no-underline shadow-[var(--shadow-card)] transition-[border-color,box-shadow] hover:border-[var(--violet-ring)] hover:shadow-[0_1px_0_rgba(255,255,255,0.95)_inset,0_0_0_1px_rgba(108,92,231,0.12),0_10px_28px_rgba(14,21,32,0.08)]"
      style={{
        background:
          "linear-gradient(180deg, var(--surface-raised) 0%, var(--surface) 100%)",
      }}
    >
      <span className="mb-2 inline-block rounded border border-[var(--violet-ring)] bg-[var(--violet-soft)] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-[var(--violet)]">
        {categoryLabel(story.primary_category)}
      </span>
      <h3 className="mb-3 flex-1 text-[15.5px] font-semibold leading-snug tracking-tight text-[var(--ink)]">
        {story.title}
      </h3>
      <BiasMeter band={story.labels.bias_band} />
      <BlindspotRow blindspot={story.labels.blindspot} />
      <div className="mt-2 flex items-center justify-between gap-2 border-t border-[var(--border)] pt-2.5 text-[11px] text-[var(--faint)]">
        <span className="font-semibold text-[var(--muted)]">
          {story.outlet_count} outlet{story.outlet_count === 1 ? "" : "s"}
        </span>
        <span>{formatRelativeUpdated(story.last_updated_at)}</span>
        <span className="font-semibold tracking-tight text-[var(--violet)]">
          Open cluster →
        </span>
      </div>
    </Link>
  );
}
