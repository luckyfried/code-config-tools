"""Morning Paper: sets today's front page from the person's inputs.

Run from the project folder:

    python3 <agent-apps root>/morning-paper/scripts/run.py

It reads morning-paper.inputs.json from the current folder and writes out/morning-paper/, a static page to serve
with python3 -m http.server. With "live": false the paper is the sample edition that ships with the app and the run
touches no network, so two runs on the same inputs write the same bytes. With "live": true it fetches each source's
RSS or Atom feed (and Hacker News, and the Guardian when GUARDIAN_API_KEY is set) into feed.json, with the run time,
Wikipedia's featured feed for the day, and the weather, which the page refreshes when it opens.

Standard library only; written for Python 3.12.
"""

import html
import json
import os
import re
import shutil
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

APP = "morning-paper"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
PROJECT = Path.cwd()
INPUTS = PROJECT / f"{APP}.inputs.json"
OUT = PROJECT / "out" / APP
USER_AGENT = "MorningPaper/1.0 (an agent app from code-config.com; one reader's front page)"
PER_SECTION = 8
KINDS = ("feed", "hackernews", "guardian")
PAPERS = {"A4": "A4", "Letter": "letter"}
KEYS = {
    "masthead": str,
    "motto": str,
    "sources": list,
    "sections": list,
    "location": dict,
    "paper": str,
    "theme": str,
    "units": str,
    "live": bool,
}
OPTIONAL = {"motto", "units", "live"}


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def read_inputs():
    if not INPUTS.is_file():
        fail([f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key."])
    try:
        data = json.loads(INPUTS.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{APP}.inputs.json is not valid JSON ({error.msg} on line {getattr(error, 'lineno', 1)})."])
    if not isinstance(data, dict):
        fail([f"{APP}.inputs.json must be one JSON object with the keys inputs.example.json shows."])
    return data


def check(data):
    name = f"{APP}.inputs.json"
    problems = []
    for key, kind in KEYS.items():
        if key not in data:
            if key not in OPTIONAL:
                problems.append(f'{name} is missing the key "{key}".')
            continue
        if not isinstance(data[key], kind) or (kind is int and isinstance(data[key], bool)):
            word = {str: "text", list: "a list", dict: "an object", bool: "true or false"}[kind]
            problems.append(f'{name} has "{key}" as something other than {word}.')
    for key in data:
        if key not in KEYS and key != "_notes":
            problems.append(f'{name} has a key this app does not use: "{key}".')
    themes = sorted(p.stem for p in THEMES.glob("*.css"))
    if isinstance(data.get("theme"), str) and data["theme"] not in themes:
        problems.append(f'{name} has "theme" as "{data["theme"]}"; the themes are {", ".join(themes)}.')
    if problems:
        return problems

    if not data["masthead"].strip():
        problems.append(f'{name} has an empty "masthead"; give the paper a name.')
    elif len(data["masthead"]) > 48:
        problems.append(f'{name} has a "masthead" longer than 48 characters; a shorter name sets larger.')
    if data["paper"] not in PAPERS:
        problems.append(f'{name} has "paper" as "{data["paper"]}"; it must be "A4" or "Letter".')
    if data.get("units", "fahrenheit") not in ("fahrenheit", "celsius"):
        problems.append(f'{name} has "units" as "{data["units"]}"; it must be "fahrenheit" or "celsius".')

    loc = data["location"]
    for key, low, high in (("lat", -90, 90), ("lon", -180, 180)):
        value = loc.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not low <= value <= high:
            problems.append(f'{name} needs "location.{key}" as a number from {low} to {high}.')
    if "name" in loc and not isinstance(loc["name"], str):
        problems.append(f'{name} has "location.name" as something other than text.')

    ids = []
    for i, source in enumerate(data["sources"]):
        where = f'"sources[{i}]"'
        if not isinstance(source, dict):
            problems.append(f"{name} has {where} as something other than an object.")
            continue
        for key in ("id", "name"):
            if not isinstance(source.get(key), str) or not source.get(key).strip():
                problems.append(f'{name} has {where} without "{key}".')
        kind = source.get("kind", "feed")
        if kind not in KINDS:
            problems.append(f'{name} has {where} with "kind" "{kind}"; it must be "feed", "hackernews", or "guardian".')
        if kind == "feed" and not str(source.get("url", "")).startswith(("http://", "https://")):
            problems.append(f'{name} has {where} without a feed address in "url".')
        if kind == "guardian" and not isinstance(source.get("section"), str):
            problems.append(f'{name} has {where} without the Guardian "section" to read, such as "world".')
        if source.get("id") in ids:
            problems.append(f'{name} has two sources with the id "{source.get("id")}".')
        ids.append(source.get("id"))

    if not data["sections"]:
        problems.append(f'{name} has no "sections"; name at least one, with the sources that fill it.')
    for i, section in enumerate(data["sections"]):
        where = f'"sections[{i}]"'
        if not isinstance(section, dict) or not isinstance(section.get("name"), str) or not section["name"].strip():
            problems.append(f'{name} has {where} without a "name".')
            continue
        if not isinstance(section.get("sources"), list) or not section["sources"]:
            problems.append(f'{name} has the section "{section["name"]}" without a list of "sources".')
            continue
        for sid in section["sources"]:
            if sid not in ids:
                problems.append(f'{name} has the section "{section["name"]}" naming a source "{sid}" that "sources" does not list.')

    return problems


# ---------- fetching (live editions only) ----------


def get(url, accept="*/*"):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read()


def text_of(fragment):
    """Plain text from a feed's HTML fragment."""
    if not fragment:
        return ""
    fragment = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>|</p>", " ", fragment)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def clip(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + " "
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > limit * 0.5 else cut.rstrip() + "…"


def when(value):
    if not value:
        return None
    value = value.strip()
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def child(node, *names):
    for item in node:
        if local_name(item.tag) in names:
            return item
    return None


def image_of(node):
    for item in node.iter():
        tag = local_name(item.tag)
        url = item.get("url")
        if tag in ("content", "thumbnail") and url and (item.get("medium") in (None, "image") or tag == "thumbnail"):
            if re.search(r"\.(jpe?g|png|webp|gif)(\?|$)", url, re.I) or item.get("medium") == "image" or tag == "thumbnail":
                return url
        if tag == "enclosure" and url and str(item.get("type", "")).startswith("image/"):
            return url
    return None


def parse_feed(raw, source):
    root = ET.fromstring(raw)
    items = []
    if local_name(root.tag) == "feed":
        for entry in root:
            if local_name(entry.tag) != "entry":
                continue
            link = None
            for item in entry:
                if local_name(item.tag) == "link" and item.get("rel", "alternate") == "alternate":
                    link = item.get("href")
                    break
            summary = child(entry, "summary") if child(entry, "summary") is not None else child(entry, "content")
            published = child(entry, "published") if child(entry, "published") is not None else child(entry, "updated")
            items.append((child(entry, "title"), link, summary, published, image_of(entry)))
    else:
        channel = child(root, "channel")
        for entry in channel if channel is not None else root:
            if local_name(entry.tag) != "item":
                continue
            link = child(entry, "link")
            summary = child(entry, "description")
            if summary is None or not (summary.text or "").strip():
                summary = child(entry, "encoded")
            items.append((child(entry, "title"), link.text if link is not None else None, summary, child(entry, "pubDate", "date"), image_of(entry)))
    stories = []
    for title, link, summary, published, image in items:
        heading = text_of(title.text if title is not None else "")
        if not heading:
            continue
        stories.append({"title": heading, "summary": clip(text_of(summary.text if summary is not None else ""), 1400),
                        "link": (link or "").strip() or None, "published": when(published.text if published is not None else None),
                        "image": image, "source": source["name"]})
    return stories


def hacker_news(source):
    data = json.loads(get("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=12", "application/json"))
    stories = []
    for hit in data.get("hits", []):
        item = f"https://news.ycombinator.com/item?id={hit['objectID']}"
        points, comments = hit.get("points") or 0, hit.get("num_comments") or 0
        site = urllib.parse.urlsplit(hit.get("url") or item).hostname or "news.ycombinator.com"
        stories.append({"title": hit.get("title") or "", "link": hit.get("url") or item,
                        "summary": f"{points:,} points and {comments:,} comments on Hacker News, linking to {site.removeprefix('www.')}.",
                        "published": when(hit.get("created_at")), "image": None, "source": source["name"]})
    return stories


def guardian(source, key):
    query = urllib.parse.urlencode({"section": source["section"], "show-fields": "trailText,thumbnail", "page-size": 12,
                                    "order-by": "newest", "api-key": key})
    data = json.loads(get(f"https://content.guardianapis.com/search?{query}", "application/json"))
    stories = []
    for item in data.get("response", {}).get("results", []):
        fields = item.get("fields", {})
        stories.append({"title": item.get("webTitle", ""), "link": item.get("webUrl"), "summary": clip(text_of(fields.get("trailText")), 1400),
                        "published": when(item.get("webPublicationDate")), "image": fields.get("thumbnail"), "source": source["name"]})
    return stories


def fetch_wiki(day):
    def featured(d):
        return json.loads(get(f"https://api.wikimedia.org/feed/v1/wikipedia/en/featured/{d:%Y/%m/%d}", "application/json"))

    raw = featured(day)
    if not raw.get("mostread"):
        raw["mostread"] = featured(day - timedelta(days=1)).get("mostread")
    page = lambda p: (p or {}).get("content_urls", {}).get("desktop", {}).get("page")
    most = raw.get("mostread")
    image = raw.get("image")
    return {
        "date": day.isoformat(),
        "onThisDay": [{"year": e.get("year"), "text": e.get("text"), "link": page((e.get("pages") or [None])[0])} for e in raw.get("onthisday", [])[:6]],
        "mostRead": {"date": str(most.get("date", "")).rstrip("Z"),
                     "articles": [{"title": a.get("normalizedtitle") or a.get("title"), "description": a.get("description"),
                                   "extract": a.get("extract", ""), "views": a.get("views", 0), "link": page(a)} for a in most.get("articles", [])[:6]]} if most else None,
        "picture": {"src": image["thumbnail"]["source"], "width": image.get("image", image["thumbnail"])["width"],
                    "height": image.get("image", image["thumbnail"])["height"], "caption": image.get("description", {}).get("text", ""),
                    "credit": ", ".join(x for x in (image.get("artist", {}).get("text"), image.get("license", {}).get("type")) if x) + ", via Wikimedia Commons",
                    "link": image.get("file_page")} if image and image.get("thumbnail") else None,
    }


def fetch_weather(inputs):
    loc = inputs["location"]
    celsius = inputs.get("units") == "celsius"
    query = urllib.parse.urlencode({"latitude": loc["lat"], "longitude": loc["lon"], "current": "temperature_2m,weather_code,wind_speed_10m,is_day",
                                    "daily": "temperature_2m_max,temperature_2m_min", "temperature_unit": "celsius" if celsius else "fahrenheit",
                                    "wind_speed_unit": "kmh" if celsius else "mph", "timezone": "auto", "forecast_days": 1})
    data = json.loads(get(f"https://api.open-meteo.com/v1/forecast?{query}", "application/json"))
    return {"place": loc.get("name", ""), "units": "celsius" if celsius else "fahrenheit", "code": data["current"]["weather_code"],
            "temperature": data["current"]["temperature_2m"], "high": data["daily"]["temperature_2m_max"][0],
            "low": data["daily"]["temperature_2m_min"][0], "wind": data["current"]["wind_speed_10m"], "isDay": data["current"]["is_day"] == 1}


def slug(text):
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:56] or "story"


def live_edition(inputs):
    now = datetime.now().astimezone().replace(second=0, microsecond=0)
    key = os.environ.get("GUARDIAN_API_KEY", "").strip()
    by_id = {s["id"]: s for s in inputs["sources"]}
    fetched = {}
    for sid in dict.fromkeys(sid for section in inputs["sections"] for sid in section["sources"]):
        source = by_id[sid]
        kind = source.get("kind", "feed")
        try:
            if kind == "hackernews":
                fetched[sid] = hacker_news(source)
            elif kind == "guardian":
                if not key:
                    print(f"{source['name']} needs a Guardian key in GUARDIAN_API_KEY; the paper runs without it.")
                    continue
                fetched[sid] = guardian(source, key)
            else:
                fetched[sid] = parse_feed(get(source["url"], "application/rss+xml, application/atom+xml, application/xml, text/xml"), source)
        except Exception as error:  # one quiet source never stops the paper
            print(f"Could not read {source['name']} ({type(error).__name__}); the paper runs without it.")

    stories, seen_ids, seen_titles = [], set(), set()
    floor = now - timedelta(days=3)
    for section in inputs["sections"]:
        pool = [s for sid in section["sources"] for s in fetched.get(sid, [])]
        recent = [s for s in pool if s["published"] is None or s["published"] >= floor] or pool
        recent.sort(key=lambda s: s["published"] or floor, reverse=True)
        count = 0
        for s in recent:
            fold = re.sub(r"\W+", " ", s["title"].lower()).strip()
            if fold in seen_titles or count >= PER_SECTION:
                continue
            seen_titles.add(fold)
            sid = slug(s["title"])
            while sid in seen_ids:
                sid += "-x"
            seen_ids.add(sid)
            count += 1
            stories.append({"id": sid, "section": section["name"], "source": s["source"], "title": s["title"], "summary": s["summary"],
                            "body": None, "link": s["link"],
                            "published": s["published"].astimezone(now.tzinfo).isoformat(timespec="minutes") if s["published"] else None,
                            "image": {"src": s["image"], "alt": "", "caption": None, "credit": s["source"]} if s["image"] else None})
    if not stories:
        print("No source answered, so there is nothing to print. Check the network and the feed addresses, then run again.")
        sys.exit(1)

    wiki = weather = None
    try:
        wiki = fetch_wiki(now.date())
    except Exception as error:
        print(f"Could not read Wikipedia's featured feed ({type(error).__name__}); the page asks again when it opens.")
    try:
        weather = fetch_weather(inputs)
    except Exception as error:
        print(f"Could not read the weather ({type(error).__name__}); the page asks again when it opens.")
    return {"edition": "live", "setAt": now.isoformat(timespec="minutes"), "day": now.date().isoformat(),
            "stories": stories, "wiki": wiki, "weather": weather}


# ---------- writing ----------


def fill_page(page, inputs, feed):
    """Sets the masthead, motto, title, and dateline into the page so they are there before any script runs."""
    name = html.escape(inputs["masthead"].strip())
    motto = html.escape(inputs.get("motto", "").strip())
    day = datetime.fromisoformat(feed["day"])
    dateline = f"{day:%A}, {day:%B} {day.day}, {day.year}"
    swaps = (
        (r"(<title>).*?(</title>)", name),
        (r'(<h1 class="masthead is-waiting" id="masthead">).*?(</h1>)', name),
        (r'(<p class="motto" id="motto">).*?(</p>)', motto),
    )
    for pattern, value in swaps:
        page = re.sub(pattern, lambda m, v=value: m.group(1) + v + m.group(2), page, count=1)
    return re.sub(r'(<time class="dateline-date" id="dateline" datetime=")[^"]*(">).*?(</time>)',
                  lambda m: m.group(1) + feed["day"] + m.group(2) + dateline + m.group(3), page, count=1)


def main():
    inputs = read_inputs()
    problems = check(inputs)
    if problems:
        fail(problems)
    inputs = {k: v for k, v in inputs.items() if k != "_notes"}

    if inputs.get("live") is True:
        feed = live_edition(inputs)
    else:
        feed = json.loads((SITE / "sample" / "feed.json").read_text(encoding="utf-8"))

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT)
    badge = APP_DIR / "badge.js"
    if badge.is_file():
        shutil.copyfile(badge, OUT / "badge.js")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", OUT / "theme.css")
    (OUT / "paper.css").write_text(
        "/* The printed sheet, from the inputs' paper size. */\n"
        f"@page {{\n  size: {PAPERS[inputs['paper']]};\n  margin: 12mm 12mm 14mm;\n}}\n", encoding="utf-8")
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(inputs, ensure_ascii=False)};\n", encoding="utf-8")
    (OUT / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    index = OUT / "index.html"
    index.write_text(fill_page(index.read_text(encoding="utf-8"), inputs, feed), encoding="utf-8")

    files = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
