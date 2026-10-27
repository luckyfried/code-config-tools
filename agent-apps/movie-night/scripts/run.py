#!/usr/bin/env python3
"""Builds the movie night page from movie-night.inputs.json in the current folder into out/movie-night/.

Poster files are copied into out/movie-night/media/posters/. When TMDB_READ_TOKEN is set, a film with no poster file
gets its poster from TMDB, saved into the same folder; the token is only sent to TMDB and never written anywhere.
"""
import datetime
import json
import os
import re
import shutil
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

SLUG = "movie-night"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
SAMPLES = APP / "samples"
THEMES = sorted(p.stem for p in (SITE / "themes").glob("*.css"))
REQUIRED = ["people", "films", "theme"]
OPTIONAL = ["title", "watched", "lookupPosters"]
FILM_KEYS = ["title", "year", "note", "poster", "hearts"]
WATCHED_KEYS = ["title", "year", "date", "stars"]
IMAGE_TYPES = [".jpg", ".jpeg", ".png", ".webp"]
INPUTS = f"{SLUG}.inputs.json"
TOKEN = "TMDB_READ_TOKEN"


def slug_of(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not 0x300 <= ord(c) <= 0x36F).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def key_of(title, year):
    return f"{slug_of(title)}-{year}" if year else slug_of(title)


def is_year(v):
    return isinstance(v, int) and not isinstance(v, bool) and 1880 <= v <= 2100


def is_date(v):
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return False
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def find_poster(film, base):
    """The poster file for a film: the path it names, read from the project and then from this app's samples, or a
    file named posters/<title-slug>.<jpg|jpeg|png|webp> in the project."""
    named = film.get("poster")
    if named:
        for root in (base, SAMPLES):
            p = (root / named).resolve()
            if p.is_file():
                return p
        return None
    for stem in (key_of(film["title"], film.get("year")), slug_of(film["title"])):
        for ext in IMAGE_TYPES:
            p = base / "posters" / f"{stem}{ext}"
            if p.is_file():
                return p
    return None


def check(data, base):
    problems = []
    if not isinstance(data, dict):
        return [f"{INPUTS} holds one JSON object with the keys shown in inputs.example.json."]
    for key in REQUIRED:
        if key not in data:
            problems.append(f'{INPUTS} is missing the key "{key}".')
    for key in data:
        if key not in REQUIRED and key not in OPTIONAL and key != "_notes":
            problems.append(f'{INPUTS} has the key "{key}", which this app does not use. The keys are: {", ".join(REQUIRED + OPTIONAL)}.')

    if "title" in data and (not isinstance(data["title"], str) or not data["title"].strip()):
        problems.append('"title" is the page\'s name, as text, for example "Friday Movie Night".')
    if "theme" in data and data["theme"] not in THEMES:
        problems.append(f'"theme" is one of: {", ".join(THEMES)}.')
    if "lookupPosters" in data and not isinstance(data["lookupPosters"], bool):
        problems.append('"lookupPosters" is true or false.')

    people = data.get("people")
    if "people" in data:
        if not isinstance(people, list) or not 1 <= len(people) <= 8 or not all(isinstance(p, str) and p.strip() for p in people):
            problems.append('"people" is a list of one to eight names, for example ["Ed", "Sam"].')
            people = None
        elif len(set(people)) != len(people):
            problems.append('"people" names each person once.')

    if "films" in data:
        films = data["films"]
        if not isinstance(films, list) or not films:
            problems.append('"films" is a list of one or more films, each { "title", "year" }.')
        else:
            seen = set()
            for i, f in enumerate(films, 1):
                if not isinstance(f, dict):
                    problems.append(f'Film {i} in "films" is an object with "title" and "year".')
                    continue
                for key in f:
                    if key not in FILM_KEYS:
                        problems.append(f'Film {i} in "films" has the key "{key}"; a film has {", ".join(FILM_KEYS)}.')
                if not isinstance(f.get("title"), str) or not f["title"].strip():
                    problems.append(f'Film {i} in "films" is missing its "title".')
                    continue
                if "year" in f and not is_year(f["year"]):
                    problems.append(f'"{f["title"]}" has a "year" that is not a year; write it as a number, for example 1994.')
                if "note" in f and not isinstance(f["note"], str):
                    problems.append(f'"{f["title"]}" has a "note" that is not text.')
                if "poster" in f:
                    if not isinstance(f["poster"], str) or Path(f["poster"]).suffix.lower() not in IMAGE_TYPES:
                        problems.append(f'"{f["title"]}" has a "poster" that is not a .jpg, .jpeg, .png, or .webp file path.')
                    elif find_poster(f, base) is None:
                        problems.append(f'"{f["title"]}" names the poster {f["poster"]}, which is not in this folder.')
                if "hearts" in f:
                    hearts = f["hearts"]
                    if not isinstance(hearts, list) or not all(isinstance(h, str) for h in hearts):
                        problems.append(f'"{f["title"]}" has "hearts" that is not a list of names.')
                    elif people:
                        for h in hearts:
                            if h not in people:
                                problems.append(f'"{f["title"]}" has a heart from "{h}", who is not in "people".')
                key = key_of(f["title"], f.get("year") if is_year(f.get("year")) else None)
                if key in seen:
                    problems.append(f'"{f["title"]}" is on the list twice.')
                seen.add(key)

    if "watched" in data:
        watched = data["watched"]
        if not isinstance(watched, list):
            problems.append('"watched" is a list of films already seen, each { "title", "year", "date", "stars" }.')
        else:
            for i, w in enumerate(watched, 1):
                if not isinstance(w, dict) or not isinstance(w.get("title"), str) or not w["title"].strip():
                    problems.append(f'Film {i} in "watched" is an object with a "title".')
                    continue
                for key in w:
                    if key not in WATCHED_KEYS:
                        problems.append(f'"{w["title"]}" in "watched" has the key "{key}"; a watched film has {", ".join(WATCHED_KEYS)}.')
                if "year" in w and not is_year(w["year"]):
                    problems.append(f'"{w["title"]}" in "watched" has a "year" that is not a year.')
                if not is_date(w.get("date")):
                    problems.append(f'"{w["title"]}" in "watched" needs a "date" written like 2026-10-17.')
                stars = w.get("stars", 0)
                if not isinstance(stars, int) or isinstance(stars, bool) or not 0 <= stars <= 5:
                    problems.append(f'"{w["title"]}" in "watched" has "stars" from 0 to 5.')
    return problems


