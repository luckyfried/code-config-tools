"""Writes the Event Page from event-page.inputs.json in the current folder.

Run from the project folder:  python3 <agent-apps root>/event-page/scripts/run.py
Reads event-page.inputs.json and the photos folder it names; writes out/event-page/ with index.html, config.js,
theme.css, event.ics, and the photos under media/.
"""

import datetime as dt
import html
import json
import re
import shutil
import struct
import sys
from pathlib import Path
from urllib.parse import quote

SLUG = "event-page"
NAME = f"{SLUG}.inputs.json"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"

KINDS = ("wedding", "birthday", "party", "reunion")
KEYS = {"names", "kind", "line", "date", "place", "schedule", "story", "photos", "stay", "registryUrl", "rsvp", "theme", "_notes"}
REQUIRED = ("names", "kind", "date", "place", "rsvp")
PLACE_KEYS = {"name", "address", "lat", "lon"}
RSVP_KEYS = {"phone", "email", "deadline"}
STAY_KEYS = {"name", "url", "note"}
STOP_KEYS = {"time", "what"}
PHOTO_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

LINES = {
    "wedding": ("is getting married", "are getting married"),
    "birthday": ("invites you to a birthday", "invite you to a birthday"),
    "party": ("invites you to a party", "invite you to a party"),
    "reunion": ("is getting together again", "are getting together again"),
}
STORY_HEADING = {"wedding": "Our story", "birthday": "The story", "party": "The story", "reunion": "Where we have been"}
DAY_HEADING = {"wedding": "The day", "birthday": "The plan", "party": "The night", "reunion": "The plan"}
SUMMARY = {"wedding": "wedding", "birthday": "birthday", "party": "party", "reunion": "reunion"}


def fail(problems):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(2)


def text(value):
    return isinstance(value, str) and value.strip() != ""


def esc(value):
    return html.escape(str(value).strip(), quote=True)


def parse_date(value):
    for form in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value.strip(), form), form != "%Y-%m-%d"
        except ValueError:
            pass
    return None, False


