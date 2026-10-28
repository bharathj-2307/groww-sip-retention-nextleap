"""Collect public posts about SIPs / mutual funds (Groww focus) from five sources.

Run: python collect.py [source ...]   (sources: play appstore reddit tqna youtube)
Writes one JSONL file per source to ../data/raw/, every row in the same shape:
  id, source, url, date, text, rating, meta
"""
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research project; SIP discovery engine)"}
SINCE = "2024-01-01"  # only keep posts from this date on

# Cheap first filter: a post must mention SIPs / mutual funds in some way.
KEYWORDS = re.compile(
    r"\b(sip|sips|mutual funds?|mf|nav|xirr|autopay|auto ?pay|mandate|instal+ments?|"
    r"index funds?|elss|redeem|redemption|step.?up)\b",
    re.I,
)


def relevant(text):
    return bool(text and KEYWORDS.search(text))


def save(source, rows):
    seen, out = set(), []
    for r in rows:
        if r["id"] in seen or not r["text"]:
            continue
        seen.add(r["id"])
        out.append(r)
    path = RAW / f"{os.environ.get('OUT_NAME', source)}.jsonl"
    with path.open("w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{source}: saved {len(out)} rows -> {path}")


def row(source, id_, url, date, text, rating=None, **meta):
    return {"id": f"{source}:{id_}", "source": source, "url": url, "date": date,
            "text": text.strip(), "rating": rating, "meta": meta}


# ---------- Play Store ----------
def play(max_reviews=40000):
    from google_play_scraper import Sort, reviews

    app = "com.nextbillion.groww"
    rows, token, fetched = [], None, 0
    while fetched < max_reviews:
        batch, token = reviews(app, lang="en", country="in", sort=Sort.NEWEST,
                               count=200, continuation_token=token)
        if not batch:
            break
        fetched += len(batch)
        for r in batch:
            date = r["at"].strftime("%Y-%m-%d")
            if relevant(r["content"]):
                rows.append(row("play", r["reviewId"],
                                f"https://play.google.com/store/apps/details?id={app}",
                                date, r["content"], r["score"], thumbs=r["thumbsUpCount"]))
        if date < SINCE or token is None:
            break
    print(f"play: scanned {fetched} reviews")
    save("play", rows)


# ---------- App Store ----------
def appstore():
    rows = []
    for page in range(1, 11):  # Apple's public feed stops at 10 pages
        url = (f"https://itunes.apple.com/in/rss/customerreviews/page={page}"
               "/id=1404871703/sortby=mostrecent/json")
        entries = requests.get(url, headers=UA, timeout=30).json().get("feed", {}).get("entry", [])
        for e in entries:
            if "content" not in e:
                continue
            text = f'{e["title"]["label"]}. {e["content"]["label"]}'
            if relevant(text):
                rows.append(row("appstore", e["id"]["label"],
                                "https://apps.apple.com/in/app/groww/id1404871703",
                                e["updated"]["label"][:10], text, int(e["im:rating"]["label"])))
        time.sleep(1)
    save("appstore", rows)


# ---------- Reddit (via the Arctic Shift public archive; reddit.com blocks direct access) ----------
ARCTIC = "https://arctic-shift.photon-reddit.com/api"
SUBS = os.environ.get("REDDIT_SUBS", "IndiaInvestments,mutualfunds,personalfinanceindia").split(",")


def arctic_get(path, params, tries=5):
    for attempt in range(tries):
        try:
            r = requests.get(f"{ARCTIC}/{path}", params=params, headers=UA, timeout=60)
            data = r.json() if r.ok else {}
        except (requests.RequestException, ValueError):
            data = {}
        if data.get("data") is not None:
            return data["data"]
        time.sleep(10 * (attempt + 1))
    return None  # gave up on this window


def month_windows(start="2025-01-01"):
    """Month-sized date windows (the archive times out on wide text searches)."""
    d, today = datetime.fromisoformat(start), datetime.now()
    while d < today:
        nxt = datetime(d.year + (d.month == 12), d.month % 12 + 1, 1)
        yield d.strftime("%Y-%m-%d"), nxt.strftime("%Y-%m-%d")
        d = nxt


def reddit():
    rows, skipped = [], []
    for sub in SUBS:
        for kind, field in (("posts", "title"), ("comments", "body")):
            for after, before in month_windows():
                params = {"subreddit": sub, "after": after, "before": before, "limit": 100, field: "SIP"}
                items = arctic_get(f"{kind}/search", params)
                if items is None:
                    skipped.append((sub, kind, after))
                    continue
                for it in items:
                    if kind == "posts":
                        text = f'{it.get("title", "")}\n{it.get("selftext", "")}'
                        url = f'https://www.reddit.com{it.get("permalink", "")}'
                    else:
                        text = it.get("body", "")
                        url = f'https://www.reddit.com/r/{sub}/comments/{it.get("link_id", "")[3:]}/_/{it["id"]}'
                    if text in ("[removed]", "[deleted]") or not relevant(text):
                        continue
                    date = datetime.fromtimestamp(it["created_utc"], timezone.utc).strftime("%Y-%m-%d")
                    rows.append(row("reddit", it["id"], url, date, text, None,
                                    subreddit=sub, kind=kind[:-1], score=it.get("score")))
                print(f"reddit r/{sub} {kind} {after}: {len(items)} fetched, {len(rows)} kept so far", flush=True)
                time.sleep(2)
            save("reddit", rows)  # save after each subreddit/kind so partial progress is kept
    print("reddit windows skipped after retries:", skipped)


