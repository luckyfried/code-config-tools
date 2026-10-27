"""Era Timeline: turns <project>/era-timeline.inputs.json into the page at <project>/out/era-timeline/.

Run it from the project folder:

    cd <project> && python3 <agent-apps root>/era-timeline/scripts/run.py

Standard library only. Two runs on the same inputs write byte-identical files.
"""

import json
import re
import shutil
import sys
from pathlib import Path

APP = "era-timeline"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
THEMES = SITE / "themes"
INPUTS = f"{APP}.inputs.json"

REQUIRED = {
    "title": str,
    "eras": list,
    "events": list,
    "start": str,
    "end": str,
    "orientation": str,
    "theme": str,
}
OPTIONAL = {"subtitle": str, "autoplay": bool, "_notes": dict}
ERA_KEYS = {"label": True, "from": True, "to": True, "color": True}
EVENT_KEYS = {"date": True, "label": True, "text": False, "image": False, "era": False}
HUES = ("red", "orange", "gold", "green", "teal", "blue", "violet", "rose")
ORIENTATIONS = ("auto", "horizontal", "vertical")
DATE = re.compile(r"^(-?)(\d{1,4})(?:-(\d{2})(?:-(\d{2}))?)?$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
DAYS = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif")
TYPE_WORDS = {str: "text", list: "a list", bool: "true or false", dict: "an object"}


def fail(problems):
    for line in problems:
        print(line)
    sys.exit(2)


def date_key(text):
    """A sortable (year, month, day) for a date string, or None when it is not a date."""
    found = DATE.match(text.strip()) if isinstance(text, str) else None
    if not found:
        return None
    sign, year, month, day = found.groups()
    year = int(year)
    if sign:
        year = 1 - year
    month = int(month) if month else 0
    day = int(day) if day else 0
    if month and not 1 <= month <= 12:
        return None
    if day and not 1 <= day <= DAYS[month - 1]:
        return None
    return (year, month, day)


def check_date(value, where, problems):
    if not isinstance(value, str) or date_key(value) is None:
        problems.append(f'{INPUTS} has {where} = {json.dumps(value, ensure_ascii=False)}, which is not a date like 1911, 1911-05, or 1911-05-02.')
        return None
    return date_key(value)


def check_keys(item, allowed, where, problems):
    if not isinstance(item, dict):
        problems.append(f"{INPUTS} has {where}, which is not an object.")
        return False
    for key, required in allowed.items():
        if required and key not in item:
            problems.append(f'{INPUTS} is missing the key "{key}" in {where}.')
    for key in item:
        if key not in allowed:
            problems.append(f'{INPUTS} has the key "{key}" in {where}, which this app does not use.')
    return True


def find_image(path, project):
    """The file an event's image names: beside the inputs first, then in the app's own folder (its sample pictures)."""
    for root in (project, HERE):
        candidate = (root / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(root.resolve()):
            return candidate
    return None


def validate(inputs, project):
    problems = []
    for key, kind in REQUIRED.items():
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
        elif not isinstance(inputs[key], kind):
            problems.append(f'{INPUTS} has "{key}" as {TYPE_WORDS[type(inputs[key])] if type(inputs[key]) in TYPE_WORDS else "something else"}; it must be {TYPE_WORDS[kind]}.')
    for key, kind in OPTIONAL.items():
        if key in inputs and not isinstance(inputs[key], kind):
            problems.append(f'{INPUTS} has "{key}" that is not {TYPE_WORDS[kind]}.')
    for key in inputs:
        if key not in REQUIRED and key not in OPTIONAL:
            problems.append(f'{INPUTS} has the key "{key}", which this app does not use.')
    if problems:
        return problems, []

    if not inputs["title"].strip():
        problems.append(f'{INPUTS} has an empty "title".')
    if inputs["orientation"] not in ORIENTATIONS:
        problems.append(f'{INPUTS} has "orientation" = "{inputs["orientation"]}"; it must be auto, horizontal, or vertical.')
    themes = sorted(path.stem for path in THEMES.glob("*.css"))
    if inputs["theme"] not in themes:
        problems.append(f'{INPUTS} has "theme" = "{inputs["theme"]}"; the themes are {", ".join(themes)}.')

    start = check_date(inputs["start"], '"start"', problems)
    end = check_date(inputs["end"], '"end"', problems)
    if start and end and not start < end:
        problems.append(f'{INPUTS} has "start" at or after "end"; the first view needs start before end.')

    labels = []
    for index, era in enumerate(inputs["eras"]):
        where = f"eras[{index}]"
        if not check_keys(era, ERA_KEYS, where, problems):
            continue
        label = era.get("label")
        if not isinstance(label, str) or not label.strip():
            problems.append(f'{INPUTS} has an era label in {where} that is not text.')
        else:
            if label in labels:
                problems.append(f'{INPUTS} has two eras labeled "{label}"; each era needs its own label.')
            labels.append(label)
        begin = check_date(era.get("from"), f'{where}.from', problems) if "from" in era else None
        finish = check_date(era.get("to"), f'{where}.to', problems) if "to" in era else None
        if begin and finish and not begin <= finish:
            problems.append(f'{INPUTS} has {where} ending before it starts.')
        color = era.get("color")
        if "color" in era and not (isinstance(color, str) and (color in HUES or HEX.match(color))):
            problems.append(f'{INPUTS} has {where}.color = {json.dumps(color, ensure_ascii=False)}; it must be one of {", ".join(HUES)}, or a #rrggbb color.')

    if not inputs["events"]:
        problems.append(f'{INPUTS} has no events; add at least one with a date and a label.')
    images = []
    for index, event in enumerate(inputs["events"]):
        where = f"events[{index}]"
        if not check_keys(event, EVENT_KEYS, where, problems):
            continue
        if "date" in event:
            check_date(event["date"], f"{where}.date", problems)
        for key in ("label", "text", "era"):
            if key in event and not isinstance(event[key], str):
                problems.append(f'{INPUTS} has {where}.{key} that is not text.')
        if isinstance(event.get("label"), str) and not event["label"].strip():
            problems.append(f'{INPUTS} has an empty label in {where}.')
        if isinstance(event.get("era"), str) and event["era"] not in labels:
            problems.append(f'{INPUTS} has {where}.era = "{event["era"]}", which is not the label of any era.')
        if "image" in event:
            path = event["image"]
            if not isinstance(path, str) or not path.strip():
                problems.append(f'{INPUTS} has {where}.image that is not a file path.')
            elif Path(path).is_absolute() or ".." in Path(path).parts:
                problems.append(f'{INPUTS} has {where}.image = "{path}"; give a path inside the project folder.')
            elif Path(path).suffix.lower() not in IMAGE_TYPES:
                problems.append(f'{INPUTS} has {where}.image = "{path}", which is not a picture ({", ".join(IMAGE_TYPES)}).')
            else:
                found = find_image(path, project)
                if found is None:
                    problems.append(f'{INPUTS} has {where}.image = "{path}", and there is no such file beside it.')
                else:
                    images.append((index, path, found))
    return problems, images


def js(name, value):
    return f"window.{name} = {json.dumps(value, ensure_ascii=False, indent=1)};\n"


def main():
    project = Path.cwd()
    source = project / INPUTS
    if not source.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        fail([f"{INPUTS} is not valid JSON: {error}."])
    if not isinstance(inputs, dict):
        fail([f"{INPUTS} must hold one JSON object."])

    problems, images = validate(inputs, project)
    if problems:
        fail(problems)

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SITE, out)
    badge = HERE / "badge.js"
    if badge.is_file():
        shutil.copyfile(badge, out / "badge.js")

    events = [dict(event) for event in inputs["events"]]
    for index, path, found in images:
        target = Path("media") / Path(path)
        (out / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(found, out / target)
        events[index]["image"] = target.as_posix()

    config = {key: inputs[key] for key in ("title", "subtitle", "start", "end", "orientation", "theme", "autoplay") if key in inputs}
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(js("__APP_CONFIG__", config), encoding="utf-8")
    (out / "data.js").write_text(js("__APP_DATA__", {"eras": inputs["eras"], "events": events}), encoding="utf-8")

    count = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    sys.exit(0)


if __name__ == "__main__":
    main()
