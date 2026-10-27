"""Builds Glass Chess for the project folder it runs in.

Reads glass-chess.inputs.json from the current folder (inputs.example.json when there is none yet), copies the app's site/ into out/glass-chess/, writes the
person's settings to out/glass-chess/config.js, and puts the chosen board theme at out/glass-chess/theme.css.
Running it again replaces out/glass-chess/ whole, so the result is the same every time.

    cd <project> && python3 <path to>/agent-apps/glass-chess/scripts/run.py
"""
import json
import shutil
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
SITE = APP / "site"
INPUTS = Path("glass-chess.inputs.json")
EXAMPLE = APP / "inputs.example.json"
OUT = Path("out") / "glass-chess"
KEYS = ["title", "players", "strength", "theme", "clock", "sound"]
CLOCKS = ["none", "5+0", "10+0", "15+10"]


def stop(line):
    print(line)
    sys.exit(2)


def main():
    source = INPUTS if INPUTS.is_file() else EXAMPLE
    if source is EXAMPLE:
        print("No glass-chess.inputs.json here yet, so this run uses inputs.example.json.")
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        stop(f"glass-chess.inputs.json is not valid JSON: {err.msg} on line {err.lineno}.")
    if not isinstance(inputs, dict):
        stop("glass-chess.inputs.json must hold one JSON object; inputs.example.json shows every key.")
    for key in KEYS:
        if key not in inputs:
            stop(f'glass-chess.inputs.json is missing the key "{key}".')
    for key in inputs:
        if key not in KEYS and not key.startswith("_"):
            stop(f'glass-chess.inputs.json has the key "{key}", which Glass Chess does not use. The keys are: {", ".join(KEYS)}.')

    players = inputs["players"]
    if not isinstance(players, dict) or not {"white", "black"} <= players.keys():
        stop('"players" needs a "white" and a "black" name; "computer" makes that side the computer.')
    if not isinstance(inputs["strength"], int) or not 1 <= inputs["strength"] <= 4:
        stop('"strength" is the computer\'s level, a whole number from 1 to 4.')
    if inputs["clock"] not in CLOCKS:
        stop(f'"clock" is one of: {", ".join(CLOCKS)}.')
    if not isinstance(inputs["sound"], bool):
        stop('"sound" is true or false.')
    themes = sorted(p.stem for p in (SITE / "themes").glob("*.css"))
    if inputs["theme"] not in themes:
        stop(f'"theme" names a file in site/themes/; the themes are: {", ".join(themes)}.')

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT)
    settings = {k: inputs[k] for k in KEYS}
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(settings, ensure_ascii=False)};\n", encoding="utf-8")
    shutil.copyfile(SITE / "themes" / f"{inputs['theme']}.css", OUT / "theme.css")
    shutil.copyfile(APP / "assets" / "icon.svg", OUT / "icon.svg")

    count = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote out/glass-chess/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/glass-chess")


if __name__ == "__main__":
    main()
