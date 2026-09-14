import type { BlindspotLabel } from "@/lib/types";

type BlindspotRowProps = {
  blindspot: BlindspotLabel;
};

/**
 * Blindspot row ONLY when present === true.
 * Omit entirely when false — never muted "no blindspot".
 * Cool mint/violet wash — no warm/tan/beige.
 */
export function BlindspotRow({ blindspot }: BlindspotRowProps) {
  if (blindspot?.present !== true) return null;

  return (
    <div
      className="blindspot-row"
      data-testid="blindspot-row"
      data-blindspot-present="true"
      data-rule-id={blindspot.rule_id ?? undefined}
    >
      <span className="bs-lab">Blindspot</span>
      {blindspot.rule_id ? (
        <span className="bs-rule">{blindspot.rule_id}</span>
      ) : null}
    </div>
  );
}
