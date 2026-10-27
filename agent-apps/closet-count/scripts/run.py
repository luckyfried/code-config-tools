#!/usr/bin/env python3
"""Closet Count: turn closet-count.inputs.json in this folder into a wardrobe page in out/closet-count/.

Run from the project folder:
    python3 <agent-apps>/closet-count/scripts/run.py

Standard library only. Every problem with the inputs prints as one plain line and the run exits 2.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
PROJECT = Path.cwd()
NAME = "closet-count.inputs.json"
INPUTS = PROJECT / NAME
OUT = PROJECT / "out" / "closet-count"
DIST = APP / "dist"
THEMES = APP / "src" / "themes"
COPY = DIST / "copy.js"

TOP_KEYS = {"name", "currency", "items", "outfits", "slots", "dustyDays", "capsuleSize", "theme", "copy", "_notes"}
TOP_REQUIRED = ("name", "currency", "items")
ITEM_KEYS = {"id", "name", "category", "color", "price", "brand", "seasons", "wears", "lastWorn"}
ITEM_REQUIRED = ("id", "name", "category", "color")
OUTFIT_KEYS = {"id", "name", "items", "wears", "lastWorn"}
CATEGORIES = ("top", "bottom", "dress", "layer", "shoes", "bag", "accessory")
SEASONS = ("spring", "summer", "fall", "winter")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def theme_names() -> list[str]:
    return sorted(p.stem for p in THEMES.glob("*.css")) + ["auto"]


def copy_keys() -> set[str]:
    text = COPY.read_text(encoding="utf-8")
    body = text[text.index("= {") + 2 : text.rindex("}") + 1]
    return set(json.loads(body))


def is_count(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def is_day(v: object) -> bool:
    if not isinstance(v, str):
        return False
    try:
        date.fromisoformat(v)
        return len(v) == 10
    except ValueError:
        return False


def check(data: object) -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return [f'{NAME} must hold one object, such as {{"name": ..., "currency": ..., "items": [...]}}.']
    for key in TOP_REQUIRED:
        if key not in data:
            problems.append(f'{NAME} is missing the key "{key}".')
    for key in data:
        if key not in TOP_KEYS:
            problems.append(f'{NAME} has the key "{key}", which Closet Count does not use; the keys are {", ".join(sorted(TOP_KEYS - {"_notes"}))}.')
    if "name" in data and (not isinstance(data["name"], str) or not data["name"].strip()):
        problems.append(f'"name" in {NAME} must be a title, such as "Sam\'s closet".')
    if "currency" in data and (not isinstance(data["currency"], str) or not re.fullmatch(r"[A-Za-z]{3}", data["currency"])):
        problems.append(f'"currency" in {NAME} must be a three-letter currency code, such as "USD" or "EUR".')
    if "theme" in data and data["theme"] not in theme_names():
        problems.append(f'"theme" in {NAME} must be one of {", ".join(theme_names())}.')
    for key in ("dustyDays", "capsuleSize"):
        if key in data and (not is_count(data[key]) or data[key] == 0):
            problems.append(f'"{key}" in {NAME} must be a whole number above 0.')
    slots = data.get("slots", ["top", "bottom", "shoes", "layer"])
    if not isinstance(slots, list) or not slots or not all(s in CATEGORIES for s in slots) or len(set(slots)) != len(slots):
        problems.append(f'"slots" in {NAME} must list outfit slots once each, from {", ".join(CATEGORIES)}.')
        slots = []

    if "copy" in data:
        words = data["copy"]
        if not isinstance(words, dict):
            problems.append(f'"copy" in {NAME} must be an object of words, such as {{"nav.today": "Now"}}.')
        else:
            known = copy_keys()
            for key, value in words.items():
                if key not in known:
                    problems.append(f'"copy" in {NAME} has the key "{key}", which Closet Count does not use; copy.js lists every one.')
                elif not isinstance(value, str) or not value.strip():
                    problems.append(f'"copy.{key}" in {NAME} must be text.')

    items = data.get("items")
    if "items" in data and not isinstance(items, list):
        problems.append(f'"items" in {NAME} must be a list of pieces.')
        items = []
    ids: dict[str, str] = {}
    for n, item in enumerate(items or [], start=1):
        where = f"item {n}"
        if not isinstance(item, dict):
            problems.append(f'{where} in {NAME} must be an object such as {{"id": "camel-coat", "name": "Camel coat", "category": "layer", "color": "#c19a6b"}}.')
            continue
        if isinstance(item.get("name"), str) and item["name"].strip():
            where = f'item {n} ("{item["name"]}")'
        for key in ITEM_REQUIRED:
            if key not in item:
                problems.append(f'{where} in {NAME} is missing the key "{key}".')
        for key in item:
            if key not in ITEM_KEYS:
                problems.append(f'{where} in {NAME} has the key "{key}", which Closet Count does not use; the keys are {", ".join(sorted(ITEM_KEYS))}.')
        iid = item.get("id")
        if "id" in item:
            if not isinstance(iid, str) or not ID.match(iid):
                problems.append(f'"id" of {where} must be a short name of letters, digits, and dashes, such as "camel-coat".')
            elif iid in ids:
                problems.append(f'Two items in {NAME} use the id "{iid}"; each needs its own.')
            else:
                ids[iid] = item.get("category", "")
        if "name" in item and (not isinstance(item["name"], str) or not item["name"].strip()):
            problems.append(f'"name" of {where} must be text.')
        if "category" in item and item["category"] not in CATEGORIES:
            problems.append(f'"category" of {where} must be one of {", ".join(CATEGORIES)}.')
        if "color" in item and (not isinstance(item["color"], str) or not HEX.match(item["color"])):
            problems.append(f'"color" of {where} must be a hex color, such as "#c19a6b".')
        if "price" in item and item["price"] is not None and (
            not isinstance(item["price"], (int, float)) or isinstance(item["price"], bool) or item["price"] < 0
        ):
            problems.append(f'"price" of {where} must be a number, such as 120, or left out.')
        if "brand" in item and not isinstance(item["brand"], str):
            problems.append(f'"brand" of {where} must be text.')
        if "seasons" in item and (not isinstance(item["seasons"], list) or not all(s in SEASONS for s in item["seasons"])):
            problems.append(f'"seasons" of {where} must list seasons from {", ".join(SEASONS)}.')
        if "wears" in item and not is_count(item["wears"]):
            problems.append(f'"wears" of {where} must be a whole number, such as 12.')
        if "lastWorn" in item and not is_day(item["lastWorn"]):
            problems.append(f'"lastWorn" of {where} must be a day written yyyy-mm-dd, such as "2026-10-03".')

    outfits = data.get("outfits", [])
    if not isinstance(outfits, list):
        problems.append(f'"outfits" in {NAME} must be a list of outfits.')
        outfits = []
    outfit_ids: set[str] = set()
    for n, outfit in enumerate(outfits, start=1):
        where = f"outfit {n}"
        if not isinstance(outfit, dict):
            problems.append(f'{where} in {NAME} must be an object with an id, a name, and items.')
            continue
        if isinstance(outfit.get("name"), str) and outfit["name"].strip():
            where = f'outfit {n} ("{outfit["name"]}")'
        for key in ("id", "name", "items"):
            if key not in outfit:
                problems.append(f'{where} in {NAME} is missing the key "{key}".')
        for key in outfit:
            if key not in OUTFIT_KEYS:
                problems.append(f'{where} in {NAME} has the key "{key}", which Closet Count does not use; the keys are {", ".join(sorted(OUTFIT_KEYS))}.')
        oid = outfit.get("id")
        if "id" in outfit:
            if not isinstance(oid, str) or not ID.match(oid):
                problems.append(f'"id" of {where} must be a short name of letters, digits, and dashes, such as "monday-office".')
            elif oid in outfit_ids:
                problems.append(f'Two outfits in {NAME} use the id "{oid}"; each needs its own.')
            else:
                outfit_ids.add(oid)
        picks = outfit.get("items")
        if "items" in outfit and not isinstance(picks, dict):
            problems.append(f'"items" of {where} must map each slot to an item id, such as {{"top": "white-oxford"}}.')
            picks = {}
        for slot, pick in (picks or {}).items():
            if slot not in slots:
                problems.append(f'"items" of {where} uses the slot "{slot}", which is not in "slots" ({", ".join(slots)}).')
            elif pick is not None and pick not in ids:
                problems.append(f'"items.{slot}" of {where} names "{pick}", which is not the id of any item.')
            elif pick is not None:
                allowed = ("top", "dress") if slot == "top" else (slot,)
                if ids[pick] not in allowed:
                    problems.append(f'"items.{slot}" of {where} names "{pick}", which is a {ids[pick]}, not a {slot}.')
        if "wears" in outfit and not is_count(outfit["wears"]):
            problems.append(f'"wears" of {where} must be a whole number.')
        if "lastWorn" in outfit and not is_day(outfit["lastWorn"]):
            problems.append(f'"lastWorn" of {where} must be a day written yyyy-mm-dd.')
    return problems


def theme_css(name: str) -> str:
    if name != "auto":
        return (THEMES / f"{name}.css").read_text(encoding="utf-8")
    light = (THEMES / "boutique.css").read_text(encoding="utf-8")
    dark = (THEMES / "atelier.css").read_text(encoding="utf-8")
    return f"{light}\n@media (prefers-color-scheme: dark) {{\n{dark}}}\n"


def main() -> int:
    if not INPUTS.is_file():
        print(f"Make {NAME} in this folder first; inputs.example.json shows every key.")
        return 2
    if not (DIST / "index.html").is_file():
        print(f"The built page is missing from {DIST}; the README's Make it yours section rebuilds it.")
        return 2
    try:
        data = json.loads(INPUTS.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        print(f"{NAME} must be saved as UTF-8 text.")
        return 2
    except json.JSONDecodeError as e:
        print(f"{NAME} is not valid JSON: {e.msg} at line {e.lineno}, column {e.colno}.")
        return 2
    problems = check(data)
    if problems:
        print("\n".join(problems))
        return 2

    inputs = {k: v for k, v in data.items() if k != "_notes"}
    inputs.setdefault("theme", "auto")

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(DIST, OUT)
    (OUT / "theme.css").write_text(theme_css(inputs["theme"]), encoding="utf-8")
    (OUT / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(inputs, ensure_ascii=False, indent=2)};\n", encoding="utf-8"
    )

    files = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote out/closet-count/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/closet-count")
    return 0


if __name__ == "__main__":
    sys.exit(main())
