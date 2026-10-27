#!/usr/bin/env python3
"""Builds the Hours Ledger page for the project in the current folder.

Reads hours-ledger.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/hours-ledger/, and writes config.js (the inputs) and theme.css (the chosen theme, plus the ledger paper the
statement always prints on) beside its index.html. Standard library only; runs on Python 3.8 and later.
"""
import json
import re
import shutil
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
THEMES = APP / "src" / "themes"
INPUTS = "hours-ledger.inputs.json"
OUT = Path("out") / "hours-ledger"
REQUIRED = ["name", "currency", "clients", "rounding", "weekStart", "theme"]
OPTIONAL = ["sample", "statementNote", "_notes"]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def theme_names():
    return sorted({p.stem for p in THEMES.glob("*.css")} | {"auto"})


def check(inputs):
    problems = []
    say = problems.append
    if not isinstance(inputs, dict):
        return [f"{INPUTS} must hold one JSON object, like inputs.example.json."]
    for key in REQUIRED:
        if key not in inputs:
            say(f'{INPUTS} is missing the key "{key}".')
    for key in inputs:
        if key not in REQUIRED and key not in OPTIONAL:
            say(f'{INPUTS} has the key "{key}", which Hours Ledger does not use.')

    if "name" in inputs and not (isinstance(inputs["name"], str) and inputs["name"].strip()):
        say('"name" must be the person or studio named on statements, such as "Maya Okafor Design".')
    if "currency" in inputs and not (isinstance(inputs["currency"], str) and re.fullmatch(r"[A-Z]{3}", inputs["currency"])):
        say('"currency" must be a three-letter currency code, such as "USD" or "EUR".')
    if "rounding" in inputs and inputs["rounding"] not in (0, 6, 15):
        say('"rounding" must be 0, 6, or 15: the minutes each entry rounds up to on a statement.')
    if "weekStart" in inputs and inputs["weekStart"] not in ("mon", "sun"):
        say('"weekStart" must be "mon" or "sun".')
    if "theme" in inputs and inputs["theme"] not in theme_names():
        say(f'"theme" must be one of: {", ".join(theme_names())}.')
    if "sample" in inputs and not isinstance(inputs["sample"], bool):
        say('"sample" must be true or false.')
    if "statementNote" in inputs and not isinstance(inputs["statementNote"], str):
        say('"statementNote" must be text, such as "Payment due within 14 days."')

    clients = inputs.get("clients")
    if "clients" in inputs:
        if not (isinstance(clients, list) and clients):
            say('"clients" must be a list of clients, each with an id, a name, a rate, and a color.')
        else:
            ids = set()
            for n, c in enumerate(clients, 1):
                where = f'"clients" item {n}'
                if not isinstance(c, dict):
                    say(f"{where} must be an object with an id, a name, a rate, and a color.")
                    continue
                for key in c:
                    if key not in ("id", "name", "rate", "color"):
                        say(f'{where} has the key "{key}", which Hours Ledger does not use.')
                cid = c.get("id")
                if not (isinstance(cid, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", cid)):
                    say(f'{where} needs an "id": lowercase letters, digits, and hyphens, such as "northwind".')
                elif cid in ids:
                    say(f'{where} repeats the id "{cid}"; each client needs its own.')
                else:
                    ids.add(cid)
                if not (isinstance(c.get("name"), str) and c["name"].strip()):
                    say(f'{where} needs a "name", as it appears on the statement.')
                if not (number(c.get("rate")) and c["rate"] >= 0):
                    say(f'{where} needs a "rate", the hourly rate as a number, such as 120.')
                if not (isinstance(c.get("color"), str) and HEX.match(c["color"])):
                    say(f'{where} needs a "color" as six-digit hex, such as "#4f6ef7".')
    return problems


def compose_theme(name):
    """The chosen theme, then the ledger paper for the statement sheet and for print."""
    ledger = (THEMES / "ledger.css").read_text(encoding="utf-8").strip()
    if name == "auto":
        studio = (THEMES / "studio.css").read_text(encoding="utf-8").strip()
        screen = f"{ledger}\n\n@media (prefers-color-scheme: dark) {{\n{studio}\n}}"
    else:
        screen = (THEMES / f"{name}.css").read_text(encoding="utf-8").strip()
    paper = ledger.replace(":root {", ".paper {", 1)
    return (
        f"{screen}\n\n/* The statement sheet is paper in every theme. */\n{paper}\n\n"
        f"/* A printed statement is always the ledger paper. */\n@media print {{\n{ledger}\n}}\n"
    )


def main():
    src = Path(INPUTS)
    if not src.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(src.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        print(f"{INPUTS} is not valid JSON: {e}.")
        return 2
    problems = check(inputs)
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
    config = {k: v for k, v in inputs.items() if k != "_notes"}
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")
    (OUT / "theme.css").write_text(compose_theme(inputs["theme"]), encoding="utf-8")
    count = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote {OUT}/ ({count} files). Serve it: python3 -m http.server 8000 --directory {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
