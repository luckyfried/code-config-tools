"""Subscription Wall: writes out/subscription-wall/ from subscription-wall.inputs.json in the current folder.

Run from the person's project folder:
    cd <project> && python3 <agent-apps root>/subscription-wall/scripts/run.py

Reads <project>/subscription-wall.inputs.json, rolls every past nextCharge forward by its period, gives each service
a hue, ranks the charges by yearly cost, and writes the page with config.js, data.js, and theme.css beside it.
Standard library only; Python 3.12.
"""

import argparse
import calendar
import datetime
import json
import math
import re
import shutil
import sys
from pathlib import Path

SLUG = "subscription-wall"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"

TOP_KEYS = {"currency", "subscriptions", "categories", "sort", "theme"}
OPTIONAL_TOP = {"_notes"}
SUB_KEYS = {"name", "amount", "every", "nextCharge", "category"}
OPTIONAL_SUB = {"color"}
PERIODS = {"week": 52, "month": 12, "year": 1}
SORTS = ("cost", "renewal")
LARGE_TIER = 3
MEDIUM_TIER = 4
HUE_CLOSE = 20
HUE_NUDGE = 30


def fail(problems):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(2)


def fnv1a(text):
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def hex_to_hue(value):
    """The OKLCH hue angle of a #rrggbb color, so a brand color keeps its hue under the theme's lightness."""
    r, g, b = (int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = linear(r), linear(g), linear(b)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return round(math.degrees(math.atan2(bb, a)) % 360)


def hue_gap(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def add_months(date, months, anchor_day):
    total = date.year * 12 + (date.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    day = min(anchor_day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def roll_forward(date, every, today):
    """The first charge on or after today, stepping from date by the period; a month keeps its day where it exists."""
    anchor = date.day
    if every == "week":
        if date < today:
            steps = -(-(today - date).days // 7)
            date = date + datetime.timedelta(days=7 * steps)
        return date
    step = 12 if every == "year" else 1
    n = 0
    current = date
    while current < today:
        n += step
        current = add_months(date, n, anchor)
    return current


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "item"


def validate(inputs, path_name):
    problems = []
    if not isinstance(inputs, dict):
        fail([f"{path_name} must hold one JSON object with the keys currency, subscriptions, categories, sort, and theme."])
    for key in sorted(TOP_KEYS - inputs.keys()):
        problems.append(f'{path_name} is missing the key "{key}".')
    for key in sorted(inputs.keys() - TOP_KEYS - OPTIONAL_TOP):
        problems.append(f'{path_name} has the key "{key}", which Subscription Wall does not use.')

    currency = inputs.get("currency")
    if "currency" in inputs and not (isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency)):
        problems.append('"currency" must be a three-letter code such as "USD", "EUR", or "GBP".')

    categories = inputs.get("categories")
    if "categories" in inputs:
        if not (isinstance(categories, list) and all(isinstance(c, str) and c.strip() for c in categories)):
            problems.append('"categories" must be a list of names, such as ["Streaming", "Music"].')
            categories = None
        elif len(set(categories)) != len(categories):
            problems.append('"categories" names the same category twice.')

    sort = inputs.get("sort")
    if "sort" in inputs and sort not in SORTS:
        problems.append('"sort" must be "cost" or "renewal".')

    theme = inputs.get("theme")
    names = sorted(p.stem for p in THEMES.glob("*.css"))
    if "theme" in inputs and (not isinstance(theme, str) or theme not in names):
        problems.append(f'"theme" must be one of: {", ".join(names)}.')

    subs = inputs.get("subscriptions")
    if "subscriptions" in inputs:
        if not isinstance(subs, list):
            problems.append('"subscriptions" must be a list, one entry per recurring charge.')
        else:
            for i, sub in enumerate(subs, 1):
                label = f"Subscription {i}"
                if not isinstance(sub, dict):
                    problems.append(f"{label} must be an object with name, amount, every, nextCharge, and category.")
                    continue
                if isinstance(sub.get("name"), str) and sub["name"].strip():
                    label = f'Subscription "{sub["name"]}"'
                for key in sorted(SUB_KEYS - sub.keys()):
                    problems.append(f'{label} is missing the key "{key}".')
                for key in sorted(sub.keys() - SUB_KEYS - OPTIONAL_SUB):
                    problems.append(f'{label} has the key "{key}", which Subscription Wall does not use.')
                if "name" in sub and not (isinstance(sub["name"], str) and sub["name"].strip()):
                    problems.append(f'{label} needs a "name" that is not empty.')
                amount = sub.get("amount")
                if "amount" in sub and (isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0):
                    problems.append(f'{label} needs an "amount" that is a number above zero, such as 15.49.')
                if "every" in sub and sub["every"] not in PERIODS:
                    problems.append(f'{label} needs "every" to be "week", "month", or "year".')
                if "nextCharge" in sub:
                    try:
                        datetime.date.fromisoformat(sub["nextCharge"])
                        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sub["nextCharge"]):
                            raise ValueError
                    except (TypeError, ValueError):
                        problems.append(f'{label} needs "nextCharge" as a date written YYYY-MM-DD, such as 2026-11-03.')
                if "category" in sub and isinstance(categories, list) and sub["category"] not in categories:
                    problems.append(f'{label} names the category "{sub["category"]}", which is not in "categories".')
                color = sub.get("color")
                if "color" in sub and not (isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color)):
                    problems.append(f'{label} has a "color" that is not written #rrggbb, such as "#e50914".')
    if problems:
        fail(problems)


def build_data(inputs, today):
    subs = []
    seen = set()
    for sub in inputs["subscriptions"]:
        base = slugify(sub["name"])
        sid, n = base, 2
        while sid in seen:
            sid, n = f"{base}-{n}", n + 1
        seen.add(sid)
        first = datetime.date.fromisoformat(sub["nextCharge"])
        nxt = roll_forward(first, sub["every"], today)
        cents = round(sub["amount"] * 100)
        explicit = "color" in sub
        subs.append({
            "id": sid,
            "name": sub["name"].strip(),
            "amount": cents / 100,
            "every": sub["every"],
            "nextCharge": nxt.isoformat(),
            "day": first.day,
            "category": sub["category"],
            "hue": hex_to_hue(sub["color"]) if explicit else fnv1a(sub["name"].strip().lower()) % 360,
            "fixedHue": explicit,
            "yearlyCents": cents * PERIODS[sub["every"]],
        })

    by_cost = sorted(subs, key=lambda s: (-s["yearlyCents"], s["name"].lower()))
    for rank, s in enumerate(by_cost, 1):
        s["rank"] = rank
        s["tier"] = "l" if rank <= LARGE_TIER else "m" if rank <= LARGE_TIER + MEDIUM_TIER else "s"

    if inputs["sort"] == "renewal":
        ordered = sorted(subs, key=lambda s: (s["nextCharge"], s["rank"]))
    else:
        ordered = by_cost

    for prev, s in zip(ordered, ordered[1:]):
        if not s["fixedHue"] and hue_gap(prev["hue"], s["hue"]) < HUE_CLOSE:
            away = 1 if (s["hue"] - prev["hue"]) % 360 < 180 else -1
            s["hue"] = (s["hue"] + away * HUE_NUDGE) % 360
    for s in ordered:
        del s["fixedHue"]

    yearly_cents = sum(s["yearlyCents"] for s in ordered)
    assert yearly_cents == sum(round(sub["amount"] * 100) * PERIODS[sub["every"]] for sub in inputs["subscriptions"])
    assert all(s["nextCharge"] >= today.isoformat() for s in ordered)
    return {
        "today": today.isoformat(),
        "currency": inputs["currency"],
        "sort": inputs["sort"],
        "categories": inputs["categories"],
        "yearlyCents": yearly_cents,
        "subscriptions": ordered,
    }


def main():
    parser = argparse.ArgumentParser(description="Write the Subscription Wall page from subscription-wall.inputs.json.")
    parser.add_argument("--today", help="the date to roll charges forward to, YYYY-MM-DD; today when left out")
    args = parser.parse_args()

    project = Path.cwd()
    inputs_path = project / f"{SLUG}.inputs.json"
    if not inputs_path.is_file():
        fail([f"Make {SLUG}.inputs.json in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail([f"{inputs_path.name} is not valid JSON: line {e.lineno}, column {e.colno}, {e.msg.lower()}."])
    validate(inputs, inputs_path.name)

    try:
        today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    except ValueError:
        fail(["--today must be a date written YYYY-MM-DD."])

    data = build_data(inputs, today)
    yearly = f"{data['yearlyCents'] // 100}.{data['yearlyCents'] % 100:02d}"

    out = project / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)

    index = out / "index.html"
    html = index.read_text(encoding="utf-8")
    assert html.count('data-yearly=""') == 1
    index.write_text(html.replace('data-yearly=""', f'data-yearly="{yearly}"'), encoding="utf-8")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(inputs, ensure_ascii=False)};\n", encoding="utf-8")
    (out / "data.js").write_text(f"window.__APP_DATA__ = {json.dumps(data, ensure_ascii=False)};\n", encoding="utf-8")

    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")


if __name__ == "__main__":
    main()
