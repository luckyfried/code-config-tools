"""Abyss Drift: writes the dive to out/abyss-drift/ in the current folder.

cd <project> && python3 <agent-apps root>/abyss-drift/scripts/run.py

Reads abyss-drift.inputs.json from the current folder, checks every key, copies the page, and writes config.js and
theme.css. Standard library only; two runs on the same inputs write the same bytes.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "abyss-drift"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
THEMES = SITE / "themes"
SPECIES = ["whale", "manta", "school", "jellyfish", "lanternfish", "anglerfish", "squid", "crab"]
TEXT_KEYS = ("title", "diverName", "theme", "seed")
KEYS = TEXT_KEYS + ("airSeconds", "species")


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def check(inputs):
    problems = []
    name = f"{APP}.inputs.json"
    if not isinstance(inputs, dict):
        return [f"{name} must hold one JSON object with the keys {', '.join(KEYS)}."]
    for key in KEYS:
        if key not in inputs:
            problems.append(f'{name} is missing the key "{key}".')
    for key in inputs:
        if key not in KEYS and key != "_notes":
            problems.append(f'{name} has the key "{key}", which this app does not use.')
    for key in TEXT_KEYS:
        if key in inputs and (not isinstance(inputs[key], str) or not inputs[key].strip()):
            problems.append(f'{name}: "{key}" must be a word or a few words, not empty.')
    themes = sorted(p.stem for p in THEMES.glob("*.css"))
    theme = inputs.get("theme")
    if isinstance(theme, str) and theme.strip() and theme not in themes:
        problems.append(f'{name}: "theme" is "{theme}"; the themes are {", ".join(themes)}.')
    air = inputs.get("airSeconds")
    if "airSeconds" in inputs and (isinstance(air, bool) or not isinstance(air, (int, float)) or not 45 <= air <= 600):
        problems.append(f'{name}: "airSeconds" must be a number of seconds from 45 to 600.')
    species = inputs.get("species")
    if "species" in inputs:
        if species == "all":
            pass
        elif not isinstance(species, list) or not species or not all(isinstance(s, str) for s in species):
            problems.append(f'{name}: "species" must be "all" or a list of names from {", ".join(SPECIES)}.')
        else:
            unknown = [s for s in species if s not in SPECIES]
            if unknown:
                problems.append(f'{name}: "species" names {", ".join(unknown)}; the species are {", ".join(SPECIES)}.')
    return problems


def main():
    project = Path.cwd()
    source = project / f"{APP}.inputs.json"
    if not source.is_file():
        fail([f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        fail([f"{APP}.inputs.json is not valid JSON: {err}."])
    problems = check(inputs)
    if problems:
        fail(problems)

    config = {key: inputs[key] for key in KEYS}
    if config["species"] == "all":
        config["species"] = list(SPECIES)

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    badge = HERE / "badge.js"
    if badge.is_file():
        shutil.copyfile(badge, out / "badge.js")
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
