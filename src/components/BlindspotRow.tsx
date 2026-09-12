import type { BlindspotLabel } from "@/lib/types";

type BlindspotRowProps = {
  blindspot: BlindspotLabel;
};

/**
 * Blindspot row ONLY when present === true.
 * Omit entirely when false — never muted "no blindspot".
 */
export function BlindspotRow({ blindspot }: BlindspotRowProps) {
  if (!blindspot?.present) return null;

  return (
    <div className="mt-0.5 flex items-center gap-1.5 bg-[#f3ead8] px-1.5 py-1 text-[11px] text-[#8a5a12]">
      <span className="text-[10px] font-bold uppercase tracking-[0.06em]">
        Blindspot
      </span>
      {blindspot.rule_id ? (
        <span className="text-[#7a6840]">{blindspot.rule_id}</span>
      ) : null}
    </div>
  );
}
