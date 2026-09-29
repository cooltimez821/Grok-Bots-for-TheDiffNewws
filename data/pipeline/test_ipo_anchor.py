#!/usr/bin/env python3
"""IPO/funding anchor tightening tests for cluster_v0 (2026-09-29).

Run:  /workspace/news-pipeline/.venv/bin/python debug/test_ipo_anchor.py
(pytest-compatible: test_* functions, plain asserts.) Temp out dirs only.

Regression: 5:03 PM ET refresh put home card 8CB12CAD93C59FE88B0D10B4D8 on home,
merging The Information "OpenAI in Early Talks to Raise $30 Billion Before an IPO"
(pre-IPO round) with Bloomberg "Altman Says OpenAI Investors Patient on IPO Amid
Safety Focus" (IPO timing) at title Jaccard 0.17 via the shared density key
openai_ipo + the broad anchor class "ipo". Rule now: an edge whose shared anchors
are ONLY ipo/funding (WEAK_ANCHOR_CLASSES) also needs a shared normalized $ figure
or title Jaccard >= WEAK_ANCHOR_TITLE_JACCARD_MIN (0.5); every other class /
product anchor is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cluster_v0 as cv  # noqa: E402

NOW = datetime.now(timezone.utc)
_seq = [0]


def art(outlet, title, dek, url, hours_ago=2.0):
    _seq[0] += 1
    iso = lambda h: (NOW - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "article_id": f"IPOA{_seq[0]:022d}", "outlet_id": outlet, "canonical_url": url,
        "url_hash": hashlib.sha256(url.encode()).hexdigest(), "title": title, "dek": dek,
        "published_at": iso(hours_ago), "ingested_at": iso(hours_ago - 0.1),
        "content_hash": hashlib.sha256((title + url).encode()).hexdigest(),
        "status": "fetched", "raw_ref": "test",
    }


def link(a, b):
    ok, ev = cv.soft_merge_ok(a, b, cv.extract_entities(a["title"], a.get("dek")),
                              cv.extract_entities(b["title"], b.get("dek")))
    return ok, ev


def cluster(rows):
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        with open(tmp / "articles.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        return cv.main(out_dir=tmp, app_data=None, verbose=False)


def groups(res):
    """Set of frozensets of outlet_ids per story (all stories, home + held)."""
    arts = {}
    for it in res["feed"] + res["held"]:
        arts[it["story_id"]] = frozenset(m["outlet_id"] for m in it["members"])
    return set(arts.values())


# Real rows (titles/deks/urls from out/articles.jsonl, 2026-09-29), real time gaps.
INFO_OAI = art(
    "the_information", "OpenAI in Early Talks to Raise $30 Billion Before an IPO",
    "OpenAI is in early talks with investors to raise a pre-IPO round and is targeting raising "
    "$30 billion, according to a person familiar with the matter. The ChatGPT maker could seek a "
    "valuation around $1.4 trillion, though it hasn\u2019t signed a term sheet yet with any "
    "investor, the person said. The ...",
    "https://www.theinformation.com/briefings/openai-early-talks-raise-30-billion-ipo", 5.0)
BBG_OAI = art(
    "bloomberg", "Altman Says OpenAI Investors Patient on IPO Amid Safety Focus",
    "OpenAI\u2019s Chief Executive Officer Sam Altman said the company wants to navigate a period "
    "of heightened artificial intelligence safety concerns without the pressure of being a newly "
    "public company and believes investors will be \u201cpatient\u201d with its IPO planning.",
    "https://www.bloomberg.com/news/articles/2026-09-29/altman-openai-investors-are-patient-on-ipo-amid-safety-focus",
    3.245)

FT_S1 = art(
    "ft", "Anthropic warns of \u2018existential risks to humanity\u2019 in IPO prospectus",
    "Long-awaited S-1 filing reports Claude maker lost $8bn last year on $4.6bn in revenue",
    "https://www.ft.com/content/c7685a7e-7745-4cbc-8053-4958d0ea449b?syn-25a6b1a6=1", 16.0)
GUARDIAN_S1 = art(
    "guardian", "Anthropic \u2018warns of existential AI risks to humanity\u2019 in IPO document",
    "Reported admission to investors of AI\u2019s \u2018self-preserving behaviours\u2019 comes as "
    "company prepares for a potential $2tn flotation Anthropic is telling investors that advanced AI "
    "could pose \u201ccatastrophic or existential risks to humanity\u201d, according to reports, as "
    "it prepares for a potential $2tn (\u00a31.5tn) flotation. The warning inside the startup\u2019s "
    "IPO prospectus, which has yet to be made public, was reported by Reuters and the Financial "
    "Times.",
    "https://www.theguardian.com/technology/2026/sep/29/anthropic-warns-existential-ai-risks-humanity-ipo-document-claude",
    8.17)
SEMAFOR_S1 = art(
    "semafor", "Anthropic's IPO prospectus details steep losses, existential risks",
    "The existence of Anthropic\u2019s 401(k) benefits assumes a world where we\u2019re all still here.",
    "https://www.semafor.com/article/09/29/2026/anthropics-ipo-prospectus-details-steep-losses-existential-risks",
    1.2)


# ---------------------------------------------------------------- (a) regression pair

def test_openai_raise_vs_ipo_timing_no_link():
    ok, ev = link(INFO_OAI, BBG_OAI)
    assert not ok, ev
    assert ev["title_overlap"] < cv.WEAK_ANCHOR_TITLE_JACCARD_MIN
    assert ev.get("blocked_by") == "event_anchor", ev
    # it used to link: density key openai_ipo + shared "ipo" only
    assert cv.event_key(INFO_OAI["title"]) == cv.event_key(BBG_OAI["title"]) == "openai_ipo"
    common = cv.event_anchors(INFO_OAI["title"], INFO_OAI["dek"]) & cv.event_anchors(BBG_OAI["title"], BBG_OAI["dek"])
    assert common == {"ipo"}, common


def test_openai_pair_split_end_to_end():
    res = cluster([INFO_OAI, BBG_OAI])
    assert res["feed"] == [], [i["title"] for i in res["feed"]]
    assert groups(res) == {frozenset({"the_information"}), frozenset({"bloomberg"})}
    assert res["summary"]["edges_removed_event_anchor"] >= 1


# ---------------------------------------------------------------- (b) genuine IPO pair

def test_anthropic_prospectus_pairs_still_link():
    for a, b in ((FT_S1, GUARDIAN_S1), (FT_S1, SEMAFOR_S1)):
        ok, ev = link(a, b)
        assert ok, (a["outlet_id"], b["outlet_id"], ev)
        assert ev["title_overlap"] >= cv.WEAK_ANCHOR_TITLE_JACCARD_MIN


def test_anthropic_prospectus_one_card_end_to_end():
    res = cluster([FT_S1, GUARDIAN_S1, SEMAFOR_S1])
    assert len(res["feed"]) == 1, [i["title"] for i in res["feed"]]
    assert {m["outlet_id"] for m in res["feed"][0]["members"]} == {"ft", "guardian", "semafor"}


# ---------------------------------------------------------------- (c) genuine funding pair

def test_same_round_same_figure_links_via_figure():
    # Same pre-IPO round, same $30bn figure; titles share only "OpenAI" + ipo/funding.
    bbg_round = art("bloomberg", "OpenAI Seeks $30bn in Funding Round Ahead of Listing, Eyes IPO",
                    "The ChatGPT maker is weighing a raise at a $1.4 trillion valuation.",
                    "https://www.bloomberg.com/news/articles/2026-09-29/openai-seeks-30bn-funding-round", 4.0)
    ok, ev = link(INFO_OAI, bbg_round)
    assert ev["title_overlap"] < cv.WEAK_ANCHOR_TITLE_JACCARD_MIN, ev
    assert cv.money_figures(INFO_OAI["title"], INFO_OAI["dek"]) & cv.money_figures(bbg_round["title"], bbg_round["dek"])
    assert ok, ev
    res = cluster([INFO_OAI, bbg_round])
    assert len(res["feed"]) == 1 and res["feed"][0]["outlet_count"] == 2


def test_zai_fundraise_same_figure_links_different_figure_not():
    a = art("bloomberg", "Z.ai Raises $1.5 Billion as Chinese AI Startup Races Rivals",
            "The Zhipu spinout closed the round this week.", "https://www.bloomberg.com/zai-raises", 3.0)
    b = art("ft", "China's Z.ai fundraise hits $1.5bn after shares tumble",
            "Investors backed the start-up despite the sell-off.", "https://www.ft.com/zai-fundraise", 2.0)
    c = art("ft", "China's Z.ai fundraise targets $400mn from state funds",
            "A separate state-backed round.", "https://www.ft.com/zai-state-round", 2.0)
    assert cv.event_key(a["title"]) == cv.event_key(b["title"]) == cv.event_key(c["title"]) == "zai_fundraise"
    ok, ev = link(a, b)
    assert ok, ev
    ok2, ev2 = link(a, c)
    assert not ok2 and ev2.get("blocked_by") == "event_anchor", ev2


def test_money_figures_normalized():
    assert cv.money_figures("$30 billion", "$30bn") == {30_000_000_000}
    assert cv.money_figures("valuation around $1.4 trillion") == {cv.money_figures("$1,400 billion").pop()}
    assert cv.money_figures("$2tn flotation") == {2_000_000_000_000}
    assert cv.money_figures("$40-to-$44 range") == set()   # bare prices are not figures


# ---------------------------------------------------------------- (d) other classes unaffected

def test_non_weak_anchors_ignore_floor():
    lo = {"title_overlap": 0.05}
    dinner_a = art("axios", "Scoop: Anthropic's Dario Amodei to have White House dinner with Trump", None, "https://x.test/d1")
    dinner_b = art("nyt", "Dario Amodei of Anthropic to Dine With Trump at White House", None, "https://x.test/d2")
    sue_a = art("nyt", "The Times Sues OpenAI Over Copyright", None, "https://x.test/l1")
    sue_b = art("wapo", "OpenAI hit with lawsuit from newspaper publisher", None, "https://x.test/l2")
    for a, b in ((dinner_a, dinner_b), (sue_a, sue_b)):
        ok, ev = cv._anchor_gate(a, b, dict(lo))
        assert ok, ev
    # ipo + another class shared: the other class suffices (unchanged)
    mix_a = art("ft", "Nscale files for IPO, unveils new data center", None, "https://x.test/m1")
    mix_b = art("cnbc", "Nscale launches data center push ahead of IPO", None, "https://x.test/m2")
    ok, ev = cv._anchor_gate(mix_a, mix_b, dict(lo))
    assert ok and set(ev["event_anchors"]) == {"ipo", "launch"}, ev
    # ipo only at the same low overlap: blocked
    ok, ev = cv._anchor_gate(INFO_OAI, BBG_OAI, dict(lo))
    assert not ok and ev["blocked_detail"] == "weak_anchor_uncorroborated", ev


def test_amodei_dinner_still_one_card():
    rows = [
        art("axios", "Scoop: Anthropic's Dario Amodei to have White House dinner with Trump",
            "President Trump plans to host Anthropic CEO Dario Amodei at a private White House dinner.",
            "https://www.axios.com/amodei-dinner", 30),
        art("nyt", "Dario Amodei of Anthropic to Dine With Trump at White House", None,
            "https://www.nytimes.com/amodei-dine.html", 23),
        art("ft", "Trump hosts Anthropic boss Dario Amodei at White House dinner", None,
            "https://www.ft.com/amodei-dinner", 18),
    ]
    res = cluster(rows)
    assert len(res["feed"]) == 1 and res["feed"][0]["outlet_count"] == 3, [i["title"] for i in res["feed"]]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            import traceback; traceback.print_exc()
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
