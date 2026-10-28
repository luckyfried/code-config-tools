"""Headline Board: builds the board into out/headline-board/ from headline-board.inputs.json.

Run from the project folder:

    python3 <agent-apps root>/headline-board/scripts/run.py

It checks the inputs, copies the page, writes theme.css and config.js, and
fetches today's headlines and weather into feed.json. A source that does not
answer is left out and named. Standard library only.
"""

import html
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

APP = "headline-board"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
INPUTS = f"{APP}.inputs.json"
TIMEOUT = 10
PER_FEED = 12
HN_COUNT = 30
AGENT = "HeadlineBoard/1.0 (a Code Config agent app; https://code-config.com)"
GUARDIAN_KEY = "GUARDIAN_API_KEY"

KEYS = {
    "title": "a name for the board, like \"Kitchen board\"",
    "sources": "a list of feed addresses, \"wikipedia\", or \"hackernews\"",
    "rows": "a whole number of rows from 2 to 12",
    "secondsPerFlip": "a number of seconds from 3 to 120",
    "location": "{\"lat\": …, \"lon\": …} for the weather line, or null",
    "theme": "the name of a theme",
}

# Short tags for well-known newsrooms, shown in the colored flaps at the start of a row.
KNOWN_TAGS = {
    "bbc.co.uk": "BBC", "bbci.co.uk": "BBC", "bbc.com": "BBC", "npr.org": "NPR", "nytimes.com": "NYT",
    "theguardian.com": "GDN", "reuters.com": "RTRS", "apnews.com": "AP", "aljazeera.com": "AJE",
    "arstechnica.com": "ARS", "theverge.com": "VERGE", "wired.com": "WIRED", "washingtonpost.com": "WAPO",
    "wsj.com": "WSJ", "ft.com": "FT", "economist.com": "ECON", "cnn.com": "CNN", "nature.com": "NATURE",
    "techcrunch.com": "TC", "politico.com": "POLTC", "axios.com": "AXIOS", "latimes.com": "LAT",
    "smithsonianmag.com": "SMITH", "nasa.gov": "NASA", "espn.com": "ESPN", "bloomberg.com": "BBG",
    "dw.com": "DW", "france24.com": "F24", "abc.net.au": "ABC", "cbc.ca": "CBC", "rte.ie": "RTE",
}


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def read_inputs():
    path = Path.cwd() / INPUTS
    if not path.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON ({error})."])
    if not isinstance(inputs, dict):
        fail([f"{INPUTS} must hold one JSON object."])
    return inputs


def check(inputs):
    problems = []
    for key in KEYS:
        if key not in inputs:
            problems.append(f"{INPUTS} is missing the key \"{key}\" ({KEYS[key]}).")
    for key in inputs:
        if key not in KEYS and key != "_notes":
            problems.append(f"{INPUTS} has the key \"{key}\", which this app does not use.")

    def bad(key):
        problems.append(f"{INPUTS} has \"{key}\" set to {json.dumps(inputs[key])}; it should be {KEYS[key]}.")

    if "title" in inputs and not (isinstance(inputs["title"], str) and inputs["title"].strip()):
        bad("title")
    if "sources" in inputs:
        sources = inputs["sources"]
        if not isinstance(sources, list) or not sources:
            bad("sources")
        else:
            for index, source in enumerate(sources):
                if isinstance(source, str) and source.strip():
                    continue
                if isinstance(source, dict) and isinstance(source.get("url"), str) and set(source) <= {"url", "tag", "name"}:
                    continue
                problems.append(f"{INPUTS} has sources[{index}] set to {json.dumps(source)}; each source is a feed address, \"wikipedia\", or \"hackernews\".")
    if "rows" in inputs and not (isinstance(inputs["rows"], int) and not isinstance(inputs["rows"], bool) and 2 <= inputs["rows"] <= 12):
        bad("rows")
    if "secondsPerFlip" in inputs and not (is_number(inputs["secondsPerFlip"]) and 3 <= inputs["secondsPerFlip"] <= 120):
        bad("secondsPerFlip")
    if "location" in inputs and inputs["location"] is not None:
        place = inputs["location"]
        ok = (
            isinstance(place, dict)
            and set(place) <= {"lat", "lon", "name"}
            and is_number(place.get("lat")) and -90 <= place["lat"] <= 90
            and is_number(place.get("lon")) and -180 <= place["lon"] <= 180
            and isinstance(place.get("name", ""), str)
        )
        if not ok:
            bad("location")
    if "theme" in inputs:
        names = sorted(path.stem for path in THEMES.glob("*.css"))
        if inputs["theme"] not in names:
            problems.append(f"{INPUTS} has \"theme\" set to {json.dumps(inputs['theme'])}; the themes are {', '.join(names)}.")
    if problems:
        fail(problems)