def validate(data):
    problems = []
    if not isinstance(data, dict):
        fail([f"{NAME} must hold one object with the keys names, kind, date, place, and rsvp."])
    for key in data:
        if key not in KEYS:
            problems.append(f'{NAME} has the key "{key}", which this app does not use.')
    for key in REQUIRED:
        if key not in data:
            problems.append(f'{NAME} is missing the key "{key}".')

    names = data.get("names")
    if "names" in data and (not isinstance(names, list) or not names or not all(text(n) for n in names)):
        problems.append(f'In {NAME}, "names" must be a list of one to four names, like ["Iris", "Theo"].')
    elif isinstance(names, list) and len(names) > 4:
        problems.append(f'In {NAME}, "names" holds {len(names)} names; the page shows one to four.')

    if "kind" in data and data["kind"] not in KINDS:
        problems.append(f'In {NAME}, "kind" is "{data["kind"]}"; it is wedding, birthday, party, or reunion.')
    if "line" in data and not text(data["line"]):
        problems.append(f'In {NAME}, "line" must be some text, like "are getting married".')

    if "date" in data:
        if not text(data["date"]) or parse_date(data["date"])[0] is None:
            problems.append(f'In {NAME}, "date" must look like 2027-06-12T16:30 (or 2027-06-12 with no time).')

    place = data.get("place")
    if "place" in data:
        if not isinstance(place, dict):
            problems.append(f'In {NAME}, "place" must be an object with a name and an address.')
        else:
            for key in place:
                if key not in PLACE_KEYS:
                    problems.append(f'In {NAME}, "place" has the key "{key}"; it takes name, address, lat, and lon.')
            for key in ("name", "address"):
                if not text(place.get(key)):
                    problems.append(f'In {NAME}, "place" is missing its "{key}".')
            has_lat, has_lon = "lat" in place, "lon" in place
            if has_lat != has_lon:
                problems.append(f'In {NAME}, "place" needs both "lat" and "lon", or neither.')
            for key, limit in (("lat", 90), ("lon", 180)):
                if key in place and (not isinstance(place[key], (int, float)) or isinstance(place[key], bool)
                                     or abs(place[key]) > limit):
                    problems.append(f'In {NAME}, "place.{key}" must be a number between -{limit} and {limit}.')

    rsvp = data.get("rsvp")
    if "rsvp" in data:
        if not isinstance(rsvp, dict):
            problems.append(f'In {NAME}, "rsvp" must be an object with a phone, an email, or both.')
        else:
            for key in rsvp:
                if key not in RSVP_KEYS:
                    problems.append(f'In {NAME}, "rsvp" has the key "{key}"; it takes phone, email, and deadline.')
            if not text(rsvp.get("phone")) and not text(rsvp.get("email")):
                problems.append(f'In {NAME}, "rsvp" needs a "phone" or an "email" for guests to reply to.')
            if "email" in rsvp and (not text(rsvp["email"]) or "@" not in rsvp["email"]):
                problems.append(f'In {NAME}, "rsvp.email" must be an email address.')
            if "phone" in rsvp and (not text(rsvp["phone"]) or not re.search(r"\d{3}", rsvp["phone"])):
                problems.append(f'In {NAME}, "rsvp.phone" must be a phone number.')
            if "deadline" in rsvp and (not text(rsvp["deadline"]) or parse_date(rsvp["deadline"])[0] is None):
                problems.append(f'In {NAME}, "rsvp.deadline" must look like 2027-05-01.')

    schedule = data.get("schedule", [])
    if not isinstance(schedule, list):
        problems.append(f'In {NAME}, "schedule" must be a list of {{"time", "what"}} stops.')
    else:
        for n, stop in enumerate(schedule, 1):
            if not isinstance(stop, dict) or not text(stop.get("time")) or not text(stop.get("what")):
                problems.append(f'In {NAME}, schedule stop {n} needs a "time" and a "what".')
            elif set(stop) - STOP_KEYS:
                problems.append(f'In {NAME}, schedule stop {n} takes only "time" and "what".')

    stay = data.get("stay", [])
    if not isinstance(stay, list):
        problems.append(f'In {NAME}, "stay" must be a list of {{"name", "url", "note"}} places.')
    else:
        for n, item in enumerate(stay, 1):
            if not isinstance(item, dict) or not text(item.get("name")):
                problems.append(f'In {NAME}, stay {n} needs a "name".')
            elif set(item) - STAY_KEYS:
                problems.append(f'In {NAME}, stay {n} takes name, url, and note.')
            elif "url" in item and not str(item["url"]).startswith(("https://", "http://")):
                problems.append(f'In {NAME}, stay {n} has the address "{item["url"]}"; it starts with https://.')

    if "story" in data and not isinstance(data["story"], str):
        problems.append(f'In {NAME}, "story" must be some text; a blank line starts a new paragraph.')
    if "registryUrl" in data and (not text(data["registryUrl"])
                                  or not data["registryUrl"].startswith(("https://", "http://"))):
        problems.append(f'In {NAME}, "registryUrl" must be a web address starting with https://.')
    if "photos" in data:
        if not text(data["photos"]):
            problems.append(f'In {NAME}, "photos" must name a folder of pictures beside the inputs file.')
        elif not (Path.cwd() / data["photos"]).is_dir():
            problems.append(f'The photos folder "{data["photos"]}" is not in this folder.')

    theme = data.get("theme", "ivory")
    themes = sorted(p.stem for p in THEMES.glob("*.css"))
    if theme not in themes:
        problems.append(f'In {NAME}, "theme" is "{theme}"; the themes are {", ".join(themes)}.')
    if problems:
        fail(problems)


