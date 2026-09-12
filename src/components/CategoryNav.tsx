"use client";

import {
  categoryLabel,
  type CategoryFilter,
} from "@/lib/categories";
import type { PrimaryCategory } from "@/lib/types";

type CategoryNavProps = {
  value: CategoryFilter;
  onChange: (next: CategoryFilter) => void;
  /** Only chips for these categories (plus All). Hides empty filters. */
  available: PrimaryCategory[];
};

export function CategoryNav({ value, onChange, available }: CategoryNavProps) {
  const items: { id: CategoryFilter; label: string }[] = [
    { id: "all", label: "All" },
    ...available.map((id) => ({ id, label: categoryLabel(id) })),
  ];

  return (
    <nav
      className="flex flex-wrap gap-1.5 py-2.5"
      aria-label="Category filter"
    >
      {items.map((item) => {
        const on = value === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onChange(item.id)}
            className={
              on
                ? "shrink-0 whitespace-nowrap rounded-full border border-[var(--accent)] bg-[var(--accent)] px-3 py-1.5 text-[11px] font-semibold text-[var(--on-accent)]"
                : "shrink-0 whitespace-nowrap rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-[11px] font-medium text-[var(--muted)]"
            }
          >
            {item.label}
          </button>
        );
      })}
    </nav>
  );
}