# Fetching -----------------------------------------------------------------------------------------------------------

def get(url, accept="*/*"):
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Api-User-Agent": AGENT, "Accept": accept})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def get_json(url):
    return json.loads(get(url, "application/json").decode("utf-8"))


def clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(html.unescape(text))
    return re.sub(r"\s+", " ", text).strip()


def iso(moment):
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def host_of(url):
    host = urllib.parse.urlparse(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


# Plain names for newsrooms whose feeds carry long titles ("NPR Topics: News").
KNOWN_NAMES = {"BBC": "BBC News", "NPR": "NPR", "NYT": "The New York Times", "GDN": "The Guardian", "AP": "AP News",
               "AJE": "Al Jazeera", "ARS": "Ars Technica", "VERGE": "The Verge", "RTRS": "Reuters"}


def tag_for(url, name):
    host = host_of(url)
    for domain, tag in KNOWN_TAGS.items():
        if host == domain or host.endswith("." + domain):
            return tag
    words = re.findall(r"[A-Za-z0-9]+", name or "") or re.findall(r"[A-Za-z0-9]+", host.split(".")[0])
    if not words:
        return "NEWS"
    if len(words) > 1 and len(words[0]) > 5:
        return "".join(word[0] for word in words[:4]).upper()
    return words[0][:5].upper()


def local(tag):
    return tag.rsplit("}", 1)[-1]


def child(node, *names):
    for item in node:
        if local(item.tag) in names:
            return item
    return None


def text_of(node, *names):
    item = child(node, *names)
    return (item.text or "") if item is not None else ""


def fetch_feed(source):
    url = source["url"]
    root = ET.fromstring(get(url, "application/rss+xml, application/atom+xml, application/xml, text/xml"))
    kind = local(root.tag)
    items = []
    if kind == "feed":
        title = clean(text_of(root, "title"))
        entries = [node for node in root if local(node.tag) == "entry"]
        for entry in entries:
            link = ""
            for node in entry:
                if local(node.tag) == "link" and node.get("rel", "alternate") == "alternate":
                    link = node.get("href", "")
                    break
            items.append((clean(text_of(entry, "title")), link, parse_time(text_of(entry, "published", "updated"))))
    else:
        channel = child(root, "channel")
        title = clean(text_of(channel, "title")) if channel is not None else ""
        nodes = [node for node in root.iter() if local(node.tag) == "item"]
        for node in nodes:
            link = text_of(node, "link").strip() or text_of(node, "guid").strip()
            items.append((clean(text_of(node, "title")), link, parse_time(text_of(node, "pubDate", "date", "published"))))
    tag = (source.get("tag") or tag_for(url, title or host_of(url)))[:5].upper()
    name = source.get("name") or KNOWN_NAMES.get(tag) or title or host_of(url)
    rows = [{"title": t, "url": link, "time": iso(when)} for t, link, when in items if t and link][:PER_FEED]
    if not rows:
        raise ValueError("it had no headlines")
    return {"id": url, "name": name, "tag": tag, "items": rows}


def fetch_wikipedia(_source):
    today = datetime.now(timezone.utc)
    data = None
    for back in (0, 1):
        day = today - timedelta(days=back)
        try:
            data = get_json(f"https://en.wikipedia.org/api/rest_v1/feed/featured/{day:%Y/%m/%d}")
        except urllib.error.HTTPError:
            continue
        if data.get("news") or data.get("mostread"):
            break
    if not data:
        raise ValueError("today's page was not there")
    rows = []
    for story in data.get("news", [])[:8]:
        links = story.get("links") or [{}]
        page = ((links[0].get("content_urls") or {}).get("desktop") or {}).get("page", "https://en.wikipedia.org/wiki/Portal:Current_events")
        rows.append({"title": clean(story.get("story")), "url": page, "time": None, "label": "TODAY"})
    for rank, article in enumerate((data.get("mostread") or {}).get("articles", [])[:5], start=1):
        name = clean(article.get("titles", {}).get("normalized") or article.get("title", "").replace("_", " "))
        about = clean(article.get("description"))
        page = ((article.get("content_urls") or {}).get("desktop") or {}).get("page", "")
        if name and page:
            rows.append({"title": f"{name}: {about}" if about else name, "url": page, "time": None, "label": f"TOP{rank}"})
    rows = [row for row in rows if row["title"]]
    if not rows:
        raise ValueError("it had no stories")
    return {"id": "wikipedia", "name": "Wikipedia", "tag": "WIKI", "items": rows}


def fetch_hackernews(_source):
    ids = get_json("https://hacker-news.firebaseio.com/v0/topstories.json")[:HN_COUNT]

    def item(story_id):
        try:
            return get_json(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        except (OSError, ValueError):
            return None

    with ThreadPoolExecutor(max_workers=10) as pool:
        stories = list(pool.map(item, ids))
    rows = []
    for story_id, story in zip(ids, stories):
        if not story or not story.get("title"):
            continue
        when = datetime.fromtimestamp(story["time"], tz=timezone.utc) if story.get("time") else None
        rows.append({
            "title": clean(story["title"]),
            "url": story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            "time": iso(when),
        })
    if not rows:
        raise ValueError("it had no stories")
    return {"id": "hackernews", "name": "Hacker News", "tag": "HN", "items": rows}


def fetch_guardian(source):
    key = os.environ.get(GUARDIAN_KEY, "").strip()
    if not key:
        raise ValueError(f"it needs a Guardian key in {GUARDIAN_KEY}")
    section = source["url"].partition(":")[2].strip()
    query = {"order-by": "newest", "page-size": str(PER_FEED), "api-key": key}
    if section:
        query["section"] = section
    data = get_json("https://content.guardianapis.com/search?" + urllib.parse.urlencode(query))
    results = (data.get("response") or {}).get("results") or []
    rows = [{"title": clean(r.get("webTitle")), "url": r.get("webUrl", ""), "time": r.get("webPublicationDate")} for r in results]
    rows = [row for row in rows if row["title"] and row["url"]]
    if not rows:
        raise ValueError("it had no headlines")
    name = f"The Guardian, {section.replace('-', ' ')}" if section else "The Guardian"
    return {"id": source["url"], "name": name, "tag": "GDN", "items": rows}


def describe(source):
    url = source["url"]
    if url == "wikipedia":
        return "Wikipedia", fetch_wikipedia
    if url == "hackernews":
        return "Hacker News", fetch_hackernews
    if url == "guardian" or url.startswith("guardian:"):
        return "The Guardian", fetch_guardian
    return url, fetch_feed


def fetch_weather(place):
    query = urllib.parse.urlencode({
        "latitude": place["lat"], "longitude": place["lon"],
        "current": "temperature_2m,weather_code,is_day",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "auto", "forecast_days": 1,
    })
    data = get_json(f"https://api.open-meteo.com/v1/forecast?{query}")
    current, daily = data.get("current") or {}, data.get("daily") or {}
    return {
        "temp": current.get("temperature_2m"),
        "code": current.get("weather_code"),
        "day": bool(current.get("is_day", 1)),
        "high": (daily.get("temperature_2m_max") or [None])[0],
        "low": (daily.get("temperature_2m_min") or [None])[0],
        "place": place.get("name", ""),
    }


def reason(error):
    if isinstance(error, urllib.error.HTTPError):
        return f"it answered {error.code}"
    if isinstance(error, urllib.error.URLError):
        return f"it could not be reached ({error.reason})"
    if isinstance(error, TimeoutError):
        return f"it did not answer within {TIMEOUT} seconds"
    if isinstance(error, ET.ParseError):
        return "it did not send a feed"
    return str(error) or error.__class__.__name__


def gather(inputs):
    sources = [{"url": s.strip()} if isinstance(s, str) else dict(s) for s in inputs["sources"]]
    jobs = [(source, *describe(source)) for source in sources]

    def run(job):
        source, label, fetch = job
        try:
            return label, fetch(source), None
        except Exception as error:  # a source that fails is left out and named, never fatal
            return label, None, reason(error)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, jobs))
        weather_job = pool.submit(fetch_weather, inputs["location"]) if inputs.get("location") else None
        weather, weather_problem = None, None
        if weather_job is not None:
            try:
                weather = weather_job.result()
            except Exception as error:
                weather_problem = reason(error)
    feeds = [feed for _, feed, _ in results if feed]
    missed = [(label, why) for label, _, why in results if why]
    return feeds, missed, weather, weather_problem


# Writing ------------------------------------------------------------------------------------------------------------

def main():
    inputs = read_inputs()
    check(inputs)
    config = {key: inputs[key] for key in KEYS}

    feeds, missed, weather, weather_problem = gather(inputs)

    out = Path.cwd() / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copy2(APP_DIR / "badge.js", out / "badge.js")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")

    # The run time is kept to the minute, so two runs a moment apart on the same news write the same file.
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    feed = {"updated": updated, "sources": feeds, "weather": weather}
    (out / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    count = sum(1 for path in out.rglob("*") if path.is_file())
    stories = sum(len(feed["items"]) for feed in feeds)
    print(f"Fetched {stories} headlines from {len(feeds)} of {len(feeds) + len(missed)} sources.")
    for label, why in missed:
        print(f"Left out {label}: {why}.")
    if weather_problem:
        print(f"Left out the weather line: Open-Meteo {weather_problem}.")
    if not feeds:
        print("No source answered, so the board shows its sample headlines until the next run.")
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