def image_size(path):
    """Reads the pixel size from a JPEG, PNG, GIF, or WebP header; None when the header is not one of those."""
    data = path.read_bytes()[:262144]
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
        if chunk == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if chunk == b"VP8L":
            b = int.from_bytes(data[21:25], "little")
            return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def caption(stem):
    words = re.sub(r"^[\d\s._-]+", "", stem).replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:] if words else ""


def copy_photos(data, out):
    folder = data.get("photos")
    if not folder:
        return []
    src = Path.cwd() / folder
    media = out / "media"
    media.mkdir(exist_ok=True)
    photos = []
    for path in sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in PHOTO_TYPES):
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", path.name)
        shutil.copyfile(path, media / safe)
        size = image_size(path) or (1600, 1067)
        photos.append({"src": f"media/{safe}", "w": size[0], "h": size[1], "caption": caption(path.stem)})
    return photos


def join_names(names):
    names = [n.strip() for n in names]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " & " + names[-1]


def clock(when):
    hour = when.hour % 12 or 12
    return f"{hour}:{when.minute:02d} {'am' if when.hour < 12 else 'pm'}"


def long_date(when):
    return f"{DAYS[when.weekday()]}, {MONTHS[when.month - 1]} {when.day}, {when.year}"


def phone_digits(phone):
    return re.sub(r"[^\d+]", "", phone)


def maps_links(place):
    q = quote(place["address"].strip())
    links = {
        "apple": f"https://maps.apple.com/?daddr={q}",
        "google": f"https://www.google.com/maps/dir/?api=1&destination={q}",
        "geo": f"geo:0,0?q={q}",
    }
    if "lat" in place:
        lat, lon = place["lat"], place["lon"]
        label = quote(place["name"].strip())
        links["apple"] = f"https://maps.apple.com/?daddr={lat},{lon}&q={label}"
        links["google"] = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
        links["geo"] = f"geo:{lat},{lon}?q={lat},{lon}({label})"
    return links


ICON = {
    "pin": '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z"/><circle cx="12" cy="10" r="2.4"/>',
    "cal": '<rect x="4" y="5.5" width="16" height="14.5" rx="2.5"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    "gift": '<rect x="4" y="9" width="16" height="11" rx="2"/><path d="M3 9h18M12 9v11M12 9c-1.5-3.5-6-4-6-1.5S10 9 12 9Zm0 0c1.5-3.5 6-4 6-1.5S14 9 12 9Z"/>',
    "bed": '<path d="M3 18V7M3 14h18v4M21 14v-2.5a3 3 0 0 0-3-3h-7v5.5"/><circle cx="7" cy="11" r="1.8"/>',
    "chat": '<path d="M5 18.5 3.5 21l.7-4A8 8 0 1 1 8 19.6"/>',
    "mail": '<rect x="3.5" y="5.5" width="17" height="13" rx="2.5"/><path d="m4.5 7 7.5 6 7.5-6"/>',
    "list": '<path d="M8 7h12M8 12h12M8 17h12M4 7h.01M4 12h.01M4 17h.01"/>',
    "out": '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
}


def icon(name):
    return (f'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{ICON[name]}</svg>')


