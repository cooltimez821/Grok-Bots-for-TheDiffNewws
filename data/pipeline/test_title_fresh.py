#!/usr/bin/env python3
"""Title/category-from-fresh-members tests for cluster_v0.py (title-fresh fix, 2026-09-29).

Run:  /workspace/news-pipeline/.venv/bin/python debug/test_title_fresh.py
(pytest-compatible too: test_* functions, plain asserts.)
Uses temp dirs only; never touches out/, catalog/, feeds/ or the app mirrors.

Rule under test: the feed item's title and primary_category are computed from
the fresh (<=48h, unique-by-outlet) members with the SAME rules as before
(best trust tier -> earliest published_at -> article_id; assign_category
unchanged). Only the input set changed. Members/story_id are unaffected;
stories.jsonl keeps the all-member title/category.
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

NOW = datetime.now(timezone.utc).replace(microsecond=0)
OUTLETS = {o["outlet_id"]: o for o in json.loads(cv.CATALOG.read_text())["outlets"]}
_seq = [0]

AXIOS_T = "Scoop: Anthropic's Dario Amodei to have White House dinner with Trump"
FT_T = "Trump hosts Anthropic boss Dario Amodei at White House dinner"
NYT_T = "Dario Amodei of Anthropic to Dine With Trump at White House"
WEX_T = "Trump to have dinner with Anthropic CEO Dario Amodei at White House: Report"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def row(outlet: str, title: str, url: str, hours_ago: float, now: datetime = NOW, **extra) -> dict:
    _seq[0] += 1
    r = {
        "article_id": f"TF{_seq[0]:024d}",
        "outlet_id": outlet,
        "canonical_url": url,
        "url_hash": hashlib.sha256(url.encode()).hexdigest(),
        "title": title,
        "dek": None,
        "authors": [],
        "language": "en",
        "published_at": _iso(now - timedelta(hours=hours_ago)),
        "ingested_at": _iso(now - timedelta(hours=max(hours_ago - 0.1, 0))),
        "content_hash": hashlib.sha256((title + url).encode()).hexdigest(),
        "status": "fetched",
        "raw_ref": "test",
    }
    r.update(extra)
    return r


def old_rule_title(members: list) -> str:
    """Verbatim copy of the pre-fix selection (applied to ALL members)."""
    def title_key(m):
        return (cv.trust_rank(OUTLETS.get(m["outlet_id"], {})), m["published_at"], m["article_id"])
    best_tier = cv.trust_rank(OUTLETS.get(sorted(members, key=title_key)[0]["outlet_id"], {}))
    same_tier = [m for m in members if cv.trust_rank(OUTLETS.get(m["outlet_id"], {})) == best_tier]
    return sorted(same_tier, key=lambda m: (m["published_at"], m["article_id"]))[0]["title"]


def run(rows: list) -> tuple[dict, Path, tempfile.TemporaryDirectory]:
    d = tempfile.TemporaryDirectory()
    tmp = Path(d.name)
    with open(tmp / "articles.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    res = cv.main(out_dir=tmp, app_data=None, verbose=False)
    return res, tmp, d


def _single_story(res: dict) -> tuple[dict, dict]:
    assert len(res["stories"]) == 1, [s["title"] for s in res["stories"]]
    assert len(res["feed"]) == 1, (len(res["feed"]), len(res["held"]))
    return res["stories"][0], res["feed"][0]


def _expired_case(axios_title: str = AXIOS_T):
    # Live FFD17FFE shape (Amodei White House dinner): axios scoop ~49h old,
    # the others 4-12h later and still inside the 48h window.
    ax = row("axios", axios_title, "https://www.axios.com/amodei-dinner", 49)   # expired
    wx = row("wash_examiner", WEX_T, "https://www.washingtonexaminer.com/amodei-dinner", 45)
    ny = row("nyt", NYT_T, "https://www.nytimes.com/amodei-dine.html", 42)
    ft = row("ft", FT_T, "https://www.ft.com/amodei-dinner", 37)
    return [ax, ft, ny, wx]


# ---------------------------------------------------------------- (a) expired headline member

def test_expired_headline_member_not_used():
    rows = _expired_case()
    res, _tmp, d = run(rows)
    with d:
        story, item = _single_story(res)
        assert old_rule_title(rows) == AXIOS_T          # old rule would pick the expired axios row
        assert story["title"] == AXIOS_T                # stories.jsonl keeps all-member pick
        assert item["title"] != AXIOS_T, item["title"]
        member_titles = {m["title"] for m in item["members"]}
        assert AXIOS_T not in member_titles
        assert item["title"] in member_titles
        assert item["title"] == FT_T                    # center non-provisional tier among fresh
        assert item["title"] == old_rule_title(rows[1:])  # same rule, fresh input set


def test_tie_breaks_same_rule_on_fresh_set():
    # Two fresh center tier-0 outlets: earliest published_at wins, like before.
    rows = _expired_case()
    rows.append(row("bbc", "Anthropic's Dario Amodei dines with Trump at White House",
                    "https://www.bbc.com/amodei-dinner", 44))
    res, _tmp, d = run(rows)
    with d:
        _story, item = _single_story(res)
        fresh = [r for r in rows if r["outlet_id"] != "axios"]
        assert item["title"] == old_rule_title(fresh) == rows[-1]["title"], item["title"]


# ---------------------------------------------------------------- (b) all fresh: unchanged

def test_all_fresh_title_unchanged_vs_old_rule():
    rows = _expired_case()
    rows[0] = dict(rows[0], published_at=_iso(NOW - timedelta(hours=46)),
                   ingested_at=_iso(NOW - timedelta(hours=45.9)))
    res, _tmp, d = run(rows)
    with d:
        story, item = _single_story(res)
        assert item["title"] == story["title"] == old_rule_title(rows) == AXIOS_T
        assert item["primary_category"] == story["primary_category"]
        assert item["primary_category"] == cv.assign_category(rows, OUTLETS)


def test_pick_title_member_matches_old_rule():
    rows = _expired_case()
    for subset in (rows, rows[1:], rows[2:], rows[:2]):
        assert cv.pick_title_member(subset, OUTLETS)["title"] == old_rule_title(subset)


# ---------------------------------------------------------------- (c) category from fresh

def test_category_recomputed_from_fresh_members():
    # The expired member alone carries "filing" -> source_code over ALL members;
    # fresh members alone are ordinary same-event coverage -> weight_and_bias.
    rows = _expired_case(AXIOS_T + ", filing shows")
    assert cv.assign_category(rows, OUTLETS) == "source_code"
    assert cv.assign_category(rows[1:], OUTLETS) == "weight_and_bias"
    res, _tmp, d = run(rows)
    with d:
        story, item = _single_story(res)
        assert story["primary_category"] == "source_code"      # stories.jsonl: all members
        assert item["primary_category"] == "weight_and_bias"   # feed item: fresh members
        fresh_arts = [r for r in rows if r["outlet_id"] != "axios"]
        assert item["primary_category"] == cv.assign_category(fresh_arts, OUTLETS)


# ---------------------------------------------------------------- (d) members / story_id unaffected

def test_members_and_story_id_unaffected():
    rows = _expired_case()
    res, tmp, d = run(rows)
    with d:
        story, item = _single_story(res)
        sid = story["story_id"]
        assert item["story_id"] == sid
        # feed members = fresh members (48h trim), unchanged by the fix
        assert sorted(m["outlet_id"] for m in item["members"]) == ["ft", "nyt", "wash_examiner"]
        assert item["outlet_count"] == 3 and item["article_count"] == 3
        # story-level membership (story_members + id map) still includes the expired row
        sm = [json.loads(l) for l in (tmp / "story_members.jsonl").read_text().splitlines()]
        assert sorted(x["article_id"] for x in sm) == sorted(r["article_id"] for r in rows)
        assert {x["story_id"] for x in sm} == {sid}
        idmap = json.loads((tmp / cv.STORY_ID_MAP_NAME).read_text())["stories"]
        assert list(idmap) == [sid]
        assert idmap[sid]["members"] == sorted(cv.member_key(r) for r in rows)
        # bias band / blindspot computed from the same fresh members as before
        uniq = [r for r in rows if r["outlet_id"] != "axios"]
        assert item["labels"]["bias_band"] == cv.compute_bias_band(uniq, OUTLETS)
        assert item["labels"]["blindspot"] == cv.compute_blindspot(uniq, OUTLETS, story["primary_category"])
        # re-run on the same dir: story_id reused, title stays fresh
        res2 = cv.main(out_dir=tmp, app_data=None, verbose=False)
        assert [s["story_id"] for s in res2["stories"]] == [sid]
        assert res2["feed"][0]["title"] == FT_T


def test_aged_out_held_keeps_story_title():
    rows = [row("axios", AXIOS_T, "https://www.axios.com/amodei-dinner", 60),
            row("nyt", NYT_T, "https://www.nytimes.com/amodei-dine.html", 55)]
    res, _tmp, d = run(rows)
    with d:
        assert res["feed"] == []
        held = [h for h in res["held"] if h.get("hold_reason") == "aged_out"]
        assert len(held) == 1 and held[0]["title"] == res["stories"][0]["title"] == AXIOS_T


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
