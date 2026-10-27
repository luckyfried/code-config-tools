#!/usr/bin/env python3
"""Wish List: turn wish-list.inputs.json in this folder into a wish list page in out/wish-list/.

Run from the project folder:
    python3 <agent-apps>/wish-list/scripts/run.py

Standard library only. Every problem with the inputs prints as one plain line and the run exits 2.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

APP = Path(__file__).resolve().parents[1]
PROJECT = Path.cwd()
NAME = "wish-list.inputs.json"
INPUTS = PROJECT / NAME
OUT = PROJECT / "out" / "wish-list"
DIST = APP / "dist"
THEMES = APP / "src" / "themes"
EXAMPLE = APP / "example"
COPY = DIST / "copy.js"

TOP_KEYS = {"owner", "occasion", "currency", "items", "theme", "copy", "_notes"}
TOP_REQUIRED = ("owner", "occasion", "currency", "items")
OWNER_KEYS = {"name", "phone", "email"}
ITEM_KEYS = {"name", "price", "url", "image", "note", "priority", "claimed"}
PRIORITIES = ("high", "normal", "low")
PICTURES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".svg"}


def theme_names() -> list[str]:
    return sorted(p.stem for p in THEMES.glob("*.css")) + ["auto"]


def copy_keys() -> list[str]:
    text = COPY.read_text(encoding="utf-8")
    return list(json.loads(text.split("=", 1)[1].strip().rstrip(";")).keys())


def is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_text(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def slug(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-") or "item"


def picture(path: str) -> Path | None:
    """A picture beside the inputs, or the same path in the app's example folder."""
    for base in (PROJECT, EXAMPLE):
        found = base / path
        if found.is_file():
            return found
    return None


