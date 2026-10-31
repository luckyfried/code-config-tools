#!/usr/bin/env python3
"""Movement 0, before gather when the request names no subject or a vague one ("make me a hype reel", "hype something
up", "what could you make for me"): three to five concrete ideas, one plain line each, each naming a subject and an
angle, drawn from what the kit can already reach. A request that names its subject skips this step.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/ideas.py [--pulled pulled ...] [--root .] [--most 4] [--subject NAME]

It reads the material the agent pulled from the person's connected Instagram or Facebook account or signed-in
browser (items.json, the shape gather.py reads) and the workspace, and drafts, in this order:
  friend    the account they talk with most in comments, else the one they tag most, with what the posts that tag
            them share
  interest  what their own posts and saves are most about
  follows   the account they save most from, else the first they follow
  project   a project of theirs in the workspace (a folder with a README heading or a package name)
  surprise  one they did not think of: an account they follow and never save from, else the place they post most
and fills to three with their own year. Each idea is {subject, kind, angle, tone, line, from, private}; `tone` is
one of drive.TONES and `line` is what the person reads. An idea names only what the person can see themselves;
`private` marks one drawn from a private account, whose material appears on screen or in a caption only once the
person picks that idea. No message is read. It writes build/ideas.json and prints the ideas numbered, with
"something else" last; with --subject it writes {"skipped": true} and prints that the subject is named.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

# each kind's angle and the tone it is made in
ANGLES = {
    "friend": ("played as a movie trailer", "cinematic"),
    "interest": ("loud and fast, all capitals", "chaotic"),
    "account": ("as a deadpan product launch, played completely straight", "yc-parody"),
    "quiet": ("loud and fast, flash cuts on the beat", "chaotic"),
    "project": ("as an app store feature, one claim a card", "app-store"),
    "place": ("calm and slow, like a postcard", "deadpan"),
    "you": ("played as a movie trailer", "cinematic"),
}
MOST = (3, 5)
SKIP = {"build", "out", "node_modules", ".git", ".claude", "pulled", "__pycache__", ".venv", "venv"}


def handles_in(text):
    return re.findall(r"@([a-z0-9._]+[a-z0-9_])", (text or "").lower())


def idea(subject, kind, detail, source, private=False):
    """One idea: its subject, kind, angle and tone, and the line offered. A subject that is not a name read from
    anywhere ("a friend of yours") is offered as it is."""
    angle, tone = ANGLES[kind]
    head = subject if subject.startswith(("a ", "the ", "your ")) else {"friend": f"your friend {subject}", "interest": f"the {subject} you keep posting",
            "account": f"{subject}, the account you save most from", "quiet": f"{subject}, an account you follow",
            "project": f"your project {subject}", "place": f"{subject}, the place you post most",
            "you": f"you, {subject}: your best posts of the year"}[kind]
    line = head + (f" and {detail}" if detail else "") + f", {angle}"
    kinds = {"interest": "thing", "quiet": "account", "you": "account"}
    return {"subject": subject, "kind": kinds.get(kind, kind),
            "angle": angle, "tone": tone, "line": line, "from": source, "private": bool(private)}


def project_of(root):
    """A project of theirs in the workspace: the first README heading or package name a top-level folder holds."""
    for d in sorted(p for p in Path(root).iterdir() if p.is_dir() and p.name not in SKIP and not p.name.startswith(".")):
        readme = next((f for f in (d / "README.md", d / "readme.md") if f.is_file()), None)
        if readme:
            m = re.search(r"^#\s+(.+)$", readme.read_text(errors="replace"), re.M)
            if m:
                return m.group(1).strip()
        pkg = d / "package.json"
        if pkg.is_file():
            try:
                name = json.loads(pkg.read_text()).get("name")
            except ValueError:
                name = None
            if name:
                return name
    return None


def draft(pulled, root, most=4):
    """The ideas from the pulled folders and the workspace, `most` of them at most and three at least."""
    import gather
    import research
    keys = ("posts", "saved", "likes", "comments", "following")
    d = {k: [] for k in keys}
    handle, private = None, set()
    for folder in pulled:
        p = gather.read_pulled(folder)
        if not p:
            continue
        for k in keys:
            d[k] += p[k]
        handle = handle or p["handle"]
        private |= {r.get("account") for r in p["following"] if isinstance(r, dict) and r.get("private")}
    me = (handle or "").lower()
    out, named = [], set()

    def add(x):
        if x and x["subject"].lower() not in named and len(out) < most:
            named.add(x["subject"].lower())
            out.append(x)
    talk = collections.Counter(r.get("account") for r in d["comments"] if r.get("account") and r.get("account") != me)
    tags = collections.Counter(h for r in d["posts"] for h in handles_in(r.get("caption")) if h != me)
    friend = (talk.most_common(1) or tags.most_common(1) or [(None, 0)])[0][0]
    if friend:
        shared = research.theme_counts([r.get("caption") or "" for r in d["posts"] if friend in handles_in(r.get("caption"))])
        top = shared.most_common(1)
        add(idea(f"@{friend}", "friend", f"the {top[0][0]} you share" if top else "", "comments" if talk else "tags",
                 f"{friend}" in private))
    themes = research.theme_counts([r.get("caption") or "" for r in d["posts"] + d["saved"]])
    if themes:
        add(idea(themes.most_common(1)[0][0], "interest", "", "posts and saves"))
    saves = collections.Counter(r.get("account") for r in d["saved"] if r.get("account"))
    follows = [r.get("account") for r in d["following"] if isinstance(r, dict) and r.get("account")]
    acct = (saves.most_common(1) or [(follows[0] if follows else None, 0)])[0][0]
    if acct:
        add(idea(f"@{acct}", "account", "", "saves" if saves else "follows", acct in private))
    proj = project_of(root)
    if proj:
        add(idea(proj, "project", "", "the workspace"))
    liked = set(saves) | {r.get("account") for r in d["likes"]}
    quiet = [a for a in follows if a not in liked and f"@{a}".lower() not in named]
    if quiet:
        add(idea(f"@{quiet[0]}", "quiet", "", "follows", quiet[0] in private))
    else:
        places = collections.Counter(pl for r in d["posts"] for pl in research.PLACES
                                     if pl != "home" and re.search(rf"\b{re.escape(pl)}\b", (r.get("caption") or "").lower()))
        if places:
            add(idea(places.most_common(1)[0][0].title(), "place", "", "posts"))
    if len(out) < MOST[0]:
        add(idea(f"@{handle}" if handle else "your best posts of the year", "you", "", "posts"))
    if len(out) < MOST[0] and proj is None:
        add(idea("the thing you are making next", "project", "", "the request"))
    if len(out) < MOST[0]:
        add(idea("a friend of yours", "friend", "", "the request"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pulled", action="append", default=[], help="a folder holding items.json the agent pulled")
    ap.add_argument("--root", default=".")
    ap.add_argument("--most", type=int, default=4, help="how many ideas at most (3 to 5; 4 fits the question tool)")
    ap.add_argument("--subject", help="the subject the request names: the step is skipped")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    out = root / "build" / "ideas.json"
    if a.subject:
        _env.write_json(out, {"skipped": True, "why": f"the request names its subject, {a.subject}", "ideas": []})
        print(f"the request names its subject ({a.subject}), so there is no ideas step: gather next")
        return 0
    pulled = a.pulled or ([str(root / "pulled")] if (root / "pulled" / "items.json").exists() else [])
    ideas = draft([str(Path(x).resolve()) for x in pulled], root, min(MOST[1], max(MOST[0], a.most)))
    _env.write_json(out, {"skipped": False, "ideas": ideas})
    for i, x in enumerate(ideas, 1):
        print(f"{i}. {x['line'][:1].upper()}{x['line'][1:]}")
    print(f"{len(ideas) + 1}. Something else")
    return 0


if __name__ == "__main__":
    sys.exit(main())
