#!/usr/bin/env python3
"""TheDiffNews v0 clustering — precision over recall."""
from __future__ import annotations

import json
import re
import hashlib
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/workspace/news-pipeline")
OUT = ROOT / "out"
CATALOG = ROOT / "catalog" / "v1-outlets.json"
HOME_FRESHNESS_HOURS = 48  # Bob freshness: drop home stories with no member update in this window

STOP = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "is", "are", "was", "were", "be", "been", "being", "by", "with", "from",
    "as", "into", "about", "after", "before", "over", "under", "between",
    "this", "that", "these", "those", "it", "its", "their", "his", "her",
    "they", "them", "we", "you", "i", "not", "no", "yes", "vs", "via",
    "how", "what", "why", "when", "where", "who", "which", "whom",
    "can", "could", "would", "should", "may", "might", "will", "shall",
    "has", "have", "had", "do", "does", "did", "doing", "done",
    "new", "says", "say", "said", "amid", "per", "than", "then", "also",
    "just", "more", "most", "some", "any", "all", "out", "up", "down",
    "off", "own", "too", "very", "so", "if", "because", "while", "during",
    "here", "there", "now", "still", "already", "even", "back", "only",
    "our", "your", "my", "me", "he", "she", "him", "us", "again",
    "s", "t", "re", "ve", "ll", "d", "m", "amp",
    # journalism / weak verbs
    "warns", "warn", "warning", "warnings", "blocks", "block", "blocked",
    "blocking", "reveals", "reveal", "revealed", "report", "reports",
    "reported", "reporting", "launch", "launches", "launched", "launching",
    "join", "joins", "joined", "add", "adds", "added", "put", "puts",
    "putting", "face", "faces", "faced", "open", "opens", "opened",
    "call", "calls", "called", "urge", "urges", "urged", "quit", "quits",
    "used", "using", "use", "uses", "make", "makes", "made", "making",
    "try", "tries", "tried", "trying", "build", "builds", "built", "building",
    "take", "takes", "took", "taking", "get", "gets", "got", "give", "gives",
    "gave", "need", "needs", "want", "wants", "ahead", "due", "cite", "cites",
    "cited", "according", "possible", "attempt", "efforts", "effort",
    "scoop", "newsletter", "view", "editorial", "letter", "letters",
    "former", "exec", "potential", "startup", "center", "centre", "giant",
    "voice", "powered", "sen", "led", "again", "sound", "sounds", "staffers", "staffer",
    "doubles", "down", "stance", "frightened", "frightening",
    "stopp", "stop", "stopped", "stopping", "develop", "developing",
    "scientist", "scientists", "potenti", "potentially",
    "misus", "misused", "misuse", "alarm", "model", "models", "being",
}

# phrase → canonical token (applied on lowercase title before split)
PHRASE_NORM = [
    ("hugging face", "hugging_face"),
    ("universal music", "universal_music"),
    ("biological weapons", "biological_weapons"),
    ("bio weapons", "biological_weapons"),
    ("ballistic missiles", "missile"),
    ("guided missiles", "missile"),
    ("guided weapons", "missile"),
    ("data center", " "),
    ("artificial intelligence", "ai"),
    ("a.i.", "ai"),
    ("wall street", "wall_street"),
    ("white house", "white_house"),
    ("new mexico", "new_mexico"),
    ("silicon valley", "silicon_valley"),
]

TOKEN_ALIAS = {
    "bioweapons": "biological_weapons",
    "bioweapon": "biological_weapons",
    "umg": "universal_music",
    "huggingface": "hugging_face",
    "breach": "hack",
    "hacking": "hack",
    "pause": "hold",
    "subscriptions": "subscription",
    "houthis": "houthi",
    "rebels": "houthi",
    "rebel": "houthi",
    "missiles": "missile",
    "missile": "missile",
    "ballistic": "missile",
    "weapons": "weapon",
    "mathematicians": "mathematician",
    "extinction": "extinction",
    "doomsday": "extinction",
    "catastrophe": "extinction",
    "apocalypse": "extinction",
    "uncontrollable": "extinction",
    "investigations": "investigation",
    "investigation": "investigation",
    "investiga": "investigation",  # if stemmed elsewhere
}

LEFT_BANDS = {"left", "lean_left"}
RIGHT_BANDS = {"right", "lean_right"}
CENTER_BANDS = {"center"}
TECH_BEAT_OUTLETS = {"the_verge", "wired", "techcrunch", "ars_technica"}

POLICY_HINTS = re.compile(
    r"\b(congress|senate|house|bill|lawmaker|regulate|regulation|ban|"
    r"investigation|hawley|johnson|trump|sanders|white house|gop|"
    r"democrat|republican|extinction|doomsday|doom|kill switch|"
    r"superintelligent|safeguard|safety bill|recess)\b",
    re.I,
)
# Stricter than POLICY_HINTS: name-drop of Trump alone is not partisan stakes
# (avoids missing_* on market-reaction clusters that mention a politician).
PARTISAN_STAKES = re.compile(
    r"\b(congress|senate|house|bill|lawmaker|regulate|regulation|ban|"
    r"investigation|safeguard|oversight|policy|midterm|white house|gop|"
    r"democrat|republican|safety bill|recess)\b",
    re.I,
)
PRIMARY_DOC_HINTS = re.compile(
    r"\b(paper|filing|study|arxiv|preprint|white.?paper|"
    r"threat intelligence|peer.?reviewed)\b",
    re.I,
)

