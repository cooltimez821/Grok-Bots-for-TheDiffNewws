#!/usr/bin/env python3
"""TheDiffNews seed: resolve/verify RSS, fetch AI-related items from Bias v1 catalog."""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from xml.etree import ElementTree as ET

import feedparser
import requests

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from cluster_v0 import member_key as _cluster_member_key  # noqa: E402  (same key the clusterer uses)

ROOT = Path("/workspace/news-pipeline")
CATALOG_PATH = ROOT / "catalog" / "v1-outlets.json"
STATUS_PATH = ROOT / "feeds" / "status.json"
ARTICLES_PATH = ROOT / "out" / "articles.jsonl"
SUMMARY_PATH = ROOT / "out" / "seed-summary.json"
RAW_DIR = ROOT / "feeds" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

UA = "TheDiffNews-SeedBot/0.1 (+research; polite; contact:data@thediff.news)"
TIMEOUT = 12
SLEEP = 0.35
NOW = datetime.now(timezone.utc)
CUTOFF = NOW - timedelta(hours=72)
# Carry-forward: in-window articles that a "latest N items" feed no longer returns
# are kept from the previous articles.jsonl until 48h after their ORIGINAL
# published_at (same window as cluster_v0.HOME_FRESHNESS_HOURS). Never re-dated.
CARRY_FORWARD_HOURS = 48

