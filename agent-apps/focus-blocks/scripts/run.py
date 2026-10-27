"""Writes the Focus Blocks page for the project in the current directory.

Reads focus-blocks.inputs.json from the current directory (inputs.example.json beside this app when the project has
none), copies site/ into out/focus-blocks/, and writes config.js from the inputs and theme.css from the chosen theme.

    cd <project> && python3 <agent-apps root>/focus-blocks/scripts/run.py
"""

import json
import shutil
import sys
from pathlib import Path

APP = "focus-blocks"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
INPUTS = f"{APP}.inputs.json"
OUT = Path("out") / APP
REQUIRED = {"name": str, "blockLengths": list, "labels": list, "dayStart": int, "dayEnd": int, "chime": str, "theme": str}
OPTIONAL = {"sample": bool}
NOTES = "_notes"  # the example's notes on each key; read by people, never by the page
TYPE_WORDS = {str: "text", list: "a list", int: "a whole number", bool: "true or false"}


def type_ok(value, kind):
    if kind is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, kind)


def validate(inputs, theme_names):
    if not isinstance(inputs, dict):
        return [f"{INPUTS} must hold one object with the keys {', '.join(REQUIRED)}."]
    problems = []
    for key, kind in REQUIRED.items():
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
        elif not type_ok(inputs[key], kind):
            problems.append(f'"{key}" must be {TYPE_WORDS[kind]}.')
    for key, kind in OPTIONAL.items():
        if key in inputs and not type_ok(inputs[key], kind):
            problems.append(f'"{key}" must be {TYPE_WORDS[kind]}.')
    for key in inputs:
        if key not in REQUIRED and key not in OPTIONAL and key != NOTES:
            problems.append(f'{INPUTS} has a key this app does not read: "{key}".')

    lengths = inputs.get("blockLengths")
    if type_ok(lengths, list):
        if not 1 <= len(lengths) <= 5:
            problems.append(f'"blockLengths" must list one to five lengths; it lists {len(lengths)}.')
        if not all(type_ok(n, int) and 1 <= n <= 240 for n in lengths):
            problems.append('"blockLengths" must be minutes from 1 to 240, like [25, 50, 90].')
    labels = inputs.get("labels")
    if type_ok(labels, list):
        if len(labels) > 6:
            problems.append(f'"labels" must list at most six words; it lists {len(labels)}.')
        if not all(isinstance(s, str) and s.strip() and len(s) <= 24 for s in labels):
            problems.append('"labels" must be short words of at most 24 characters, like ["writing", "code"].')
    start, end = inputs.get("dayStart"), inputs.get("dayEnd")
    if type_ok(start, int) and not 0 <= start <= 23:
        problems.append('"dayStart" must be an hour from 0 to 23.')
    if type_ok(end, int) and not 1 <= end <= 24:
        problems.append('"dayEnd" must be an hour from 1 to 24.')
    if type_ok(start, int) and type_ok(end, int) and end - start < 4:
        problems.append('"dayEnd" must be at least four hours after "dayStart".')
    if type_ok(inputs.get("chime"), str) and inputs["chime"] not in ("soft", "off"):
        problems.append('"chime" must be "soft" or "off".')
    if type_ok(inputs.get("theme"), str) and inputs["theme"] not in theme_names:
        problems.append(f'"theme" must be one of {", ".join(theme_names)}; "{inputs["theme"]}" is not a theme here.')
    if type_ok(inputs.get("name"), str) and len(inputs["name"]) > 40:
        problems.append('"name" must be at most 40 characters.')
    return problems


def main():
    source = Path(INPUTS)
    if not source.is_file():
        source = APP_DIR / "inputs.example.json"
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        print(f"{source.name} is not valid JSON: line {err.lineno}, column {err.colno}: {err.msg}.")
        return 2

    theme_names = sorted(p.stem for p in THEMES.glob("*.css"))
    problems = validate(inputs, theme_names)
    if problems:
        print("\n".join(problems))
        return 2

    config = {key: value for key, value in inputs.items() if key != NOTES}
    config["name"] = config["name"].strip()
    config["labels"] = [s.strip() for s in config["labels"]]

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT, ignore=shutil.ignore_patterns("config.js"))
    shutil.copyfile(APP_DIR / "assets" / "icon.svg", OUT / "icon.svg")
    (OUT / "theme.css").write_text((THEMES / f"{config['theme']}.css").read_text(encoding="utf-8"), encoding="utf-8")
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")

    count = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote {OUT}/ from {source.name} ({count} files). Serve it: python3 -m http.server 8000 --directory {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
