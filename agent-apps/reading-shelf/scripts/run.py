#!/usr/bin/env python3
"""Reading Shelf: writes out/reading-shelf/ from reading-shelf.inputs.json in the current folder.

    cd <project> && python3 <agent-apps root>/reading-shelf/scripts/run.py [--fetch]

The current folder is the project. Covers named in the inputs are read from beside the inputs file (the
app's own sample covers stand in when a path is not there). With --fetch, books with no cover get theirs from
Open Library now, so the hosted page calls nothing. Standard library only.
"""

import argparse
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SLUG = "reading-shelf"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
SAMPLES = APP / "samples"
INPUTS = f"{SLUG}.inputs.json"
SHELVES = ("oak", "white", "black-steel")
STATUSES = ("read", "reading", "want")
TOP = {"owner": str, "theme": str, "shelf": str, "books": list, "openLibrary": bool, "_notes": dict}
TOP_REQUIRED = ("owner", "theme", "shelf", "books")
BOOK = {
    "title": str,
    "author": str,
    "isbn": str,
    "status": str,
    "rating": (int, float),
    "note": str,
    "started": str,
    "finished": str,
    "pages": (int, float),
    "page": (int, float),
    "cover": str,
}
BOOK_REQUIRED = ("title", "author", "status")
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".gif")
TYPE_WORDS = {str: "text", list: "a list", bool: "true or false", dict: "an object", (int, float): "a number"}


def kind_of(value):
    if isinstance(value, bool):
        return "true or false"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "an object"
    return "empty"


def fits(value, expected):
    if expected is bool:
        return isinstance(value, bool)
    if expected == (int, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, expected)


def file_slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "book"


def validate(data, project):
    problems = []
    if not isinstance(data, dict):
        return [f"{INPUTS} should hold one object with the keys owner, theme, shelf, and books."]
    for key in TOP_REQUIRED:
        if key not in data:
            problems.append(f'{INPUTS} is missing the key "{key}".')
    for key, value in data.items():
        if key not in TOP:
            problems.append(f'{INPUTS} has a key this app does not use: "{key}".')
        elif not fits(value, TOP[key]):
            problems.append(f'{INPUTS} has "{key}" as {kind_of(value)}; it should be {TYPE_WORDS[TOP[key]]}.')
    themes = sorted(p.stem for p in (SITE / "themes").glob("*.css"))
    theme = data.get("theme")
    if isinstance(theme, str) and theme not in themes:
        problems.append(f'The theme "{theme}" does not exist; pick one of {", ".join(themes)}.')
    shelf = data.get("shelf")
    if isinstance(shelf, str) and shelf not in SHELVES:
        problems.append(f'The shelf "{shelf}" does not exist; pick one of {", ".join(SHELVES)}.')
    books = data.get("books")
    if isinstance(books, list):
        for i, book in enumerate(books, 1):
            if not isinstance(book, dict):
                problems.append(f"Book {i} should be an object with a title, an author, and a status.")
                continue
            name = f'Book {i} ("{book.get("title")}")' if isinstance(book.get("title"), str) else f"Book {i}"
            for key in BOOK_REQUIRED:
                if key not in book:
                    problems.append(f'{name} is missing the key "{key}".')
            for key, value in book.items():
                if key not in BOOK:
                    problems.append(f'{name} has a key this app does not use: "{key}".')
                elif not fits(value, BOOK[key]):
                    problems.append(f'{name} has "{key}" as {kind_of(value)}; it should be {TYPE_WORDS[BOOK[key]]}.')
            status = book.get("status")
            if isinstance(status, str) and status not in STATUSES:
                problems.append(f'{name} has the status "{status}"; use read, reading, or want.')
            rating = book.get("rating")
            if fits(rating, (int, float)) and not 0 <= rating <= 5:
                problems.append(f"{name} has the rating {rating}; use 0 to 5.")
            cover = book.get("cover")
            if isinstance(cover, str) and cover:
                if find_cover(cover, project) is None:
                    problems.append(f"{name} names the cover {cover}, which is not beside {INPUTS}.")
                elif Path(cover).suffix.lower() not in IMAGE_TYPES:
                    problems.append(f"{name} names the cover {cover}; a cover is a .jpg, .png, .webp, or .gif image.")
    return problems


def find_cover(cover, project):
    rel = Path(cover)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    for base in (project, SAMPLES):
        path = base / rel
        if path.is_file():
            return path
    return None


def fetch(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": "reading-shelf (agent app)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_cover(book):
    """A cover image's bytes from Open Library for a book, by ISBN or by title and author; None when there is none."""
    isbn = re.sub(r"[^0-9Xx]", "", book.get("isbn", "") or "")
    urls = []
    if isbn:
        urls.append(f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false")
    else:
        query = urllib.parse.urlencode({"title": book["title"], "author": book["author"], "limit": 1, "fields": "cover_i"})
        found = json.loads(fetch(f"https://openlibrary.org/search.json?{query}"))
        docs = found.get("docs") or []
        if docs and docs[0].get("cover_i"):
            urls.append(f"https://covers.openlibrary.org/b/id/{docs[0]['cover_i']}-L.jpg")
    for url in urls:
        try:
            body = fetch(url)
        except Exception:
            continue
        if len(body) > 1000:
            return body
    return None


def main():
    parser = argparse.ArgumentParser(description="Write out/reading-shelf/ from reading-shelf.inputs.json.")
    parser.add_argument("--fetch", action="store_true", help="get covers from Open Library for books that have none")
    args = parser.parse_args()

    project = Path.cwd()
    inputs_path = project / INPUTS
    if not inputs_path.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        data = json.loads(inputs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"{INPUTS} is not valid JSON: {error.msg} on line {error.lineno}.")
        return 2
    problems = validate(data, project)
    if problems:
        for line in problems:
            print(line)
        return 2

    out = project / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)
    shutil.copyfile(APP / "badge.js", out / "badge.js")
    shutil.copyfile(SITE / "themes" / f"{data['theme']}.css", out / "theme.css")

    covers = out / "media" / "covers"
    found = 0
    fetched = 0
    missed = 0
    used = set()
    books = []
    for book in data["books"]:
        entry = {key: book[key] for key in BOOK if key in book}
        name = file_slug(f"{book['title']}-{book['author']}")
        while name in used:
            name += "-2"
        used.add(name)
        source = find_cover(book["cover"], project) if book.get("cover") else None
        if source is not None:
            covers.mkdir(parents=True, exist_ok=True)
            target = covers / f"{name}{source.suffix.lower()}"
            shutil.copyfile(source, target)
            entry["cover"] = f"media/covers/{target.name}"
            found += 1
        else:
            entry.pop("cover", None)
            if args.fetch:
                try:
                    body = fetch_cover(book)
                except Exception:
                    body = None
                if body:
                    covers.mkdir(parents=True, exist_ok=True)
                    (covers / f"{name}.jpg").write_bytes(body)
                    entry["cover"] = f"media/covers/{name}.jpg"
                    fetched += 1
                else:
                    missed += 1
        books.append(entry)

    config = {
        "owner": data["owner"],
        "theme": data["theme"],
        "shelf": data["shelf"],
        "openLibrary": bool(data.get("openLibrary", False)),
        "books": books,
    }
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")

    count = len(books)
    line = f"{count} {'book' if count == 1 else 'books'}; {found} {'cover' if found == 1 else 'covers'} from your folder"
    if args.fetch:
        line += f", {fetched} fetched from Open Library"
        if missed:
            line += f", {missed} with none to be found (drawn in the theme's colors)"
    print(f"{line}.")
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