def render(data, photos, when, timed):
    kind = data["kind"]
    names = [n.strip() for n in data["names"]]
    plural = len(names) > 1
    line = data.get("line") or LINES[kind][1 if plural else 0]
    place = data["place"]
    rsvp = data["rsvp"]
    schedule = data.get("schedule", [])
    stay = data.get("stay", [])
    links = maps_links(place)
    out = []

    mark = " & ".join(n[0] for n in names) if len(names) <= 3 else names[0]
    out.append('<header class="bar" data-bar>')
    out.append(f'<a class="bar__mark" href="#top" aria-label="Back to the top">{esc(mark)}</a>')
    nav = []
    if data.get("story", "").strip() or photos:
        nav.append(("#story", "Story"))
    if schedule:
        nav.append(("#schedule", "Schedule"))
    nav.append(("#place", "Place"))
    if stay:
        nav.append(("#stay", "Stay"))
    out.append('<nav class="bar__nav" aria-label="Sections"><ul>')
    out += [f'<li><a href="{h}">{t}</a></li>' for h, t in nav]
    out.append("</ul></nav>")
    out.append('<a class="button button--accent bar__reply" href="#reply">Reply</a>')
    out.append("</header>")

    out.append('<main id="top">')
    # The hero: names, the date in digits, the countdown.
    name_html = []
    for i, n in enumerate(names):
        if i:
            name_html.append('<span class="names__amp" aria-hidden="true">&amp;</span>' if i == len(names) - 1
                             else '<span class="names__amp names__amp--comma" aria-hidden="true">,</span>')
        letters = "".join(f'<span class="ch">{esc(c) if c != " " else "&nbsp;"}</span>' for c in n)
        name_html.append(f'<span class="names__name" aria-hidden="true">{letters}</span>')
    digits = f"{when.month:02d}{when.day:02d}{when.year:04d}"
    cells = []
    for i, d in enumerate(digits):
        if i in (2, 4):
            cells.append('<span class="date__rule" aria-hidden="true"></span>')
        cells.append(f'<span class="date__cell" aria-hidden="true"><span class="date__digit">{d}</span></span>')
    when_text = long_date(when) + (f", at {clock(when)}" if timed else "")
    out += [
        '<section class="hero" data-hero>',
        '<div class="hero__stage" data-stage>',
        '<div class="hero__copy" data-hero-copy>',
        f'<h1 class="names"><span class="visually-hidden">{esc(join_names(names))}</span>{"".join(name_html)}</h1>',
        f'<p class="hero__line">{esc(line)}</p>',
        f'<div class="date" data-date role="img" aria-label="{esc(long_date(when))}">{"".join(cells)}</div>',
        f'<p class="hero__when"><time datetime="{when.isoformat(timespec="minutes") if timed else when.date().isoformat()}">'
        f'{esc(when_text)}</time><span class="hero__where">{esc(place["name"])}</span></p>',
        "</div>",
        '<div class="countdown" data-countdown aria-live="off">',
    ]
    for unit, n in (("days", 3), ("hours", 2), ("minutes", 2), ("seconds", 2)):
        tiles = "".join(
            '<span class="flip"><span class="flip__half flip__half--top"><span class="flip__num">0</span></span>'
            '<span class="flip__half flip__half--bottom"><span class="flip__num">0</span></span></span>'
            for _ in range(n)
        )
        out.append(f'<div class="countdown__unit" data-unit="{unit}"><div class="countdown__tiles">{tiles}</div>'
                   f'<span class="countdown__label">{unit}</span></div>')
    out += ["</div>", '<a class="hero__cue" href="#story" data-cue>Scroll</a>', "</div>", "</section>"]

    story = [p.strip() for p in re.split(r"\n\s*\n", data.get("story", "")) if p.strip()]
    if story or photos:
        out.append('<section class="story" id="story" data-section>')
        out.append('<div class="story__text">')
        out.append(f'<h2 class="heading">{STORY_HEADING[kind]}</h2>')
        out += [f'<p class="story__p">{esc(p)}</p>' for p in story]
        out.append("</div>")
        if photos:
            out.append('<div class="gallery">')
            for i, ph in enumerate(photos):
                tall = " photo--tall" if ph["h"] > ph["w"] else ""
                out.append(
                    f'<figure class="photo{tall}" data-photo><div class="photo__frame">'
                    f'<img class="photo__img" src="{esc(ph["src"])}" width="{ph["w"]}" height="{ph["h"]}" '
                    f'alt="{esc(ph["caption"])}" loading="{"eager" if i < 2 else "lazy"}" decoding="async"></div>'
                    f'<figcaption class="photo__caption">{esc(ph["caption"])}</figcaption></figure>'
                )
            out.append("</div>")
        out.append("</section>")

    def stops_html(extra=""):
        rows = [f'<ol class="timeline{extra}">']
        for stop in schedule:
            rows.append(f'<li class="stop"><span class="stop__dot" aria-hidden="true"></span>'
                        f'<span class="stop__time">{esc(stop["time"])}</span>'
                        f'<span class="stop__what">{esc(stop["what"])}</span></li>')
        rows.append("</ol>")
        return rows

    if schedule:
        out.append('<section class="schedule" id="schedule" data-section data-schedule>')
        out.append(f'<div class="schedule__head"><h2 class="heading">{DAY_HEADING[kind]}</h2>'
                   f'<p class="schedule__date">{esc(long_date(when))}</p></div>')
        out.append('<div class="schedule__body"><div class="timeline__track" aria-hidden="true">'
                   '<span class="timeline__ink" data-ink></span></div>')
        out += stops_html()
        out.append("</div></section>")

    has_map = "lat" in place
    out.append(f'<section class="place{"" if has_map else " place--card"}" id="place" data-section data-place>')
    if has_map:
        out.append('<div class="place__map" data-map-wrap><div class="map" data-map>'
                   '<svg class="map__svg" data-map-svg viewBox="0 0 1000 700" preserveAspectRatio="xMidYMid slice" '
                   f'role="img" aria-label="A map to {esc(place["name"])}"></svg>'
                   f'<div class="map__pin" data-pin><span class="map__pin-head">{icon("pin")}</span>'
                   '<span class="map__pin-shadow"></span></div>'
                   f'<span class="map__label" data-pin-label>{esc(place["name"])}</span></div></div>')
    out.append('<div class="place__info">')
    out.append('<h2 class="heading">The place</h2>')
    out.append(f'<p class="place__name">{esc(place["name"])}</p>')
    out.append(f'<address class="place__address">{esc(place["address"])}</address>')
    out.append('<div class="place__links">')
    out.append(f'<a class="button button--accent" href="{esc(links["google"])}" data-maps="google">{icon("pin")}Directions in Google Maps</a>')
    out.append(f'<a class="button" href="{esc(links["apple"])}" data-maps="apple">{icon("pin")}Apple Maps</a>')
    out.append(f'<a class="button" href="{esc(links["geo"])}" data-maps="geo" hidden>{icon("pin")}Open in Maps</a>')
    out.append("</div></div></section>")

    out.append('<section class="extras" id="stay" data-section>')
    if stay:
        out.append('<div class="stay"><h2 class="heading">Where to stay</h2><ul class="stays">')
        for item in stay:
            inner = f'<span class="stays__name">{esc(item["name"])}</span>'
            if text(item.get("note")):
                inner += f'<span class="stays__note">{esc(item["note"])}</span>'
            if text(item.get("url")):
                out.append(f'<li><a class="stays__item" href="{esc(item["url"])}">{icon("bed")}'
                           f'<span class="stays__text">{inner}</span>{icon("out")}</a></li>')
            else:
                out.append(f'<li><div class="stays__item">{icon("bed")}<span class="stays__text">{inner}</span></div></li>')
        out.append("</ul></div>")
    out.append('<div class="keep">')
    out.append(f'<a class="keep__tile" href="event.ics" download="{esc(file_stem(names, kind))}.ics">{icon("cal")}'
               f'<span class="keep__title">Add to calendar</span>'
               f'<span class="keep__note">{esc(long_date(when))}</span></a>')
    if text(data.get("registryUrl")):
        out.append(f'<a class="keep__tile" href="{esc(data["registryUrl"])}">{icon("gift")}'
                   '<span class="keep__title">Registry</span>'
                   '<span class="keep__note">The gift list</span></a>')
    out.append("</div></section>")

    # The reply: a short form whose buttons open a filled text or email to the host.
    phone, email = rsvp.get("phone", "").strip(), rsvp.get("email", "").strip()
    deadline = parse_date(rsvp["deadline"])[0] if text(rsvp.get("deadline")) else None
    out.append('<section class="reply" id="reply" data-section>')
    out.append('<div class="reply__head"><h2 class="heading">Will you come?</h2>')
    if deadline:
        out.append(f'<p class="reply__by">Please reply by {MONTHS[deadline.month - 1]} {deadline.day}, {deadline.year}.</p>')
    out.append("</div>")
    out.append('<form class="rsvp" data-rsvp novalidate>')
    out.append('<fieldset class="rsvp__answer"><legend class="rsvp__legend">Your answer</legend>'
               '<label class="choice"><input type="radio" name="answer" value="yes" checked><span>We&#39;ll be there</span></label>'
               '<label class="choice"><input type="radio" name="answer" value="no"><span>Can&#39;t make it</span></label>'
               "</fieldset>")
    out.append('<label class="field"><span class="field__label">Your names</span>'
               '<input class="field__input" name="names" autocomplete="name" placeholder="Ana and Ben Ruiz"></label>')
    out.append('<div class="field stepper-field"><span class="field__label" id="count-label">How many of you</span>'
               '<div class="stepper" role="group" aria-labelledby="count-label">'
               '<button class="stepper__btn" type="button" data-step="-1" aria-label="One fewer">&minus;</button>'
               '<output class="stepper__value" name="count" data-count>2</output>'
               '<button class="stepper__btn" type="button" data-step="1" aria-label="One more">+</button></div></div>')
    out.append('<label class="field field--wide"><span class="field__label">A note</span>'
               '<textarea class="field__input" name="note" rows="3" placeholder="A song for the dance floor, a food we should know about"></textarea></label>')
    out.append('<div class="rsvp__send">')
    if phone:
        out.append(f'<a class="button button--accent button--big" data-send="sms" href="sms:{esc(phone_digits(phone))}">{icon("chat")}Send by text</a>')
    if email:
        cls = "button button--big" + ("" if phone else " button--accent")
        out.append(f'<a class="{cls}" data-send="email" href="mailto:{esc(email)}">{icon("mail")}Send by email</a>')
    out.append("</div>")
    out.append('<p class="rsvp__after">Your reply opens as a message to the hosts. Send it from there.</p>')
    out.append("</form></section>")

    out.append(f'<footer class="foot"><p class="foot__names">{esc(join_names(names))}</p>'
               f'<p class="foot__when">{esc(long_date(when))}, {esc(place["name"])}</p></footer>')
    out.append("</main>")

    # Phones: a bottom bar with the Details sheet (the schedule and the stay list) and the reply.
    out.append('<div class="dock" data-dock>')
    if schedule or stay:
        out.append(f'<button class="button dock__btn" type="button" data-open-sheet>{icon("list")}Details</button>')
    out.append(f'<a class="button button--accent dock__btn" href="#reply">{icon("chat")}Reply</a></div>')
    if schedule or stay:
        out.append('<dialog class="sheet" data-sheet aria-labelledby="sheet-title"><div class="sheet__panel">')
        out.append('<div class="sheet__grip" aria-hidden="true"></div>')
        out.append(f'<div class="sheet__top"><h2 class="sheet__title" id="sheet-title">Details</h2>'
                   f'<button class="sheet__close" type="button" data-close-sheet aria-label="Close">{icon("x")}</button></div>')
        if schedule:
            out.append(f'<h3 class="sheet__h">{DAY_HEADING[kind]}</h3>')
            out += stops_html(" timeline--compact")
        if stay:
            out.append('<h3 class="sheet__h">Where to stay</h3><ul class="sheet__stays">')
            for item in stay:
                note = f'<span class="stays__note">{esc(item["note"])}</span>' if text(item.get("note")) else ""
                name = (f'<a href="{esc(item["url"])}">{esc(item["name"])}</a>' if text(item.get("url"))
                        else esc(item["name"]))
                out.append(f'<li><span class="stays__name">{name}</span>{note}</li>')
            out.append("</ul>")
        out.append(f'<p class="sheet__place">{esc(place["name"])}<br>{esc(place["address"])}</p>')
        out.append("</div></dialog>")
    return "\n".join(out)


