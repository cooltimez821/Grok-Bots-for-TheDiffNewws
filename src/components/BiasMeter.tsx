import { biasBandLabel, biasMeterWidths } from "@/lib/bias";
import type { BiasBand } from "@/lib/types";

type BiasMeterProps = {
  band: BiasBand;
  maxWidthClass?: string;
};

export function BiasMeter({
  band,
  maxWidthClass = "max-w-[180px]",
}: BiasMeterProps) {
  const w = biasMeterWidths(band);

  return (
    <div className="mb-1.5 flex items-center gap-2">
      <span className="w-16 shrink-0 text-[9px] uppercase tracking-[0.08em] text-[var(--faint)]">
        bias_band
      </span>
      <div
        className={`flex h-2 w-full overflow-hidden rounded-sm border border-[var(--border-strong)] bg-[var(--meter-track)] ${maxWidthClass}`}
        role="img"
        aria-label={`Bias band: ${biasBandLabel(band)}`}
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
      <span className="whitespace-nowrap text-[10px] font-semibold text-[var(--muted)]">
        {biasBandLabel(band)}
      </span>
    </div>
  );
}
