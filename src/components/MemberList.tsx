import { formatPublishedAt } from "@/lib/format";
import type { StoryMember } from "@/lib/types";

type MemberListProps = {
  members: StoryMember[];
  outletCount: number;
};

export function MemberList({ members, outletCount }: MemberListProps) {
  return (
    <section>
      <div className="mb-2 mt-4 text-[10px] uppercase tracking-[0.1em] text-[#8e8e8e]">
        {outletCount} member source{outletCount === 1 ? "" : "s"} · title · dek
        · outlet_name · canonical_url · published_at
      </div>
      <ul className="flex list-none flex-col gap-2.5 p-0">
        {members.map((m, i) => (
          <li
            key={`${m.canonical_url}-${i}`}
            className="border border-[#d4d4d2] bg-white p-3"
          >
            <div className="text-[11px] font-bold uppercase tracking-[0.06em] text-[#085652]">
              {m.outlet_name}
            </div>
            <h4 className="mt-1 text-[14px] font-semibold leading-snug text-[#141414]">
              {m.title}
            </h4>
            {m.dek ? (
              <p className="mt-1.5 text-[13px] leading-relaxed text-[#2a2a2a]">
                {m.dek}
              </p>
            ) : null}
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#6a6a6a]">
              <span>{formatPublishedAt(m.published_at)}</span>
              <a
                href={m.canonical_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-[#085652] underline-offset-2 hover:underline"
              >
                Open source ↗
              </a>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
