#!/usr/bin/env python3
"""The brand system and the 30-day plan. Writes build/brand.json, build/plan.json and out/plan.md.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/brand.py system          # build/taste.json "brand" -> build/brand.json, validated
    python3 S/scripts/brand.py plan [--start 2026-10-20] [--fresh]
                                               # build/plan.json (made once, then yours to edit) -> out/plan.md,
                                               # and the plan's first seven days into brand.json "first_week"
    python3 S/scripts/brand.py check [FILE]    # validate a brand.json against design/brand.schema.json

system: the agent edits taste.json's "brand" block (statement, palette names, pillars, voice lines, stop list,
aspire line) in the person's own words, then runs this. Palette roles: the color that leads most posts is
"lead", the lightest of the rest "ground", the darkest "ink", the most vivid of what is left "accent", any
other "support". Pillar shares must sum to 1 within 0.01. Exits 1 on any schema error, naming each one.

plan: 30 days from --start (default tomorrow). Each of their cadence days carries a feed post at its time;
every other day a story. Pillars are dealt by weighted round robin so the month matches their shares. Each
caption is a draft assembled from their own pieces (their labels, their pillar's words, their questions) and
marked "draft": the agent rewrites every one in their voice in build/plan.json, then runs plan again (without
--fresh) to render out/plan.md. Each entry in plan.md is one line "- **YYYY-MM-DD** Tue · post 08:00 ·
pillar: table" with the caption under it.
"""
import argparse
import colorsys
import datetime as dt
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

SCHEMA = _env.SKILL / "design" / "brand.schema.json"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def validate(obj, schema, path="brand"):
    """Errors of obj against the subset of JSON Schema the kit's schema uses (type, enum, required, properties,
    items, min/maxItems, min/maxLength, minimum, maximum, pattern)."""
    errs = []
    types = schema.get("type")
    if types:
        ok = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "null": type(None),
              "boolean": bool}
        allowed = types if isinstance(types, list) else [types]
        if not any(isinstance(obj, ok[t]) and not (t in ("integer", "number") and isinstance(obj, bool)) for t in allowed):
            return [f"{path}: expected {' or '.join(allowed)}, got {type(obj).__name__}"]
    if "enum" in schema and obj not in schema["enum"]:
        errs.append(f"{path}: {obj!r} is not one of {schema['enum']}")
    if isinstance(obj, dict):
        for k in schema.get("required", []):
            if k not in obj:
                errs.append(f"{path}: missing {k}")
        for k, sub in schema.get("properties", {}).items():
            if k in obj:
                errs += validate(obj[k], sub, f"{path}.{k}")
    if isinstance(obj, list):
        if len(obj) < schema.get("minItems", 0):
            errs.append(f"{path}: {len(obj)} items, at least {schema['minItems']} needed")
        if "maxItems" in schema and len(obj) > schema["maxItems"]:
            errs.append(f"{path}: {len(obj)} items, at most {schema['maxItems']} allowed")
        for i, x in enumerate(obj):
            if "items" in schema:
                errs += validate(x, schema["items"], f"{path}[{i}]")
    if isinstance(obj, str):
        if len(obj) < schema.get("minLength", 0):
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(obj) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], obj):
            errs.append(f"{path}: {obj!r} does not match {schema['pattern']}")
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if "minimum" in schema and obj < schema["minimum"]:
            errs.append(f"{path}: {obj} below {schema['minimum']}")
        if "maximum" in schema and obj > schema["maximum"]:
            errs.append(f"{path}: {obj} above {schema['maximum']}")
    return errs


def check(brand):
    """Schema errors plus the rules a schema cannot say."""
    errs = validate(brand, json.loads(SCHEMA.read_text()))
    pil = brand.get("pillars") or []
    total = sum(p.get("share", 0) for p in pil if isinstance(p, dict))
    if pil and abs(total - 1) > 0.01:
        errs.append(f"brand.pillars: shares sum to {total:.3f}, not 1 within 0.01")
    names = [c.get("name") for c in brand.get("palette") or [] if isinstance(c, dict)]
    if len(set(names)) != len(names):
        errs.append("brand.palette: two colors share a name")
    names = [p.get("name") for p in pil if isinstance(p, dict)]
    if len(set(names)) != len(names):
        errs.append("brand.pillars: two pillars share a name")
    return errs


