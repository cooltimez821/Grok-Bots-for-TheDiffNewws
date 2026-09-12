import type { PrimaryCategory } from "./types";

export const CATEGORY_LABELS: Record<PrimaryCategory, string> = {
  weight_and_bias: "Weight & Bias",
  parallax: "Parallax",
  blindspot: "Blindspot",
  prism: "Prism",
  source_code: "Source Code",
  off_distribution: "Off-Distribution",
};

export const CATEGORY_HELPERS: Record<PrimaryCategory, string> = {
  weight_and_bias: "outlet lean distribution",
  parallax: "same facts, divergent framing",
  blindspot: "spectrum side missing",
  prism: "multi-angle non-partisan split",
  source_code: "primary docs vs commentary",
  off_distribution: "under-covered angles",
};

export const CATEGORY_ORDER: PrimaryCategory[] = [
  "weight_and_bias",
  "parallax",
  "blindspot",
  "prism",
  "source_code",
  "off_distribution",
];

export type CategoryFilter = "all" | PrimaryCategory;

export function categoryLabel(id: PrimaryCategory): string {
  return CATEGORY_LABELS[id];
}

/** Categories that appear on at least one story in the feed (stable order). */
export function categoriesInFeed(
  stories: { primary_category: PrimaryCategory }[],
): PrimaryCategory[] {
  const present = new Set(stories.map((s) => s.primary_category));
  return CATEGORY_ORDER.filter((id) => present.has(id));
}
