"""Tournament Bracket: builds the bracket page from tournament-bracket.inputs.json in the current folder into out/tournament-bracket/.

Run from the project folder:  cd <project> && python3 <agent-apps>/tournament-bracket/scripts/run.py
The page is the built dist/ folder; this script copies it, then writes config.js from the inputs and theme.css from the
chosen theme. Nothing is compiled and nothing is fetched.
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

APP = "tournament-bracket"
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
THEMES = ROOT / "src" / "themes"
INPUTS = f"{APP}.inputs.json"
AUTO = "auto"

TOP_KEYS = {
    "title": str,
    "entrants": list,
    "people": list,
    "results": list,
    "picks": dict,
    "colors": dict,
    "theme": str,
    "copy": dict,
}
TOP_REQUIRED = ("title", "entrants")
COPY_KEYS = (
    "bracket", "picks", "results", "pool", "bigScreen", "leaveBigScreen", "replay", "wholeBracket", "export", "import",
    "champion", "upset", "bye", "points", "correct", "maxPossible", "championPick", "picksFor", "passTo", "picksDone",
    "resultsHint", "picksHint", "scorePlaceholder", "clear", "waiting", "imported", "importFailed", "noPeople",
)
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def fail(problems):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(2)


def theme_names():
    return sorted([AUTO] + [p.stem for p in THEMES.glob("*.css")])


def theme_css(name):
    """auto is paper in a light system and broadcast in a dark one; every other name is its file."""
    if name == AUTO:
        light = (THEMES / "paper.css").read_text()
        dark = (THEMES / "broadcast.css").read_text()
        return f"{light}\n@media (prefers-color-scheme: dark) {{\n{dark}}}\n"
    return (THEMES / f"{name}.css").read_text()


def type_name(kind):
    return {list: "a list", dict: "an object", str: "text"}[kind]


def seed_order(size):
    order = [1]
    while len(order) < size:
        n = len(order) * 2
        order = [x for s in order for x in (s, n + 1 - s)]
    return order


def bracket(entrants):
    """The matches in play order, as (id, [source, source]); a source is an entrant's name or an earlier match id.
    The same table as src/lib/bracket.ts: byes go to the top seeds, and round one holds only real pairs."""
    n = len(entrants)
    size = 2
    while size < n:
        size *= 2
    order = seed_order(size)
    seeded = lambda s: entrants[s - 1] if s <= n else None
    sources, matches, byes = [], [], 0
    for k in range(size // 2):
        a, b = seeded(order[2 * k]), seeded(order[2 * k + 1])
        if a and b:
            mid = f"R1-{sum(1 for m in matches) + 1}"
            matches.append((mid, [a, b]))
            sources.append(mid)
        else:
            byes += 1
            sources.append(a or b)
    r = 2
    while len(sources) > 1:
        nxt = []
        for k in range(len(sources) // 2):
            mid = f"R{r}-{k + 1}"
            matches.append((mid, [sources[2 * k], sources[2 * k + 1]]))
            nxt.append(mid)
        sources, r = nxt, r + 1
    return matches, byes


def check_keys(data, problems):
    for key in TOP_REQUIRED:
        if key not in data:
            problems.append(f"{INPUTS} is missing the key \"{key}\".")
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if key not in TOP_KEYS:
            problems.append(f"{INPUTS} has a key this app does not use: \"{key}\". It uses: {', '.join(TOP_KEYS)}.")
        elif not isinstance(value, TOP_KEYS[key]):
            problems.append(f"{INPUTS}: \"{key}\" must be {type_name(TOP_KEYS[key])}.")


def validate(inputs):
    problems = []
    if not isinstance(inputs, dict):
        fail([f"{INPUTS} must hold one object with at least a title and the entrants."])
    check_keys(inputs, problems)
    if problems:
        fail(problems)

    entrants = inputs["entrants"]
    if not all(isinstance(e, str) and e.strip() for e in entrants):
        problems.append(f"{INPUTS}: every entrant must be a name in quotes.")
        fail(problems)
    if not 4 <= len(entrants) <= 64:
        problems.append(f"{INPUTS}: \"entrants\" holds {len(entrants)} names; a bracket takes 4 to 64.")
    dupes = sorted({e for e in entrants if entrants.count(e) > 1})
    if dupes:
        problems.append(f"{INPUTS}: each entrant is listed once; listed twice: {', '.join(dupes)}.")
    if problems:
        fail(problems)

    names = set(entrants)
    people = inputs.get("people", [])
    if not all(isinstance(p, str) and p.strip() for p in people):
        problems.append(f"{INPUTS}: every name in \"people\" must be text.")
    elif len(set(people)) != len(people):
        problems.append(f"{INPUTS}: each person in \"people\" is listed once.")

    theme = inputs.get("theme", AUTO)
    if theme not in theme_names():
        problems.append(f"{INPUTS}: the theme \"{theme}\" does not exist. Pick one of: {', '.join(theme_names())}.")

    for entrant, color in inputs.get("colors", {}).items():
        if entrant not in names:
            problems.append(f"{INPUTS}: \"colors\" names \"{entrant}\", who is not in \"entrants\".")
        elif not isinstance(color, str) or not HEX.match(color):
            problems.append(f"{INPUTS}: the color for \"{entrant}\" must be a hex color such as \"#1f6feb\".")

    for key, value in inputs.get("copy", {}).items():
        if key not in COPY_KEYS:
            problems.append(f"{INPUTS} has a key this app does not use: \"{key}\" in \"copy\". It uses: {', '.join(COPY_KEYS)}.")
        elif not isinstance(value, str):
            problems.append(f"{INPUTS}: \"{key}\" in \"copy\" must be text.")

    matches, byes = bracket(entrants)
    ids = {mid for mid, _ in matches}
    winners = {}
    given = {}
    for i, result in enumerate(inputs.get("results", [])):
        if not isinstance(result, dict) or not isinstance(result.get("match"), str) or not isinstance(result.get("winner"), str):
            problems.append(f"{INPUTS}: result {i + 1} must be {{\"match\": \"R1-1\", \"winner\": \"<entrant>\", \"score\": \"64-58\"}}.")
            continue
        if "score" in result and not isinstance(result["score"], str):
            problems.append(f"{INPUTS}: the score for {result['match']} must be text such as \"64-58\".")
        if result["match"] not in ids:
            problems.append(f"{INPUTS}: there is no match \"{result['match']}\" in a {len(entrants)}-entrant bracket; matches run {matches[0][0]} to {matches[-1][0]}.")
            continue
        if result["match"] in given:
            problems.append(f"{INPUTS}: match {result['match']} has two results.")
        given[result["match"]] = result["winner"]
    for mid, sources in matches:
        players = [winners.get(s) if s in ids else s for s in sources]
        winner = given.get(mid)
        if winner is None:
            continue
        if None in players:
            problems.append(f"{INPUTS}: match {mid} has a result, but the match that feeds it has none yet.")
        elif winner not in players:
            problems.append(f"{INPUTS}: the result for {mid} names \"{winner}\", who is not in that match ({players[0]} against {players[1]}).")
        else:
            winners[mid] = winner

    for person, mine in inputs.get("picks", {}).items():
        if person not in people:
            problems.append(f"{INPUTS}: \"picks\" has picks for \"{person}\", who is not in \"people\".")
            continue
        if not isinstance(mine, dict):
            problems.append(f"{INPUTS}: the picks for \"{person}\" must be an object such as {{\"R1-1\": \"<entrant>\"}}.")
            continue
        for mid, name in mine.items():
            if mid not in ids:
                problems.append(f"{INPUTS}: {person} has a pick for \"{mid}\", which is not a match in this bracket.")
            elif name not in names:
                problems.append(f"{INPUTS}: {person}'s pick for {mid}, \"{name}\", is not in \"entrants\".")

    if problems:
        fail(problems)
    return len(matches), byes


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
    match_count, bye_count = validate(inputs)
    if not (DIST / "index.html").is_file():
        fail([f"The app folder has no built page at {DIST}; rebuild it with npm ci && npm run build in {ROOT}."])

    config = {key: value for key, value in inputs.items() if not key.startswith("_")}
    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DIST, out)
    write_atomic(out / "config.js", f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n")
    write_atomic(out / "theme.css", theme_css(inputs.get("theme", AUTO)))
    count = sum(1 for p in out.rglob("*") if p.is_file())
    entrants = len(inputs["entrants"])
    print(f"{entrants} entrants: {match_count} matches, {bye_count} {'bye' if bye_count == 1 else 'byes'}.")
    print(f"Wrote out/{APP}/ ({count} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
