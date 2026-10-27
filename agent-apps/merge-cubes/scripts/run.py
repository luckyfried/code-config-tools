"""Writes this person's Merge Cubes into out/merge-cubes/ in the current folder.

Run it from the project folder:

    cd <project> && python3 <agent-apps root>/merge-cubes/scripts/run.py

It reads merge-cubes.inputs.json from the current folder, checks every key, copies the page, and writes config.js
and theme.css. Standard library only; two runs on the same inputs give the same files.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "merge-cubes"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
BADGE = APP_DIR / "badge.js"

# key: (required, what it should be when wrong)
KEYS = {
    "title": (True, "text, the name at the top of the page"),
    "size": (True, "a whole number from 3 to 6"),
    "theme": (True, "the name of a theme"),
    "labels": (True, '"numbers", or a list of twelve short labels'),
    "sound": (False, "true or false"),
}


def problems_in(inputs):
    problems = []
    for key in inputs:
        if key not in KEYS and key != "_notes":
            problems.append(f'{APP}.inputs.json has the key "{key}", which Merge Cubes does not use.')
    missing = [key for key, (required, _) in KEYS.items() if required and key not in inputs]
    for key in missing:
        problems.append(f'{APP}.inputs.json is missing the key "{key}".')
    if missing:
        return problems

    def wrong(key):
        problems.append(f'{APP}.inputs.json has "{key}" set to {json.dumps(inputs[key], ensure_ascii=False)}; it should be {KEYS[key][1]}.')

    title = inputs["title"]
    if not isinstance(title, str) or not title.strip():
        wrong("title")
    elif len(title.strip()) > 40:
        problems.append(f'{APP}.inputs.json has a "title" longer than 40 characters; the top of the page holds 40.')

    size = inputs["size"]
    if isinstance(size, bool) or not isinstance(size, int) or not 3 <= size <= 6:
        wrong("size")

    themes = sorted(path.stem for path in THEMES.glob("*.css"))
    if not isinstance(inputs["theme"], str) or inputs["theme"] not in themes:
        problems.append(f'{APP}.inputs.json has "theme" set to {json.dumps(inputs["theme"])}; the themes are {", ".join(themes)}.')

    labels = inputs["labels"]
    if labels != "numbers":
        if not isinstance(labels, list) or len(labels) != 12:
            wrong("labels")
        else:
            for i, label in enumerate(labels):
                value = 2 ** (i + 1)
                if not isinstance(label, str) or not label.strip():
                    problems.append(f'{APP}.inputs.json has an empty label for {value} (number {i + 1} of 12).')
                elif len(label.strip()) > 14:
                    problems.append(f'{APP}.inputs.json has the label {json.dumps(label, ensure_ascii=False)} for {value}, longer than 14 characters; a cube holds 14.')

    if "sound" in inputs and not isinstance(inputs["sound"], bool):
        wrong("sound")
    return problems


def main():
    project = Path.cwd()
    source = project / f"{APP}.inputs.json"
    if not source.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"{APP}.inputs.json is not valid JSON: {error}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{APP}.inputs.json should hold one JSON object with the keys inputs.example.json shows.")
        return 2
    problems = problems_in(inputs)
    if problems:
        for line in problems:
            print(line)
        return 2

    labels = inputs["labels"]
    config = {
        "title": inputs["title"].strip(),
        "size": inputs["size"],
        "theme": inputs["theme"],
        "labels": labels if labels == "numbers" else [label.strip() for label in labels],
        "sound": inputs.get("sound", True),
    }

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out, ignore=shutil.ignore_patterns("config.js"))
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")

    count = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