def tmdb_poster(film, token, dest):
    """Saves a film's TMDB poster to dest and returns the path, or returns a sentence saying why not."""
    query = {"query": film["title"], "include_adult": "false"}
    if film.get("year"):
        query["year"] = str(film["year"])
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    req = urllib.request.Request(f"https://api.themoviedb.org/3/search/movie?{urllib.parse.urlencode(query)}", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            results = json.load(res).get("results") or []
    except Exception as e:
        return f'TMDB did not answer for "{film["title"]}" ({e}); it gets a drawn card.'
    path = next((r.get("poster_path") for r in results if r.get("poster_path")), None)
    if not path:
        return f'TMDB has no poster for "{film["title"]}"; it gets a drawn card.'
    try:
        with urllib.request.urlopen(f"https://image.tmdb.org/t/p/w500{path}", timeout=15) as res:
            dest.write_bytes(res.read())
    except Exception as e:
        return f'The TMDB poster for "{film["title"]}" did not download ({e}); it gets a drawn card.'
    return dest


def main():
    base = Path.cwd()
    path = base / INPUTS
    if not path.exists():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"{INPUTS} is not valid JSON: line {e.lineno}, column {e.colno}: {e.msg}.")
        return 2
    problems = check(data, base)
    if problems:
        print("\n".join(problems))
        return 2

    inputs = {k: v for k, v in data.items() if k != "_notes"}
    out = base / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    shutil.copyfile(SITE / "themes" / f"{inputs['theme']}.css", out / "theme.css")
    media = out / "media" / "posters"
    media.mkdir(parents=True)

    token = os.environ.get(TOKEN, "").strip()
    films = []
    found = fetched = 0
    for f in inputs["films"]:
        year = f.get("year")
        key = key_of(f["title"], year)
        poster = None
        src = find_poster(f, base)
        if src:
            name = f"{key}{src.suffix.lower()}"
            shutil.copyfile(src, media / name)
            poster = f"media/posters/{name}"
            found += 1
        elif token:
            got = tmdb_poster(f, token, media / f"{key}.jpg")
            if isinstance(got, Path):
                poster = f"media/posters/{key}.jpg"
                fetched += 1
            else:
                print(got)
        films.append({
            "key": key,
            "title": f["title"],
            "year": year,
            "note": f.get("note", ""),
            "poster": poster,
            "hearts": f.get("hearts", []),
        })
    inputs["films"] = films
    if "watched" in inputs:
        inputs["watched"] = [
            {"key": key_of(w["title"], w.get("year")), "title": w["title"], "year": w.get("year"), "date": w["date"], "stars": w.get("stars", 0)}
            for w in inputs["watched"]
        ]
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(inputs, ensure_ascii=False, sort_keys=True)};\n", encoding="utf-8")

    files = sum(1 for p in out.rglob("*") if p.is_file())
    with_art = found + fetched
    rest = len(films) - with_art
    lookup = inputs.get("lookupPosters", True)
    note = f" {fetched} came from TMDB." if fetched else ""
    if rest:
        note += f" The other {rest} get a drawn card" + (", or a Wikipedia poster when the page is online." if lookup else ".")
    print(f"{len(films)} films, {found} with a poster file.{note}")
    print(f"Wrote out/{SLUG}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