def file_stem(names, kind):
    base = "-".join(re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-") for n in names)
    return f"{base}-{kind}".strip("-") or "event"


def ics_text(value):
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def fold(line):
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, current = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > (75 if not parts else 74):
            parts.append(current.decode("utf-8"))
            current = b""
        current += b
    parts.append(current.decode("utf-8"))
    return "\r\n ".join(parts)


def render_ics(data, when, timed):
    names = [n.strip() for n in data["names"]]
    place = data["place"]
    title = f"{join_names(names)}'s {SUMMARY[data['kind']]}"
    stamp = when.strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Code Config//Event Page//EN", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH", "BEGIN:VEVENT",
        f"UID:{file_stem(names, data['kind'])}-{when.strftime('%Y%m%d')}@event-page",
        f"DTSTAMP:{stamp}",
    ]
    if timed:
        lines.append(f"DTSTART:{when.strftime('%Y%m%dT%H%M%S')}")
        lines.append(f"DTEND:{(when + dt.timedelta(hours=6)).strftime('%Y%m%dT%H%M%S')}")
    else:
        lines.append(f"DTSTART;VALUE=DATE:{when.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{(when + dt.timedelta(days=1)).strftime('%Y%m%d')}")
    lines.append(f"SUMMARY:{ics_text(title)}")
    lines.append(f"LOCATION:{ics_text(place['name'].strip() + ', ' + place['address'].strip())}")
    if "lat" in place:
        lines.append(f"GEO:{place['lat']};{place['lon']}")
    stops = [f"{s['time'].strip()}  {s['what'].strip()}" for s in data.get("schedule", [])]
    if stops:
        lines.append(f"DESCRIPTION:{ics_text(chr(10).join(stops))}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(fold(line) for line in lines) + "\r\n"


def fill(page, marker, value):
    if page.count(marker) != 1:
        fail([f"The page template in {SITE} is missing its {marker!r} slot; reinstall the app folder."])
    return page.replace(marker, value)


def main():
    inputs = Path.cwd() / NAME
    if not inputs.is_file():
        fail([f"Make {NAME} in this folder first; inputs.example.json shows every key."])
    try:
        data = json.loads(inputs.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        fail([f"{NAME} is not valid JSON: {err.msg} on line {err.lineno}."])
    validate(data)
    when, timed = parse_date(data["date"])

    out = Path.cwd() / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    (out / "config.js").unlink(missing_ok=True)
    shutil.rmtree(out / "themes")

    photos = copy_photos(data, out)
    theme = data.get("theme", "ivory")
    shutil.copyfile(THEMES / f"{theme}.css", out / "theme.css")

    names = [n.strip() for n in data["names"]]
    config = {key: value for key, value in data.items() if key != "_notes"}
    config["photos"] = photos
    config["theme"] = theme
    config["date"] = when.isoformat(timespec="minutes") if timed else when.date().isoformat()
    config["timed"] = timed
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config)};\n", encoding="utf-8")

    page = (SITE / "index.html").read_text(encoding="utf-8")
    title = f"{join_names(names)}, {long_date(when)}"
    page = fill(page, "<title>Event Page</title>", f"<title>{esc(title)}</title>")
    page = fill(page, '<meta name="description" content="">',
                f'<meta name="description" content="{esc(data.get("line") or LINES[data["kind"]][1 if len(names) > 1 else 0])}'
                f', {esc(long_date(when))}, {esc(data["place"]["name"])}.">')
    page = fill(page, '<body class="kind-wedding">', f'<body class="kind-{data["kind"]}">')
    page = fill(page, "<!-- page -->", render(data, photos, when, timed))
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "event.ics").write_bytes(render_ics(data, when, timed).encode("utf-8"))

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")


if __name__ == "__main__":
    main()
