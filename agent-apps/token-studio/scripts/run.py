"""Token Studio's one entry point.

Run from the project folder:
    python3 <agent-apps root>/token-studio/scripts/run.py

Reads token-studio.inputs.json from the current folder, copies the built page
into out/token-studio/, writes config.js from the inputs and theme.css from the
chosen theme, and prints how to serve it. Standard library only.
"""

import json
import math
import re
import shutil
import sys
from pathlib import Path

APP = "token-studio"
HERE = Path(__file__).resolve().parents[1]
BUILT = HERE / "dist"
THEMES = HERE / "src" / "themes"
BADGE = HERE / "badge.js"

HEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
KEYS = {"brand", "neutralHue", "typeScaleRatio", "baseSize", "spacingBase", "fonts", "theme", "_notes"}
RANGES = {
    "neutralHue": (0, 360),
    "typeScaleRatio": (1.067, 1.618),
    "baseSize": (12, 22),
    "spacingBase": (2, 8),
}


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def hex_to_oklch(text):
    """OKLCH hue and chroma of an sRGB hex color (Bjorn Ottosson's Oklab)."""
    digits = HEX.match(text.strip()).group(1)
    if len(digits) == 3:
        digits = "".join(d * 2 for d in digits)

    def linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(int(digits[i : i + 2], 16) / 255) for i in (0, 2, 4))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    hue = math.degrees(math.atan2(bb, a)) % 360
    return round(hue, 1), round(math.hypot(a, bb), 3)


def problems_in(inputs):
    name = f"{APP}.inputs.json"
    problems = []
    if not isinstance(inputs, dict):
        return [f"{name} must hold one JSON object, like inputs.example.json."]
    for key in sorted(set(inputs) - KEYS):
        problems.append(f'{name} has the key "{key}", which Token Studio does not use.')
    for key in ("brand", "neutralHue", "typeScaleRatio", "baseSize", "spacingBase", "fonts", "theme"):
        if key not in inputs:
            problems.append(f'{name} is missing the key "{key}".')

    brand = inputs.get("brand")
    if "brand" in inputs:
        if not isinstance(brand, dict):
            problems.append(f'In {name}, "brand" must be an object with hue and chroma, or hex.')
        elif "hex" in brand:
            if not isinstance(brand["hex"], str) or not HEX.match(brand["hex"]):
                problems.append(f'In {name}, "brand.hex" must be a color like "#3d5afe".')
        else:
            if not is_number(brand.get("hue")) or not 0 <= brand["hue"] <= 360:
                problems.append(f'In {name}, "brand.hue" must be a number from 0 to 360, or give "brand.hex" instead.')
            if not is_number(brand.get("chroma")) or not 0.02 <= brand["chroma"] <= 0.37:
                problems.append(f'In {name}, "brand.chroma" must be a number from 0.02 to 0.37, or give "brand.hex" instead.')
        if isinstance(brand, dict):
            for key in sorted(set(brand) - {"hue", "chroma", "hex"}):
                problems.append(f'In {name}, "brand" has the key "{key}", which Token Studio does not use.')

    for key, (low, high) in RANGES.items():
        if key in inputs and (not is_number(inputs[key]) or not low <= inputs[key] <= high):
            problems.append(f'In {name}, "{key}" must be a number from {low} to {high}.')

    fonts = inputs.get("fonts")
    if "fonts" in inputs:
        if not isinstance(fonts, dict):
            problems.append(f'In {name}, "fonts" must be an object with "sans" and "mono".')
        else:
            for key in ("sans", "mono"):
                if not isinstance(fonts.get(key), str) or not fonts[key].strip():
                    problems.append(f'In {name}, "fonts.{key}" must be a font family name.')
            for key in sorted(set(fonts) - {"sans", "mono"}):
                problems.append(f'In {name}, "fonts" has the key "{key}", which Token Studio does not use.')

    if "theme" in inputs:
        names = sorted(path.stem for path in THEMES.glob("*.css"))
        if inputs["theme"] not in names:
            problems.append(f'In {name}, "theme" must be one of: {", ".join(names)}.')
    return problems


def main():
    project = Path.cwd()
    source = project / f"{APP}.inputs.json"
    if not source.is_file():
        print(f"Make {APP}.inputs.json in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"{APP}.inputs.json is not valid JSON ({error}).")
        return 2

    problems = problems_in(inputs)
    if problems:
        for line in problems:
            print(line)
        return 2
    if not (BUILT / "index.html").is_file():
        print(f"The built page is missing from {BUILT}; rebuild it with npm ci && npm run build in the app folder.")
        return 2

    config = {key: value for key, value in inputs.items() if key != "_notes"}
    brand = dict(config["brand"])
    if "hex" in brand:
        brand["hue"], brand["chroma"] = hex_to_oklch(brand["hex"])
        brand["chroma"] = min(0.37, max(0.02, brand["chroma"]))
        brand["hex"] = "#" + HEX.match(brand["hex"].strip()).group(1).lower()
    config["brand"] = brand

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(BUILT, out)
    if BADGE.is_file():
        shutil.copyfile(BADGE, out / "badge.js")
    shutil.copyfile(THEMES / f"{config['theme']}.css", out / "theme.css")
    (out / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8"
    )

    count = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
