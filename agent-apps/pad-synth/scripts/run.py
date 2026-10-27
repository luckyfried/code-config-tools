"""Writes the Pad Synth page into out/pad-synth/ from pad-synth.inputs.json.

Run it from the project folder:

    python3 <agent-apps root>/pad-synth/scripts/run.py

It reads pad-synth.inputs.json from the current folder, checks every key,
copies the page from site/ into out/pad-synth/, writes theme.css from the
chosen theme and config.js from the inputs, and prints how to serve it. Two
runs on the same inputs write the same bytes.
"""

import json
import shutil
import sys
from pathlib import Path

APP = "pad-synth"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
BADGE = APP_DIR / "badge.js"

SCALES = (
    "major",
    "minor",
    "dorian",
    "mixolydian",
    "lydian",
    "phrygian",
    "harmonic-minor",
    "major-pentatonic",
    "minor-pentatonic",
    "blues",
    "chromatic",
)
KEYS = ("C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B")
VOICES = ("pluck", "pad", "bass", "keys")
GRIDS = ("5x8", "6x10")
REQUIRED = ("name", "scale", "key", "voices", "grid", "bpm", "theme")


def quoted(items):
    return ", ".join(f'"{item}"' for item in items)


def problems_in(inputs, file_name):
    problems = []
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{file_name} is missing the key "{key}".')
    for key in inputs:
        if key not in REQUIRED and not key.startswith("_"):
            problems.append(f'{file_name} has the key "{key}", which Pad Synth does not use.')

    name = inputs.get("name")
    if "name" in inputs and (not isinstance(name, str) or not name.strip() or len(name) > 40):
        problems.append(f'"name" in {file_name} must be text of 1 to 40 characters.')
    scale = inputs.get("scale")
    if "scale" in inputs and scale not in SCALES:
        problems.append(f'"scale" in {file_name} must be one of {quoted(SCALES)}.')
    key = inputs.get("key")
    if "key" in inputs and key not in KEYS:
        problems.append(f'"key" in {file_name} must be one of {quoted(KEYS)}.')
    voices = inputs.get("voices")
    if "voices" in inputs and (
        not isinstance(voices, list)
        or not voices
        or any(voice not in VOICES for voice in voices)
        or len(set(voices)) != len(voices)
    ):
        problems.append(f'"voices" in {file_name} must list one or more of {quoted(VOICES)}, each once.')
    grid = inputs.get("grid")
    if "grid" in inputs and grid not in GRIDS:
        problems.append(f'"grid" in {file_name} must be "5x8" or "6x10".')
    bpm = inputs.get("bpm")
    if "bpm" in inputs and (isinstance(bpm, bool) or not isinstance(bpm, int) or not 50 <= bpm <= 200):
        problems.append(f'"bpm" in {file_name} must be a whole number from 50 to 200.')
    theme = inputs.get("theme")
    themes = sorted(path.stem for path in THEMES.glob("*.css"))
    if "theme" in inputs and theme not in themes:
        problems.append(f'"theme" in {file_name} must be one of {quoted(themes)}.')
    return problems


def main():
    file_name = f"{APP}.inputs.json"
    inputs_path = Path.cwd() / file_name
    if not inputs_path.is_file():
        print(f"Make {file_name} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"{file_name} is not readable JSON: {error}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{file_name} must hold one JSON object.")
        return 2

    problems = problems_in(inputs, file_name)
    if problems:
        for line in problems:
            print(line)
        return 2

    config = {key: inputs[key] for key in REQUIRED}
    config["name"] = config["name"].strip()

    out = Path.cwd() / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    config_text = "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False) + ";\n"
    (out / "config.js").write_text(config_text, encoding="utf-8")

    count = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
