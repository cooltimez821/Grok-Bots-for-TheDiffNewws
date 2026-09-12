"use client";

import { useMemo, useState } from "react";
import type { CategoryFilter } from "@/lib/categories";
import type { Story } from "@/lib/types";
import { CategoryNav } from "./CategoryNav";
import { StoryCard } from "./StoryCard";

type HomeFeedProps = {
  stories: Story[];
};

export function HomeFeed({ stories }: HomeFeedProps) {
  const [category, setCategory] = useState<CategoryFilter>("all");

  const filtered = useMemo(() => {
    if (category === "all") return stories;
    return stories.filter((s) => s.primary_category === category);
  }, [stories, category]);

  return (
    <>
      <CategoryNav value={category} onChange={setCategory} />
      {stories.length > 0 && stories.length < 12 ? (
        <p className="mb-3 text-[12px] text-[#6a6a6a]">
          Showing multi-outlet stories
        </p>
      ) : null}
      {filtered.length === 0 ? (
        <p className="rounded border border-dashed border-[#d4d4d2] bg-white px-3 py-6 text-center text-[13px] text-[#6a6a6a]">
          No clusters in this category yet.
        </p>
      ) : (
        <div className="grid gap-2.5 md:grid-cols-2">
          {filtered.map((story) => (
            <StoryCard key={story.story_id} story={story} />
          ))}
        </div>
      )}
    </>
  );
}
