"""Writes the Key Trainer page into out/key-trainer/ from key-trainer.inputs.json in the current folder.

Run it from the project folder:  python3 <agent-apps root>/key-trainer/scripts/run.py
"""

import json
import shutil
import sys
from pathlib import Path

APP = "key-trainer"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
THEMES = SITE / "themes"
LAYOUTS = ("qwerty", "qwertz", "azerty", "dvorak", "colemak")
MODES = ("prose", "code")
KEYS = {
    "name": "a name for the greeting, in quotes",
    "layout": "one of " + ", ".join(LAYOUTS),
    "mode": "prose or code",
    "passages": "a list of passages in quotes, or [] for the built-in set",
    "drillSeconds": "a whole number of seconds from 15 to 600",
    "theme": "a theme name",
}


def problems_in(inputs):
    themes = sorted(p.stem for p in THEMES.glob("*.css"))
    found = []
    for key in KEYS:
        if key not in inputs:
            found.append(f'{APP}.inputs.json is missing the key "{key}".')
    for key in inputs:
        if key not in KEYS and key != "_notes":
            found.append(f'{APP}.inputs.json has a key this app does not use: "{key}".')
    name = inputs.get("name")
    if "name" in inputs and not isinstance(name, str):
        found.append(f'"name" in {APP}.inputs.json should be {KEYS["name"]}.')
    if "layout" in inputs and inputs["layout"] not in LAYOUTS:
        found.append(f'"layout" in {APP}.inputs.json should be {KEYS["layout"]}.')
    if "mode" in inputs and inputs["mode"] not in MODES:
        found.append(f'"mode" in {APP}.inputs.json should be {KEYS["mode"]}.')
    passages = inputs.get("passages")
    if "passages" in inputs and (not isinstance(passages, list) or not all(isinstance(p, str) for p in passages)):
        found.append(f'"passages" in {APP}.inputs.json should be {KEYS["passages"]}.')
    seconds = inputs.get("drillSeconds")
    if "drillSeconds" in inputs and (isinstance(seconds, bool) or not isinstance(seconds, int) or not 15 <= seconds <= 600):
        found.append(f'"drillSeconds" in {APP}.inputs.json should be {KEYS["drillSeconds"]}.')
    theme = inputs.get("theme")
    if "theme" in inputs and theme not in themes:
        found.append(f'"theme" in {APP}.inputs.json should be one of: {", ".join(themes)}.')
    return found


def main():
    project = Path.cwd()
    source = project / f"{APP}.inputs.json"
    if not source.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        print(f"{APP}.inputs.json is not valid JSON: {error}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{APP}.inputs.json should hold one object with the keys inputs.example.json shows.")
        return 2
    found = problems_in(inputs)
    if found:
        print("\n".join(found))
        return 2

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)
    shutil.copyfile(HERE / "assets" / "icon.svg", out / "icon.svg")
    badge = HERE / "badge.js"
    if badge.is_file():
        shutil.copyfile(badge, out / "badge.js")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")

    config = {key: inputs[key] for key in KEYS}
    text = "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False, sort_keys=True) + ";\n"
    (out / "config.js").write_text(text, encoding="utf-8")

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
