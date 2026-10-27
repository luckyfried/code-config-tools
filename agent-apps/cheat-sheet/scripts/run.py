"""Writes the Cheat Sheet page from cheat-sheet.inputs.json in the current folder.

Run from the project folder:  python3 <agent-apps root>/cheat-sheet/scripts/run.py
Reads cheat-sheet.inputs.json; writes out/cheat-sheet/ (the page, config.js, and theme.css).
"""

import json
import shutil
import sys
from pathlib import Path

SLUG = "cheat-sheet"
APP = Path(__file__).resolve().parents[1]
SITE = APP / "site"
THEMES = SITE / "themes"
INPUTS = f"{SLUG}.inputs.json"

KEYS = ["title", "platform", "columns", "paper", "theme", "sections", "_notes"]
REQUIRED = ["title", "sections"]
DEFAULTS = {"platform": "mac", "columns": 3, "paper": "Letter", "theme": "graphite"}
PLATFORMS = ["mac", "windows", "linux"]
PAPERS = ["A4", "Letter"]
SECTION_KEYS = {"label", "entries"}
ENTRY_KEYS = {"action", "keys", "command", "note", "platforms"}


def fail(problems):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(2)


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def keys_problem(value):
    """Keys are one chord (a list of key names) or a sequence of chords (a list of lists). None when they are fine."""
    if not isinstance(value, list) or not value:
        return "must be a list of key names, like [\"mod\", \"shift\", \"p\"]"
    chords = value if all(isinstance(c, list) for c in value) else [value]
    for chord in chords:
        if not chord or not all(is_text(k) for k in chord):
            return "must hold key names as text, like [\"mod\", \"shift\", \"p\"] or [[\"ctrl\", \"b\"], [\"%\"]]"
    return None


def theme_names():
    return sorted(p.stem for p in THEMES.glob("*.css"))


def validate(data):
    if not isinstance(data, dict):
        fail([f"{INPUTS} must hold one object with the keys title and sections."])
    problems = []
    for key in data:
        if key not in KEYS:
            problems.append(f'{INPUTS} has the key "{key}", which this app does not use.')
    for key in REQUIRED:
        if key not in data:
            problems.append(f'{INPUTS} is missing the key "{key}".')

    if "title" in data and not is_text(data["title"]):
        problems.append(f'In {INPUTS}, "title" must be some text.')
    if "platform" in data and data["platform"] not in PLATFORMS:
        problems.append(f'In {INPUTS}, "platform" must be mac, windows, or linux.')
    if "columns" in data and (isinstance(data["columns"], bool) or data["columns"] not in (2, 3)):
        problems.append(f'In {INPUTS}, "columns" must be 2 or 3.')
    if "paper" in data and data["paper"] not in PAPERS:
        problems.append(f'In {INPUTS}, "paper" must be A4 or Letter.')
    if "theme" in data and data["theme"] not in theme_names():
        problems.append(f'In {INPUTS}, "theme" must be one of: {", ".join(theme_names())}.')

    sections = data.get("sections")
    if "sections" in data:
        if not isinstance(sections, list) or not sections:
            problems.append(f'In {INPUTS}, "sections" must be a list with at least one section.')
        else:
            for s, section in enumerate(sections, 1):
                if not isinstance(section, dict):
                    problems.append(f"In {INPUTS}, section {s} must be an object with a label and entries.")
                    continue
                for key in section:
                    if key not in SECTION_KEYS:
                        problems.append(f'In {INPUTS}, section {s} has the key "{key}"; a section takes label and entries.')
                if not is_text(section.get("label")):
                    problems.append(f'In {INPUTS}, section {s} is missing its "label".')
                entries = section.get("entries")
                if not isinstance(entries, list) or not entries:
                    problems.append(f'In {INPUTS}, section {s} needs "entries", a list with at least one entry.')
                    continue
                for e, entry in enumerate(entries, 1):
                    where = f"section {s}, entry {e}"
                    if not isinstance(entry, dict):
                        problems.append(f"In {INPUTS}, {where} must be an object with an action.")
                        continue
                    for key in entry:
                        if key not in ENTRY_KEYS:
                            problems.append(
                                f'In {INPUTS}, {where} has the key "{key}"; an entry takes action, keys, command, note, and platforms.'
                            )
                    if not is_text(entry.get("action")):
                        problems.append(f'In {INPUTS}, {where} is missing its "action".')
                    if not any(k in entry for k in ("keys", "command", "platforms")):
                        problems.append(f"In {INPUTS}, {where} needs keys, a command, or platforms.")
                    if "keys" in entry and (msg := keys_problem(entry["keys"])):
                        problems.append(f'In {INPUTS}, {where}: "keys" {msg}.')
                    for key in ("command", "note"):
                        if key in entry and not is_text(entry[key]):
                            problems.append(f'In {INPUTS}, {where}: "{key}" must be some text.')
                    platforms = entry.get("platforms")
                    if "platforms" in entry:
                        if not isinstance(platforms, dict) or not platforms:
                            problems.append(f'In {INPUTS}, {where}: "platforms" must be an object like {{"windows": ["ctrl", "k"]}}.')
                        else:
                            for name, keys in platforms.items():
                                if name not in PLATFORMS:
                                    problems.append(f'In {INPUTS}, {where}: "platforms" has "{name}"; it takes mac, windows, and linux.')
                                elif msg := keys_problem(keys):
                                    problems.append(f'In {INPUTS}, {where}: "platforms.{name}" {msg}.')
                            if "keys" not in entry and set(platforms) != set(PLATFORMS) and "command" not in entry:
                                missing = [p for p in PLATFORMS if p not in platforms]
                                problems.append(
                                    f'In {INPUTS}, {where} has no "keys" and no keys for {" or ".join(missing)} in "platforms".'
                                )
    if problems:
        fail(problems)


def main():
    project = Path.cwd()
    source = project / INPUTS
    if not source.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        fail([f"{INPUTS} is not valid JSON: line {err.lineno}, column {err.colno}: {err.msg}."])
    validate(data)

    config = {key: data.get(key, DEFAULTS.get(key)) for key in KEYS if key != "_notes"}

    out = project / "out" / SLUG
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False, indent=2)};\n", encoding="utf-8"
    )

    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{SLUG}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{SLUG}")


if __name__ == "__main__":
    main()
