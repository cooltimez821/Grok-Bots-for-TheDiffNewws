import Link from "next/link";
import {
  CATEGORY_ORDER,
  categoryLabel,
  type CategoryFilter,
} from "@/lib/categories";
import type { PrimaryCategory } from "@/lib/types";

type CategoryNavStubProps = {
  active?: PrimaryCategory | "all";
};

/** Same chrome chips as home; on detail they navigate back to the feed. */
export function CategoryNavStub({ active = "all" }: CategoryNavStubProps) {
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
        const on = active === item.id;
        return (
          <Link
            key={item.id}
            href="/"
            className={
              on
                ? "shrink-0 whitespace-nowrap rounded-full border border-[#141414] bg-[#141414] px-2 py-1 text-[11px] text-white no-underline"
                : "shrink-0 whitespace-nowrap rounded-full border border-[#d4d4d2] bg-white px-2 py-1 text-[11px] text-[#2a2a2a] no-underline"
            }
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
