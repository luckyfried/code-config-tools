"""Writes the Spend Map page from a bank's CSV export described in ./spend-map.inputs.json.

Run from the project folder:
    python3 <agent-apps root>/spend-map/scripts/run.py

Reads  ./spend-map.inputs.json and the export its csvFile names
Writes ./out/spend-map/ (the page, config.js, theme.css, and data.js, which holds monthly totals by category and
       merchant and never a transaction row)
"""

import csv
import datetime as dt
import json
import re
import shutil
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

APP = "spend-map"
APP_DIR = Path(__file__).resolve().parents[1]
SITE = APP_DIR / "site"
INPUTS = f"{APP}.inputs.json"
MERCHANTS_PER_CATEGORY = 8
INCOME_SOURCES = 3
SIGNS = ("negative-is-spend", "positive-is-spend", "debit-credit-columns")
SPECIAL = ("income", "ignore")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
CATEGORY_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")

KEYS = {
    "csvFile": str,
    "columns": dict,
    "dateFormat": str,
    "amountSign": str,
    "currency": str,
    "rules": list,
    "categories": list,
    "months": int,
    "showMerchants": bool,
    "theme": str,
}
REQUIRED = ("csvFile", "columns", "dateFormat", "amountSign", "rules", "categories")
DEFAULTS = {"currency": "USD", "months": 6, "showMerchants": True, "theme": "auto"}
TYPE_WORDS = {str: "text", dict: "an object", list: "a list", int: "a whole number", bool: "true or false"}

NOISE_PREFIX = re.compile(r"^(?:SQ \*|TST\* ?|SP \*|PAYPAL \*|POS (?:PURCHASE )?|DEBIT CARD PURCHASE |CHECKCARD \d+ |"
                          r"PURCHASE AUTHORIZED ON \d\d/\d\d |RECURRING PAYMENT )", re.I)
NOISE_TAIL = re.compile(r"(?:\s#\s?\d+|\s\d{3,}|\s\*|\s[A-Z]{2}\s*$|\sPPD ID:|\.COM\b|\s\d{3}-\d{3}-\d{4}).*$", re.I)


def fail(problems, code=2):
    for line in problems:
        print(line, file=sys.stderr)
    sys.exit(code)


def load_inputs(path):
    if not path.exists():
        fail([f"Make {INPUTS} in this folder first; inputs.example.json shows every key."])
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        fail([f"{INPUTS} is not valid JSON (line {err.lineno}, column {err.colno}): {err.msg}."])
    if not isinstance(raw, dict):
        fail([f"{INPUTS} must hold one object with the keys inputs.example.json shows."])
    return raw


def theme_names():
    return ["auto"] + sorted(p.stem for p in (SITE / "themes").glob("*.css"))


