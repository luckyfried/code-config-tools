#!/usr/bin/env python3
"""Movement 1, research: the month's moments, read from their posts: what happened, with whom, where, on which day, in
their own words. Reads the run's library.json; writes the run's stats.json (stats.py), month.json, research.json, a
machine draft of taste.json and taste.draft.md (the month's posts under the five headings the agent turns into
taste.md).

USAGE (from the workspace root):
    python3 S/scripts/research.py

month.json is what the board builder composes:
  {"handle", "name", "month": {"year", "month"},
   "posts": [{"day", "type": "photo"|"reel", "caption", "photo", "place", "likes", "comments"}]}
      the month's posts and reels; photo is the post's first still, else a frame cut from its video into the run's
      stills/ (a reel with no still), else null; likes and comments are the post's figures as the data carries them, or
      null
research.json lists the same posts with the people each caption tags (@mentions) and its place. taste.json's `ask` is
what the person asked for, read from their own words: {"counts": true when they ask for their top posts or their
numbers, "seconds": the reel's length when they name one, else null, "series": true only when they ask for the cards
joined into one video}; the draft is all false and null, and the agent sets it from the request. taste.json's
`moments` draft is the month as its captions tell it (compose/month.py `story`): its first post and its last, and
between them the one whose caption says the most, that one the peak, each {"day", "photo": the post's photograph as
month.json names it, or null, "what": its caption, "line": its caption, "peak", "shot"}; the agent picks the three or
four best things that happened (four when the person asks for four cards), the peak the one they would tell first, and
sets each line to the words that moment says on screen (pipeline/1-research.md). Likes and comments never choose a
moment. Each moment's `shot` is
the clip a cinematographer would shoot from its photograph: {"subject", "move", "lens", "height", "light"}; the draft
measures the lens (from how busy the photograph is), the camera's height (from where its subject sits) and the light
(from its lightness and warmth) and leaves the subject and the move empty, and the agent writes all five from looking
at the photograph. taste.json's
`music` is the person's own brief for the film's music: {"styles": genre and instrument words, "avoid": what the
music leaves out}, never an artist, band or song. The look the person picks brings its own music (its style card's
recipe), so the draft's `styles` is empty and its `avoid` keeps out vocals and spoken word; the agent writes `styles`
only when the person says what the music should be. The series needs at least three posts in the month: with fewer it says so and exits 4.
"""
import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
from compose.month import Post, story  # noqa: E402
from compose import photos  # noqa: E402
from gather import IMG, VID  # noqa: E402
from PIL import ImageStat  # noqa: E402

S = Path(__file__).resolve().parent
HEADINGS = ["you are", "you like", "your style is", "your voice is", "avoid"]
TAG = re.compile(r"@([A-Za-z0-9._]{2,30}[A-Za-z0-9_])")


def when(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc)


def still_of(media, dest):
    """The post's photograph: its first still, else a representative frame cut from its video to `dest`; None with neither."""
    img = next((f for f in media if Path(f).suffix.lower() in IMG), None)
    vid = next((f for f in media if Path(f).suffix.lower() in VID and Path(f).is_file()), None)
    if img or not vid:
        return img
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-i", vid, "-vf", "thumbnail", "-frames:v", "1", "-q:v", "2", str(dest)],
                       capture_output=True, text=True)
    return str(dest.resolve()) if r.returncode == 0 and dest.exists() else None