# --- entity lexicon ---
KNOWN: dict[str, str] = {}

def _add(typ: str, *names: str) -> None:
    for n in names:
        KNOWN[n.lower()] = typ

_add("org",
    "Anthropic", "OpenAI", "Google", "Meta", "Microsoft", "Apple", "Amazon",
    "Oracle", "Nvidia", "NVIDIA", "Salesforce", "Hugging Face", "DeepSeek",
    "Alibaba", "Moonshot", "Moonshot AI", "Cohere", "ElevenLabs",
    "Universal Music", "UMG", "Clearview", "Clearview AI", "Claude", "ChatGPT",
    "Gemini", "Siri", "Astra", "Muse", "Slack", "Figma", "Blackstone",
    "JPMorgan", "Pimco", "PGIM", "Vantage Data Centers", "Nscale", "Dell",
    "Y Combinator", "Sequoia", "Mecka", "Listen Labs", "Pocket FM", "Instinct",
    "Enflame", "Tencent", "Adobe", "Spirit", "Situational Awareness", "Altimeter",
    "Latham & Watkins", "Cabinet Office", "Muslim Brotherhood", "Houthis",
    "GOP", "Democrats", "Republicans", "Z.ai", "ZAI",
)
_add("person",
    "Elon Musk", "Musk", "Jacob Coxon", "Coxon", "Josh Hawley", "Hawley",
    "Bernie Sanders", "Sanders", "Mike Johnson", "Trump", "Donald Trump",
    "Fidji Simo", "Simo", "Garry Tan", "Larry Ellison", "Ellison", "Chesky",
    "Brian Chesky", "Garrison Lovely", "Ruchir Sharma", "Gerstner", "Burnham",
    "Andy Burnham", "Obama", "Barack Obama", "Sam Altman", "Altman",
    "Dario Amodei", "Amodei", "Steve Bannon", "Bannon", "Bessent",
)
_add("place",
    "United States", "United Kingdom", "Britain", "England", "London",
    "Washington", "Beijing", "China", "Iran", "Russia", "Yemen", "Dallas",
    "Hong Kong", "Shanghai", "UAE", "Asia", "Europe", "India", "New Mexico",
    "NYC", "New York", "Hollywood",
)

PHRASES = sorted(KNOWN.keys(), key=len, reverse=True)

ENTITY_ALIAS = {
    "houthi": "houthis",
    "huggingface": "hugging face",
    "moonshot ai": "moonshot",
    "clearview ai": "clearview",
    "mecka ai": "mecka",
    "donald trump": "trump",
    "elon musk": "musk",
    "brian chesky": "chesky",
    "larry ellison": "ellison",
    "josh hawley": "hawley",
    "mike johnson": "mike johnson",
    "fidji simo": "simo",
    "jacob coxon": "coxon",
    "bernie sanders": "sanders",
    "barack obama": "obama",
    "sam altman": "altman",
    "dario amodei": "amodei",
    "steve bannon": "bannon",
    "united kingdom": "uk",
    "britain": "uk",
    "united states": "us",
    "new york": "nyc",
    "umg": "universal music",
    "chinese": "china",
    "iranian": "iran",
    "russian": "russia",
    "zai": "z.ai",
    "z.ai": "z.ai",
}

MONTHS = {
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
}

GENERIC_ENTS = {
    "ai", "tech", "technology", "silicon valley", "big tech", "researchers",
    "researcher", "company", "companies", "startup", "model", "models",
    "agent", "agents", "warning", "report", "congress", "senate", "house",
    "white house", "wall street", "humanity", "humans", "people", "world",
}

# Density event keys — keep Amodei satellites from colliding into one mega-story.
# Classification is TITLE-PRIMARY (dek ignored for routing).
DENSITY_EVENT_KEYS = (
    "amodei_call",
    "trump_reject",
    "china_reject",
    "ai_stocks_fall",
    "openai_ipo",
    "microsoft_caution",
    "zai_fundraise",
    "obama_safeguards",
)

_CATALOG_WIRE_IDS = ("reuters", "ap")  # failed feeds ⇒ catalog ceiling for some blindspots


