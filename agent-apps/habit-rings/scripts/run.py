"""Write Habit Rings for the project in the current folder.

Reads habit-rings.inputs.json from the current folder, checks it, copies the page from site/ into
out/habit-rings/, and writes config.js (the inputs) and theme.css (the chosen theme) beside index.html.
Each theme gets every habit's ring color and its five-step heat ramp, worked out here from the ring
color at fixed lightness steps, so a year map always reads. Two runs on the same inputs give the same files.

    cd <project> && python3 <agent-apps root>/habit-rings/scripts/run.py
"""

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path

APP = "habit-rings"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
THEMES = SITE / "themes"
BADGE = APP_DIR / "badge.js"
SRC = f"{APP}.inputs.json"

KEYS = {"name", "habits", "weekStart", "theme", "nudgeHour", "sample", "_notes"}
REQUIRED = ("name", "habits")
HABIT_KEYS = {"id", "label", "icon", "color", "target"}
MAX_HABITS = 8
WEEK_STARTS = ("mon", "sun")
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
ICONS = (
    "water", "run", "walk", "bike", "lift", "stretch", "breathe", "read", "write", "sleep", "sun",
    "leaf", "sprout", "cup", "pill", "heart", "music", "code", "talk", "no-phone", "spark", "check",
)

# The heat ramp: steps 1 to 4 at these OKLCH lightness values, with the ring color's chroma scaled by
# CHROMA. Step 0 is the theme's --cell-empty.
LIGHT_STEPS = (0.905, 0.80, 0.685, 0.565)
DARK_STEPS = (0.335, 0.455, 0.585, 0.725)
CHROMA = (0.32, 0.58, 0.82, 1.0)


def fail(lines):
    for line in lines:
        print(line)
    sys.exit(2)


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def check(inputs, theme_names):
    problems = []
    if not isinstance(inputs, dict):
        return [f"{SRC} must hold one JSON object with the keys inputs.example.json shows."]
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{SRC} is missing the key "{key}".')
    for key in sorted(set(inputs) - KEYS):
        problems.append(f'{SRC} has the key "{key}", which Habit Rings does not use.')

    if "name" in inputs and not isinstance(inputs["name"], str):
        problems.append(f'"name" in {SRC} must be text, the name the greeting uses.')

    habits = inputs.get("habits")
    if "habits" in inputs:
        if not isinstance(habits, list) or not habits:
            problems.append(f'"habits" in {SRC} must be a list of one to eight habits.')
        elif len(habits) > MAX_HABITS:
            problems.append(f'"habits" in {SRC} has {len(habits)} habits; the dial takes eight at most.')
        else:
            seen = set()
            for index, habit in enumerate(habits, start=1):
                where = f"Habit {index} in {SRC}"
                if not isinstance(habit, dict):
                    problems.append(f"{where} must be an object with an id, a label, and an icon.")
                    continue
                for key in ("id", "label", "icon"):
                    if key not in habit:
                        problems.append(f'{where} is missing the key "{key}".')
                for key in sorted(set(habit) - HABIT_KEYS):
                    problems.append(f'{where} has the key "{key}", which a habit does not use.')
                hid = habit.get("id")
                if "id" in habit:
                    if not isinstance(hid, str) or not ID.match(hid):
                        problems.append(f'{where} needs an "id" of lowercase letters, digits, and hyphens, like "water".')
                    elif hid in seen:
                        problems.append(f'{where} has the id "{hid}", which another habit already uses.')
                    else:
                        seen.add(hid)
                if "label" in habit and not is_text(habit["label"]):
                    problems.append(f'{where} needs a "label", the one or two words on its chip.')
                if "icon" in habit and habit["icon"] not in ICONS:
                    problems.append(f'{where} has the icon "{habit["icon"]}"; the icons are {", ".join(ICONS)}.')
                if "color" in habit and not (isinstance(habit["color"], str) and COLOR.match(habit["color"])):
                    problems.append(f'{where} has a "color" that is not a hex color like "#ff6a3d".')
                if "target" in habit:
                    target = habit["target"]
                    if isinstance(target, bool) or not isinstance(target, int) or not 2 <= target <= 99:
                        problems.append(f'{where} has a "target" that is not a whole number from 2 to 99.')

    if "weekStart" in inputs and inputs["weekStart"] not in WEEK_STARTS:
        problems.append(f'"weekStart" in {SRC} must be "mon" or "sun".')
    if "theme" in inputs and inputs["theme"] not in theme_names:
        problems.append(f'"theme" in {SRC} must be one of {", ".join(theme_names)}.')
    if "nudgeHour" in inputs:
        hour = inputs["nudgeHour"]
        if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
            problems.append(f'"nudgeHour" in {SRC} must be a whole hour from 0 to 23, like 20 for 8 pm.')
    if "sample" in inputs and not isinstance(inputs["sample"], bool):
        problems.append(f'"sample" in {SRC} must be true or false.')
    return problems


