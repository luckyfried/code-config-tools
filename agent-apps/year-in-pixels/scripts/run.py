"""Writes the Year in Pixels page from ./year-in-pixels.inputs.json.

Run from the project folder:
    python3 <agent-apps root>/year-in-pixels/scripts/run.py

Reads  ./year-in-pixels.inputs.json
Writes ./out/year-in-pixels/ (the page, config.js, theme.css)
"""

import json
import math
import re
import shutil
import sys
from pathlib import Path

APP = "year-in-pixels"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
INPUTS = f"{APP}.inputs.json"

KEYS = {
    "name": str,
    "year": int,
    "moods": list,
    "weekStart": str,
    "paper": str,
    "theme": str,
    "example": bool,
}
REQUIRED = ("name", "year")
# The default ramp runs cool to warm, roughest day to best, and every pair is far apart in OKLab.
DEFAULT_MOODS = [
    {"id": "rough", "label": "Rough", "color": "#3B4CC0"},
    {"id": "low", "label": "Low", "color": "#2C9AD1"},
    {"id": "okay", "label": "Okay", "color": "#5CC6A0"},
    {"id": "good", "label": "Good", "color": "#F4C04A"},
    {"id": "great", "label": "Great", "color": "#F05A38"},
]
DEFAULTS = {"moods": DEFAULT_MOODS, "weekStart": "mon", "paper": "A3", "theme": "auto", "example": False}
TYPE_WORDS = {str: "text", int: "a whole number", list: "a list", bool: "true or false"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
MOOD_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,23}$")
PAPERS = ("A3", "A4", "Letter")
WEEK_STARTS = ("mon", "sun")
# Two moods closer than this in OKLab look alike in a 9-pixel square.
CLOSE = 0.08


def fail(problems):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(2)


def oklab(hex_color):
    """sRGB hex to OKLab (L, a, b)."""
    def linear(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(int(hex_color[i:i + 2], 16)) for i in (1, 3, 5))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def load_inputs(path):
    if not path.exists():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        fail([f"{INPUTS} is not valid JSON (line {err.lineno}, column {err.colno}): {err.msg}."])
    if not isinstance(raw, dict):
        fail([f"{INPUTS} must hold one object with the keys inputs.example.json shows."])
    return {k: v for k, v in raw.items() if k != "_notes"}


def check_moods(moods):
    problems = []
    if len(moods) != 5:
        return [f'"moods" in {INPUTS} needs exactly five moods, from the roughest day to the best; it has {len(moods)}.']
    seen = set()
    for n, mood in enumerate(moods, start=1):
        where = f'mood {n} in "moods"'
        if not isinstance(mood, dict):
            problems.append(f'{where} must be an object with "id", "label", and "color".')
            continue
        for key in mood:
            if key not in ("id", "label", "color"):
                problems.append(f'{where} has the key "{key}"; a mood takes "id", "label", and "color".')
        for key in ("id", "label", "color"):
            if key not in mood:
                problems.append(f'{where} is missing the key "{key}".')
            elif not isinstance(mood[key], str):
                problems.append(f'"{key}" of {where} must be text.')
        if problems:
            continue
        if not MOOD_ID.match(mood["id"]):
            problems.append(f'"id" of {where} is "{mood["id"]}"; use lowercase letters, digits, and hyphens, like "great".')
        elif mood["id"] in seen:
            problems.append(f'Two moods have the id "{mood["id"]}"; each mood needs its own.')
        seen.add(mood["id"])
        if not mood["label"].strip() or len(mood["label"]) > 16:
            problems.append(f'"label" of {where} must be one to sixteen characters; it is "{mood["label"]}".')
        if not HEX.match(mood["color"]):
            problems.append(f'"color" of {where} is "{mood["color"]}"; write it as a hex color like "#F2643D".')
    return problems


def close_pairs(moods):
    """Names each pair of mood colors too close to tell apart."""
    labs = [oklab(m["color"]) for m in moods]
    lines = []
    for i in range(len(moods)):
        for j in range(i + 1, len(moods)):
            if math.dist(labs[i], labs[j]) < CLOSE:
                lines.append(
                    f'The colors for "{moods[i]["label"]}" ({moods[i]["color"]}) and "{moods[j]["label"]}" '
                    f'({moods[j]["color"]}) are close enough to look the same; pick one further from the other.'
                )
    return lines


def validate(inputs):
    problems = []
    for key in inputs:
        if key not in KEYS:
            problems.append(f'{INPUTS} has the key "{key}", which this app does not read. The keys are: {", ".join(KEYS)}.')
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
    for key, kind in KEYS.items():
        if key not in inputs:
            continue
        value = inputs[key]
        wrong = not isinstance(value, kind) or (kind is int and isinstance(value, bool))
        if wrong:
            problems.append(f'"{key}" in {INPUTS} must be {TYPE_WORDS[kind]}.')
    if problems:
        fail(problems)

    config = {**DEFAULTS, **inputs}
    if not config["name"].strip():
        problems.append(f'"name" in {INPUTS} is empty; it goes on the poster.')
    if not 1900 <= config["year"] <= 2100:
        problems.append(f'"year" is the year shown first, like 2026; it is {config["year"]}.')
    if config["weekStart"] not in WEEK_STARTS:
        problems.append(f'"weekStart" is "mon" or "sun"; it is "{config["weekStart"]}".')
    if config["paper"] not in PAPERS:
        problems.append(f'"paper" is A3, A4, or Letter; it is "{config["paper"]}".')
    themes = sorted(p.stem for p in THEMES.glob("*.css"))
    if config["theme"] not in themes:
        problems.append(f'"theme" is "{config["theme"]}"; the themes are: {", ".join(themes)}.')
    problems += check_moods(config["moods"])
    if problems:
        fail(problems)
    return config


def main():
    project = Path.cwd()
    config = validate(load_inputs(project / INPUTS))
    for line in close_pairs(config["moods"]):
        print(line, file=sys.stderr)

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)
    shutil.copyfile(THEMES / f'{config["theme"]}.css', out / "theme.css")
    ordered = {key: config[key] for key in KEYS}
    (out / "config.js").write_text(
        "window.__APP_CONFIG__ = " + json.dumps(ordered, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8"
    )
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