def event_key(title: str, dek: str | None = None) -> str | None:
    """Return primary density event token, or None.

    dek is accepted for API symmetry but intentionally unused: RSS standfirsts
    often mention adjacent events (China, Trump, pace) and would smash satellites.
    """
    del dek  # title-primary by product lock
    t = (title or "").lower()
    t = (
        t.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("'", "'")
        .replace("'", "'")
        .replace('"', '"')
        .replace('"', '"')
    )

    # --- satellites / distinct events first (most specific) ---
    if re.search(r"\bz\.?\s*ai\b|\bzai\b", t) and re.search(
        r"fund|rais|share|tumble|billion|\$5", t
    ):
        return "zai_fundraise"
    if re.search(r"\bobama\b", t) and re.search(
        r"safeguard|oversight|democrat|plan|policy|dangerous|apocalypse|alarm", t
    ):
        return "obama_safeguards"
    if re.search(r"\b(ipo|go public|going public|ill-advised)\b", t) and re.search(
        r"\b(openai|altman)\b", t
    ):
        if re.search(r"\bnscale\b", t):
            return None
        return "openai_ipo"
    if re.search(r"\bmicrosoft\b", t) and re.search(
        r"caution|people matter|limits|throttl|humanist|joins rivals", t
    ):
        return "microsoft_caution"
    # stocks before trump so "Trump ... as tech stocks slide" stays stocks
    if re.search(r"\b(stock|stocks)\b", t) and re.search(
        r"\b(fall|slide|drop|tumble)\b", t
    ):
        if not re.search(r"\bz\.?\s*ai\b|\bzai\b", t):
            return "ai_stocks_fall"
    if re.search(r"\b(china|beijing)\b", t) and re.search(
        r"fear\s*monger|fearmonger|rebuff|dismiss|reject", t
    ):
        return "china_reject"
    if re.search(r"\btrump\b", t) and re.search(
        r"reject|attack|overreact|guardrail|sick conspiracy|high iq|"
        r"brushes off|push ahead|team says|on them|"
        r"only .{0,50}(regulation|guardrail)",
        t,
    ):
        return "trump_reject"
    # Vance / political pushback on doom warnings (same satellite family as trump_reject)
    if re.search(r"\bvance\b", t) and re.search(
        r"trojan|fires back|doom warning|overreact", t
    ):
        return "trump_reject"

    # --- primary Amodei / industry "pace the frontier" call ---
    slow = (
        r"slow(?:ing|s)?(?:\s+down)?|slowdown|pump the brake|hit the brake|"
        r"too fast|pace the frontier|put (?:the )?brakes|throttle|"
        r"advancing too|going too fast|slow the pace|"
        r"calls? for (?:an )?ai slow|call for slow"
    )
    actors = (
        r"amodei|anthropic|openai|altman|musk|"
        r"ai ceos|ai leaders|ai bosses|ai groups|ai companies|ai honchos|"
        r"ai developers|tech bosses|tech ceos|chief executives"
    )
    if re.search(actors, t) and re.search(slow, t):
        return "amodei_call"
    if re.search(r"pace the frontier|pump the brake", t):
        return "amodei_call"
    if re.search(
        r"unite to warn|raced to build|top ai leaders unite|"
        r"ceos call|ceos demand|ceos say they need to slow|"
        r"publicly agree on slowing",
        t,
    ):
        return "amodei_call"
    return None