def hex_rgb(h):
    return tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def roles(palette):
    """lead = most posts; of the rest, ground = lightest, ink = darkest, accent = most vivid, support = the others."""
    if not palette:
        return palette
    lum = lambda c: sum(w * v for w, v in zip((0.2126, 0.7152, 0.0722), hex_rgb(c["hex"])))
    sat = lambda c: colorsys.rgb_to_hls(*(v / 255 for v in hex_rgb(c["hex"])))[2]
    out = sorted((dict(c) for c in palette), key=lambda c: -(c.get("share") or 0))
    out[0]["role"] = "lead"
    rest = out[1:]
    if rest:
        max(rest, key=lum)["role"] = "ground"
    left = [c for c in rest if "role" not in c or c["role"] not in ("ground",)]
    if left:
        min(left, key=lum)["role"] = "ink"
    left = [c for c in rest if c.get("role") not in ("ground", "ink")]
    if left:
        max(left, key=sat)["role"] = "accent"
    for c in rest:
        c.setdefault("role", "support")
        if c["role"] not in ("ground", "ink", "accent"):
            c["role"] = "support"
    return out


def system(a):
    taste = _env.read_json("build/taste.json") or {}
    research = _env.read_json("build/research.json") or {}
    lib = _env.read_json("build/library.json") or {}
    b = dict(taste.get("brand") or {})
    if not b:
        sys.exit("build/taste.json has no brand block: run research.py first")
    old = _env.read_json("build/brand.json") or {}
    aspire = dict(b.get("aspire") or {})
    if not aspire.get("line"):
        mine = " and ".join(c["name"] for c in (b.get("palette") or [])[:2])
        theirs = " and ".join(c["name"] for c in (aspire.get("palette") or [])[:2])
        aspire["line"] = (f"your likes lean {theirs}" + (f" and {aspire['subjects'][0]}" if aspire.get("subjects") else "") +
                          f"; your feed is {mine}")
    brand = {
        "handle": b.get("handle") or lib.get("handle") or research.get("handle") or "you",
        "name": b.get("name") or lib.get("name"),
        "statement": b.get("statement"),
        "source": b.get("source") or lib.get("source") or "",
        "palette": roles([{k: c[k] for k in ("name", "hex", "share", "posts", "role") if k in c} for c in b.get("palette") or []]),
        "type": b.get("type"),
        "compositions": b.get("compositions") or [],
        "pillars": [{k: p[k] for k in ("name", "share", "words", "example") if k in p} for p in b.get("pillars") or []],
        "cadence": b.get("cadence"),
        "voice": b.get("voice"),
        "aspire": aspire,
        "stop": b.get("stop") or [],
        "first_week": old.get("first_week") or [],
    }
    if brand["type"] and "lead" in brand["type"] and "direction" not in brand["type"]:
        brand["type"]["direction"] = brand["type"].pop("lead")
    _env.write_json("build/brand.json", brand)
    errs = [e for e in check(brand) if not e.startswith("brand.first_week")]
    print(f"brand: {brand['statement']}")
    print("palette: " + ", ".join(f"{c['name']} {c['hex']} {c['role']}" for c in brand["palette"]))
    print("pillars: " + ", ".join(f"{p['name']} {p['share']:.0%}" for p in brand["pillars"]))
    for e in errs:
        print("ERROR", e)
    print("wrote build/brand.json" + ("" if brand["first_week"] else "; run `brand.py plan` to fill first_week"))
    return 1 if errs else 0


def deal(pillars, n):
    """n pillar names by smooth weighted round robin: the month follows the shares and never bunches."""
    cur = {p["name"]: 0.0 for p in pillars}
    out = []
    for _ in range(n):
        for p in pillars:
            cur[p["name"]] += p["share"]
        pick = max(cur, key=lambda k: cur[k])
        cur[pick] -= 1
        out.append(pick)
    return out


def pieces(research, brand):
    """Per pillar: their labels, their questions and their words, taken from their own captions."""
    out = {}
    for p in brand["pillars"]:
        rp = next((x for x in research.get("pillars") or [] if x["name"] == p["name"]), {})
        caps = list(dict.fromkeys((rp.get("examples") or []) + [rp.get("example") or p.get("example") or ""]))
        labels = [m.group(1) for c in caps for m in [re.match(r"^\s*([^:\n#]{2,28}):\s", c)] if m]
        questions = [m.group(0).strip() for c in caps for m in re.finditer(r"[^.!?\n]*\?", c)]
        out[p["name"]] = {"labels": rp.get("labels") or labels, "questions": list(dict.fromkeys(questions)),
                          "words": rp.get("items") or p.get("words") or rp.get("words") or [p["name"]], "tag": rp.get("hashtag")}
    return out


