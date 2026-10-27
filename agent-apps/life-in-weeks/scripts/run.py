"""Write Life in Weeks for the project in the current folder.

Reads life-in-weeks.inputs.json from the current folder, checks it, copies the page from site/ into
out/life-in-weeks/, and writes config.js (the inputs), data.js (the life worked out into weeks), and
theme.css (the chosen theme) beside index.html. Two runs on the same inputs on the same day give the
same files.

    cd <project> && python3 <agent-apps root>/life-in-weeks/scripts/run.py
"""

import argparse
import json
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

APP = "life-in-weeks"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
BADGE = APP_DIR / "badge.js"
SRC = f"{APP}.inputs.json"

WEEKS = 52
KEYS = {"name", "birthdate", "years", "eras", "events", "quote", "paper", "theme", "_notes"}
REQUIRED = ("name", "birthdate", "eras")
ERA_KEYS = {"from", "to", "label", "color"}
EVENT_KEYS = {"date", "label"}
PAPERS = ("A2", "A3", "A4", "Letter")
MAX_ERAS = 8
MIN_YEARS, MAX_YEARS = 40, 120
DAY = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def parse_day(text, end=False):
    """A date from YYYY, YYYY-MM, or YYYY-MM-DD: the first day of that span, or its last day with end=True."""
    if not isinstance(text, str):
        return None
    match = DAY.match(text.strip())
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2)) if match.group(2) else None
    day = int(match.group(3)) if match.group(3) else None
    try:
        if month is None:
            return date(year, 12, 31) if end else date(year, 1, 1)
        if day is None:
            if not end:
                return date(year, month, 1)
            following = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
            return following - timedelta(days=1)
        return date(year, month, day)
    except ValueError:
        return None


def birthday(born, age):
    """The day `born` turns `age`; a 29 February birthday falls on 1 March in other years."""
    year = born.year + age
    try:
        return date(year, born.month, born.day)
    except ValueError:
        return date(year, 3, 1)


