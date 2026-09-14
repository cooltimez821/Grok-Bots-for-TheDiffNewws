import Link from "next/link";
import { categoryLabel, type CategoryFilter } from "@/lib/categories";
import type { PrimaryCategory } from "@/lib/types";

type CategoryNavStubProps = {
  active?: PrimaryCategory | "all";
  /** Only chips for these categories (plus All). Same chrome as home. */
  available: PrimaryCategory[];
};

/** Same chrome chips as home; on detail they navigate back to the feed. */
export function CategoryNavStub({
  active = "all",
  available,
}: CategoryNavStubProps) {
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
        const on = active === item.id;
        return (
          <Link
            key={item.id}
            href="/"
            className={
              on
                ? "shrink-0 whitespace-nowrap rounded-full border border-[var(--violet)] bg-[var(--violet)] px-3 py-1.5 text-[11px] font-semibold text-[var(--on-violet)] no-underline"
                : "shrink-0 whitespace-nowrap rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-[11px] font-medium text-[var(--muted)] no-underline"
            }
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
