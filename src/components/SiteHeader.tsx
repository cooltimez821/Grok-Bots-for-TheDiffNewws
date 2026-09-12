import Link from "next/link";

type SiteHeaderProps = {
  variant?: "home" | "detail";
  rightLabel?: string;
};

export function SiteHeader({
  variant = "home",
  rightLabel = "v1 · no search · no account",
}: SiteHeaderProps) {
  const brand = (
    <div>
      <div className="text-[18px] font-bold tracking-tight md:text-[22px]">
        The<em className="not-italic text-[#0a7a75]">Diff</em>News
      </div>
      <div className="mt-0.5 text-[10px] uppercase tracking-[0.08em] text-[#6a6a6a]">
        {variant === "detail"
          ? "Cluster detail · same chrome as home"
          : "Independent AI coverage · not affiliated with Ground News"}
      </div>
    </div>
  );

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-[#141414] pb-2.5 pt-2">
      {variant === "detail" ? (
        <div className="flex items-center gap-2">
          <Link
            href="/"
            className="grid h-[22px] w-[22px] place-items-center rounded-full border border-[#141414] text-xs leading-none text-[#141414]"
            aria-label="Back to feed"
          >
            ←
          </Link>
          <Link href="/" className="text-inherit no-underline">
            {brand}
          </Link>
        </div>
      ) : (
        <Link href="/" className="text-inherit no-underline">
          {brand}
        </Link>
      )}
      <div className="hidden text-[10px] uppercase tracking-[0.04em] text-[#8e8e8e] sm:block">
        {rightLabel}
      </div>
    </header>
  );
}
