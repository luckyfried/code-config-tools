"""Net worth ledger: turns net-worth-ledger.inputs.json into a page you can serve.

Run it from the project folder:

    python3 <agent-apps root>/net-worth-ledger/scripts/run.py

It reads net-worth-ledger.inputs.json from the current folder, checks every key, and writes
out/net-worth-ledger/: the page, theme.css from the chosen theme, config.js with the inputs, and
data.js with every snapshot and its totals. Standard library only; two runs on the same inputs
write the same bytes.
"""

import json
import re
import shutil
import sys
from pathlib import Path

APP = "net-worth-ledger"
INPUTS = f"{APP}.inputs.json"
HERE = Path(__file__).resolve().parents[1]
SITE = HERE / "site"
THEMES = SITE / "themes"

KEYS = {"title", "currency", "accounts", "snapshots", "milestones", "theme"}
REQUIRED = ("currency", "accounts", "snapshots", "theme")
ACCOUNT_KEYS = {"id", "label", "kind", "color"}
KINDS = ("asset", "liability")
CURRENCY = re.compile(r"[A-Z]{3}")
ACCOUNT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
MONTH = re.compile(r"(\d{4})-(0[1-9]|1[0-2])")
HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) != float("inf")


def problems_in(inputs):
    """Every problem with the inputs, one plain line each; empty when there are none."""
    problems = []
    say = problems.append
    for key in REQUIRED:
        if key not in inputs:
            say(f'{INPUTS} is missing the key "{key}".')
    for key in inputs:
        if key not in KEYS and key != "_notes":
            say(f'{INPUTS} has the key "{key}", which this app does not use.')

    if "title" in inputs and not isinstance(inputs["title"], str):
        say(f'"title" in {INPUTS} must be text.')
    if "currency" in inputs and not (isinstance(inputs["currency"], str) and CURRENCY.fullmatch(inputs["currency"])):
        say(f'"currency" in {INPUTS} must be a three-letter code such as "USD".')

    ids = []
    accounts = inputs.get("accounts")
    if "accounts" in inputs:
        if not isinstance(accounts, list) or not accounts:
            say(f'"accounts" in {INPUTS} must be a list with at least one account.')
            accounts = []
        for n, account in enumerate(accounts, 1):
            where = f"account {n}"
            if not isinstance(account, dict):
                say(f"{where} in {INPUTS} must be an object with an id, a label, and a kind.")
                continue
            for key in ("id", "label", "kind"):
                if key not in account:
                    say(f'{where} in {INPUTS} is missing the key "{key}".')
            for key in account:
                if key not in ACCOUNT_KEYS:
                    say(f'{where} in {INPUTS} has the key "{key}", which this app does not use.')
            account_id = account.get("id")
            if "id" in account:
                if not (isinstance(account_id, str) and ACCOUNT_ID.fullmatch(account_id)):
                    say(f'{where} in {INPUTS} needs an "id" of letters, numbers, and dashes.')
                elif account_id in ids:
                    say(f'Two accounts in {INPUTS} have the id "{account_id}".')
                else:
                    ids.append(account_id)
            if "label" in account and not (isinstance(account["label"], str) and account["label"].strip()):
                say(f'{where} in {INPUTS} needs a "label" with some words in it.')
            if "kind" in account and account["kind"] not in KINDS:
                say(f'{where} in {INPUTS} has the kind {json.dumps(account["kind"])}; use "asset" or "liability".')
            color = account.get("color", "auto")
            if not (color == "auto" or (isinstance(color, str) and HEX.fullmatch(color))):
                say(f'{where} in {INPUTS} has the color {json.dumps(color)}; use "auto" or a hex color such as "#2e7bff".')

    snapshots = inputs.get("snapshots")
    if "snapshots" in inputs:
        if not isinstance(snapshots, list) or not snapshots:
            say(f'"snapshots" in {INPUTS} must be a list with at least one month.')
            snapshots = []
        months = []
        for n, snapshot in enumerate(snapshots, 1):
            if not isinstance(snapshot, dict):
                say(f"snapshot {n} in {INPUTS} must be an object with a month and balances.")
                continue
            month = snapshot.get("month")
            where = f"the {month} snapshot" if isinstance(month, str) else f"snapshot {n}"
            for key in snapshot:
                if key not in ("month", "balances"):
                    say(f'{where} in {INPUTS} has the key "{key}", which this app does not use.')
            if not (isinstance(month, str) and MONTH.fullmatch(month)):
                say(f'snapshot {n} in {INPUTS} needs a "month" written as YYYY-MM, such as "2026-10".')
            elif month in months:
                say(f"{INPUTS} has two snapshots for {month}.")
            else:
                months.append(month)
            balances = snapshot.get("balances")
            if not isinstance(balances, dict):
                say(f'{where} in {INPUTS} needs "balances", an object of account ids and amounts.')
                continue
            for account_id, value in balances.items():
                if ids and account_id not in ids:
                    say(f'{where} in {INPUTS} has a balance for "{account_id}", which is not one of the accounts.')
                elif not is_number(value):
                    say(f'{where} in {INPUTS} has a balance for "{account_id}" that is not a number.')
                elif value < 0:
                    say(f'{where} in {INPUTS} has a negative balance for "{account_id}"; write an amount owed as a positive number.')

    milestones = inputs.get("milestones", [])
    if not isinstance(milestones, list):
        say(f'"milestones" in {INPUTS} must be a list.')
        milestones = []
    for n, milestone in enumerate(milestones, 1):
        if not (isinstance(milestone, dict) and isinstance(milestone.get("label"), str) and is_number(milestone.get("value"))):
            say(f'milestone {n} in {INPUTS} needs a "label" and a number "value".')
        elif set(milestone) - {"label", "value"}:
            extra = sorted(set(milestone) - {"label", "value"})[0]
            say(f'milestone {n} in {INPUTS} has the key "{extra}", which this app does not use.')

    if "theme" in inputs:
        names = sorted(path.stem for path in THEMES.glob("*.css"))
        if not (isinstance(inputs["theme"], str) and (THEMES / f"{inputs['theme']}.css").is_file()):
            say(f'The theme {json.dumps(inputs["theme"])} is not one of this app\'s themes: {", ".join(names)}.')
    return problems


