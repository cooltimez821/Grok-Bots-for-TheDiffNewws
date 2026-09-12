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
      <span className="w-16 shrink-0 text-[9px] uppercase tracking-[0.08em] text-[#8e8e8e]">
        bias_band
      </span>
      <div
        className={`flex h-2 w-full overflow-hidden border border-[#d4d4d2] bg-[#efefed] ${maxWidthClass}`}
        role="img"
        aria-label={`Bias band: ${biasBandLabel(band)}`}
      >
        <span className="block h-full bg-[#4a4a4a]" style={{ width: `${w.left}%` }} />
        <span className="block h-full bg-[#9a9a9a]" style={{ width: `${w.center}%` }} />
        <span
          className="block h-full border-l border-white bg-[#d0d0d0]"
          style={{ width: `${w.right}%` }}
        />
      </div>
      <span className="whitespace-nowrap text-[10px] text-[#6a6a6a]">
        {biasBandLabel(band)}
      </span>
    </div>
  );
}