def validate(raw, base):
    problems = []
    inputs = {k: v for k, v in raw.items() if k != "_notes"}
    for key in inputs:
        if key not in KEYS:
            problems.append(f'{INPUTS} has the key "{key}", which this app does not read. '
                            f"The keys are: {', '.join(KEYS)}.")
    for key in REQUIRED:
        if key not in inputs:
            problems.append(f'{INPUTS} is missing the key "{key}".')
    for key, kind in KEYS.items():
        if key in inputs:
            value = inputs[key]
            wrong = not isinstance(value, kind) or (kind is int and isinstance(value, bool))
            if wrong:
                problems.append(f'"{key}" in {INPUTS} must be {TYPE_WORDS[kind]}.')
    if problems:
        fail(problems)

    cfg = {**DEFAULTS, **inputs}
    cols = cfg["columns"]
    sign = cfg["amountSign"]
    if sign not in SIGNS:
        problems.append(f'"amountSign" is "{sign}"; it can be {", ".join(SIGNS)}.')
    needed = ["date", "description"] + (["debit", "credit"] if sign == "debit-credit-columns" else ["amount"])
    for name in needed:
        if not isinstance(cols.get(name), str) or not cols[name].strip():
            problems.append(f'"columns" in {INPUTS} is missing "{name}", the export\'s column name for it.')
    for name in cols:
        if name not in ("date", "description", "amount", "debit", "credit", "category"):
            problems.append(f'"columns" has "{name}"; it takes date, description, amount, debit, credit, and category.')

    if "%" not in cfg["dateFormat"]:
        problems.append(f'"dateFormat" is "{cfg["dateFormat"]}"; write a strptime pattern such as %m/%d/%Y.')
    if not re.fullmatch(r"[A-Z]{3}", cfg["currency"]):
        problems.append(f'"currency" is "{cfg["currency"]}"; write a three-letter code such as USD or EUR.')
    if not 1 <= cfg["months"] <= 24:
        problems.append(f'"months" is {cfg["months"]}; the page covers 1 to 24 months.')
    if cfg["theme"] not in theme_names():
        problems.append(f'"theme" is "{cfg["theme"]}"; the themes are {", ".join(theme_names())}.')

    cats = cfg["categories"]
    ids = []
    if not 4 <= len(cats) <= 8:
        problems.append(f'"categories" has {len(cats)} entries; it takes four to eight.')
    for n, cat in enumerate(cats, start=1):
        if not isinstance(cat, dict):
            problems.append(f'Category {n} in "categories" must be an object with id, label, and color.')
            continue
        cid, label, color = cat.get("id"), cat.get("label"), cat.get("color")
        if not isinstance(cid, str) or not CATEGORY_ID.match(cid) or cid in SPECIAL + ("other",):
            problems.append(f'Category {n} needs an "id" in lowercase letters, digits, and hyphens '
                            f'(not income, ignore, or other); it is {json.dumps(cid)}.')
        else:
            ids.append(cid)
        if not isinstance(label, str) or not label.strip():
            problems.append(f'Category {n} needs a "label", the word shown on the map.')
        if not isinstance(color, str) or not HEX.match(color):
            problems.append(f'Category {n} needs a "color" written like "#3466F0"; it is {json.dumps(color)}.')
    if len(set(ids)) != len(ids):
        problems.append('Two categories in "categories" share an id.')

    for n, rule in enumerate(cfg["rules"], start=1):
        if not isinstance(rule, dict) or not isinstance(rule.get("match"), str) or not rule["match"].strip():
            problems.append(f'Rule {n} in "rules" needs "match", the words to find in the description.')
            continue
        if rule.get("category") not in ids and rule.get("category") not in SPECIAL:
            problems.append(f'The rule "{rule["match"]}" has the category {json.dumps(rule.get("category"))}; '
                            f"use a category id ({', '.join(ids)}), income, or ignore.")
        if "merchant" in rule and not isinstance(rule["merchant"], str):
            problems.append(f'The rule "{rule["match"]}" has a "merchant" that is not text.')
        for key in rule:
            if key not in ("match", "category", "merchant"):
                problems.append(f'The rule "{rule["match"]}" has the key "{key}"; a rule takes match, category, '
                                "and merchant.")

    # A path is read beside the inputs file first, then inside the app folder, where the sample export lives.
    csv_path = next((p for p in ((base / cfg["csvFile"]).resolve(), (APP_DIR / cfg["csvFile"]).resolve())
                     if p.is_file()), None)
    if csv_path is None:
        problems.append(f'"csvFile" names {cfg["csvFile"]}, and there is no such file beside {INPUTS}.')
    if problems:
        fail(problems)
    return cfg, csv_path