# Prefer AI/tech topic feeds first; then general official feeds.
CANDIDATES: dict[str, list[str]] = {
    "reuters": [
        "https://www.reuters.com/arc/outboundfeeds/rss/category/technology/?outputType=xml",
        "https://www.reuters.com/arc/outboundfeeds/rss/?outputType=xml",
        "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
        "https://www.reutersagency.com/feed/",
        "https://www.reuters.com/technology/rss",
        "https://www.reuters.com/rss",
        "https://www.reuters.com/feed",
    ],
    "ap": [
        "https://apnews.com/index.rss",
        "https://apnews.com/hub/technology.rss",
        "https://apnews.com/rss",
        "https://rss.ap.org/",
        "https://www.apnews.com/index.rss",
        "https://www.apnews.com/rss",
    ],
    "bbc": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://feeds.bbci.co.uk/news/rss.xml",
    ],
    "bloomberg": [
        "https://feeds.bloomberg.com/technology/news.rss",
        "https://feeds.bloomberg.com/markets/news.rss",
    ],
    "ft": [
        "https://www.ft.com/artificial-intelligence?format=rss",
        "https://www.ft.com/technology?format=rss",
        "https://www.ft.com/rss/home",
    ],
    "economist": [
        "https://www.economist.com/science-and-technology/rss.xml",
        "https://www.economist.com/business/rss.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
    ],
    "axios": [
        "https://api.axios.com/feed/",
        "https://www.axios.com/feeds/feed.rss",
    ],
    "semafor": [
        "https://www.semafor.com/rss.xml",
    ],
    "techcrunch": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://techcrunch.com/feed/",
    ],
    "ars_technica": [
        "https://arstechnica.com/ai/feed/",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://arstechnica.com/feed/",
    ],
    "mit_tr": [
        "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "https://www.technologyreview.com/feed/ai/rss/",
        "https://www.technologyreview.com/feed/",
    ],
    "ieee_spectrum": [
        "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss",
        "https://spectrum.ieee.org/feeds/feed.rss",
        "https://spectrum.ieee.org/rss/fulltext",
    ],
    "nature": [
        "https://www.nature.com/subjects/machine-learning.rss",
        "https://www.nature.com/subjects/artificial-intelligence.rss",
        "https://www.nature.com/nature.rss",
    ],
    "science": [
        "https://www.science.org/rss/news_current.xml",
        "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
    ],
    "cnbc": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=2000&keyword=artificial%20intelligence",
        "https://www.cnbc.com/id/19854910/device/rss/rss.html",
    ],
    "forbes": [
        "https://www.forbes.com/innovation/ai/feed/",
        "https://www.forbes.com/innovation/feed",
        "https://www.forbes.com/digital-assets/feed/",
    ],
    "venturebeat": [
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://venturebeat.com/category/ai/feed/",
        "https://venturebeat.com/feed/",
        "https://www.venturebeat.com/feed/",
    ],
    "rest_of_world": [
        "https://restofworld.org/feed/",
        "https://restofworld.org/feed/latest/",
    ],
    "the_information": [
        "https://www.theinformation.com/feed",
        "https://www.theinformation.com/rss",
    ],
    "the_verge": [
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://www.theverge.com/rss/index.xml",
    ],
    "wired": [
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://www.wired.com/feed/category/business/latest/rss",
        "https://www.wired.com/feed/rss",
    ],
    "nyt": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    ],
    "wapo": [
        "https://feeds.washingtonpost.com/rss/business/technology",
        "https://feeds.washingtonpost.com/rss/business",
    ],
    "guardian": [
        "https://www.theguardian.com/technology/artificialintelligenceai/rss",
        "https://www.theguardian.com/technology/rss",
        "https://www.theguardian.com/uk/technology/rss",
    ],
    "cnn": [
        "http://rss.cnn.com/rss/cnn_tech.rss",
        "http://rss.cnn.com/rss/edition_technology.rss",
        "http://rss.cnn.com/rss/cnn_topstories.rss",
    ],
    "nbc": [
        "https://feeds.nbcnews.com/nbcnews/public/tech",
        "https://feeds.nbcnews.com/nbcnews/public/news",
    ],
    "404_media": [
        "https://www.404media.co/tag/ai/rss/",
        "https://www.404media.co/tag/ai/feed/",
        "https://www.404media.co/feed/",
        "https://www.404media.co/rss",
    ],
    "platformer": [
        "https://www.platformer.news/feed",
        "https://www.platformer.news/feed/",
        "https://platformer.news/feed",
    ],
    "intercept": [
        "https://theintercept.com/technology/feed/",
        "https://theintercept.com/feed/?rss",
        "https://www.theintercept.com/feed/?rss",
    ],
    "mother_jones": [
        "https://www.motherjones.com/topics/technology/feed/",
        "https://www.motherjones.com/feed/",
    ],
    "wsj": [
        "https://feeds.a.dj.com/rss/RSSWSJD.xml",
        "https://feeds.content.dowjones.io/public/rss/RSSWSJD",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    ],
    "nypost": [
        "https://nypost.com/tag/artificial-intelligence/feed/",
        "https://nypost.com/tech/feed/",
        "https://nypost.com/feed/",
        "https://www.nypost.com/tech/feed/",
    ],
    "wash_examiner": [
        "https://www.washingtonexaminer.com/tag/artificial-intelligence/feed/",
        "https://www.washingtonexaminer.com/tag/technology/feed/",
        "https://www.washingtonexaminer.com/policy/technology/feed",
        "https://www.washingtonexaminer.com/news/feed/",
        "https://www.washingtonexaminer.com/feed/",
    ],
    "dispatch": [
        "https://thedispatch.com/tag/technology/feed/",
        "https://www.thedispatch.com/tag/technology/feed/",
        "https://www.thedispatch.com/feed/",
        "https://thedispatch.com/feed/",
    ],
    "fox_news": [
        "https://moxie.foxnews.com/google-publisher/tech.xml",
        "https://moxie.foxnews.com/google-publisher/latest.xml",
    ],
    "national_review": [
        "https://www.nationalreview.com/tag/artificial-intelligence/feed/",
        "https://www.nationalreview.com/tag/technology/feed/",
        "https://www.nationalreview.com/feed/",
        "https://www.nationalreview.com/corner/feed/",
        "https://www.nationalreview.com/news/feed/",
    ],
}

GENERIC_PATHS = ["/rss", "/feed", "/index.xml", "/rss.xml", "/atom.xml", "/feeds/posts/default"]

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "sref", "ncid", "sr_share",
    "smid", "smtyp", "ito", "CMP", "cmp", "icid", "ocid", "ns_mchannel", "ns_source",
}

AI_PATTERNS = re.compile(
    r"\b("
    r"ai|a\.i\.|artificial intelligence|machine learning|\bml\b|llm|llms|"
    r"large language model|generative ai|genai|chatgpt|gpt-?\d|openai|anthropic|"
    r"claude|gemini|deepmind|google deepmind|meta ai|xai|grok|"
    r"nvidia ai|midjourney|stable diffusion|diffusion model|"
    r"foundation model|transformer model|neural net|deep learning|"
    r"copilot|bard|sora|perplexity|mistral|cohere|"
    r"artificial[- ]general intelligence|\bagi\b"
    r")\b",
    re.I,
)

