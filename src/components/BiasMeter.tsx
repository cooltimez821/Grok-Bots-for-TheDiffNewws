import { biasBandLabel, biasMeterWidths } from "@/lib/bias";
import type { BiasBand } from "@/lib/types";

type BiasMeterProps = {
  band: BiasBand;
  maxWidthClass?: string;
};

export function BiasMeter({
  band,
  maxWidthClass = "max-w-[172px]",
}: BiasMeterProps) {
  const w = biasMeterWidths(band);
  const label = biasBandLabel(band);

  return (
    <div className="mb-2 flex items-center gap-2">
      <span className="w-[88px] shrink-0 text-[9px] font-semibold uppercase tracking-[0.06em] text-[var(--faint)]">
        Coverage lean
      </span>
      <div
        className={`flex h-2 w-full overflow-hidden rounded-[3px] border border-[var(--border-strong)] bg-[var(--meter-track)] ${maxWidthClass}`}
        role="img"
        aria-label={`Coverage lean: ${label}`}
      >
        <span
          className="block h-full bg-[var(--meter-l)]"
          style={{ width: `${w.left}%` }}
        />
        <span
          className="block h-full bg-[var(--meter-c)]"
          style={{ width: `${w.center}%` }}
        />
        <span
          className="block h-full border-l border-[var(--meter-track)] bg-[var(--meter-r)]"
          style={{ width: `${w.right}%` }}
        />
      </div>
      <span className="min-w-[44px] whitespace-nowrap text-[10px] font-semibold tracking-[0.02em] text-[var(--ink-2)]">
        {label}
      </span>
    </div>
  );
}