def cell_of(born, day):
    """(row, column) of the week `day` falls in: the row is the age, the column the week since that birthday."""
    age = day.year - born.year
    if day < birthday(born, age):
        age -= 1
    week = min(WEEKS - 1, (day - birthday(born, age)).days // 7)
    return age, week


def index_of(born, day):
    row, col = cell_of(born, day)
    return row * WEEKS + col


def check(inputs, theme_names):
    problems = []

    for key in sorted(set(inputs) - KEYS):
        problems.append(f'{SRC} has a key this app does not use: "{key}".')
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{SRC} is missing the key "{key}".')

    if "name" in inputs and not is_text(inputs["name"]):
        problems.append(f'"name" in {SRC} must be some text, such as "Ines Halvorsen".')

    born = None
    if "birthdate" in inputs:
        text = inputs["birthdate"]
        born = parse_day(text) if isinstance(text, str) and len(text.strip()) == 10 else None
        if born is None:
            problems.append(f'"birthdate" in {SRC} must be a date written YYYY-MM-DD, such as "1991-03-14".')
        elif born > date.today():
            problems.append(f'"birthdate" in {SRC} is {text}, which has not happened yet.')
            born = None

    years = inputs.get("years", 90)
    if not isinstance(years, int) or isinstance(years, bool) or not MIN_YEARS <= years <= MAX_YEARS:
        problems.append(f'"years" in {SRC} must be a whole number of rows from {MIN_YEARS} to {MAX_YEARS}, such as 90.')
        years = None

    last = None
    if born is not None and years is not None:
        last = birthday(born, years) - timedelta(days=1)

    eras = inputs.get("eras")
    if eras is not None:
        if not isinstance(eras, list):
            problems.append(f'"eras" in {SRC} must be a list of eras, each with from, to, label, and color.')
        elif len(eras) > MAX_ERAS:
            problems.append(f'"eras" in {SRC} lists {len(eras)} eras; the poster holds up to {MAX_ERAS}.')
        else:
            for n, era in enumerate(eras, start=1):
                where = f"Era {n} in {SRC}"
                if not isinstance(era, dict):
                    problems.append(f"{where} must be an object with from, to, label, and color.")
                    continue
                if is_text(era.get("label")):
                    where = f'The era "{era["label"]}" in {SRC}'
                for key in ("from", "to", "label", "color"):
                    if key not in era:
                        problems.append(f'{where} is missing "{key}".')
                for key in sorted(set(era) - ERA_KEYS):
                    problems.append(f'{where} has a key this app does not use: "{key}".')
                if "label" in era and not is_text(era["label"]):
                    problems.append(f'{where} needs some text for "label".')
                if "color" in era and not (isinstance(era["color"], str) and COLOR.match(era["color"])):
                    problems.append(f'{where} needs a color written like "#5E8C6A".')
                start = parse_day(era.get("from")) if "from" in era else None
                if "from" in era and start is None:
                    problems.append(f'{where} needs "from" written YYYY, YYYY-MM, or YYYY-MM-DD.')
                end = None
                if "to" in era:
                    if era["to"] == "now":
                        end = date.today()
                    else:
                        end = parse_day(era["to"], end=True)
                        if end is None:
                            problems.append(f'{where} needs "to" written YYYY, YYYY-MM, YYYY-MM-DD, or "now".')
                if start is not None and end is not None and end < start:
                    problems.append(f'{where} ends before it starts.')
                elif born is not None and end is not None and end < born:
                    problems.append(f'{where} ends before the birthdate.')
                elif last is not None and start is not None and start > last:
                    problems.append(f'{where} starts after the last row of the poster; raise "years" or move the era.')

    events = inputs.get("events", [])
    if not isinstance(events, list):
        problems.append(f'"events" in {SRC} must be a list of events, each with a date and a label.')
    else:
        for n, event in enumerate(events, start=1):
            where = f"Event {n} in {SRC}"
            if not isinstance(event, dict):
                problems.append(f"{where} must be an object with a date and a label.")
                continue
            if is_text(event.get("label")):
                where = f'The event "{event["label"]}" in {SRC}'
            for key in ("date", "label"):
                if key not in event:
                    problems.append(f'{where} is missing "{key}".')
            for key in sorted(set(event) - EVENT_KEYS):
                problems.append(f'{where} has a key this app does not use: "{key}".')
            if "label" in event and not is_text(event["label"]):
                problems.append(f'{where} needs some text for "label".')
            day = parse_day(event.get("date")) if "date" in event else None
            if "date" in event and day is None:
                problems.append(f'{where} needs "date" written YYYY-MM-DD.')
            elif day is not None and born is not None and day < born:
                problems.append(f'{where} is dated before the birthdate.')
            elif day is not None and last is not None and day > last:
                problems.append(f'{where} is dated after the last row of the poster; raise "years" or change the date.')

    if "quote" in inputs and not isinstance(inputs["quote"], str):
        problems.append(f'"quote" in {SRC} must be text; use "" for no line.')

    if "paper" in inputs and inputs["paper"] not in PAPERS:
        problems.append(f'"paper" in {SRC} is {json.dumps(inputs["paper"])}; the sizes are {", ".join(PAPERS)}.')

    if "theme" in inputs and inputs["theme"] not in theme_names:
        problems.append(f'"theme" in {SRC} is {json.dumps(inputs["theme"])}; the themes are {", ".join(theme_names)}.')

    return problems


def life_data(config, today):
    """The life worked out into weeks: the cells the page fills, marks, and tints."""
    born = parse_day(config["birthdate"])
    rows = config["years"]
    total = rows * WEEKS
    last = birthday(born, rows) - timedelta(days=1)
    now = index_of(born, today) if today <= last else total
    spans = []
    for era in config["eras"]:
        start = max(parse_day(era["from"]), born)
        still = era["to"] == "now"
        end = min(today if still else parse_day(era["to"], end=True), last)
        spans.append({"start": start, "end": end, "still": still})
    # An era that ends in the same year the next one starts runs up to it: the months between are the move, not a gap.
    in_order = sorted(spans, key=lambda span: span["start"])
    for span, following in zip(in_order, in_order[1:]):
        gap_start = span["end"] + timedelta(days=1)
        if not span["still"] and gap_start < following["start"] and span["end"].year == following["start"].year:
            span["end"] = following["start"] - timedelta(days=1)
    eras = []
    for era, span in zip(config["eras"], spans):
        eras.append({
            "label": era["label"],
            "color": era["color"],
            "from": index_of(born, span["start"]),
            "to": index_of(born, span["end"]),
            "now": span["still"],
        })
    events = []
    for event in config["events"]:
        events.append({"label": event["label"], "date": event["date"], "cell": index_of(born, parse_day(event["date"]))})
    return {
        "birthdate": config["birthdate"],
        "asOf": today.isoformat(),
        "rows": rows,
        "cells": total,
        "lived": min(now, total),
        "now": now if now < total else None,
        "eras": eras,
        "events": events,
    }


def main():
    parser = argparse.ArgumentParser(description=f"Write Life in Weeks into out/{APP}/ from {SRC}.")
    parser.parse_args()

    project = Path.cwd()
    inputs_path = project / SRC
    if not inputs_path.is_file():
        print(f"Make {SRC} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        print(f"{SRC} is not valid JSON: line {err.lineno}, column {err.colno}: {err.msg}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{SRC} must be one object with the keys inputs.example.json shows.")
        return 2

    theme_names = sorted(p.stem for p in THEMES.glob("*.css"))
    problems = check(inputs, theme_names)
    if problems:
        print("\n".join(problems))
        return 2

    config = {key: value for key, value in inputs.items() if key != "_notes"}
    config.setdefault("years", 90)
    config.setdefault("events", [])
    config.setdefault("quote", "")
    config.setdefault("paper", "A3")
    config.setdefault("theme", "auto")
    config["name"] = config["name"].strip()

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")
    (out / "theme.css").write_bytes((THEMES / f"{config['theme']}.css").read_bytes())
    (out / "config.js").write_text(
        "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8"
    )
    data = life_data(config, date.today())
    (out / "data.js").write_text(
        "window.__LIFE_DATA__ = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8"
    )

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
