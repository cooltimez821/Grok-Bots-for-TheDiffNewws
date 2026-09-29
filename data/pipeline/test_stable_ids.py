#!/usr/bin/env python3
"""Stable story_id tests for cluster_v0.

Run:  /workspace/news-pipeline/.venv/bin/python debug/test_stable_ids.py
(pytest-compatible too: test_* functions, plain asserts.)
Uses temp out dirs only; never touches out/ or the app mirrors.
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


def _iso(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def art(outlet: str, title: str, url: str, hours_ago: float = 2.0) -> dict:
    _seq[0] += 1
    aid = f"TEST{_seq[0]:022d}"
    return {
        "article_id": aid,
        "outlet_id": outlet,
        "canonical_url": url,
        "url_hash": hashlib.sha256(url.encode()).hexdigest(),
        "title": title,
        "dek": None,
        "published_at": _iso(hours_ago),
        "ingested_at": _iso(hours_ago - 0.1),
        "content_hash": hashlib.sha256((title + url).encode()).hexdigest(),
        "status": "fetched",
        "raw_ref": "test",
    }


def reseed(articles: list) -> list:
    """Fresh copies with NEW article_ids, like seed_feeds.py does every refresh."""
    out = []
    for a in articles:
        b = {k: v for k, v in a.items() if k not in ("story_id", "duplicate_of", "drop_reason")}
        _seq[0] += 1
        b["article_id"] = f"RESEED{_seq[0]:020d}"
        b["status"] = "fetched"
        out.append(b)
    return out


def run(out_dir: Path, articles: list) -> dict:
    with open(out_dir / "articles.jsonl", "w") as f:
        for a in articles:
            f.write(json.dumps(a) + "\n")
    return cv.main(out_dir=out_dir, app_data=None, verbose=False)


def sid_by_url(result: dict) -> dict:
    """canonical_url of each story member -> story_id (from stories + members)."""
    return {
        m["canonical_url"]: s["story_id"]
        for s in result["feed"] + result["held"]
        for m in s.get("members") or []
    }


# Amodei "pace the frontier" density event (same event_key -> one cluster).
# Softfix 2026-09-29: the shared event_key alone no longer links (generic
# slow-down phrasing); fixtures name a shared event ("summit" -> meeting) in
# every title so the density path still forms one cluster for the ID tests.
AMODEI = [
    art("nyt", "Amodei calls on AI companies to slow down at AI summit", "https://www.nytimes.com/2026/ai/amodei-slow.html"),
    art("axios", "Anthropic's Amodei urges AI leaders to pump the brakes at AI summit", "https://www.axios.com/amodei-brakes"),
    art("the_verge", "Amodei says AI is advancing too fast at AI summit", "https://www.theverge.com/amodei-too-fast"),
    art("bloomberg", "AI CEOs call for slowdown at AI summit as Amodei leads", "https://www.bloomberg.com/news/amodei-slowdown"),
]
EXTRA_MEMBER = art("techcrunch", "Anthropic CEO Amodei wants AI to slow down at AI summit", "https://techcrunch.com/amodei-slow-down/")
OBAMA = [
    art("cnn", "Obama unveils AI safeguards plan for Democrats", "https://www.cnn.com/obama-ai-safeguards"),
    art("wapo", "Obama unveils AI safeguard policy push", "https://www.washingtonpost.com/obama-ai-safeguards"),
]


def _amodei_id(res: dict) -> str:
    ids = {sid_by_url(res)[a["canonical_url"]] for a in AMODEI if a["canonical_url"] in sid_by_url(res)}
    assert len(ids) == 1, f"Amodei members split across stories: {ids}"
    return ids.pop()


def test_outlets_exist_in_catalog():
    cat = {o["outlet_id"] for o in json.loads(cv.CATALOG.read_text())["outlets"]}
    for a in AMODEI + [EXTRA_MEMBER] + OBAMA:
        assert a["outlet_id"] in cat, a["outlet_id"]


def test_same_input_twice_identical_ids():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        r1 = run(d, AMODEI + OBAMA)
        ids1 = sorted(s["story_id"] for s in r1["stories"])
        assert r1["summary"]["story_id_prior_source"] == "none"
        # second run: same articles but re-seeded article_ids (real refresh shape)
        r2 = run(d, reseed(AMODEI + OBAMA))
        ids2 = sorted(s["story_id"] for s in r2["stories"])
        assert ids1 == ids2, (ids1, ids2)
        assert r2["summary"]["story_ids_minted"] == 0
        assert r2["summary"]["story_id_prior_source"] == "story_id_map"
        # third run on the file output itself (stamped articles.jsonl)
        r3 = cv.main(out_dir=d, app_data=None, verbose=False)
        assert sorted(s["story_id"] for s in r3["stories"]) == ids1


def test_member_added_then_removed_keeps_id():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        base = _amodei_id(run(d, AMODEI))
        # add one member: Jaccard 4/5 = 0.8
        added = _amodei_id(run(d, reseed(AMODEI + [EXTRA_MEMBER])))
        assert added == base
        # remove two (incl. the extra): {nyt, axios, the_verge} vs 5 -> 3/5 = 0.6
        removed = _amodei_id(run(d, reseed(AMODEI[:3])))
        assert removed == base


def test_url_normalization_keeps_id():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        base = _amodei_id(run(d, AMODEI))
        tweaked = reseed(AMODEI)
        for a in tweaked:
            a["canonical_url"] = a["canonical_url"].replace("https://www.", "http://") + "?utm_source=rss#top"
        res = run(d, tweaked)
        ids = {s["story_id"] for s in res["stories"]}
        assert ids == {base}, (ids, base)


def test_new_cluster_gets_new_id():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        r1 = run(d, AMODEI)
        prior_ids = {s["story_id"] for s in r1["stories"]}
        r2 = run(d, reseed(AMODEI + OBAMA))
        m = sid_by_url(r2)
        obama_ids = {m[a["canonical_url"]] for a in OBAMA}
        assert len(obama_ids) == 1
        assert not (obama_ids & prior_ids), "new cluster must not reuse a prior id"
        assert _amodei_id(r2) in prior_ids
        assert r2["summary"]["story_ids_minted"] == 1


def test_below_threshold_mints_new_id():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        base = _amodei_id(run(d, AMODEI))
        # 1 of 4 prior members remains + 2 new -> 1/6 < 0.5 -> new id
        survivors = reseed([AMODEI[0], EXTRA_MEMBER])
        res = run(d, survivors)
        new = {s["story_id"] for s in res["stories"]}
        assert base not in new, (base, new)


def test_greedy_one_claim_highest_overlap_and_tiebreak():
    prior = {
        "BBBB": {"a", "b", "c", "d"},
        "AAAA": {"a", "b", "c", "d"},  # identical member set -> smaller id wins
        "CCCC": {"x", "y"},
    }
    new = [{"a", "b", "c", "d"}, {"a", "b", "c"}, {"x", "y", "z"}, {"q"}]
    got = cv.assign_stable_story_ids(new, {k: set(v) for k, v in prior.items()})
    assert got[0] == ("AAAA", 1.0), got
    assert got[1] == ("BBBB", 0.75), got  # AAAA already claimed
    assert got[2][0] == "CCCC", got  # 2/3
    assert got[3] == (None, None), got
    # exact threshold: 1/2 reuses, 1/3 does not
    assert cv.assign_stable_story_ids([{"a"}], {"P": {"a", "b"}})[0][0] == "P"
    assert cv.assign_stable_story_ids([{"a"}], {"P": {"a", "b", "c"}})[0][0] is None


def test_retained_id_survives_brief_drop():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        base = _amodei_id(run(d, AMODEI + OBAMA))
        run(d, reseed(OBAMA))  # Amodei articles gone this refresh
        mp = json.loads((d / cv.STORY_ID_MAP_NAME).read_text())
        assert base in mp["stories"], "unclaimed prior id should be retained"
        back = _amodei_id(run(d, reseed(AMODEI + OBAMA)))
        assert back == base


def test_bootstrap_from_legacy_outputs():
    """No story_id_map.json yet: ids recovered from feed/stories/members."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        base = _amodei_id(run(d, AMODEI))
        (d / cv.STORY_ID_MAP_NAME).unlink()
        res = run(d, reseed(AMODEI))  # reseed: legacy article_ids no longer join
        assert res["summary"]["story_id_prior_source"] == "bootstrap"
        assert _amodei_id(res) == base


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