# ---------- TradingQ&A (Zerodha's public Discourse forum) ----------
def tqna(pages_per_query=6):
    base = "https://tradingqna.com"
    topic_ids = {}
    for q in ("stop sip", "pause sip", "sip loss", "sip groww", "sip mandate", "first sip", "sip returns"):
        for page in range(1, pages_per_query + 1):
            d = requests.get(f"{base}/search.json", params={"q": f"{q} after:{SINCE}", "page": page},
                             headers=UA, timeout=30).json()
            for t in d.get("topics", []):
                topic_ids[t["id"]] = t.get("slug", "")
            if not d.get("grouped_search_result", {}).get("more_full_page_results"):
                break
            time.sleep(1)
    print(f"tqna: {len(topic_ids)} topics")
    rows = []
    for tid, slug in topic_ids.items():
        r = requests.get(f"{base}/t/{tid}.json", headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(20)
            r = requests.get(f"{base}/t/{tid}.json", headers=UA, timeout=30)
        if not r.ok:
            continue
        t = r.json()
        for p in t.get("post_stream", {}).get("posts", [])[:20]:
            text = html.unescape(re.sub(r"<[^>]+>", " ", p.get("cooked", "")))
            text = re.sub(r"\s+", " ", text)
            if p["post_number"] == 1:
                text = f'{t.get("title", "")}\n{text}'
            if relevant(text) and p.get("username") != "system":
                rows.append(row("tqna", p["id"], f"{base}/t/{slug}/{tid}/{p['post_number']}",
                                p["created_at"][:10], text, None, topic=t.get("title"),
                                post_number=p["post_number"]))
        time.sleep(0.7)
    save("tqna", rows)


# ---------- YouTube comments ----------
YT_QUERIES = ["groww sip", "should i stop my sip", "sip loss what to do", "sip for beginners india",
              "sip negative returns", "mutual fund sip mistakes beginners", "groww mutual fund review",
              "sip pause or stop"]


def youtube_search(query, n=6):
    page = requests.get("https://www.youtube.com/results", params={"search_query": query},
                        headers={**UA, "Accept-Language": "en-IN"}, timeout=30).text
    ids = []
    for vid in re.findall(r'"videoId":"([\w-]{11})"', page):
        if vid not in ids:
            ids.append(vid)
    return ids[:n]


def youtube(per_video=300):
    """Comments via YouTube's own web endpoint (the watch page itself is rate limited here)."""
    api = "https://www.youtube.com/youtubei/v1/next?prettyPrint=false"
    ctx = {"context": {"client": {"clientName": "WEB", "clientVersion": "2.20250101.00.00",
                                  "hl": "en", "gl": "IN"}}}

    def nxt(**kw):
        for _ in range(3):
            r = requests.post(api, json={**ctx, **kw}, headers=UA, timeout=(10, 20))
            if r.ok:
                return r.json()
            time.sleep(5)
        return {}

    videos = []
    for q in YT_QUERIES:
        for v in youtube_search(q):
            if v not in videos:
                videos.append(v)
    print(f"youtube: {len(videos)} videos")
    rows = []
    for v in videos:
        d = nxt(videoId=v)
        secs = [x for x in d.get("contents", {}).get("twoColumnWatchNextResults", {})
                .get("results", {}).get("results", {}).get("contents", [])
                if x.get("itemSectionRenderer", {}).get("sectionIdentifier") == "comment-item-section"]
        toks = re.findall(r'"token": "([^"]+)"', json.dumps(secs))
        tok, n, deadline = (toks[0] if toks else None), 0, time.time() + 90
        while tok and n < per_video and time.time() < deadline:
            c = nxt(continuation=tok)
            muts = c.get("frameworkUpdates", {}).get("entityBatchUpdate", {}).get("mutations", [])
            for m in muts:
                e = m.get("payload", {}).get("commentEntityPayload")
                if not e:
                    continue
                n += 1
                text = e["properties"]["content"]["content"]
                cid = e["properties"]["commentId"]
                if relevant(text):
                    url = f"https://www.youtube.com/watch?v={v}"
                    rows.append(row("youtube", cid, f"{url}&lc={cid}", None, text, None,
                                    video=v, when=e["properties"].get("publishedTime")))
            toks = re.findall(r'"token": "([^"]+)"', json.dumps(c.get("onResponseReceivedEndpoints", [])))
            tok = toks[-1] if toks else None
            time.sleep(0.5)
        print(f"youtube {v}: {n} comments", flush=True)
    save("youtube", rows)


SOURCES = {"play": play, "appstore": appstore, "reddit": reddit, "tqna": tqna, "youtube": youtube}

if __name__ == "__main__":
    for name in sys.argv[1:] or SOURCES:
        SOURCES[name]()
