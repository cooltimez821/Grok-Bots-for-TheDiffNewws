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
      className="block border border-[#d4d4d2] bg-white p-3 text-inherit no-underline transition-colors hover:border-[#0a7a75]"
    >
      <span className="mb-1.5 inline-block border border-[#0a7a75] bg-[#d7eceb] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.1em] text-[#085652]">
        {categoryLabel(story.primary_category)}
      </span>
      <h3 className="mb-2 text-[15px] font-semibold leading-snug tracking-tight text-[#141414]">
        {story.title}
      </h3>
      <BiasMeter band={story.labels.bias_band} />
      <BlindspotRow blindspot={story.labels.blindspot} />
      <div className="mt-2 flex items-center justify-between border-t border-[#e6e6e4] pt-2 text-[11px] text-[#6a6a6a]">
        <span className="font-semibold text-[#2a2a2a]">
          {story.outlet_count} outlet{story.outlet_count === 1 ? "" : "s"}
        </span>
        <span>{formatRelativeUpdated(story.last_updated_at)}</span>
        <span className="font-semibold text-[#085652]">Open cluster →</span>
      </div>
    </Link>
  );
}