NON_ARTICLE_HINTS = re.compile(
    r"(podcast|video:|watch:|live blog|liveblog|newsletter signup|crossword|horoscope|"
    r"cartoon|obituary photo|sponsored|advertisement|web story)",
    re.I,
)


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#39;|&apos;", "'", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def canonical_url(url: str) -> str:
    if not url:
        return ""
    p = urlparse(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
    # drop fragment
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(q, doseq=True), ""))


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def make_ulid_like() -> str:
    # Crockford-ish: time prefix + uuid entropy
    ts = int(NOW.timestamp() * 1000)
    return f"{ts:011X}"[:10] + uuid.uuid4().hex[:16].upper()


def looks_like_feed(body: bytes) -> bool:
    head = body[:8000].lower()
    return any(tok in head for tok in (b"<rss", b"<feed", b"<rdf:rdf")) and (
        b"<item" in head or b"<entry" in head or b"<channel" in head or b"<feed" in head
    )


def parse_published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
        try:
            # ISO-ish
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return None


def fetch_url(url: str) -> tuple[int | None, str | None, bytes, str | None]:
    try:
        r = requests.get(
            url,
            headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        return r.status_code, r.headers.get("Content-Type"), r.content, None
    except requests.RequestException as e:
        return None, None, b"", str(e)


def verify_feed(url: str) -> dict:
    status, ctype, body, err = fetch_url(url)
    result = {
        "feed_url": url,
        "http_status": status,
        "content_type": ctype,
        "ok": False,
        "error": err,
        "item_count": 0,
        "body": body,
    }
    if err:
        return result
    if status is None:
        result["error"] = "no_response"
        return result
    if status >= 400:
        result["error"] = f"http_{status}"
        return result
    if not looks_like_feed(body):
        # sometimes HTML with feed markers stripped; try feedparser anyway
        parsed = feedparser.parse(body)
        if not parsed.entries and not getattr(parsed, "version", None):
            result["error"] = "not_rss_or_atom"
            return result
    parsed = feedparser.parse(body)
    n = len(parsed.entries or [])
    result["item_count"] = n
    result["ok"] = True
    result["parsed"] = parsed
    if n == 0:
        result["error"] = "empty_feed"
        # still structurally ok; caller may reject empty
    return result


def fallback_paths(homepage: str) -> list[str]:
    base = homepage.rstrip("/")
    return [base + p for p in GENERIC_PATHS]


def resolve_outlet(outlet: dict) -> dict:
    oid = outlet["outlet_id"]
    tried = []
    candidates = list(CANDIDATES.get(oid, []))
    # Prefer already-verified catalog feed_url when present
    cur = outlet.get("feed_url")
    if cur and cur not in candidates:
        candidates.insert(0, cur)
    elif cur and cur in candidates:
        candidates.remove(cur)
        candidates.insert(0, cur)
    for u in fallback_paths(outlet["homepage_url"]):
        if u not in candidates:
            candidates.append(u)

    best_empty = None
    last_fail = None
    for url in candidates:
        time.sleep(SLEEP)
        tried.append(url)
        v = verify_feed(url)
        print(f"  try {oid}: {url} -> status={v['http_status']} ok={v['ok']} items={v['item_count']} err={v.get('error')}")
        if v["ok"] and v["item_count"] > 0:
            # save raw
            (RAW_DIR / f"{oid}.xml").write_bytes(v["body"])
            return {
                "outlet_id": oid,
                "feed_url": v["feed_url"],
                "http_status": v["http_status"],
                "content_type": v["content_type"],
                "ok": True,
                "error": None,
                "item_count": v["item_count"],
                "parsed": v["parsed"],
                "tried": tried,
            }
        if v["ok"] and v["item_count"] == 0:
            best_empty = v
            last_fail = "empty_feed"
            continue
        last_fail = v.get("error") or f"http_{v.get('http_status')}"
        # soft fail continue

    if best_empty:
        (RAW_DIR / f"{oid}.xml").write_bytes(best_empty["body"])
        return {
            "outlet_id": oid,
            "feed_url": best_empty["feed_url"],
            "http_status": best_empty["http_status"],
            "content_type": best_empty["content_type"],
            "ok": True,
            "error": "empty_feed",
            "item_count": 0,
            "parsed": feedparser.parse(best_empty["body"]),
            "tried": tried,
        }

    return {
        "outlet_id": oid,
        "feed_url": None,
        "http_status": None,
        "content_type": None,
        "ok": False,
        "error": last_fail or "no_official_feed_found",
        "item_count": 0,
        "parsed": None,
        "tried": tried,
    }


def entry_authors(entry) -> list[str]:
    authors = []
    if entry.get("author"):
        authors.append(strip_html(entry.get("author")))
    for a in entry.get("authors") or []:
        name = a.get("name") if isinstance(a, dict) else str(a)
        if name:
            authors.append(strip_html(name))
    # dedupe preserve order
    seen = set()
    out = []
    for a in authors:
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def entry_link(entry) -> str:
    link = entry.get("link") or ""
    if not link:
        for l in entry.get("links") or []:
            if l.get("rel") in (None, "alternate") and l.get("href"):
                link = l["href"]
                break
    return link


def is_ai_related(title: str, dek: str) -> bool:
    return bool(AI_PATTERNS.search(f"{title} {dek}"))


def is_non_article(title: str, dek: str, url: str) -> bool:
    blob = f"{title} {dek} {url}"
    if NON_ARTICLE_HINTS.search(blob):
        return True
    # video-only paths
    path = urlparse(url).path.lower()
    if any(x in path for x in ("/video/", "/videos/", "/watch/", "/live/", "/gallery/", "/podcast/")):
        return True
    return False


def process_entries(outlet: dict, feed_url: str, parsed) -> list[dict]:
    articles = []
    entries = list(parsed.entries or [])
    dated = []
    undated = []
    for e in entries:
        pub = parse_published(e)
        if pub:
            dated.append((e, pub))
        else:
            undated.append((e, None))

    if dated:
        # Dates exist: last 72 hours only (no silent fallback to older items).
        selected = [(e, p) for e, p in dated if p >= CUTOFF]
    else:
        selected = undated[:30]

    ingested = NOW.isoformat().replace("+00:00", "Z")
    for e, pub in selected:
        title = strip_html(e.get("title") or "")
        dek = strip_html(e.get("summary") or e.get("description") or "")
        # feedparser may put content in content[]
        if not dek and e.get("content"):
            try:
                dek = strip_html(e["content"][0].get("value") or "")
            except Exception:
                pass
        # truncate dek
        if len(dek) > 2000:
            dek = dek[:2000].rstrip() + "…"

        url = entry_link(e)
        canon = canonical_url(url)
        authors = entry_authors(e)
        lang = outlet.get("language") or "en"
        pub_iso = pub.isoformat().replace("+00:00", "Z") if pub else None

        drop_reason = None
        status = "fetched"
        if not canon or not title:
            status = "dropped"
            drop_reason = "non_article"
        elif is_non_article(title, dek, canon):
            status = "dropped"
            drop_reason = "non_article"
        elif not is_ai_related(title, dek):
            status = "dropped"
            drop_reason = "policy"  # AI-topic filter

        content_hash = sha256_hex((title.strip().lower() + "\n" + dek.strip().lower()))
        art = {
            "article_id": make_ulid_like(),
            "outlet_id": outlet["outlet_id"],
            "canonical_url": canon,
            "url_hash": sha256_hex(canon) if canon else sha256_hex(""),
            "title": title,
            "dek": dek or None,
            "authors": authors,
            "language": lang,
            "published_at": pub_iso,
            "ingested_at": ingested,
            "content_hash": content_hash,
            "status": status,
            "raw_ref": feed_url,
        }
        if drop_reason:
            art["drop_reason"] = drop_reason
        # Do NOT set story_id; do NOT copy bias_band
        articles.append(art)
    return articles


# ---------------------------------------------------------------------------
# Carry-forward (feeds that only return their latest N items)
# ---------------------------------------------------------------------------

def _parse_iso_utc(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def carry_member_key(a: dict) -> str:
    """outlet_id + normalized canonical_url (identical to cluster_v0.member_key)."""
    return _cluster_member_key(a)


def load_prior_articles(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return rows


def carry_forward(
    prior_rows: list[dict],
    fetched_rows: list[dict],
    catalog_outlet_ids: set[str],
    now: datetime,
    window_hours: float = CARRY_FORWARD_HOURS,
) -> tuple[list[dict], dict]:
    """Return (carried_rows, report).

    A prior row is carried iff
      * neither its url_hash nor its member key (outlet_id|normalized canonical_url)
        is in the current fetch,
      * it was not dropped (policy/non_article) last run,
      * its ORIGINAL published_at is within ``window_hours`` of ``now``
        (a carried row keeps its original published_at, so it expires on the
        original clock and can never be re-carried after that), and
      * its outlet is still in the catalog.
    Carried rows keep article_id, URL and every field; carried_forward=True.
    In-window prior rows that are neither fetched nor carried are reported as
    warnings (``in_window_losses``), grouped per prior story_id in
    ``story_member_losses``.
    """
    fetched_hashes = {a.get("url_hash") for a in fetched_rows if a.get("url_hash")}
    fetched_keys = {carry_member_key(a) for a in fetched_rows}
    window_s = float(window_hours) * 3600.0

    carried: list[dict] = []
    seen_keys: set[str] = set()
    losses: list[dict] = []
    stats = {"prior_rows": len(prior_rows), "refetched": 0, "expired": 0,
             "skipped_dropped": 0, "skipped_duplicate": 0, "carried": 0,
             "carried_again": 0, "lost_in_window": 0}

    for row in prior_rows:
        key = carry_member_key(row)
        if row.get("url_hash") in fetched_hashes or key in fetched_keys:
            stats["refetched"] += 1
            continue
        if row.get("status") == "dropped":
            stats["skipped_dropped"] += 1
            continue
        pub = _parse_iso_utc(row.get("published_at"))
        age_s = (now - pub).total_seconds() if pub else None
        if age_s is None or age_s > window_s:
            stats["expired"] += 1
            continue
        if key in seen_keys:
            stats["skipped_duplicate"] += 1
            continue
        if row.get("outlet_id") not in catalog_outlet_ids:
            losses.append({
                "article_id": row.get("article_id"),
                "outlet_id": row.get("outlet_id"),
                "title": row.get("title"),
                "canonical_url": row.get("canonical_url"),
                "published_at": row.get("published_at"),
                "prior_story_id": row.get("story_id"),
                "reason": "outlet_not_in_catalog",
            })
            continue
        seen_keys.add(key)
        c = dict(row)
        if c.get("carried_forward"):
            stats["carried_again"] += 1
        c["carried_forward"] = True
        carried.append(c)

    stats["carried"] = len(carried)
    stats["lost_in_window"] = len(losses)
    story_losses: dict[str, list[str]] = {}
    for l in losses:
        if l.get("prior_story_id"):
            story_losses.setdefault(l["prior_story_id"], []).append(
                f"{l['outlet_id']}|{l.get('canonical_url') or ''}")
    report = {
        "window_hours": window_hours,
        "rule": "carry prior in-window rows missing from the current fetch; expiry = original published_at + 48h; outlet must still be in catalog",
        "stats": stats,
        "carried_article_ids": [c.get("article_id") for c in carried],
        "in_window_losses": losses,
        "story_member_losses": [
            {"story_id": sid, "lost_member_keys": sorted(keys)}
            for sid, keys in sorted(story_losses.items())
        ],
    }
    return carried, report


def main(out_dir: Path | None = None, write_catalog: bool = True):
    """out_dir: where articles.jsonl / seed-summary.json are read+written
    (default out/). write_catalog=False skips rewriting catalog + feeds/status.json
    (dry runs)."""
    articles_path = (Path(out_dir) / "articles.jsonl") if out_dir else ARTICLES_PATH
    summary_path = (Path(out_dir) / "seed-summary.json") if out_dir else SUMMARY_PATH
    catalog = json.loads(CATALOG_PATH.read_text())
    outlets = catalog["outlets"]
    assert len(outlets) == 36, f"expected 36 outlets, got {len(outlets)}"

    status_rows = []
    all_articles = []
    feeds_ok = 0
    feeds_failed = []

    for outlet in outlets:
        oid = outlet["outlet_id"]
        print(f"== {oid} ==")
        res = resolve_outlet(outlet)
        row = {
            "outlet_id": oid,
            "feed_url": res["feed_url"],
            "http_status": res["http_status"],
            "content_type": res["content_type"],
            "ok": bool(res["ok"] and res["feed_url"] and res.get("item_count", 0) >= 0 and res["ok"]),
            "error": res.get("error"),
            "item_count": res.get("item_count") or 0,
        }
        # Treat structurally valid empty as ok=True with error empty_feed; failed if no feed_url
        if res["feed_url"] and res["ok"]:
            outlet["feed_url"] = res["feed_url"]
            # Also set feed_status field? catalog contract only has feed_url; use null on fail
            feeds_ok += 1
            if res.get("parsed") is not None and res["item_count"] > 0:
                arts = process_entries(outlet, res["feed_url"], res["parsed"])
                all_articles.extend(arts)
            elif res["item_count"] == 0:
                row["error"] = row["error"] or "empty_feed"
        else:
            outlet["feed_url"] = None
            outlet["feed_status"] = "failed"
            outlet["feed_fail_reason"] = res.get("error") or "no_official_feed_found"
            row["ok"] = False
            row["error"] = outlet["feed_fail_reason"]
            feeds_failed.append({"outlet_id": oid, "reason": row["error"]})
            feeds_ok -= 0  # no-op clarity
            # adjust: feeds_ok should not count failed
            # we incremented only on success branch
        # Fix feeds_ok counting: only success branch increments — but empty still counts as ok
        if not (res["feed_url"] and res["ok"]):
            pass
        else:
            # already incremented
            pass

        # Recalculate ok for status: working feed means we verified RSS/Atom
        if res["feed_url"] and res["ok"]:
            row["ok"] = True
        else:
            row["ok"] = False
            if feeds_ok and res.get("feed_url") is None:
                pass

        status_rows.append(row)

    # Recalculate feeds_ok from status_rows to avoid bug
    feeds_ok = sum(1 for r in status_rows if r["ok"])
    feeds_failed = [{"outlet_id": r["outlet_id"], "reason": r["error"]} for r in status_rows if not r["ok"]]

    # Write catalog (strip feed_status helper fields? keep for transparency of failed — contract says feed_url optional.
    # Spec: "set feed_url when verified" and "feed_status=failed with a reason"
    # So feed_status on outlet for failed is OK.
    for o in outlets:
        if o.get("feed_url"):
            o.pop("feed_status", None)
            o.pop("feed_fail_reason", None)
        else:
            o["feed_status"] = "failed"
            if not o.get("feed_fail_reason"):
                # from status
                st = next((r for r in status_rows if r["outlet_id"] == o["outlet_id"]), None)
                o["feed_fail_reason"] = (st or {}).get("error") or "no_official_feed_found"

    catalog["outlets"] = outlets
    catalog["outlet_count_listed"] = len(outlets)
    if write_catalog:
        CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
        STATUS_PATH.write_text(json.dumps({"generated_at": NOW.isoformat().replace("+00:00", "Z"), "feeds": status_rows}, indent=2) + "\n")

    # Carry-forward: load the previous articles.jsonl BEFORE overwriting it.
    prior_rows = load_prior_articles(articles_path)
    carried, carry_report = carry_forward(
        prior_rows, all_articles, {o["outlet_id"] for o in outlets}, NOW
    )
    fetched_count = len(all_articles)
    all_articles.extend(carried)
    for w in carry_report["in_window_losses"]:
        print(f"WARNING in-window loss: {w['outlet_id']} {w['published_at']} {w['reason']} :: {(w.get('title') or '')[:90]}")
    for w in carry_report["story_member_losses"]:
        print(f"WARNING story {w['story_id']} lost in-window members: {w['lost_member_keys']}")

    tmp_articles = articles_path.with_name(articles_path.name + ".tmp")
    with tmp_articles.open("w") as f:
        for a in all_articles:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    tmp_articles.replace(articles_path)

    dropped_reasons: dict[str, int] = {}
    ai_kept = 0
    for a in all_articles[:fetched_count]:
        if a["status"] == "fetched":
            ai_kept += 1
        else:
            reason = a.get("drop_reason") or "unknown"
            dropped_reasons[reason] = dropped_reasons.get(reason, 0) + 1

    summary = {
        "outlets_total": len(outlets),
        "feeds_ok": feeds_ok,
        "feeds_failed": feeds_failed,
        "articles_fetched": fetched_count,
        "articles_ai_kept": ai_kept,
        "articles_carried_forward": len(carried),
        "carry_forward": carry_report,
        "articles_dropped_by_reason": dropped_reasons,
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "paths": {
            "catalog": str(CATALOG_PATH),
            "status": str(STATUS_PATH),
            "articles": str(articles_path),
            "summary": str(summary_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
