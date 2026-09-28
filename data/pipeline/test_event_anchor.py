#!/usr/bin/env python3
"""Shared-event-anchor regression tests for cluster_v0.

Run:  /workspace/news-pipeline/.venv/bin/python debug/test_event_anchor.py
(pytest-compatible: test_* functions, plain asserts.) Temp out dirs only.

Regression: 2026-09-28 3:01 PM ET refresh merged WaPo "Trump dined with the
Anthropic CEO..." with CNBC "Anthropic launches cheaper AI model..." (Sonnet 5.5)
on a shared entity + the "CEO's call for a slowdown" backstory phrase (~0.40).

Regression 2 (5:02 PM ET refresh): Meta/MongoDB story FFD1731A8EB8FF60DD10788911
fell apart once its Bloomberg text article (the bridge) left the feed. TechCrunch
"...hires MongoDB CEO to lead..." vs The Information "Meta Taps MongoDB CEO to
Lead..." scored title Jaccard 0.5455 < 0.55 because "taps" != "hire". Event words
are now normalized to canonical classes (EVENT_WORD_CANON) in anchors AND titles,
EXCEPT the "dinner" class, which is normalized for anchors only (variant 2):
normalizing dine/dined/dinner in title similarity joins TechCrunch "Anthropic's
CEO is about to have dinner with President Trump" + WaPo "Trump dined with the
Anthropic CEO..." (0.57) into a duplicate satellite dinner card beside the main
Amodei card. They stay separate until satellite-folding is designed.
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
        "article_id": f"ANCH{_seq[0]:022d}", "outlet_id": outlet, "canonical_url": url,
        "url_hash": hashlib.sha256(url.encode()).hexdigest(), "title": title, "dek": dek,
        "published_at": iso(hours_ago), "ingested_at": iso(hours_ago - 0.1),
        "content_hash": hashlib.sha256((title + url).encode()).hexdigest(),
        "status": "fetched", "raw_ref": "test",
    }


WAPO = art("wapo", "Trump dined with the Anthropic CEO who called for AI slowdown",
           "The president\u2019s first one-on-one meeting with Dario Amodei followed months of tensions.",
           "https://www.washingtonpost.com/politics/2026/09/28/trump-dined-with-anthropic-ceo-who-called-ai-slowdown",
           hours_ago=7.0)
CNBC = art("cnbc", "Anthropic launches cheaper AI model, its second release since CEO's call for a slowdown",
           "The company said Sonnet 5.5 doesn't advance the frontier, but that it is better at coding "
           "and knowledge work tasks than its predecessor.",
           "https://www.cnbc.com/2026/09/28/anthropic-sonnet-5-5-launch.html", hours_ago=1.2)
AXIOS = art("axios", "Scoop: Anthropic's Dario Amodei to have White House dinner with Trump",
            "President Trump plans to host Anthropic CEO Dario Amodei at a private White House dinner.",
            "https://www.axios.com/2026/09/27/amodei-trump-dinner", hours_ago=5.0)
WEX = art("wash_examiner", "Trump to have dinner with Anthropic CEO Dario Amodei at White House: Report",
          "President Donald Trump is reportedly slated to have dinner with Anthropic CEO Dario Amodei.",
          "https://www.washingtonexaminer.com/trump-dinner-amodei", hours_ago=4.0)

TC_META = art("techcrunch", "Meta launches enterprise AI platform, hires MongoDB CEO to lead new initiative",
              "Meta says it will focus on bringing its full technology stack, including Muse, Meta Business "
              "Agent, Muse API, Muse Code, and more to businesses and developers.",
              "https://techcrunch.com/2026/09/28/meta-launches-enterprise-ai-platform-hires-mongodb-ceo-to-lead-new-initiative",
              hours_ago=4.2)
TI_META = art("the_information", "Meta Taps MongoDB CEO to Lead New Enterprise AI Division",
              "Meta Platforms is launching a new division to sell its AI tools to businesses, tapping MongoDB "
              "Chief Executive Chirantan Desai to lead the unit as chief enterprise platform officer.",
              "https://www.theinformation.com/briefings/meta-taps-mongodb-ceo-lead-new-enterprise-ai-division",
              hours_ago=5.4)
TC_DINNER = art("techcrunch", "Anthropic\u2019s CEO is about to have dinner with President Trump",
                "This will be the first one-on-one meeting between Dario Amodei and Donald Trump",
                "https://techcrunch.com/2026/09/27/anthropics-ceo-is-about-to-have-dinner-with-president-trump",
                hours_ago=20.0)


def _ok(a, b):
    ea, eb = (cv.extract_entities(x["title"], x.get("dek")) for x in (a, b))
    return cv.soft_merge_ok(a, b, ea, eb)


def test_anchor_extraction():
    assert cv.event_anchors(WAPO["title"], WAPO["dek"]) == {"dinner", "meeting"}
    assert cv.event_anchors(CNBC["title"], CNBC["dek"]) == {"launch", "product:sonnet 5.5"}
    assert cv.event_anchors("Amodei calls on AI companies to slow down") == set()


def test_density_key_fallback_only_when_one_side_unanchored():
    a = art("nyt", "Amodei calls on AI companies to slow down", None, "https://x.test/a")
    b = art("axios", "Anthropic's Amodei urges AI leaders to pump the brakes", None, "https://x.test/b")
    ok, ev = _ok(a, b)
    assert ok is True and ev["event_anchors"] == ["event:amodei_call"], ev
    # WaPo (dinner) and CNBC (launch) both share amodei_call but name different events
    assert cv.event_key(WAPO["title"]) == cv.event_key(CNBC["title"]) == "amodei_call"


def test_wapo_cnbc_no_edge():
    ok, ev = _ok(WAPO, CNBC)
    assert ok is False, ev
    assert ev.get("blocked_by") == "event_anchor", ev


def test_same_dinner_still_merges():
    ok, ev = _ok(AXIOS, WEX)
    assert ok is True, ev
    assert "dinner" in ev["event_anchors"], ev


def test_end_to_end_split():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        with open(d / "articles.jsonl", "w") as f:
            for a in (WAPO, CNBC, AXIOS, WEX):
                f.write(json.dumps(a) + "\n")
        r = cv.main(out_dir=d, app_data=None, verbose=False)
    assert r["summary"]["edges_removed_event_anchor"] == 1, r["summary"]
    feed_urls = [sorted(m["canonical_url"] for m in s["members"]) for s in r["feed"]]
    assert feed_urls == [sorted([AXIOS["canonical_url"], WEX["canonical_url"]])], feed_urls
    held_urls = {m["canonical_url"] for s in r["held"] for m in s["members"]}
    assert CNBC["canonical_url"] in held_urls and WAPO["canonical_url"] in held_urls


def test_event_word_normalization():
    canon = cv.canonical_event_word
    for w in ("launch", "launches", "launched", "launching", "unveils", "released"):
        assert canon(w) == "launch", w
    for w in ("hire", "hires", "hired", "hiring", "taps", "tapped", "tapping", "appoints", "appointed"):
        assert canon(w) == "hire", w
    for w in ("meeting", "meet", "meets", "met"):
        assert canon(w) == "meeting", w
    for w in ("dine", "dined", "dinner"):
        assert canon(w) == "dinner", w
    for w in ("sue", "sues", "sued", "lawsuit"):
        assert canon(w) == "lawsuit", w
    for w in ("acquire", "acquires", "acquisition", "buy", "buys"):
        assert canon(w) == "acquisition", w
    assert canon("ceo") is None and canon("model") is None
    # phrase classes
    assert "hire" in cv.event_anchors("Acme names Jane Doe as chief executive")
    assert "hire" in cv.event_anchors("Jane Doe to lead Acme's new AI unit")
    assert "hire" not in cv.event_anchors("A startup named Acme ships a chatbot")
    # title tokens share the canonical class
    assert "hire" in cv.tokenize_title(TI_META["title"]) and "hire" in cv.tokenize_title(TC_META["title"])


def test_meta_pair_links():
    assert {"hire", "launch"} <= cv.event_anchors(TC_META["title"], TC_META["dek"])
    assert {"hire", "launch"} <= cv.event_anchors(TI_META["title"], TI_META["dek"])
    ok, ev = _ok(TC_META, TI_META)
    assert ok is True, ev
    assert ev["title_overlap"] >= 0.55, ev
    assert "hire" in ev["event_anchors"], ev


def test_meta_links_wapo_cnbc_still_split_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        with open(d / "articles.jsonl", "w") as f:
            for a in (WAPO, CNBC, AXIOS, WEX, TC_META, TI_META):
                f.write(json.dumps(a) + "\n")
        r = cv.main(out_dir=d, app_data=None, verbose=False)
    assert r["summary"]["edges_removed_event_anchor"] == 1, r["summary"]
    feed_urls = sorted(sorted(m["canonical_url"] for m in s["members"]) for s in r["feed"])
    assert sorted([TC_META["canonical_url"], TI_META["canonical_url"]]) in feed_urls, feed_urls
    held_urls = {m["canonical_url"] for s in r["held"] for m in s["members"]}
    assert CNBC["canonical_url"] in held_urls and WAPO["canonical_url"] in held_urls


def test_dinner_not_normalized_in_title_similarity():
    # anchors: dinner class fully normalized
    assert "dinner" in cv.event_anchors(TC_DINNER["title"], TC_DINNER["dek"])
    assert "dinner" in cv.event_anchors(WAPO["title"], WAPO["dek"])
    assert "dinner" in cv.event_anchors("Amodei dines with Trump")
    # title tokens: dinner class NOT canonicalized (other classes still are)
    assert "dinner" in cv.TITLE_CANON_EXCLUDE
    assert "dinner" not in cv.tokenize_title(WAPO["title"])
    assert "hire" in cv.tokenize_title(TI_META["title"])


def test_tc_dinner_wapo_dined_stay_separate():
    ok, ev = _ok(TC_DINNER, WAPO)
    assert ok is False, ev
    ta, tb = cv.tokenize_title(TC_DINNER["title"]), cv.tokenize_title(WAPO["title"])
    assert cv.jaccard(ta, tb) < 0.55, (ta, tb)


def test_wapo_cnbc_sonnet_still_no_link():
    ok, ev = _ok(WAPO, CNBC)
    assert ok is False and ev.get("blocked_by") == "event_anchor", ev
    ok, ev = _ok(CNBC, WAPO)
    assert ok is False, ev


def test_tc_dinner_wapo_separate_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        with open(d / "articles.jsonl", "w") as f:
            for a in (WAPO, CNBC, TC_DINNER, TC_META, TI_META):
                f.write(json.dumps(a) + "\n")
        r = cv.main(out_dir=d, app_data=None, verbose=False)
    feed_urls = sorted(sorted(m["canonical_url"] for m in s["members"]) for s in r["feed"])
    assert feed_urls == [sorted([TC_META["canonical_url"], TI_META["canonical_url"]])], feed_urls
    held = [sorted(m["canonical_url"] for m in s["members"]) for s in r["held"]]
    assert [TC_DINNER["canonical_url"]] in held and [WAPO["canonical_url"]] in held, held
    assert [CNBC["canonical_url"]] in held, held


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL PASS")
