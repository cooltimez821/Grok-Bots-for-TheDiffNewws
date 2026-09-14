import type { Metadata } from "next";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = {
  title: "For Agents · TheDiffNews",
  description:
    "Structured feeds and frozen read shape for agents — not a chat surface.",
};

const SITE = "https://thediffnews.com";

export default function ForAgentsPage() {
  return (
    <main className="mx-auto min-h-screen max-w-[720px] px-4 py-7 md:px-10 md:pb-16">
      <SiteHeader variant="agents" />

      <p className="mb-2 mt-7 text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--violet)]">
        Machine access
      </p>
      <h1 className="mb-2.5 text-[28px] font-bold leading-tight tracking-tight text-[var(--ink)]">
        For Agents
      </h1>
      <p className="mb-7 max-w-[58ch] text-[15px] leading-relaxed text-[var(--muted)]">
        Structured feeds and a frozen read shape — not a chat surface. Pull
        clusters, cite outlets, leave human chrome alone.
      </p>

      <section
        className="mb-3.5 rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-5 py-[18px] shadow-[var(--shadow-card)]"
        aria-labelledby="feeds-h"
      >
        <h2
          id="feeds-h"
          className="mb-3 text-[13px] font-bold uppercase tracking-[0.04em] text-[var(--ink)]"
        >
          Feeds
        </h2>
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-2 rounded-md border border-[var(--border)] bg-[var(--code-bg)] px-3 py-2.5">
            <span className="min-w-[48px] text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--violet)]">
              RSS
            </span>
            <code className="break-all font-[family-name:var(--font-ibm-plex-mono)] text-[12.5px] font-medium text-[var(--ink)]">
              {SITE}/rss.xml
            </code>
          </div>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-2 rounded-md border border-[var(--border)] bg-[var(--code-bg)] px-3 py-2.5">
            <span className="min-w-[48px] text-[10px] font-bold uppercase tracking-[0.1em] text-[var(--violet)]">
              JSON
            </span>
            <code className="break-all font-[family-name:var(--font-ibm-plex-mono)] text-[12.5px] font-medium text-[var(--ink)]">
              {SITE}/feed.json
            </code>
          </div>
        </div>
        <p className="mt-3 text-[13px] leading-snug text-[var(--muted)]">
          Also see{" "}
          <code className="font-[family-name:var(--font-ibm-plex-mono)] text-[12px] text-[var(--ink)]">
            /llms.txt
          </code>{" "}
          for a short machine-readable site summary (endpoints, cite rules,
          field enums). Prefer JSON for clustering fields; RSS for title / link
          / published. Poll home feeds on a polite interval (e.g. every 15–30
          min); freshness floor is 48h with no member update.
        </p>
      </section>

      <section
        className="mb-3.5 rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-5 py-[18px] shadow-[var(--shadow-card)]"
        aria-labelledby="shape-h"
      >
        <h2
          id="shape-h"
          className="mb-3 text-[13px] font-bold uppercase tracking-[0.04em] text-[var(--ink)]"
        >
          Frozen read shape
        </h2>
        <span className="mb-2.5 inline-block rounded-full border border-[var(--violet-ring)] bg-[var(--violet-soft)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--violet)]">
          v0.1 · enums unchanged
        </span>
        <table className="w-full border-collapse text-[13px]">
          <tbody>
            {[
              ["story_id", "Stable cluster id"],
              ["title", "Ingest title (not model-generated)"],
              [
                "primary_category",
                "Enum: weight_and_bias · parallax · blindspot · prism · source_code · off_distribution",
              ],
              [
                "labels.bias_band",
                'Machine enum (left | lean_left | center | lean_right | right | mixed). UI may say “Coverage lean”.',
              ],
              [
                "labels.blindspot",
                "{ present, rule_id } — omit UI row when present ≠ true",
              ],
              ["outlet_count", "Member outlet count"],
              [
                "members[]",
                "outlet_name · title · dek · canonical_url · published_at",
              ],
            ].map(([field, desc], i, arr) => (
              <tr key={field}>
                <th
                  className={`w-[38%] py-2 text-left align-top font-[family-name:var(--font-ibm-plex-mono)] text-[12px] font-semibold text-[var(--ink)] ${
                    i < arr.length - 1 ? "border-b border-[var(--border)]" : ""
                  }`}
                >
                  {field}
                </th>
                <td
                  className={`py-2 align-top text-[var(--muted)] ${
                    i < arr.length - 1 ? "border-b border-[var(--border)]" : ""
                  }`}
                >
                  {desc}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-[13px] leading-snug text-[var(--muted)]">
          IA: feed → cluster → members. Category chips hide when empty. Detail
          section header: <strong className="text-[var(--ink-2)]">Sources</strong>.
        </p>
      </section>

      <section
        className="mb-3.5 rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-5 py-[18px] shadow-[var(--shadow-card)]"
        aria-labelledby="cite-h"
      >
        <h2
          id="cite-h"
          className="mb-3 text-[13px] font-bold uppercase tracking-[0.04em] text-[var(--ink)]"
        >
          Cite rules
        </h2>
        <ul className="m-0 list-disc space-y-1.5 pl-[1.15em] text-[14px] leading-normal text-[var(--ink-2)]">
          <li>
            Cite the <strong>outlet</strong> (
            <code className="font-[family-name:var(--font-ibm-plex-mono)] text-[12px]">
              outlet_name
            </code>{" "}
            +{" "}
            <code className="font-[family-name:var(--font-ibm-plex-mono)] text-[12px]">
              canonical_url
            </code>
            ), not TheDiffNews as the publisher of the article.
          </li>
          <li>
            When summarizing a cluster, name at least two member outlets when{" "}
            <code className="font-[family-name:var(--font-ibm-plex-mono)] text-[12px]">
              outlet_count ≥ 2
            </code>
            .
          </li>
          <li>
            Do not invent{" "}
            <code className="font-[family-name:var(--font-ibm-plex-mono)] text-[12px]">
              bias_band
            </code>
            ,{" "}
            <code className="font-[family-name:var(--font-ibm-plex-mono)] text-[12px]">
              blindspot.rule_id
            </code>
            , or category enums — use feed values only.
          </li>
          <li>
            Do not treat “Coverage lean” UI copy as a machine field; the enum
            remains{" "}
            <code className="font-[family-name:var(--font-ibm-plex-mono)] text-[12px]">
              bias_band
            </code>
            .
          </li>
          <li>
            This page is access docs only — no agent chat, no write API.
          </li>
        </ul>
      </section>

      <footer className="mt-7 text-[12px] leading-relaxed text-[var(--faint)]">
        Human default theme: Aurora · Dark option (Signal) waitlisted.
        <br />
        <Link
          href="/"
          className="font-semibold text-[var(--violet)] no-underline hover:text-[var(--violet-hover)]"
        >
          Return to feed
        </Link>
        {" · "}
        <a
          href="/llms.txt"
          className="font-semibold text-[var(--violet)] no-underline hover:text-[var(--violet-hover)]"
        >
          /llms.txt
        </a>
      </footer>
    </main>
  );
}
