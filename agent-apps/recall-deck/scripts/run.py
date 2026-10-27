#!/usr/bin/env python3
"""Builds the Recall Deck page for the project in the current folder.

Reads recall-deck.inputs.json from the current folder, checks it, copies the built page from dist/ into
out/recall-deck/, and writes config.js (the deck and its defaults) and theme.css (the chosen theme) beside its
index.html. Running it twice with the same inputs writes the same files. Standard library only.
"""
import json
import re
import shutil
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
INPUTS = "recall-deck.inputs.json"
OUT = Path("out") / "recall-deck"
REQUIRED = ["deckName", "cards", "newPerDay", "typing", "font", "theme"]
OPTIONAL = ["progress", "_notes"]
CARD_KEYS = {"id", "front", "back", "tags", "hint"}
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def text(v):
    return isinstance(v, str) and v.strip() != ""


def check_cards(cards, say):
    ids = set()
    if not (isinstance(cards, list) and cards):
        say('"cards" must be a list of cards, each with an id, a front, a back, and tags.')
        return ids
    for n, c in enumerate(cards, 1):
        where = f'"cards" item {n}'
        if not isinstance(c, dict):
            say(f"{where} must be an object with an id, a front, a back, and tags.")
            continue
        for key in c:
            if key not in CARD_KEYS:
                say(f'{where} has the key "{key}", which Recall Deck does not use.')
        if not text(c.get("id")):
            say(f'{where} needs an "id", a short name that never changes, such as "stazione".')
        elif c["id"] in ids:
            say(f'{where} repeats the id "{c["id"]}"; each card needs its own.')
        else:
            ids.add(c["id"])
        for side in ("front", "back"):
            if not text(c.get(side)):
                say(f'{where} needs a "{side}", the text on that side of the card.')
        tags = c.get("tags")
        if not (isinstance(tags, list) and all(text(t) for t in tags)):
            say(f'{where} needs "tags", a list of words such as ["food"], or [] for none.')
        if "hint" in c and not text(c["hint"]):
            say(f'{where} has "hint", which must be text.')
    return ids


def check_progress(progress, ids, say):
    if not isinstance(progress, dict) or set(progress) - {"state", "log"}:
        say('"progress" must be an object with "state" and "log", like a file Export made, or leave it out.')
        return
    state = progress.get("state", {})
    if not isinstance(state, dict):
        say('"progress" "state" must map card ids to their schedules.')
    else:
        for cid, s in state.items():
            ok = (isinstance(s, dict) and number(s.get("ease")) and isinstance(s.get("interval"), int)
                  and isinstance(s.get("reps"), int) and isinstance(s.get("due"), str) and DAY.match(s["due"]))
            if not ok:
                say(f'"progress" card "{cid}" needs ease, interval, reps, and a due date written YYYY-MM-DD.')
            elif cid not in ids:
                say(f'"progress" names the card "{cid}", which is not in "cards".')
    log = progress.get("log", {})
    if not isinstance(log, dict):
        say('"progress" "log" must map days written YYYY-MM-DD to the counts for that day.')
    else:
        for day, l in log.items():
            if not (DAY.match(day) and isinstance(l, dict) and all(isinstance(l.get(k, 0), int) for k in ("seen", "fresh", "again"))):
                say(f'"progress" day "{day}" must be written YYYY-MM-DD and hold whole counts for seen, fresh, and again.')


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
            say(f'{INPUTS} has the key "{key}", which Recall Deck does not use.')
    if "deckName" in inputs and not text(inputs["deckName"]):
        say('"deckName" must be text, such as "Italian for the trip".')
    if "newPerDay" in inputs and not (isinstance(inputs["newPerDay"], int) and not isinstance(inputs["newPerDay"], bool)
                                      and 1 <= inputs["newPerDay"] <= 100):
        say('"newPerDay" must be a whole number from 1 to 100, such as 10.')
    if "typing" in inputs and not isinstance(inputs["typing"], bool):
        say('"typing" must be true or false.')
    if "font" in inputs and inputs["font"] not in ("sans", "serif"):
        say('"font" must be "sans" or "serif".')
    if "theme" in inputs and inputs["theme"] not in themes:
        say(f'"theme" must be one of: {", ".join(sorted(themes))}.')
    ids = check_cards(inputs.get("cards"), say) if "cards" in inputs else set()
    if "progress" in inputs:
        check_progress(inputs["progress"], ids, say)
    return problems


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
    config = {k: v for k, v in inputs.items() if k != "_notes"}
    (OUT / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")
    shutil.copyfile(APP / "src" / "themes" / f"{inputs['theme']}.css", OUT / "theme.css")
    count = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"Wrote {OUT}/ ({count} files, {len(inputs['cards'])} cards). Serve it: python3 -m http.server 8000 --directory {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