def check(data: object) -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return [f'{NAME} must hold one object, such as {{"owner": ..., "occasion": ..., "items": [...]}}.']
    for key in TOP_REQUIRED:
        if key not in data:
            problems.append(f'{NAME} is missing the key "{key}".')
    for key in data:
        if key not in TOP_KEYS:
            problems.append(f'{NAME} has the key "{key}", which Wish List does not use; the keys are {", ".join(sorted(TOP_KEYS - {"_notes"}))}.')

    owner = data.get("owner")
    if "owner" in data:
        if not isinstance(owner, dict):
            problems.append(f'"owner" in {NAME} must be an object, such as {{"name": "Maya", "phone": "+1 415 555 0142"}}.')
        else:
            if not is_text(owner.get("name")):
                problems.append(f'"owner" in {NAME} is missing the key "name".')
            for key in owner:
                if key not in OWNER_KEYS:
                    problems.append(f'"owner" in {NAME} has the key "{key}"; the keys are name, phone, and email.')
            if not is_text(owner.get("phone")) and not is_text(owner.get("email")):
                problems.append(f'"owner" in {NAME} needs a "phone" or an "email", so friends can say what they are getting.')
            if "phone" in owner and (not is_text(owner["phone"]) or len(re.sub(r"\D", "", owner["phone"])) < 5):
                problems.append(f'"owner.phone" in {NAME} must be a phone number, such as "+1 415 555 0142".')
            if "email" in owner and (not is_text(owner["email"]) or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", owner["email"])):
                problems.append(f'"owner.email" in {NAME} must be an email address, such as "maya@example.com".')

    if "occasion" in data and not is_text(data["occasion"]):
        problems.append(f'"occasion" in {NAME} must be the title, such as "Maya turns 30".')
    if "currency" in data and (not isinstance(data["currency"], str) or not re.fullmatch(r"[A-Z]{3}", data["currency"])):
        problems.append(f'"currency" in {NAME} must be a three-letter code in capitals, such as "USD" or "EUR".')
    if "theme" in data and data["theme"] not in theme_names():
        problems.append(f'"theme" in {NAME} must be one of {", ".join(theme_names())}.')

    if "copy" in data:
        words = data["copy"]
        if not isinstance(words, dict):
            problems.append(f'"copy" in {NAME} must be an object of words, such as {{"getThis": "Count me in"}}.')
        else:
            known = copy_keys()
            for key, value in words.items():
                if key not in known:
                    problems.append(f'"copy" in {NAME} has the key "{key}", which Wish List does not use; copy.js lists every one.')
                elif not is_text(value):
                    problems.append(f'"copy.{key}" in {NAME} must be text.')

    items = data.get("items")
    if "items" in data and (not isinstance(items, list) or not items):
        problems.append(f'"items" in {NAME} must be a list of one or more wishes.')
        items = []
    for n, item in enumerate(items or [], start=1):
        where = f"item {n}"
        if not isinstance(item, dict):
            problems.append(f'{where} in {NAME} must be an object such as {{"name": "Record player", "price": 199}}.')
            continue
        if is_text(item.get("name")):
            where = f'item {n} ("{item["name"]}")'
        for key in ("name", "price"):
            if key not in item:
                problems.append(f'{where} in {NAME} is missing the key "{key}".')
        for key in item:
            if key not in ITEM_KEYS:
                problems.append(f'{where} in {NAME} has the key "{key}", which Wish List does not use; the keys are {", ".join(sorted(ITEM_KEYS))}.')
        if "name" in item and not is_text(item["name"]):
            problems.append(f'"name" of {where} must be text.')
        if "price" in item and (not is_number(item["price"]) or item["price"] < 0):
            problems.append(f'"price" of {where} must be a number, such as 49 or 12.50.')
        if "url" in item and (not isinstance(item["url"], str) or urlparse(item["url"]).scheme not in ("http", "https") or not urlparse(item["url"]).netloc):
            problems.append(f'"url" of {where} must be a web address that starts with https://.')
        if "note" in item and not isinstance(item["note"], str):
            problems.append(f'"note" of {where} must be text.')
        if "priority" in item and item["priority"] not in PRIORITIES:
            problems.append(f'"priority" of {where} must be high, normal, or low.')
        if "claimed" in item and not isinstance(item["claimed"], bool):
            problems.append(f'"claimed" of {where} must be true or false.')
        if "image" in item:
            image = item["image"]
            if not is_text(image):
                problems.append(f'"image" of {where} must be the path of a picture beside {NAME}.')
            elif Path(image).suffix.lower() not in PICTURES:
                problems.append(f'"image" of {where} names {image}, which is not a picture (png, jpg, webp, gif, avif, or svg).')
            elif picture(image) is None:
                problems.append(f'"image" of {where} names {image}, which is not a file in this folder.')
    return problems


def theme_css(name: str) -> str:
    if name != "auto":
        return (THEMES / f"{name}.css").read_text(encoding="utf-8")
    light = (THEMES / "ribbon.css").read_text(encoding="utf-8")
    dark = (THEMES / "midnight.css").read_text(encoding="utf-8")
    return f"{light}\n@media (prefers-color-scheme: dark) {{\n{dark}}}\n"


def amount(value: float, currency: str) -> str:
    text = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
    return f"{text} {currency}"


def main() -> int:
    if not INPUTS.is_file():
        print(f"Make {NAME} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        data = json.loads(INPUTS.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        print(f"{NAME} must be saved as UTF-8 text.")
        return 2
    except json.JSONDecodeError as e:
        print(f"{NAME} is not valid JSON: {e.msg} at line {e.lineno}, column {e.colno}.")
        return 2
    if not (DIST / "index.html").is_file():
        print(f"The built page is missing from {DIST}; the README's Make it yours section rebuilds it.")
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

    media = OUT / "media"
    seen: set[str] = set()
    for item in inputs["items"]:
        base = slug(item["name"])
        item_id, n = base, 2
        while item_id in seen:
            item_id, n = f"{base}-{n}", n + 1
        seen.add(item_id)
        item["id"] = item_id
        if item.get("image"):
            src = picture(item["image"])
            media.mkdir(exist_ok=True)
            dest = f"{item_id}{src.suffix.lower()}"
            shutil.copyfile(src, media / dest)
            item["image"] = f"./media/{dest}"

    (OUT / "theme.css").write_text(theme_css(inputs["theme"]), encoding="utf-8")
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(inputs, ensure_ascii=False)};\n", encoding="utf-8")

    # The list in plain HTML too, for a browser with scripts off.
    currency = inputs["currency"]
    rows = "".join(
        f"<li>{html.escape(item['name'])}: {html.escape(amount(item['price'], currency))}{' (gotten)' if item.get('claimed') else ''}</li>"
        for item in inputs["items"]
    )
    page = OUT / "index.html"
    text = page.read_text(encoding="utf-8")
    page.write_text(
        text.replace("</body>", f"<noscript><h1>{html.escape(inputs['occasion'])}</h1><ul>{rows}</ul></noscript>\n  </body>", 1),
        encoding="utf-8",
    )

    open_items = [item for item in inputs["items"] if not item.get("claimed")]
    total = sum(item["price"] for item in open_items)
    files = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Still wished for: {amount(total, currency)} across {len(open_items)} of {len(inputs['items'])} items.")
    print(f"Wrote out/wish-list/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/wish-list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