def draft(rng, piece, voice_names, lower):
    """A caption draft from their own pieces, following the devices they use."""
    ws = list(piece["words"])
    rng.shuffle(ws)
    head = (rng.choice(piece["labels"]) + ": ") if piece["labels"] and "opening label" in voice_names else ""
    body = ", ".join(ws[:3]) + "." if "list of three" in voice_names and len(ws) >= 3 else " ".join(ws[:2]) + "."
    cap = head + body
    if piece["questions"] and ("closing question" in voice_names or "question after a blank line" in voice_names):
        cap += ("\n\n" if "question after a blank line" in voice_names else " ") + rng.choice(piece["questions"])
    if piece["tag"] and "hashtag line" in voice_names:
        cap += "\n" + piece["tag"]
    return cap.lower() if lower else cap


def plan(a):
    brand = _env.read_json("build/brand.json")
    if not brand:
        sys.exit("build/brand.json is missing: run `brand.py system` first")
    research = _env.read_json("build/research.json") or {}
    path = Path("build/plan.json")
    if a.fresh or not path.exists():
        start = a.start or (dt.date.today() + dt.timedelta(days=1))
        slots = {s["day"]: s["time"] for s in brand["cadence"]["slots"]}
        names = deal(brand["pillars"], 30)
        rng = random.Random(7)
        pcs = pieces(research, brand)
        vnames = {d["name"] for d in brand["voice"]["devices"]}
        lower = brand["voice"].get("case") == "lowercase"
        days = []
        for i in range(30):
            d = start + dt.timedelta(days=i)
            wd = WEEKDAYS[d.weekday()]
            kind = "post" if wd in slots else "story"
            days.append({"date": d.isoformat(), "day": wd[:3], "kind": kind, "time": slots.get(wd, ""), "pillar": names[i],
                         "caption": draft(rng, pcs[names[i]], vnames, lower), "draft": True})
        _env.write_json(path, {"handle": brand["handle"], "start": start.isoformat(), "days": days})
    p = _env.read_json(path)
    valid = {x["name"] for x in brand["pillars"]}
    errs = [f"{d['date']}: pillar {d['pillar']!r} is not in brand.json" for d in p["days"] if d.get("pillar") not in valid]
    if len(p["days"]) != 30:
        errs.append(f"plan has {len(p['days'])} days, not 30")
    drafts = sum(1 for d in p["days"] if d.get("draft"))
    L = [f"# 30 days for @{brand['handle']}", "", f"{brand['statement']}", "",
         f"Feed posts on {', '.join(s['day'] + ' ' + s['time'] for s in brand['cadence']['slots'])} "
         f"({brand['cadence'].get('timezone', 'UTC')}); a story on the other days. Pillars: " +
         ", ".join(f"{x['name']} {x['share']:.0%}" for x in brand["pillars"]) + ".", ""]
    for d in p["days"]:
        when = f"{d['kind']} {d['time']}".strip()
        L.append(f"- **{d['date']}** {d['day']} · {when} · pillar: {d['pillar']}")
        L += ["  > " + line if line.strip() else "  >" for line in d["caption"].splitlines()]
        L.append("")
    Path("out").mkdir(exist_ok=True)
    Path("out/plan.md").write_text("\n".join(L))
    brand["first_week"] = [{k: d[k] for k in ("date", "day", "kind", "time", "pillar", "caption")} for d in p["days"][:7]]
    _env.write_json("build/brand.json", brand)
    errs += check(brand)
    count = {}
    for d in p["days"]:
        count[d["pillar"]] = count.get(d["pillar"], 0) + 1
    print(f"plan: {p['start']} + 30 days; " + ", ".join(f"{k} {v}" for k, v in count.items()) +
          f"; {sum(1 for d in p['days'] if d['kind'] == 'post')} posts; {drafts} captions still marked draft")
    for e in errs:
        print("ERROR", e)
    print("wrote out/plan.md and brand.json first_week" + (f"; rewrite the {drafts} draft captions in build/plan.json "
                                                           "in their voice, set draft false, run plan again" if drafts else ""))
    return 1 if errs else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("system", help="taste.json brand -> build/brand.json")
    pp = sub.add_parser("plan", help="build/plan.json -> out/plan.md")
    pp.add_argument("--start", type=dt.date.fromisoformat, help="first day (default tomorrow)")
    pp.add_argument("--fresh", action="store_true", help="draft build/plan.json again from brand.json")
    cp = sub.add_parser("check", help="validate a brand.json")
    cp.add_argument("file", nargs="?", default="build/brand.json")
    a = ap.parse_args()
    if a.cmd == "system":
        return system(a)
    if a.cmd == "plan":
        return plan(a)
    errs = check(json.loads(Path(a.file).read_text()))
    for e in errs:
        print("ERROR", e)
    print(f"{a.file}: {'valid' if not errs else str(len(errs)) + ' errors'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