def shot_of(photo):
    """A moment's shot drafted from its photograph: the lens from how busy it is, the camera's height from where its
    subject sits, the light from its lightness and warmth and the side its brighter third is on; the subject and the move
    are the agent's to write."""
    shot = {"subject": "", "move": "", "lens": "", "height": "", "light": ""}
    if not photo or not Path(photo).exists():
        return shot
    im = photos.sample(photo)
    m, (_, fy) = photos.measure(photo, None), photos.focus_of(im)
    r, _, b = ImageStat.Stat(im).mean
    shot["lens"] = ("24 mm, wide, the whole scene in" if m["busy"] > 0.17 else "85 mm, close, the background soft" if m["busy"] < 0.13
                    else "50 mm, the subject at arm's length, the background a little soft")
    shot["height"] = ("the camera low, looking up at the subject" if fy < 0.42 else "the camera high, looking down on the subject"
                      if fy > 0.58 else "the camera at eye height")
    shot["light"] = (("warm " if r > 1.08 * b else "cool " if b > 1.08 * r else "")
                     + ("bright daylight" if m["light"] > 0.55 else "low light" if m["light"] < 0.42 else "soft light")
                     + " " + light_from(im) + ", as in the photograph")
    return shot


def light_from(im):
    """Where the photograph's light falls from: the side of it whose outer third is brighter by more than a twentieth."""
    g = im.convert("L")
    w, h = g.size
    lum = lambda box: ImageStat.Stat(g.crop(box)).mean[0]
    across = lum((0, 0, w // 3, h)) - lum((w - w // 3, 0, w, h))
    down = lum((0, 0, w, h // 3)) - lum((0, h - h // 3, w, h))
    side = "left" if across > 12 else "right" if across < -12 else ""
    high = "upper" if down > 12 else "lower" if down < -12 else ""
    if side and high:
        return f"from the {high} {side}"
    if side:
        return f"from the {side}"
    return {"upper": "from above", "lower": "from below"}.get(high, "from in front of the subject")


def month_json(lib, run):
    mo = lib["month"]
    inm = lambda r: r.get("ts") and f"{when(r['ts']):%Y-%m}" == mo["key"]
    rows = [(t, r) for k, t in (("posts", "photo"), ("reels", "reel")) for r in lib[k] if inm(r)]
    posts = [{"day": when(r["ts"]).day, "type": t, "caption": (r.get("caption") or "").strip(),
              "photo": still_of(r.get("media") or [], run / "stills" / f"{when(r['ts']).day:02d}-{j + 1}.jpg"), "place": (r.get("place") or "").strip(),
              "likes": r.get("likes"), "comments": r.get("comments")}
             for j, (t, r) in enumerate(rows)]
    return {"handle": lib.get("handle"), "name": lib.get("name"),
            "month": {"year": mo["year"], "month": mo["month"]}, "posts": sorted(posts, key=lambda p: p["day"])}


def people_of(caption):
    return list(dict.fromkeys(a.lower() for a in TAG.findall(caption or "")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    run = _env.run()
    lib = _env.read_json(run / "library.json")
    if not lib or not lib.get("month"):
        sys.exit(f"{run / 'library.json'} is missing or names no month: run gather.py first")
    p = subprocess.run([sys.executable, str(S / "stats.py")], capture_output=True, text=True)
    if p.returncode:
        sys.exit(p.stdout + p.stderr)
    print(p.stdout.strip().splitlines()[-1])
    stats = _env.read_json(run / "stats.json")
    month = month_json(lib, run)
    mo = lib["month"]
    if len(month["posts"]) < 3:
        msg = f"To tell your {mo['name']} in stories I need three posts from it; the data has {len(month['posts'])}."
        _env.write_text(run / "brief.md", msg + "\n")
        print(msg)
        return 4
    _env.write_json(run / "month.json", month)
    posts = [dict(x, people=people_of(x["caption"])) for x in month["posts"]]
    reg, reg_year = stats.get("register") or {}, stats.get("register_year") or {}
    caps = [x["caption"] for x in posts if x["caption"]]
    research = {"handle": lib.get("handle"), "month": mo, "window": lib.get("window"), "source": lib.get("source"),
                "doors": lib.get("doors", {}), "posts": posts, "cadence": stats.get("cadence"),
                "register": reg, "register_year": reg_year}
    _env.write_json(run / "research.json", research)
    lower = reg.get("lowercase_share")
    quiet = (lower if lower is not None else reg_year.get("lowercase_share") or 0) >= 0.6
    # the draft's moments are the month as its captions tell it, the one whose caption says the most the peak
    made = [Post(x, mo["year"], mo["month"]) for x in posts]
    for t, x in zip(made, posts):
        t.row = x
    chosen = story(made)
    picks = [t.row for t in chosen]
    peak = max(chosen, key=lambda t: (t.weight, -t.day)).row if len(chosen) > 1 else None
    taste = {"written_by": "research.py draft; the agent edits this file and writes taste.md",
             "handle": lib.get("handle"), "month": {"key": mo["key"], "name": mo["name"], "year": mo["year"]},
             "register": {"lowercase": quiet,
                          "exclamations": any("!" in c for c in caps), "emoji": reg.get("emoji_per_caption", 0),
                          "avg_words": reg.get("avg_words"), "hashtags": (reg.get("top_hashtags") or [])[:3], "samples": caps[:4]},
             "ask": {"counts": False, "seconds": None, "series": False},
             "moments": [{"day": x["day"], "photo": x["photo"], "what": x["caption"], "line": x["caption"], "peak": x is peak,
                          "shot": shot_of(x["photo"])} for x in picks],
             "music": {"styles": [], "avoid": ["vocals", "spoken word"]}}
    old = _env.read_json(run / "taste.json") or {}
    if not old or "research.py draft" in old.get("written_by", ""):
        _env.write_json(run / "taste.json", taste)
    short = mo["name"][:3].lower()
    row = lambda x: (f"  - {short} {x['day']} ({x['type']}): \"{x['caption']}\""
                     + (f", with {', '.join('@' + a for a in x['people'])}" if x["people"] else "")
                     + (f", at {x['place']}" if x["place"] else "") + (f", photo {x['photo']}" if x["photo"] else ", no photograph")
                     + "".join(f", {x[k]} {k}" for k in ("likes", "comments") if x[k] is not None))
    lines = [f"# taste draft{' for @' + lib['handle'] if lib.get('handle') else ''}: {mo['name']} {mo['year']}", "",
             f"The agent writes {run / 'taste.md'} from this: one page, five paragraphs that start with the five headings below,",
             f"sets {run / 'taste.json'} `ask` from the person's words, and picks the month's three or four moments into its `moments`.", "",
             f"## {HEADINGS[0]}", "- the month, post by post (day, kind, their caption, who they tagged, where, its photograph):"]
    lines += [row(x) for x in posts]
    lines += ["- the moments: the three or four best things that happened (what they did, made, went to, pulled off, or the",
              "  person they did it with), each a post above with the line it says on screen; one of them the peak, the one",
              "  they would tell first. Their figures reach the screen only when they ask for their numbers."]
    lines += ["", f"## {HEADINGS[1]}", "- what their photographs keep returning to: the people, the places, the things",
              "", f"## {HEADINGS[2]}", f"- {sum(1 for x in posts if x['type'] == 'reel')} reels, {sum(1 for x in posts if x['type'] == 'photo')} photos; "
              "the light, the color and the framing of their photographs",
              "", f"## {HEADINGS[3]}",
              f"- {reg.get('avg_words')} words a caption, {int((lower or 0) * 100)}% lowercase, "
              f"{'no exclamation marks' if not taste['register']['exclamations'] else 'exclamation marks'}, {reg.get('emoji_per_caption', 0)} emoji a caption",
              f"- lines: {' / '.join(caps[:4])}",
              f"- music: the look's own, no {', no '.join(taste['music']['avoid'])}",
              "", f"## {HEADINGS[4]}", "- anything louder than their captions", ""]
    _env.write_text(run / "taste.draft.md", "\n".join(lines))
    print(f"{mo['name']} {mo['year']}: {len(posts)} posts")
    for x in posts:
        print(row(x))
    print(f"wrote {run}/month.json, research.json, taste.json (draft) and taste.draft.md; now write {run / 'taste.md'}, "
          f"set taste.json `ask` from their words and pick the moments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