# OKLCH, for ramps that step evenly in lightness whatever the hue.
def to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_gamma(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def hex_to_oklch(text):
    text = text.lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    r, g, b = (to_linear(int(text[i:i + 2], 16) / 255) for i in (0, 2, 4))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return lightness, math.hypot(a, bb), math.atan2(bb, a)


def oklch_to_rgb(lightness, chroma, hue):
    a, b = chroma * math.cos(hue), chroma * math.sin(hue)
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )


def oklch_hex(lightness, chroma, hue):
    """The sRGB color nearest in chroma: chroma comes down until the color fits."""
    low, high = 0.0, chroma
    rgb = oklch_to_rgb(lightness, high, hue)
    if not all(-1e-6 <= c <= 1 + 1e-6 for c in rgb):
        for _ in range(28):
            mid = (low + high) / 2
            if all(-1e-6 <= c <= 1 + 1e-6 for c in oklch_to_rgb(lightness, mid, hue)):
                low = mid
            else:
                high = mid
        rgb = oklch_to_rgb(lightness, low, hue)
    return "#" + "".join(f"{round(min(1, max(0, to_gamma(min(1, max(0, c))))) * 255):02X}" for c in rgb)


def ramp(color, dark):
    _, chroma, hue = hex_to_oklch(color)
    steps = DARK_STEPS if dark else LIGHT_STEPS
    return [oklch_hex(lightness, chroma * scale, hue) for lightness, scale in zip(steps, CHROMA)]


BLOCK = re.compile(r"\{([^{}]*--ring-1:[^{}]*)\}")


def with_habits(css, habits):
    """The theme with --habit-N and --heat-N-1 to 4 added to every block that sets the ring colors."""

    def fill(match):
        body = match.group(1)
        dark = re.search(r"color-scheme:\s*dark", body) is not None
        indent = re.search(r"\n(\s*)--", body).group(1)
        lines = []
        for index, habit in enumerate(habits, start=1):
            ring = re.search(rf"--ring-{index}:\s*(#[0-9a-fA-F]{{3,6}})", body).group(1)
            color = habit.get("color", ring).upper()
            lines.append(f"{indent}--habit-{index}: {color};")
            for step, value in enumerate(ramp(color, dark), start=1):
                lines.append(f"{indent}--heat-{index}-{step}: {value};")
        closing = body[len(body.rstrip()):]
        return "{" + body.rstrip() + "\n" + "\n".join(lines) + closing + "}"

    return BLOCK.sub(fill, css)


def main():
    parser = argparse.ArgumentParser(description="Write Habit Rings into out/habit-rings/ from habit-rings.inputs.json.")
    parser.parse_args()

    project = Path.cwd()
    source = project / SRC
    if not source.is_file():
        fail([f"Make {SRC} in this folder first; inputs.example.json shows every key."])
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail([f"{SRC} is not valid JSON: {error}."])

    theme_names = sorted(path.stem for path in THEMES.glob("*.css"))
    problems = check(inputs, theme_names)
    if problems:
        fail(problems)

    config = {key: value for key, value in inputs.items() if key != "_notes"}
    config.setdefault("weekStart", "mon")
    config.setdefault("theme", "auto")
    config.setdefault("nudgeHour", 20)
    config.setdefault("sample", False)
    habits = config["habits"]

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")

    for path in sorted((out / "themes").glob("*.css")):
        path.write_text(with_habits(path.read_text(encoding="utf-8"), habits), encoding="utf-8")
    shutil.copyfile(out / "themes" / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(
        "window.__APP_CONFIG__ = " + json.dumps(config, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8"
    )

    count = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