def parse_dt(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def make_ulid() -> str:
    t = int(time.time() * 1000)
    h = hashlib.sha256(f"{t}-{time.time_ns()}-{id(t)}".encode()).hexdigest()[:20].upper()
    ts = f"{t:012X}"[-6:]
    return (ts + h)[:26]


def stem_token(w: str) -> str:
    canon = {
        "biological_weapons", "hugging_face", "universal_music",
        "wall_street", "white_house", "new_mexico", "silicon_valley", "ai",
    }
    if w in canon:
        return w
    w = TOKEN_ALIAS.get(w, w)
    if w in canon:
        return w
    for suf in ("ational", "ing", "ers", "er", "tions", "tion", "ments", "ment",
                "ness", "ously", "edly", "ally", "ly", "ies", "ied", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            w = w[: -len(suf)]
            break
    w = TOKEN_ALIAS.get(w, w)
    return w


def tokenize_title(title: str) -> set[str]:
    t = title.lower()
    t = re.sub(r"&(#\d+|[a-z]+);", " ", t)
    for src, dst in PHRASE_NORM:
        t = t.replace(src, f" {dst} ")
    t = re.sub(r"[^\w\s-]", " ", t)
    out: set[str] = set()
    for w in t.split():
        w = w.strip("-_")
        if len(w) < 2 or w in STOP or w in MONTHS:
            continue
        out.add(stem_token(w))
    if "biological_weapons" in out:
        out.discard("weapon")
        out.discard("biological")
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def canon_ent(s: str) -> str:
    return ENTITY_ALIAS.get(s, s)


def extract_entities(title: str, dek: str | None) -> dict:
    text = f"{title}. {dek or ''}"
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    lower = text.lower()
    found: dict[str, str] = {}
    used: list[tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        return any(start < e and end > s for s, e in used)

    for phrase in PHRASES:
        start = 0
        while True:
            idx = lower.find(phrase, start)
            if idx < 0:
                break
            end = idx + len(phrase)
            before_ok = idx == 0 or not lower[idx - 1].isalnum()
            after_ok = end >= len(lower) or not lower[end].isalnum()
            if before_ok and after_ok and not overlaps(idx, end):
                found[phrase] = KNOWN[phrase]
                used.append((idx, end))
            start = idx + 1

    # UK / US as places when present as tokens
    for m in re.finditer(r"\b(UK|US|U\.S\.|U\.K\.)\b", text):
        key = "uk" if "K" in m.group(1).upper() or m.group(1) == "UK" else "us"
        found[key] = "place"

    # rebels ≈ Houthis in this corpus when Anthropic/Yemen/missile context
    if re.search(r"\brebels?\b", lower) and re.search(
        r"\b(anthropic|yemen|houthi|missile|weapon|claude)\b", lower
    ):
        found["houthis"] = "org"

    orgs = {canon_ent(k) for k, v in found.items() if v == "org"}
    people = {canon_ent(k) for k, v in found.items() if v == "person"}
    places = {canon_ent(k) for k, v in found.items() if v == "place"}
    # drop months accidentally
    places -= MONTHS
    people -= MONTHS
    anchors = {e for e in (orgs | people | places) if e not in GENERIC_ENTS and e not in MONTHS}
    return {"all": anchors, "orgs": orgs, "people": people, "places": places}


def primary_org(ents: dict, title: str) -> str | None:
    title_l = title.lower()
    priority = [
        "anthropic", "openai", "google", "meta", "microsoft", "apple",
        "amazon", "oracle", "nvidia", "salesforce", "hugging face",
        "cohere", "moonshot", "deepseek", "alibaba", "elevenlabs",
        "nscale", "universal music", "clearview", "claude", "chatgpt", "muse",
    ]
    for p in priority:
        if p in ents["orgs"] and (p in title_l or p.replace(" ", "") in title_l.replace(" ", "")):
            return p
    title_orgs = [o for o in ents["orgs"] if o in title_l]
    if title_orgs:
        return sorted(title_orgs, key=lambda o: title_l.find(o))[0]
    return None


def has_contradiction(e1: dict, e2: dict, t1: str, t2: str) -> bool:
    o1, o2 = primary_org(e1, t1), primary_org(e2, t2)
    exclusive_pairs = {
        frozenset({"openai", "anthropic"}),
        frozenset({"openai", "meta"}),
        frozenset({"anthropic", "meta"}),
        frozenset({"google", "openai"}),
        frozenset({"apple", "meta"}),
        frozenset({"oracle", "openai"}),
        frozenset({"oracle", "anthropic"}),
    }
    if o1 and o2 and o1 != o2:
        shared = e1["orgs"] & e2["orgs"]
        if frozenset({o1, o2}) in exclusive_pairs:
            return True
        if not shared:
            return True
        if o1 not in shared and o2 not in shared:
            return True

    p1, p2 = e1["places"], e2["places"]
    hard = {"yemen", "iran", "russia", "china", "uae", "uk", "dallas", "new mexico", "india"}
    if p1 and p2 and not (p1 & p2):
        if (p1 & hard) and (p2 & hard):
            return True
    return False


def soft_merge_ok(a, b, ea, eb) -> tuple[bool, dict]:
    ta, tb = tokenize_title(a["title"]), tokenize_title(b["title"])
    jac = jaccard(ta, tb)
    dt_h = abs((parse_dt(a["published_at"]) - parse_dt(b["published_at"])).total_seconds()) / 3600.0
    shared = ea["all"] & eb["all"]
    ka, kb = event_key(a["title"]), event_key(b["title"])
    evidence = {
        "shared_entities": sorted(shared),
        "title_overlap": round(jac, 4),
        "time_delta_hours": round(dt_h, 3),
        "event_keys": [k for k in (ka, kb) if k],
    }
    # Satellite-split: distinct primary event tokens never soft-merge (any Δt)
    if ka and kb and ka != kb:
        return False, evidence
    if has_contradiction(ea, eb, a["title"], b["title"]):
        return False, evidence
    # Same density event (e.g. Amodei cycle) stays ONE home card across the
    # 48h freshness window — 18h was forking Sep-12 vs Sep-13/14 waves.
    if ka and kb and ka == kb:
        if dt_h > float(HOME_FRESHNESS_HOURS):
            return False, evidence
        evidence["shared_entities"] = sorted(set(shared) | {ka})
        evidence["density_event"] = ka
        return True, evidence
    if dt_h > 18.0:
        return False, evidence
    # Strict legacy path (no density event on either side, or only one side keyed)
    if jac < 0.55:
        return False, evidence
    if len(shared) < 1:
        return False, evidence
    return True, evidence


def trust_rank(outlet: dict) -> tuple:
    band = outlet.get("bias_band") or "mixed"
    prov = bool(outlet.get("provisional"))
    if band == "center" and not prov:
        return (0, 0)
    if band == "center":
        return (1, 1 if prov else 0)
    return (2, 1 if prov else 0)


def assign_category(members: list, outlets: dict) -> str:
    titles = " ".join(m["title"] for m in members)
    deks = " ".join((m.get("dek") or "") for m in members)
    blob = titles + " " + deks
    bands = [outlets[m["outlet_id"]]["bias_band"] for m in members if m["outlet_id"] in outlets]
    left = sum(1 for b in bands if b in LEFT_BANDS)
    right = sum(1 for b in bands if b in RIGHT_BANDS)

    primary_outlets = {"nature", "science"}
    if any(m["outlet_id"] in primary_outlets for m in members) and PRIMARY_DOC_HINTS.search(blob):
        return "source_code"
    if re.search(r"\b(arxiv|peer.?reviewed|preprint|filing)\b", blob, re.I):
        return "source_code"

    frame_pos = bool(re.search(
        r"\b(extinction|doom|catastrophe|kill|uncontrollable|disaster|alarm|warn)\b",
        titles, re.I))
    frame_neg = bool(re.search(
        r"\b(psyop|distract|dismiss|blast|overblown|never having to say|"
        r"fear itself|doomspeak|nothing to fear|politic)\b",
        titles, re.I))
    if frame_pos and frame_neg and len(members) >= 2:
        return "parallax"

    angles = 0
    if re.search(r"\b(ipo|revenue|stock|funding|raise|billion|capex|loan|valuation|markets?)\b", blob, re.I):
        angles += 1
    if re.search(r"\b(regulat|congress|law|bill|policy|ban|investigation)\b", blob, re.I):
        angles += 1
    if re.search(r"\b(model|agent|api|open.?weight|distill|cyber|product|app)\b", blob, re.I):
        angles += 1
    if angles >= 2 and left + right == 0:
        return "prism"
    if angles >= 3:
        return "prism"

    if len(members) >= 3 and POLICY_HINTS.search(blob):
        if (left == 0) ^ (right == 0):
            return "blindspot"

    # off_distribution: under-covered / non-mainstream angle — not ordinary same-event clusters
    if len(members) >= 2 and re.search(
        r"\b(rest of world|global south|non-mainstream|under.?covered|obscure)\b",
        blob, re.I,
    ):
        return "off_distribution"

    return "weight_and_bias"


def compute_bias_band(members: list, outlets: dict) -> str:
    bands = [outlets[m["outlet_id"]]["bias_band"] for m in members if m["outlet_id"] in outlets]
    if not bands:
        return "mixed"
    c = Counter(bands)
    top, n = c.most_common(1)[0]
    if n > len(bands) / 2:
        return top
    return "mixed"



def parse_utc(ts: str) -> datetime:
    if not ts:
        return datetime.min.replace(tzinfo=timezone.utc)
    ts = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_fresh(ts: str, now: datetime, hours: float = HOME_FRESHNESS_HOURS) -> bool:
    return (now - parse_utc(ts)).total_seconds() <= hours * 3600

def compute_blindspot(members: list, outlets: dict, category: str) -> dict:
    """Positive finding only. Default absent: {present:false, rule_id:null}.

    Product locks:
    - missing_left/right: ≥3 members AND ≥2 on present side + partisan stakes
    - no_primary_source / geo_thin: quiet on skeleton pairs (outlet_count < 3)
      and catalog-ceiling cases (Reuters/AP feeds failed)
    """
    absent = {"present": False, "rule_id": None}
    # members are already unique-by-outlet
    outlet_count = len({m["outlet_id"] for m in members})
    bands = [outlets[m["outlet_id"]]["bias_band"] for m in members if m["outlet_id"] in outlets]
    left = sum(1 for b in bands if b in LEFT_BANDS)
    right = sum(1 for b in bands if b in RIGHT_BANDS)
    center = sum(1 for b in bands if b in CENTER_BANDS)
    blob = " ".join(m["title"] + " " + (m.get("dek") or "") for m in members)
    stakes_policy = bool(POLICY_HINTS.search(blob))
    partisan_stakes = bool(PARTISAN_STAKES.search(blob))

    wires_failed = all(
        (outlets.get(w) or {}).get("feed_status") == "failed"
        or not (outlets.get(w) or {}).get("feed_url")
        for w in _CATALOG_WIRE_IDS
    )
    catalog_ceiling = wires_failed

    # Skeleton pairs + catalog ceiling: keep no_primary_source / geo_thin quiet
    allow_doc_geo = outlet_count >= 3 and not catalog_ceiling

    if category == "source_code" and allow_doc_geo:
        if not any(m["outlet_id"] in {"nature", "science"} for m in members):
            return {"present": True, "rule_id": "no_primary_source"}

    # Bias v1 tighten: missing_left/right need ≥3 members and ≥2 on present side
    # plus partisan stakes (not mere politician name-drop in a market yarn)
    if partisan_stakes and outlet_count >= 3:
        if left == 0 and right >= 2:
            return {"present": True, "rule_id": "missing_left"}
        if right == 0 and left >= 2:
            return {"present": True, "rule_id": "missing_right"}

    if stakes_policy and outlet_count >= 3:
        if center == 0 and (left > 0 or right > 0):
            return {"present": True, "rule_id": "missing_center"}
        # Bias 2026-09-14: one_side_thin needs the thick partisan side to
        # strictly outnumber center (and ≥3 vs ≤1). Tied with center or
        # center absolute majority stays quiet — beat/catalog skew.
        if left > 0 and right > 0:
            thick_left = left >= 3 and right == 1 and left > center
            thick_right = right >= 3 and left == 1 and right > center
            if thick_left or thick_right:
                oids = [m["outlet_id"] for m in members]
                thin_ids = [
                    m["outlet_id"]
                    for m in members
                    if outlets.get(m["outlet_id"], {}).get("bias_band")
                    in (RIGHT_BANDS if thick_left else LEFT_BANDS)
                ]
                tech_on_thick = sum(1 for oid in oids if oid in TECH_BEAT_OUTLETS)
                # Bias: nypost-only thin vs tech-heavy thick is catalog beat skew
                if set(thin_ids) <= {"nypost"} and tech_on_thick >= 2:
                    pass
                else:
                    return {"present": True, "rule_id": "one_side_thin"}

    if allow_doc_geo:
        places: set[str] = set()
        for m in members:
            places |= extract_entities(m["title"], m.get("dek"))["places"]
        countries = {
            outlets[m["outlet_id"]]["country"]
            for m in members
            if m["outlet_id"] in outlets
        }
        if places & {"china", "yemen", "iran", "uae", "india", "europe"} and countries <= {"US"}:
            return {"present": True, "rule_id": "geo_thin"}

    if partisan_stakes and left == 0 and right == 0 and center > 0 and outlet_count >= 3:
        if re.search(r"\b(trump|gop|democrat|republican|hawley|johnson|sanders)\b", blob, re.I):
            if re.search(r"\b(trump|gop|republican|hawley|johnson)\b", blob, re.I):
                return {"present": True, "rule_id": "missing_left"}
            return {"present": True, "rule_id": "missing_right"}

    return absent


def dedupe_members_by_outlet(members: list) -> list:
    """Keep one article per outlet_id (earliest published, then article_id)."""
    members = sorted(members, key=lambda x: (x["published_at"], x["article_id"]))
    seen: set[str] = set()
    out = []
    for m in members:
        oid = m["outlet_id"]
        if oid in seen:
            continue
        seen.add(oid)
        out.append(m)
    return out


def main() -> None:
    catalog = json.loads(CATALOG.read_text())
    outlets = {o["outlet_id"]: o for o in catalog["outlets"]}

    articles = []
    with open(OUT / "articles.jsonl") as f:
        for line in f:
            articles.append(json.loads(line))

    # Reset prior clustering on non-dropped rows so re-runs are idempotent
    for a in articles:
        if a["status"] in ("clustered", "deduped", "fetched"):
            if a["status"] != "dropped":
                a["status"] = "fetched"
                a.pop("story_id", None)
                a.pop("duplicate_of", None)
                if a.get("drop_reason") == "duplicate":
                    a.pop("drop_reason", None)

    fetched = [a for a in articles if a["status"] == "fetched"]
    assert len(fetched) > 0, f"expected fetched articles, got {len(fetched)}"
    print(f"fetched_articles={len(fetched)}")

    # --- 1. Exact dedupe ---
    by_url: dict[str, list] = defaultdict(list)
    by_content: dict[str, list] = defaultdict(list)
    for a in fetched:
        by_url[a["url_hash"]].append(a)
        if a.get("content_hash"):
            by_content[a["content_hash"]].append(a)

    survivor_of: dict[str, str] = {}

    def pick_survivor(group):
        return sorted(group, key=lambda x: (x["ingested_at"], x["article_id"]))[0]

    for group in by_url.values():
        if len(group) < 2:
            continue
        surv = pick_survivor(group)
        for a in group:
            if a["article_id"] != surv["article_id"]:
                survivor_of[a["article_id"]] = surv["article_id"]

    for group in by_content.values():
        alive = [a for a in group if a["article_id"] not in survivor_of]
        if len(alive) < 2:
            continue
        surv = pick_survivor(alive)
        for a in alive:
            if a["article_id"] != surv["article_id"]:
                survivor_of[a["article_id"]] = surv["article_id"]

    survivors = [a for a in fetched if a["article_id"] not in survivor_of]

    # --- 2. Soft clustering ---
    parent = {a["article_id"]: a["article_id"] for a in survivors}
    rank = {a["article_id"]: 0 for a in survivors}
    edge_evidence: dict[frozenset, dict] = {}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if rank[rx] < rank[ry]:
            parent[rx] = ry
        elif rank[rx] > rank[ry]:
            parent[ry] = rx
        else:
            parent[ry] = rx
            rank[rx] += 1

    ents_cache = {a["article_id"]: extract_entities(a["title"], a.get("dek")) for a in survivors}

    for i in range(len(survivors)):
        for j in range(i + 1, len(survivors)):
            a, b = survivors[i], survivors[j]
            ok, ev = soft_merge_ok(a, b, ents_cache[a["article_id"]], ents_cache[b["article_id"]])
            if ok:
                union(a["article_id"], b["article_id"])
                edge_evidence[frozenset({a["article_id"], b["article_id"]})] = ev

    clusters: dict[str, list] = defaultdict(list)
    for a in survivors:
        clusters[find(a["article_id"])].append(a)

    # --- 3. Stories + members ---
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    stories = []
    members_out = []
    art_by_id = {a["article_id"]: a for a in articles}
    story_id_by_article: dict[str, str] = {}
    unexplained = 0

    for _root, raw_members in clusters.items():
        raw_members = sorted(raw_members, key=lambda x: (x["published_at"], x["article_id"]))
        members = dedupe_members_by_outlet(raw_members)
        if not members:
            continue
        kept_by_outlet = {m["outlet_id"]: m for m in members}
        # Same-outlet extras: exact-dedupe style (unique outlet_id per story members)
        for rm in raw_members:
            if rm["article_id"] == kept_by_outlet[rm["outlet_id"]]["article_id"]:
                continue
            survivor_of[rm["article_id"]] = kept_by_outlet[rm["outlet_id"]]["article_id"]

        def title_key(m):
            return (trust_rank(outlets.get(m["outlet_id"], {})), m["published_at"], m["article_id"])

        best_tier = trust_rank(outlets.get(sorted(members, key=title_key)[0]["outlet_id"], {}))
        same_tier = [m for m in members if trust_rank(outlets.get(m["outlet_id"], {})) == best_tier]
        title_src = sorted(same_tier, key=lambda m: (m["published_at"], m["article_id"]))[0]

        story_id = make_ulid()
        time.sleep(0.001)

        story = {
            "story_id": story_id,
            "title": title_src["title"],
            "first_seen_at": min(m["published_at"] for m in members),
            "last_updated_at": max(m["published_at"] for m in members),
            "article_count": len(members),
            "outlet_count": len({m["outlet_id"] for m in members}),
            "cluster_version": 1,
            "primary_category": assign_category(members, outlets),
            "status": "open",
        }
        stories.append(story)

        seed = members[0]
        for m in members:
            story_id_by_article[m["article_id"]] = story_id
            if m["article_id"] == seed["article_id"]:
                method = "title_entity"
                score = 1.0
                ev = {
                    "shared_entities": sorted(ents_cache[m["article_id"]]["all"])[:12],
                    "title_overlap": 1.0,
                    "time_delta_hours": 0.0,
                }
            else:
                best = None
                for other in members:
                    if other["article_id"] == m["article_id"]:
                        continue
                    key = frozenset({m["article_id"], other["article_id"]})
                    if key in edge_evidence:
                        e = edge_evidence[key]
                        if best is None or e["title_overlap"] > best["title_overlap"]:
                            best = e
                if best is not None:
                    method = "title_entity"
                    ev = best
                    score = ev["title_overlap"]
                else:
                    # transitive
                    method = "title_entity"
                    best_j = -1.0
                    best_ev = None
                    shared_any = False
                    for other in members:
                        if other["article_id"] == m["article_id"]:
                            continue
                        _, ev2 = soft_merge_ok(
                            m, other,
                            ents_cache[m["article_id"]],
                            ents_cache[other["article_id"]],
                        )
                        if ents_cache[m["article_id"]]["all"] & ents_cache[other["article_id"]]["all"]:
                            shared_any = True
                        if ev2["title_overlap"] > best_j:
                            best_j = ev2["title_overlap"]
                            best_ev = ev2
                    ev = best_ev or {
                        "shared_entities": [],
                        "title_overlap": 0.0,
                        "time_delta_hours": 0.0,
                    }
                    score = ev.get("title_overlap")
                    if not shared_any:
                        unexplained += 1

            members_out.append({
                "story_id": story_id,
                "article_id": m["article_id"],
                "method": method,
                "score": score,
                "evidence": {
                    "shared_entities": ev.get("shared_entities", []),
                    "title_overlap": ev.get("title_overlap"),
                    "time_delta_hours": ev.get("time_delta_hours"),
                },
                "assigned_at": now,
            })

    # --- 4. Update articles ---
    for a in articles:
        if a["status"] != "fetched":
            continue
        aid = a["article_id"]
        if aid in survivor_of:
            a["status"] = "deduped"
            a["duplicate_of"] = survivor_of[aid]
            a["drop_reason"] = "duplicate"
        elif aid in story_id_by_article:
            a["status"] = "clustered"
            a["story_id"] = story_id_by_article[aid]

    # --- 5. Feed + held ---
    feed = []
    held = []
    members_by_story: dict[str, list] = defaultdict(list)
    for sm in members_out:
        members_by_story[sm["story_id"]].append(sm)

    now_dt = datetime.now(timezone.utc)
    aged_out_stories = 0
    for s in stories:
        mem_arts = [art_by_id[sm["article_id"]] for sm in members_by_story[s["story_id"]]]
        mem_arts_sorted = sorted(mem_arts, key=lambda x: x["published_at"])
        # Freshness: drop members older than 48h; story leaves home if no remaining
        # member update in that window or outlet_count falls below 2.
        fresh_mems = [m for m in mem_arts_sorted if is_fresh(m.get("published_at") or "", now_dt)]
        if not fresh_mems:
            aged_out_stories += 1
            held.append({
                "story_id": s["story_id"],
                "title": s["title"],
                "first_seen_at": s["first_seen_at"],
                "last_updated_at": s["last_updated_at"],
                "article_count": s["article_count"],
                "outlet_count": s["outlet_count"],
                "primary_category": s["primary_category"],
                "hold_reason": "aged_out",
                "members": [],
                "labels": {
                    "bias_band": "mixed",
                    "blindspot": {"present": False, "rule_id": None},
                },
            })
            continue
        last_updated = max(m["published_at"] for m in fresh_mems)
        if not is_fresh(last_updated, now_dt):
            aged_out_stories += 1
            held.append({
                "story_id": s["story_id"],
                "title": s["title"],
                "hold_reason": "aged_out",
                "first_seen_at": s["first_seen_at"],
                "last_updated_at": last_updated,
                "article_count": len(fresh_mems),
                "outlet_count": len({m["outlet_id"] for m in fresh_mems}),
                "primary_category": s["primary_category"],
                "members": [],
                "labels": {
                    "bias_band": "mixed",
                    "blindspot": {"present": False, "rule_id": None},
                },
            })
            continue
        uniq = []
        seen = set()
        for m in sorted(fresh_mems, key=lambda x: x["published_at"]):
            if m["outlet_id"] in seen:
                continue
            seen.add(m["outlet_id"])
            uniq.append(m)
        outlet_count = len(uniq)
        item = {
            "story_id": s["story_id"],
            "title": s["title"],
            "first_seen_at": min(m["published_at"] for m in uniq),
            "last_updated_at": last_updated,
            "article_count": len(uniq),
            "outlet_count": outlet_count,
            "primary_category": s["primary_category"],
            "members": [
                {
                    "title": m["title"],
                    "canonical_url": m["canonical_url"],
                    "published_at": m["published_at"],
                    "outlet_id": m["outlet_id"],
                    "outlet_name": outlets[m["outlet_id"]]["name"],
                    "dek": m.get("dek"),
                }
                for m in uniq
            ],
            "labels": {
                "bias_band": compute_bias_band(uniq, outlets),
                "blindspot": compute_blindspot(uniq, outlets, s["primary_category"]),
            },
        }
        if outlet_count >= 2:
            feed.append(item)
        else:
            held.append(item)

    feed.sort(key=lambda x: x["last_updated_at"], reverse=True)
    held.sort(key=lambda x: x["last_updated_at"], reverse=True)

    by_cat = Counter(s["primary_category"] for s in stories)
    by_bias = Counter(i["labels"]["bias_band"] for i in feed)
    summary = {
        "stories_total": len(stories),
        "feed_stories": len(feed),
        "held_single_outlet": len(held),
        "deduped": sum(1 for a in articles if a["status"] == "deduped"),
        "unclustered": sum(1 for a in articles if a["status"] == "fetched"),
        "by_category": dict(sorted(by_cat.items())),
        "by_bias_band": dict(sorted(by_bias.items())),
        "unexplained_merges": unexplained,
        "clustered_articles": sum(1 for a in articles if a["status"] == "clustered"),
        "survivors": len(survivors),
        "aged_out_stories": aged_out_stories,
        "freshness_hours": HOME_FRESHNESS_HOURS,
        "generated_at": now,
    }

    with open(OUT / "stories.jsonl", "w") as f:
        for s in stories:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with open(OUT / "story_members.jsonl", "w") as f:
        for m in members_out:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    with open(OUT / "articles.jsonl", "w") as f:
        for a in articles:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    feed_json = json.dumps(feed, ensure_ascii=False, indent=2) + "\n"
    held_json = json.dumps(held, ensure_ascii=False, indent=2) + "\n"
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    (OUT / "feed-v1.json").write_text(feed_json)
    (OUT / "held-single-outlet.json").write_text(held_json)
    (OUT / "cluster-summary.json").write_text(summary_json)
    # Mirror durable feed for TheDiffNews app (survives scheduled refresh consumers)
    app_data = Path("/workspace/thediffnews/data")
    app_data.mkdir(parents=True, exist_ok=True)
    (app_data / "feed-v1.json").write_text(feed_json)
    (app_data / "cluster-summary.json").write_text(summary_json)

    print("=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print("\n=== FEED ===")
    for item in feed:
        print(f"[{item['outlet_count']} out|{item['article_count']} art|{item['primary_category']}|{item['labels']['bias_band']}] {item['title'][:110]}")
        for m in item["members"]:
            print(f"    - {m['outlet_id']}: {m['title'][:95]}")
        if item["labels"]["blindspot"]["present"]:
            print(f"    blindspot={item['labels']['blindspot']['rule_id']}")
    print("\n=== DIRECT EDGES ===")
    for key, ev in sorted(edge_evidence.items(), key=lambda x: -x[1]["title_overlap"]):
        ids = list(key)
        a, b = art_by_id[ids[0]], art_by_id[ids[1]]
        print(f"jac={ev['title_overlap']:.2f} dt={ev['time_delta_hours']:.1f}h ents={ev['shared_entities']}")
        print(f"  {a['outlet_id']}: {a['title'][:85]}")
        print(f"  {b['outlet_id']}: {b['title'][:85]}")


if __name__ == "__main__":
    main()
