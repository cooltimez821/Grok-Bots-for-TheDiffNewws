/** Frozen Read API v0.1 shapes for TheDiffNews feed. */

export type BiasBand =
  | "left"
  | "lean_left"
  | "center"
  | "lean_right"
  | "right"
  | "mixed";

export type PrimaryCategory =
  | "weight_and_bias"
  | "parallax"
  | "blindspot"
  | "prism"
  | "source_code"
  | "off_distribution";

export type StoryMember = {
  title: string;
  canonical_url: string;
  published_at: string;
  outlet_name: string;
  dek: string | null;
  outlet_id?: string;
};

export type BlindspotLabel = {
  present: boolean;
  rule_id: string | null;
};

export type StoryLabels = {
  bias_band: BiasBand;
  blindspot: BlindspotLabel;
};

export type Story = {
  story_id: string;
  title: string;
  outlet_count: number;
  primary_category: PrimaryCategory;
  members: StoryMember[];
  labels: StoryLabels;
  first_seen_at?: string;
  last_updated_at?: string;
  article_count?: number;
};
