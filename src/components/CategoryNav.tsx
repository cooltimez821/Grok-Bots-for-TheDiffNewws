"use client";

import {
  CATEGORY_ORDER,
  categoryLabel,
  type CategoryFilter,
} from "@/lib/categories";

type CategoryNavProps = {
  value: CategoryFilter;
  onChange: (next: CategoryFilter) => void;
};

export function CategoryNav({ value, onChange }: CategoryNavProps) {
  const items: { id: CategoryFilter; label: string }[] = [
    { id: "all", label: "All" },
    ...CATEGORY_ORDER.map((id) => ({ id, label: categoryLabel(id) })),
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
                ? "shrink-0 whitespace-nowrap rounded-full border border-[#141414] bg-[#141414] px-2 py-1 text-[11px] text-white"
                : "shrink-0 whitespace-nowrap rounded-full border border-[#d4d4d2] bg-white px-2 py-1 text-[11px] text-[#2a2a2a]"
            }
          >
            {item.label}
          </button>
        );
      })}
    </nav>
  );
}
