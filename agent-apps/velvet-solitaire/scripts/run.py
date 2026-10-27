"""Builds the Velvet Solitaire page from the person's choices.

Run from the project folder:

    python3 <agent-apps root>/velvet-solitaire/scripts/run.py

It reads velvet-solitaire.inputs.json from the current folder, checks every key, copies the
page into out/velvet-solitaire/, copies the chosen theme to theme.css and the person's own
card back (when they gave one) into media/, writes config.js, and prints how to serve it.
Two runs on the same inputs write the same bytes. Python 3 standard library only.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "velvet-solitaire"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
THEMES = SITE / "themes"
BACKS = ("classic", "lattice", "monogram")
IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".webp", ".gif")

# Each key: (type check, description used in the error line).
KEYS = {
    "title": (lambda v: isinstance(v, str) and v.strip() != "", "a name in quotes"),
    "playerName": (lambda v: isinstance(v, str), "a name in quotes (it may be empty)"),
    "draw": (lambda v: v in (1, 3) and not isinstance(v, bool), "1 or 3"),
    "scoring": (lambda v: v in ("standard", "vegas"), '"standard" or "vegas"'),
    "theme": (lambda v: isinstance(v, str) and v != "", "a theme name in quotes"),
    "cardBack": (lambda v: isinstance(v, str) and v != "", '"classic", "lattice", "monogram", or a picture\'s path'),
    "sound": (lambda v: isinstance(v, bool), "true or false"),
}


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def main():
    project = Path.cwd()
    inputs_file = project / f"{APP}.inputs.json"
    if not inputs_file.is_file():
        fail([f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(inputs_file.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as err:
        fail([f"{APP}.inputs.json is not valid JSON: {err}."])
    if not isinstance(inputs, dict):
        fail([f"{APP}.inputs.json must hold one object with the keys inputs.example.json shows."])

    problems = []
    for key, (ok, words) in KEYS.items():
        if key not in inputs:
            problems.append(f'{APP}.inputs.json is missing the key "{key}".')
        elif not ok(inputs[key]):
            problems.append(f'{APP}.inputs.json has "{key}" set to {json.dumps(inputs[key])}; it should be {words}.')
    for key in inputs:
        if key not in KEYS and not key.startswith("_"):
            problems.append(f'{APP}.inputs.json has a key this app does not use: "{key}".')

    theme = inputs.get("theme")
    names = sorted(p.stem for p in THEMES.glob("*.css"))
    if isinstance(theme, str) and theme and theme not in names:
        problems.append(f'The theme "{theme}" does not exist; pick one of {", ".join(names)}.')

    back = inputs.get("cardBack")
    back_file = None
    if isinstance(back, str) and back and back not in BACKS:
        back_file = (project / back).resolve()
        if not back_file.is_file():
            problems.append(f'The card back picture "{back}" is not in this folder; give its path from here, or use classic, lattice, or monogram.')
        elif back_file.suffix.lower() not in IMAGE_TYPES:
            problems.append(f'The card back picture "{back}" should be a PNG, JPEG, WebP, or GIF.')
    if problems:
        fail(problems)

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)

    config = {key: inputs[key] for key in KEYS}
    if back_file is not None:
        media = out / "media"
        media.mkdir(exist_ok=True)
        target = media / f"card-back{back_file.suffix.lower()}"
        shutil.copyfile(back_file, target)
        config["cardBack"] = f"media/{target.name}"

    shutil.copyfile(THEMES / f"{theme}.css", out / "theme.css")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
