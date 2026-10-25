"""Numbers Wall: builds the wall from numbers-wall.inputs.json in the current folder into out/numbers-wall/.

Run from the project folder:  cd <project> && python3 <agent-apps>/numbers-wall/scripts/run.py
The page is the built dist/ folder; this script copies it, then writes config.js from the inputs and theme.css from the
chosen theme. Nothing is compiled and nothing is fetched unless a metric names a source (scripts/sources.py).
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

APP = "numbers-wall"
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
THEMES = ROOT / "src" / "themes"
INPUTS = f"{APP}.inputs.json"

FORMATS = ("number", "currency", "percent", "duration")
SIZES = ("1x1", "2x1", "2x2")
TOP_KEYS = {"title": str, "refreshedAt": str, "theme": str, "copy": dict, "groups": list}
TOP_REQUIRED = ("title", "refreshedAt", "groups")
GROUP_KEYS = {"label": str, "metrics": list}
METRIC_KEYS = {
    "id": str,
    "label": str,
    "unit": str,
    "format": str,
    "higherIsBetter": bool,
    "size": str,
    "goal": (int, float, type(None)),
    "history": list,
    "source": dict,
}
METRIC_REQUIRED = ("id", "label", "format", "higherIsBetter", "size", "history")
AUTO = "auto"
COPY_KEYS = (
    "tvMode", "leaveTvMode", "tvHint", "refreshed", "notRefreshed", "since", "goal", "goalMet", "firstReading",
    "noReadings", "readings", "everyReading", "date", "reading", "change", "first", "emptyTitle", "emptyText",
)


def fail(problems):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(2)


def theme_names():
    return sorted([AUTO] + [p.stem for p in THEMES.glob("*.css")])


def theme_css(name):
    """auto is paper in a light system and obsidian in a dark one; every other name is its file."""
    if name == AUTO:
        light = (THEMES / "paper.css").read_text()
        dark = (THEMES / "obsidian.css").read_text()
        return f"{light}\n@media (prefers-color-scheme: dark) {{\n{dark}}}\n"
    return (THEMES / f"{name}.css").read_text()


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def type_name(kind):
    if kind is bool:
        return "true or false"
    if kind is list:
        return "a list"
    if kind is dict:
        return "an object"
    if kind is str:
        return "text"
    return "a number"


def check_keys(where, data, keys, required, problems):
    for key in required:
        if key not in data:
            problems.append(f"{INPUTS} is missing the key \"{key}\"{where}.")
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if key not in keys:
            problems.append(f"{INPUTS} has a key this app does not use: \"{key}\"{where}.")
            continue
        kind = keys[key]
        ok = is_number(value) or value is None if kind == (int, float, type(None)) else isinstance(value, kind)
        if not ok:
            problems.append(f"{INPUTS}: \"{key}\"{where} must be {type_name(kind if not isinstance(kind, tuple) else float)}.")


def parse_date(text):
    try:
        datetime.fromisoformat(text)
        return True
    except (TypeError, ValueError):
        return False


def validate(inputs):
    problems = []
    if not isinstance(inputs, dict):
        fail([f"{INPUTS} must hold one object with title, refreshedAt, and groups."])
    check_keys("", inputs, TOP_KEYS, TOP_REQUIRED, problems)
    if isinstance(inputs.get("refreshedAt"), str) and not parse_date(inputs["refreshedAt"]):
        problems.append(f"{INPUTS}: \"refreshedAt\" must be an ISO timestamp such as 2026-10-20T16:30:00Z.")
    theme = inputs.get("theme", AUTO)
    if isinstance(theme, str) and theme not in theme_names():
        problems.append(f"{INPUTS}: the theme \"{theme}\" does not exist. Pick one of: {', '.join(theme_names())}.")
    copy = inputs.get("copy")
    if isinstance(copy, dict):
        for key, value in copy.items():
            if key not in COPY_KEYS:
                problems.append(f"{INPUTS} has a key this app does not use: \"{key}\" in \"copy\". It uses: {', '.join(COPY_KEYS)}.")
            elif not isinstance(value, str):
                problems.append(f"{INPUTS}: \"{key}\" in \"copy\" must be text.")
    seen = set()
    for g, group in enumerate(inputs.get("groups") or []):
        if not isinstance(group, dict):
            problems.append(f"{INPUTS}: group {g + 1} must be an object with a label and metrics.")
            continue
        gname = group.get("label", f"group {g + 1}")
        check_keys(f" in the group \"{gname}\"", group, GROUP_KEYS, GROUP_KEYS, problems)
        for m, metric in enumerate(group.get("metrics") or []):
            if not isinstance(metric, dict):
                problems.append(f"{INPUTS}: metric {m + 1} in \"{gname}\" must be an object.")
                continue
            mname = metric.get("id") or metric.get("label") or f"metric {m + 1} in {gname}"
            where = f" in the metric \"{mname}\""
            check_keys(where, metric, METRIC_KEYS, METRIC_REQUIRED, problems)
            if isinstance(metric.get("id"), str):
                if metric["id"] in seen:
                    problems.append(f"{INPUTS}: two metrics share the id \"{metric['id']}\"; each id is used once.")
                seen.add(metric["id"])
            if isinstance(metric.get("format"), str) and metric["format"] not in FORMATS:
                problems.append(f"{INPUTS}: \"format\"{where} must be one of {', '.join(FORMATS)}.")
            if isinstance(metric.get("size"), str) and metric["size"] not in SIZES:
                problems.append(f"{INPUTS}: \"size\"{where} must be one of {', '.join(SIZES)}.")
            if isinstance(metric.get("source"), dict) and not isinstance(metric["source"].get("from"), str):
                problems.append(f"{INPUTS}: \"source\"{where} needs \"from\", the name of a function in scripts/sources.py.")
            history = metric.get("history")
            if isinstance(history, list):
                if not history and "source" not in metric:
                    problems.append(f"{INPUTS}: \"history\"{where} has no readings; add at least one {{\"date\", \"value\"}}.")
                for p, point in enumerate(history):
                    if not isinstance(point, dict) or not parse_date(point.get("date")) or not is_number(point.get("value")):
                        problems.append(
                            f"{INPUTS}: reading {p + 1}{where} must be {{\"date\": \"2026-10-19\", \"value\": 42}}."
                        )
    if problems:
        fail(problems)


def apply_sources(inputs):
    """Adds each sourced metric's fetched reading to its history, replacing a reading of the same date."""
    sourced = [m for g in inputs["groups"] for m in g["metrics"] if m.get("source")]
    if not sourced:
        return False
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "scripts"))
    import sources

    for metric in sourced:
        name = metric["source"]["from"]
        fetch = getattr(sources, name, None)
        if not callable(fetch) or name.startswith("_"):
            fail([f"{INPUTS}: the source \"{name}\" for \"{metric['id']}\" is not a function in scripts/sources.py."])
        try:
            point = fetch(metric["source"])
        except sources.MissingKey as missing:
            fail([f"The source \"{name}\" for \"{metric['id']}\" needs {missing.name}. Set it with csc key set, then run again."])
        except sources.SourceError as error:
            fail([f"The source \"{name}\" for \"{metric['id']}\" could not read a number: {error}"])
        history = [p for p in metric["history"] if p["date"] != point["date"]]
        history.append({"date": point["date"], "value": point["value"]})
        metric["history"] = sorted(history, key=lambda p: p["date"])
    return True


def write_atomic(path, text):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text)
    os.replace(temp, path)


def main():
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    project = Path.cwd()
    inputs_path = project / INPUTS
    if not inputs_path.is_file():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(inputs_path.read_text())
    except json.JSONDecodeError as error:
        fail([f"{INPUTS} is not valid JSON: line {error.lineno}, column {error.colno}: {error.msg}."])
    validate(inputs)
    if not (DIST / "index.html").is_file():
        fail([f"The app folder has no built page at {DIST}; rebuild it with npm ci && npm run build in {ROOT}."])

    if apply_sources(inputs):
        write_atomic(inputs_path, json.dumps(inputs, indent=2, ensure_ascii=False) + "\n")

    config = {key: value for key, value in inputs.items() if not key.startswith("_")}
    for group in config["groups"]:
        for metric in group["metrics"]:
            metric.pop("source", None)
            metric["history"] = sorted(metric["history"], key=lambda p: p["date"])

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DIST, out)
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n")
    (out / "theme.css").write_text(theme_css(inputs.get("theme", AUTO)))
    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