def ledger_of(inputs):
    """Every snapshot oldest first, each account's balance filled in, and the month's totals."""
    accounts = [
        {"id": a["id"], "label": a["label"].strip(), "kind": a["kind"], "color": a.get("color", "auto")}
        for a in inputs["accounts"]
    ]
    kinds = {a["id"]: a["kind"] for a in accounts}
    snapshots = []
    for snapshot in sorted(inputs["snapshots"], key=lambda s: s["month"]):
        balances = {a["id"]: snapshot["balances"].get(a["id"], 0) for a in accounts}
        assets = sum(v for k, v in balances.items() if kinds[k] == "asset")
        debts = sum(v for k, v in balances.items() if kinds[k] == "liability")
        snapshots.append({"month": snapshot["month"], "balances": balances, "assets": assets, "debts": debts, "net": assets - debts})
    return {
        "title": inputs.get("title", ""),
        "currency": inputs["currency"],
        "accounts": accounts,
        "snapshots": snapshots,
        "milestones": [{"label": m["label"], "value": m["value"]} for m in inputs.get("milestones", [])],
    }


def main():
    project = Path.cwd()
    source = project / INPUTS
    if not source.is_file():
        print(f"Make {INPUTS} in this folder first; inputs.example.json shows every key.")
        return 2
    try:
        inputs = json.loads(source.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        print(f"{INPUTS} is not valid JSON: {error}.")
        return 2
    if not isinstance(inputs, dict):
        print(f"{INPUTS} must hold one JSON object; inputs.example.json shows every key.")
        return 2
    problems = problems_in(inputs)
    if problems:
        for line in problems:
            print(line)
        return 2

    ledger = ledger_of(inputs)
    latest = ledger["snapshots"][-1]
    if latest["net"] != latest["assets"] - latest["debts"]:
        print(f"The {latest['month']} net worth does not equal its assets minus its debts.")
        return 1
    if len(ledger["snapshots"]) != len(inputs["snapshots"]):
        print("Some snapshots did not make it into the page.")
        return 1

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out, ignore=shutil.ignore_patterns("themes", "config.js", "data.js", "theme.css"))
    shutil.copyfile(HERE / "badge.js", out / "badge.js")
    shutil.copyfile(HERE / "assets" / "icon.svg", out / "icon.svg")
    shutil.copyfile(THEMES / f"{inputs['theme']}.css", out / "theme.css")
    config = {key: value for key, value in inputs.items() if key != "_notes"}
    (out / "config.js").write_text(f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False)};\n", encoding="utf-8")
    (out / "data.js").write_text(f"window.__LEDGER__ = {json.dumps(ledger, ensure_ascii=False)};\n", encoding="utf-8")

    files = sum(1 for path in out.rglob("*") if path.is_file())
    print(f"Wrote out/{APP}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
