#!/usr/bin/env python3
"""Builds the Radio Dial page for the project in the current folder.

Reads radio-dial.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/radio-dial/, copies any station logo given as a file into out/radio-dial/media/, and writes config.js (the
inputs) and theme.css (the chosen theme) beside its index.html. Standard library only.
"""
import json
import shutil
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
INPUTS = "radio-dial.inputs.json"
OUT = Path("out") / "radio-dial"
REQUIRED = ["name", "presets", "theme"]
OPTIONAL = ["_notes"]
PRESET_KEYS = {"name", "url", "homepage", "country", "logo", "about"}
LOGO_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}


def text(v):
    return isinstance(v, str) and v.strip() != ""


def check(inputs, themes):
    problems = []
    say = problems.append
    if not isinstance(inputs, dict):
        return [f"{INPUTS} must hold one JSON object, like inputs.example.json."]
    for key in REQUIRED:
        if key not in inputs:
            say(f'{INPUTS} is missing the key "{key}".')
    for key in inputs:
        if key not in REQUIRED and key not in OPTIONAL:
            say(f'{INPUTS} has the key "{key}", which Radio Dial does not use.')
    if "name" in inputs and not text(inputs["name"]):
        say('"name" must be text, such as "Radio Dial" or "Sam\'s Radio".')
    if "theme" in inputs and inputs["theme"] not in themes:
        say(f'"theme" must be one of: {", ".join(sorted(themes))}.')

    presets = inputs.get("presets")
    if "presets" in inputs:
        if not isinstance(presets, list):
            say('"presets" must be a list of stations, each with a name and an https stream url.')
            return problems
        urls = set()
        for n, p in enumerate(presets, 1):
            where = f'"presets" item {n}'
            if not isinstance(p, dict):
                say(f"{where} must be an object with a name and a url.")
                continue
            for key in p:
                if key not in PRESET_KEYS:
                    say(f'{where} has the key "{key}", which Radio Dial does not use.')
            if not text(p.get("name")):
                say(f'{where} needs a "name", the station name shown on the dial.')
            url = p.get("url")
            if not (text(url) and url.strip().startswith("https://")):
                say(f'{where} needs a "url" that starts with https://, the station\'s stream.')
            elif url.strip() in urls:
                say(f'{where} repeats the stream {url.strip()}; each station needs its own.')
            else:
                urls.add(url.strip())
            for key in ("homepage", "country", "about"):
                if key in p and not isinstance(p[key], str):
                    say(f'{where} has "{key}", which must be text.')
            if "homepage" in p and text(p["homepage"]) and not p["homepage"].startswith(("https://", "http://")):
                say(f'{where} has a "homepage" that is not a web address.')
            logo = p.get("logo")
            if logo is not None:
                if not text(logo):
                    say(f'{where} has "logo", which must be an https address or a picture file in this folder.')
                elif not logo.startswith("https://"):
                    path = Path(logo)
                    if path.is_absolute() or ".." in path.parts or not path.is_file():
                        say(f'{where} names the logo "{logo}", which is not a file inside this folder.')
                    elif path.suffix.lower() not in LOGO_TYPES:
                        say(f'{where} names the logo "{logo}"; use a .png, .jpg, .webp, .svg, or .gif file.')
    return problems


def main():
    src = Path(INPUTS)
    if not src.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json in the app folder shows every key.")
        return 2
    try:
        inputs = json.loads(src.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        print(f"{INPUTS} is not valid JSON: {e}.")
        return 2
    themes = {p.stem for p in (APP / "src" / "themes").glob("*.css")}
    problems = check(inputs, themes)
    if problems:
        print("\n".join(problems))
        return 2

    dist = APP / "dist"
    if not (dist / "index.html").is_file():
        print(f"The built page is missing from {dist}; in {APP} run: npm ci && npm run build")
        return 2
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(dist, OUT)

    presets = []
    for n, p in enumerate(inputs["presets"], 1):
        station = {k: v.strip() for k, v in p.items() if isinstance(v, str) and v.strip()}
        logo = station.get("logo")
        if logo and not logo.startswith("https://"):
            media = OUT / "media"
            media.mkdir(exist_ok=True)
            name = f"{n}-{Path(logo).name}"
            shutil.copyfile(logo, media / name)
            station["logo"] = f"media/{name}"
        presets.append(station)
    config = {"name": inputs["name"].strip(), "theme": inputs["theme"], "presets": presets}
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")
    shutil.copyfile(APP / "src" / "themes" / f"{inputs['theme']}.css", OUT / "theme.css")
    count = sum(1 for f in OUT.rglob("*") if f.is_file())
    print(f"Wrote {OUT}/ ({count} files, {len(presets)} stations on the dial). "
          f"Serve it: python3 -m http.server 8000 --directory {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
