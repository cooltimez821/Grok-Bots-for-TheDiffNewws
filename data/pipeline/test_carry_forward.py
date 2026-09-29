#!/usr/bin/env python3
"""Carry-forward tests for seed_feeds.py (+ clusterer treatment of carried rows).

Run:  /workspace/news-pipeline/.venv/bin/python debug/test_carry_forward.py
(pytest-compatible too: test_* functions, plain asserts.)
Uses temp dirs only; never touches out/, catalog/, feeds/ or the app mirrors.
No network: resolve_outlet is monkeypatched with an in-memory RSS feed.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cluster_v0 as cv  # noqa: E402
import seed_feeds as sf  # noqa: E402

import feedparser  # noqa: E402

NOW = datetime.now(timezone.utc).replace(microsecond=0)
CATALOG = {"axios", "the_information", "wash_examiner", "nyt", "ft"}
_seq = [0]


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def row(outlet: str, title: str, url: str, hours_ago: float, now: datetime = NOW, **extra) -> dict:
    _seq[0] += 1
    canon = sf.canonical_url(url)
    r = {
        "article_id": f"CF{_seq[0]:024d}",
        "outlet_id": outlet,
        "canonical_url": canon,
        "url_hash": sf.sha256_hex(canon),
        "title": title,
        "dek": None,
        "authors": [],
        "language": "en",
        "published_at": _iso(now - timedelta(hours=hours_ago)),
        "ingested_at": _iso(now - timedelta(hours=max(hours_ago - 0.1, 0))),
        "content_hash": hashlib.sha256((title + url).encode()).hexdigest(),
        "status": "clustered",
        "raw_ref": "test",
    }
    r.update(extra)
    return r


# ---------------------------------------------------------------- expiry

def test_expiry_47h_carried_49h_not():
    prior = [row("wash_examiner", "AI a", "https://x.test/a", 47),
             row("wash_examiner", "AI b", "https://x.test/b", 49)]
    carried, rep = sf.carry_forward(prior, [], CATALOG, NOW)
    assert [c["canonical_url"] for c in carried] == ["https://x.test/a"]
    assert carried[0]["carried_forward"] is True
    assert rep["stats"]["expired"] == 1
    assert rep["in_window_losses"] == []  # 49h is out of window: not a loss


def test_carry_keeps_original_id_url_and_fields():
    p = row("the_information", "Anthropic AI thing", "https://x.test/keep", 10, story_id="S1", dek="d")
    carried, _ = sf.carry_forward([p], [], CATALOG, NOW)
    c = carried[0]
    for k, v in p.items():
        assert c[k] == v, k
    assert c["carried_forward"] is True


def test_carried_twice_still_expires_by_original_published_at():
    t0 = NOW
    p = row("wash_examiner", "AI dinner", "https://x.test/d", 30, now=t0)
    run1, _ = sf.carry_forward([p], [], CATALOG, t0)                       # age 30h
    assert len(run1) == 1
    run2, rep2 = sf.carry_forward(run1, [], CATALOG, t0 + timedelta(hours=17))  # age 47h
    assert len(run2) == 1 and rep2["stats"]["carried_again"] == 1
    assert run2[0]["published_at"] == p["published_at"]  # never re-dated
    run3, rep3 = sf.carry_forward(run2, [], CATALOG, t0 + timedelta(hours=19))  # age 49h
    assert run3 == [] and rep3["stats"]["expired"] == 1
    # and never comes back later
    run4, _ = sf.carry_forward(run2, [], CATALOG, t0 + timedelta(hours=30))
    assert run4 == []


def test_clusterer_drops_carried_member_past_48h():
    """Carried rows follow the same 48h is_fresh rule in cluster_v0."""
    now = datetime.now(timezone.utc)
    assert cv.is_fresh(_iso(now - timedelta(hours=47)), now)
    assert not cv.is_fresh(_iso(now - timedelta(hours=49)), now)
    assert sf.CARRY_FORWARD_HOURS == cv.HOME_FRESHNESS_HOURS


# ---------------------------------------------------------------- dedupe

def test_refetched_article_not_duplicated():
    p = row("axios", "AI scoop", "https://www.axios.com/scoop", 5)
    fresh = row("axios", "AI scoop", "https://www.axios.com/scoop?utm_source=rss", 5, status="fetched")
    carried, rep = sf.carry_forward([p], [fresh], CATALOG, NOW)
    assert carried == [] and rep["stats"]["refetched"] == 1
    # member-key match even if url_hash differs (www / trailing slash)
    fresh2 = row("axios", "AI scoop", "https://axios.com/scoop/", 5, status="fetched")
    assert fresh2["url_hash"] != p["url_hash"]
    carried, rep = sf.carry_forward([p], [fresh2], CATALOG, NOW)
    assert carried == [] and rep["stats"]["refetched"] == 1


def test_duplicate_prior_rows_carried_once_and_dropped_rows_skipped():
    a = row("ft", "AI one", "https://ft.test/one", 3)
    b = dict(a, article_id="CFDUP")
    d = row("ft", "Not relevant", "https://ft.test/pol", 3, status="dropped", drop_reason="policy")
    carried, rep = sf.carry_forward([a, b, d], [], CATALOG, NOW)
    assert [c["article_id"] for c in carried] == [a["article_id"]]
    assert rep["stats"]["skipped_dropped"] == 1


# ---------------------------------------------------------------- catalog removal

def test_outlet_removed_from_catalog_not_carried_and_warns():
    p = row("the_information", "Anthropic AI dinner", "https://ti.test/din", 20, story_id="FFD17FFE")
    old = row("the_information", "AI old", "https://ti.test/old", 60, story_id="OLD")
    carried, rep = sf.carry_forward([p, old], [], CATALOG - {"the_information"}, NOW)
    assert carried == []
    assert len(rep["in_window_losses"]) == 1
    w = rep["in_window_losses"][0]
    assert w["reason"] == "outlet_not_in_catalog" and w["article_id"] == p["article_id"]
    assert rep["story_member_losses"] == [
        {"story_id": "FFD17FFE", "lost_member_keys": [f"the_information|{p['canonical_url']}"]}]


# ---------------------------------------------------------------- end to end (seed main, no network)

def _rss(items: list[tuple[str, str, datetime]]) -> bytes:
    body = "".join(
        f"<item><title>{t}</title><link>{u}</link><pubDate>{format_datetime(d)}</pubDate>"
        f"<description>{t}</description></item>" for t, u, d in items)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{body}</channel></rss>'.encode()


def _run_seed(tmp: Path, feeds: dict[str, bytes], monkey_now: datetime):
    """Run sf.main(out_dir=tmp) with resolve_outlet stubbed; other outlets fail."""
    orig_resolve, orig_now, orig_cutoff = sf.resolve_outlet, sf.NOW, sf.CUTOFF

    def fake_resolve(outlet):
        oid = outlet["outlet_id"]
        if oid in feeds:
            parsed = feedparser.parse(feeds[oid])
            return {"outlet_id": oid, "feed_url": f"https://feed.test/{oid}", "http_status": 200,
                    "content_type": "application/rss+xml", "ok": True, "error": None,
                    "item_count": len(parsed.entries), "parsed": parsed, "tried": []}
        return {"outlet_id": oid, "feed_url": None, "http_status": None, "content_type": None,
                "ok": False, "error": "test_offline", "item_count": 0, "parsed": None, "tried": []}

    sf.resolve_outlet = fake_resolve
    sf.NOW, sf.CUTOFF = monkey_now, monkey_now - timedelta(hours=72)
    try:
        summary = sf.main(out_dir=tmp, write_catalog=False)
    finally:
        sf.resolve_outlet, sf.NOW, sf.CUTOFF = orig_resolve, orig_now, orig_cutoff
    rows = [json.loads(l) for l in (tmp / "articles.jsonl").read_text().splitlines() if l.strip()]
    return summary, rows


def test_latest_10_feed_keeps_older_in_window_items_via_carry():
    now = NOW
    items = [(f"AI policy item {i}", f"https://www.washingtonexaminer.com/ai/{i}",
              now - timedelta(hours=2 * i + 1)) for i in range(15)]  # 1h..29h old, all in window
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        s1, rows1 = _run_seed(tmp, {"wash_examiner": _rss(items)}, now)
        assert s1["articles_carried_forward"] == 0 and len(rows1) == 15
        ids1 = {r["canonical_url"]: r["article_id"] for r in rows1}
        # next refresh: the feed only returns its latest 10 items
        s2, rows2 = _run_seed(tmp, {"wash_examiner": _rss(items[:10])}, now + timedelta(minutes=5))
        assert len(rows2) == 15, len(rows2)
        carried = [r for r in rows2 if r.get("carried_forward")]
        assert len(carried) == 5 and s2["articles_carried_forward"] == 5
        assert {r["canonical_url"] for r in carried} == {u for _t, u, _d in items[10:]}
        for r in carried:  # original article_id preserved
            assert r["article_id"] == ids1[r["canonical_url"]]
        # no duplicates by url
        assert len({r["canonical_url"] for r in rows2}) == 15
        # third run 20h later: items older than 48h by ORIGINAL published_at expire
        s3, rows3 = _run_seed(tmp, {"wash_examiner": _rss(items[:10])}, now + timedelta(hours=20))
        kept = {r["canonical_url"] for r in rows3 if r.get("carried_forward")}
        expect = {u for _t, u, dt in items[10:] if (now + timedelta(hours=20) - dt) <= timedelta(hours=48)}
        assert kept == expect, (kept, expect)
        assert s3["carry_forward"]["stats"]["expired"] >= 1


def test_carried_rows_cluster_like_normal_rows():
    """A carried member counts toward outlet_count and members_carried_forward."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = row("axios", "Scoop: Anthropic's Dario Amodei to have White House dinner with Trump",
                "https://www.axios.com/amodei-dinner", 20, status="fetched")
        n = row("nyt", "Dario Amodei of Anthropic to Dine With Trump at White House",
                "https://www.nytimes.com/amodei-dine.html", 13, status="fetched")
        t = row("the_information", "Anthropic's Amodei to Dine With Trump at White House",
                "https://www.theinformation.com/amodei-dine", 17, status="clustered", carried_forward=True)
        with open(tmp / "articles.jsonl", "w") as f:
            for r in (a, n, t):
                f.write(json.dumps(r) + "\n")
        res = cv.main(out_dir=tmp, app_data=None, verbose=False)
        top = [i for i in res["feed"] if len(i["members"]) == 3]
        assert top, [(i["outlet_count"], i["title"]) for i in res["feed"]]
        assert res["summary"]["articles_carried_forward"] == 1
        assert res["summary"]["members_carried_forward"] == 1
        saved = [json.loads(l) for l in (tmp / "articles.jsonl").read_text().splitlines()]
        assert [r for r in saved if r.get("carried_forward")][0]["status"] == "clustered"


def test_clusterer_warns_when_home_member_key_disappears_in_window():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = row("axios", "Scoop: Anthropic's Dario Amodei to have White House dinner with Trump",
                "https://www.axios.com/amodei-dinner", 20, status="fetched")
        n = row("nyt", "Dario Amodei of Anthropic to Dine With Trump at White House",
                "https://www.nytimes.com/amodei-dine.html", 13, status="fetched")
        t = row("the_information", "Anthropic's Amodei to Dine With Trump at White House",
                "https://www.theinformation.com/amodei-dine", 17, status="fetched")

        def write(rows):
            with open(tmp / "articles.jsonl", "w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
        write([a, n, t])
        cv.main(out_dir=tmp, app_data=None, verbose=False)
        write([dict(a, status="fetched"), dict(n, status="fetched")])  # t vanished, still in window
        res = cv.main(out_dir=tmp, app_data=None, verbose=False)
        w = res["summary"]["in_window_member_loss_warnings"]
        assert any(x["was_home"] and cv.member_key(t) in x["lost_member_keys"] for x in w), w


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
