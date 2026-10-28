"""Builds the Daily Word page from the person's inputs.

Run from the project folder:

    python3 <agent-apps root>/daily-word/scripts/run.py

It reads daily-word.inputs.json from the current folder, checks every key and every word, copies the page into
out/daily-word/, and writes theme.css and config.js there. Standard library only; two runs on the same inputs
write the same bytes.
"""

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

APP = "daily-word"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
BADGE = HERE / "badge.js"
INPUTS = f"{APP}.inputs.json"
WORD = re.compile(r"^[A-Za-z]{5}$")

# key: (kind, required)
KEYS = {
    "title": (str, True),
    "topic": (str, True),
    "words": (list, True),
    "launchDate": (str, True),
    "allowExtra": (list, False),
    "theme": (str, True),
    "hardMode": (bool, False),
}
KIND_WORDS = {str: "text", list: "a list", bool: "true or false"}


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def check_words(key, values, problems):
    seen = set()
    clean = []
    for value in values:
        if not isinstance(value, str) or not WORD.match(value.strip()):
            problems.append(f'{INPUTS}: "{value}" in {key} is not a five-letter word made of letters only.')
            continue
        word = value.strip().upper()
        if word in seen:
            problems.append(f'{INPUTS}: "{word}" is in {key} twice.')
            continue
        seen.add(word)
        clean.append(word)
    return clean


def main():
    project = Path.cwd()
    path = project / INPUTS
    if not path.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON: {error}."])
    if not isinstance(inputs, dict):
        fail([f"{INPUTS} must be one JSON object with the keys inputs.example.json shows."])

    problems = []
    for key, (kind, required) in KEYS.items():
        if key not in inputs:
            if required:
                problems.append(f'{INPUTS} is missing the key "{key}".')
            continue
        if not isinstance(inputs[key], kind):
            problems.append(f'{INPUTS}: "{key}" must be {KIND_WORDS[kind]}.')
    for key in inputs:
        if key not in KEYS and key != "_notes":
            problems.append(f'{INPUTS} has a key this app does not use: "{key}".')
    if problems:
        fail(problems)

    title = inputs["title"].strip()
    topic = inputs["topic"].strip()
    if not title:
        problems.append(f'{INPUTS}: "title" is empty.')
    elif len(title) > 40:
        problems.append(f'{INPUTS}: "title" is {len(title)} characters; keep it to 40 so it fits the header.')

    words = check_words("words", inputs["words"], problems)
    if not inputs["words"]:
        problems.append(f'{INPUTS}: "words" is empty; it needs at least one five-letter word.')
    extra = check_words("allowExtra", inputs.get("allowExtra", []), problems)

    launch = inputs["launchDate"].strip()
    try:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", launch):
            raise ValueError
        date.fromisoformat(launch)
    except ValueError:
        problems.append(f'{INPUTS}: "launchDate" must be a date written YYYY-MM-DD, like 2026-10-01.')

    themes = sorted(p.stem for p in (SITE / "themes").glob("*.css"))
    theme = inputs["theme"].strip()
    if theme not in themes:
        problems.append(f'{INPUTS}: "theme" is "{theme}"; use one of {", ".join(themes)}.')
    if problems:
        fail(problems)

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")
    shutil.copyfile(SITE / "themes" / f"{theme}.css", out / "theme.css")

    config = {
        "title": title,
        "topic": topic,
        "words": words,
        "launchDate": launch,
        "allowExtra": extra,
        "theme": theme,
        "hardMode": bool(inputs.get("hardMode", False)),
    }
    (out / "config.js").write_text(
        "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False, sort_keys=True) + ";\n", encoding="utf-8"
    )

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
