import feedJson from "../../data/feed-v1.json";
import type { Story } from "./types";

const allStories = feedJson as Story[];

/** v1 home feed: outlet_count >= 2 only (fixture already filtered). */
export function getFeedStories(): Story[] {
  return allStories.filter((s) => s.outlet_count >= 2);
}

export function getStoryById(storyId: string): Story | undefined {
  return allStories.find((s) => s.story_id === storyId);
}

export function getAllStoryIds(): string[] {
  return allStories.map((s) => s.story_id);
}