def parse_amount(text):
    """A bank amount as a Decimal: handles $, spaces, (parentheses), a trailing minus, DR/CR, and 1.234,56."""
    s = (text or "").strip()
    if not s:
        return None
    negative = False
    if s.upper().endswith(("DR", "CR")):
        negative = s.upper().endswith("DR")
        s = s[:-2].strip()
    if s.startswith("(") and s.endswith(")"):
        negative, s = True, s[1:-1]
    if s.endswith("-"):
        negative, s = True, s[:-1]
    s = re.sub(r"[^\d,.\-]", "", s)
    if s.startswith("-"):
        negative, s = not negative, s[1:]
    if re.search(r",\d{1,2}$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return -value if negative else value


def clean_merchant(description):
    name = NOISE_PREFIX.sub("", description.strip())
    name = re.split(r"[*,]", name)[0] if re.match(r"^[A-Z .&'-]+[*,]", name) else name
    name = NOISE_TAIL.sub("", name).strip(" -*.,")
    words = name.split()[:3] or description.split()[:2]
    return " ".join(w if any(c.islower() for c in w) else w.capitalize() for w in words)[:28]


def read_rows(cfg, csv_path):
    text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    cols = cfg["columns"]
    headers = reader.fieldnames or []
    missing = [cols[k] for k in ("date", "description", "amount", "debit", "credit", "category")
               if k in cols and cols[k] not in headers]
    if missing:
        fail([f'The export has no column named "{name}". Its columns are: {", ".join(headers)}.' for name in missing])

    rows, skipped = [], 0
    for line in reader:
        try:
            day = dt.datetime.strptime((line.get(cols["date"]) or "").strip(), cfg["dateFormat"]).date()
        except ValueError:
            skipped += 1
            continue
        if cfg["amountSign"] == "debit-credit-columns":
            debit = parse_amount(line.get(cols["debit"])) or Decimal(0)
            credit = parse_amount(line.get(cols["credit"])) or Decimal(0)
            flow = abs(credit) - abs(debit)
        else:
            amount = parse_amount(line.get(cols["amount"]))
            if amount is None:
                skipped += 1
                continue
            flow = amount if cfg["amountSign"] == "negative-is-spend" else -amount
        description = (line.get(cols["description"]) or "").strip()
        given = (line.get(cols["category"]) or "").strip() if "category" in cols else ""
        rows.append((day, description, flow, given))
    if not rows:
        fail([f'No row of {cfg["csvFile"]} has a date in the form {cfg["dateFormat"]} and an amount. '
              "Check dateFormat and columns."])
    return rows, skipped


def classify(cfg, rows):
    """Each row becomes (month, kind, category, name, cents): kind is spend or income; ignored rows drop out."""
    rules = [(r["match"].lower(), r["category"], r.get("merchant")) for r in cfg["rules"]]
    by_label = {c["label"].lower(): c["id"] for c in cfg["categories"]}
    by_id = {c["id"]: c["id"] for c in cfg["categories"]}
    out, unmatched = [], defaultdict(int)
    for day, description, flow, given in rows:
        low = description.lower()
        hit = next(((cat, name) for match, cat, name in rules if match in low), None)
        name = (hit[1] if hit and hit[1] else None) or clean_merchant(description)
        cents = int((flow * 100).to_integral_value())
        month = f"{day.year:04d}-{day.month:02d}"
        if hit and hit[0] == "ignore":
            continue
        if flow > 0:
            if hit and hit[0] not in SPECIAL:
                out.append((month, "spend", hit[0], name, -cents))  # a return lands back on its category
            else:
                out.append((month, "income", None, name, cents))
            continue
        category = hit[0] if hit and hit[0] not in SPECIAL else None
        if category is None and given:
            category = by_id.get(given.lower()) or by_label.get(given.lower())
        if category is None:
            category = "other"
            unmatched[name] += -cents
        out.append((month, "spend", category, name, -cents))
    return out, unmatched


def month_keys(newest, count):
    year, month = map(int, newest.split("-"))
    keys = []
    for _ in range(count):
        keys.append(f"{year:04d}-{month:02d}")
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return list(reversed(keys))


def aggregate(cfg, items):
    keys = month_keys(max(m for m, *_ in items), cfg["months"])
    window = set(keys)
    show = cfg["showMerchants"]
    spend = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    income = defaultdict(lambda: defaultdict(int))
    for month, kind, category, name, cents in items:
        if month not in window:
            continue
        if kind == "income":
            income[month][name if show else "Income"] += cents
        else:
            spend[month][category][name] += cents

    order = [c["id"] for c in cfg["categories"]] + ["other"]
    months = []
    for key in keys:
        cats = []
        for cid in order:
            merchants = {n: v for n, v in spend[key].get(cid, {}).items() if v != 0}
            total = sum(merchants.values())
            if total <= 0:
                continue
            ranked = sorted(merchants.items(), key=lambda kv: (-kv[1], kv[0]))
            if not show:
                shown, rest = [(f"{len(ranked)} merchant{'s' if len(ranked) != 1 else ''}", total)], []
            else:
                shown, rest = ranked[:MERCHANTS_PER_CATEGORY], ranked[MERCHANTS_PER_CATEGORY:]
            others = sum(v for _, v in rest)
            cats.append({
                "id": cid,
                "cents": total,
                "merchants": [{"name": n, "cents": v} for n, v in shown if v > 0],
                "others": {"count": len(rest), "cents": others} if others > 0 else None,
            })
        sources = sorted(income[key].items(), key=lambda kv: (-kv[1], kv[0]))
        sources = [(n, v) for n, v in sources if v > 0]
        top, rest = sources[:INCOME_SOURCES], sources[INCOME_SOURCES:]
        if rest:
            top.append(("Other income", sum(v for _, v in rest)))
        spent = sum(c["cents"] for c in cats)
        check = sum(sum(m["cents"] for m in c["merchants"]) + (c["others"]["cents"] if c["others"] else 0)
                    for c in cats)
        if check != spent:
            fail([f"The totals for {key} do not add up ({check} against {spent} cents); this is a defect in run.py."],
                 code=1)
        year, month = map(int, key.split("-"))
        months.append({
            "key": key,
            "label": dt.date(year, month, 1).strftime("%B %Y"),
            "short": dt.date(year, month, 1).strftime("%b"),
            "spent": spent,
            "income": [{"name": n, "cents": v} for n, v in top],
            "categories": cats,
        })
    return months


def theme_css(name):
    """theme.css: the chosen look on :root, the other look under the in-page switch (and the system, for auto)."""
    ledger = (SITE / "themes" / "ledger.css").read_text(encoding="utf-8")
    vault = (SITE / "themes" / "vault.css").read_text(encoding="utf-8")
    for text, file in ((ledger, "ledger.css"), (vault, "vault.css")):
        if text.count(":root {") != 1:
            fail([f"site/themes/{file} must hold one :root {{ … }} block of tokens."], code=1)
    if name == "vault":
        return (vault.replace(":root {", ':root, [data-theme="dark"] {') + "\n" +
                ledger.replace(":root {", '[data-theme="light"] {'))
    head = ledger.replace(":root {", ':root, [data-theme="light"] {')
    if name == "ledger":
        return head + "\n" + vault.replace(":root {", '[data-theme="dark"] {')
    return (head + "\n@media (prefers-color-scheme: dark) {\n" +
            vault.replace(":root {", ':root:not([data-theme="light"]) {') + "}\n\n" +
            vault.replace(":root {", '[data-theme="dark"] {'))


def money(cents, currency):
    sign = "-" if cents < 0 else "+"
    return f"{sign}{abs(cents) / 100:,.2f} {currency}"


def main():
    project = Path.cwd()
    inputs_path = project / INPUTS
    raw = load_inputs(inputs_path)
    cfg, csv_path = validate(raw, inputs_path.parent)
    rows, skipped = read_rows(cfg, csv_path)
    items, unmatched = classify(cfg, rows)
    if not any(kind == "spend" for _, kind, *_ in items):
        fail(["Every row was income or ignored, so there is no spending to map. Check amountSign and the rules."])
    months = aggregate(cfg, items)

    print(f"Read {len(rows)} rows from {cfg['csvFile']}" + (f" ({skipped} without a date or amount skipped)."
                                                            if skipped else "."))
    for n, (day, description, flow, _) in enumerate(rows[:3], start=1):
        print(f"  row {n}: {day.isoformat()}  {money(int(flow * 100), cfg['currency'])}  {description[:48]}")
    if unmatched:
        top = sorted(unmatched.items(), key=lambda kv: -kv[1])[:5]
        print(f"{len(unmatched)} merchants matched no rule and show as Other, the largest: "
              + "; ".join(f"{n} ({v / 100:,.2f})" for n, v in top) + ".")

    data = {
        "currency": cfg["currency"],
        "categories": [{"id": c["id"], "label": c["label"].strip(), "color": c["color"]} for c in cfg["categories"]],
        "months": months,
    }

    out = project / "out" / APP
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    (out / "theme.css").write_text(theme_css(cfg["theme"]), encoding="utf-8")
    config = {k: v for k, v in raw.items() if k != "_notes"}
    (out / "config.js").write_text(
        f"window.__APP_CONFIG__ = {json.dumps(config, ensure_ascii=False, sort_keys=True)};\n", encoding="utf-8")
    (out / "data.js").write_text(
        f"window.__SPEND_DATA__ = {json.dumps(data, ensure_ascii=False, sort_keys=True)};\n", encoding="utf-8")

    for m in months:
        income = sum(s["cents"] for s in m["income"])
        print(f"  {m['label']}: spent {m['spent'] / 100:,.2f}, income {income / 100:,.2f}, "
              f"{len(m['categories'])} categories")
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"Wrote out/{APP}/ ({files} files). Serve it: python3 -m http.server 8000 --directory out/{APP}")


if __name__ == "__main__":
    main()
