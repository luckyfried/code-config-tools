#!/usr/bin/env python3
"""Movement 1, research: prepare each person's best photo, the group photos for the wall, and the opener. Writes
R/photo_index.json, R/picks.json and R/photos/*.jpg.

USAGE (from the workspace root):
    python3 S/scripts/picks.py

Scores every photo of the year, the person's own and the ones their people posted of them (color, contrast,
exposure), finds each one's focal point (where the detail is, so a cover crop keeps it), converts HEIC and rotates
by EXIF, and saves a 1600 px JPEG copy in R/photos/. Reads R/people.json.
  people   one best photo per person, in rank order, with the line of theirs it carries: the post their best line
           was left on first (people.json's line, then their other lines), then a photo whose caption names them, then
           the one with the fewest other people in it, then the best scored, never the same photo for two people;
           the line is the one left on that photo, else their best line
  wall     nine photos with the most of the people in them, every person in at least one, in date order (a group
           reel stands in by its poster frame, 40% of the way in, and keeps its footage for the film); when the
           year has fewer group photos, each person's next photos fill the wall
  opener   the photo with the most of them in it, outside the wall when there is one
cast.py draft starts each person's photographs from these picks; a different photograph of a person goes into
R/cast.json before cast.py match.
"""
import datetime as dt
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

_env.need("PIL")
from PIL import Image, ImageFilter, ImageOps, ImageStat  # noqa: E402

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

PHOTOS = Path("photos")
VIDEO = {".mp4", ".mov", ".m4v"}


def open_image(path, draft=None):
    im = Image.open(path)
    if draft and im.format == "JPEG":
        im.draft("RGB", draft)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def prepare(path):
    """A 1600 px JPEG copy in R/photos/ (HEIC converted, EXIF rotation applied). Returns its path or None."""
    src = Path(path)
    dest = PHOTOS / (hashlib.sha1(str(src.resolve()).encode()).hexdigest()[:12] + ".jpg")
    if dest.exists():
        return str(dest.resolve())
    try:
        im = open_image(src)
    except Exception as e:
        print(f"skip {src.name}: cannot open ({e}){' ; HEIC needs pillow-heif' if src.suffix.lower() in ('.heic', '.heif') else ''}",
              file=sys.stderr)
        return None
    im.thumbnail((1600, 1600), Image.LANCZOS)
    PHOTOS.mkdir(parents=True, exist_ok=True)
    # a copy is reused once it exists, so it is made under its part name and moved in whole
    im.save(_env.part(dest), "JPEG", quality=90)
    os.replace(_env.part(dest), dest)
    return str(dest.resolve())


def poster(video):
    """A reel's poster frame as a 1600 px JPEG in R/photos/, 40% of the way in. Returns its path or None."""
    src = Path(video)
    dest = PHOTOS / (hashlib.sha1((str(src.resolve()) + "#poster").encode()).hexdigest()[:12] + ".jpg")
    if dest.exists():
        return str(dest.resolve())
    PHOTOS.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                       capture_output=True, text=True)
    try:
        at = float(r.stdout.strip()) * 0.4
    except ValueError:
        at = 0.5
    tmp = _env.part(dest)
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1",
                        "-vf", "scale='min(1600,iw)':-2", "-q:v", "2", str(tmp)], capture_output=True)
    if r.returncode or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        return None
    os.replace(tmp, dest)
    return str(dest.resolve())


def analyse(path):
    im = open_image(path, draft=(160, 200))
    w, h = im.size
    small = im.resize((64, max(1, round(64 * h / w))))
    hsv = small.convert("HSV")
    sat = ImageStat.Stat(hsv.getchannel("S")).mean[0] / 255
    light = ImageStat.Stat(small.convert("L"))
    bright, contrast = light.mean[0] / 255, light.stddev[0] / 128
    expo = 1 - min(1, abs(bright - 0.52) * 2.2)
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES)
    px = edges.load()
    sw, sh = edges.size
    tot = sx = sy = 0
    for y in range(sh):
        for x in range(sw):
            v = px[x, y]
            tot += v
            sx += v * x
            sy += v * y
    fx, fy = (sx / tot / sw, sy / tot / sh) if tot else (0.5, 0.5)
    q = small.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:15]
    cols = sorted(q.getcolors(), reverse=True)
    dom = [{"rgb": pal[3 * i:3 * i + 3], "share": round(n / (sw * sh), 3)} for n, i in cols]
    score = round(0.45 * sat + 0.35 * min(1, contrast) + 0.2 * expo, 3)
    return {"w": w, "h": h, "score": score, "bright": round(bright, 3),
            "focal": [round(min(0.8, max(0.2, fx)), 2), round(min(0.8, max(0.2, fy)), 2)], "colors": dom}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    _env.enter_run()
    d = _env.read_json("library.json")
    ppl = _env.read_json("people.json")
    if not d or not ppl:
        sys.exit("run gather.py and people.py first")
    index, skipped, seen = [], 0, set()
    for kind, rows in (("post", d["posts"]), ("tagged", d.get("tagged_in", [])), ("story", d["stories"])):
        for r in rows:
            for m in r["media"]:
                if Path(m).suffix.lower() in VIDEO or m in seen:
                    continue
                seen.add(m)
                try:
                    a = analyse(m)
                except Exception:
                    skipped += 1
                    continue
                month = dt.datetime.fromtimestamp(int(r["ts"]), dt.timezone.utc).month
                index.append({"src": m, "kind": kind, "ts": r["ts"], "month": month, "likes": r.get("likes"),
                              "tagged": r.get("tagged") or [], **a})
    if not index:
        sys.exit("no photos could be opened; the film needs at least one photo")
    _env.write_json("photo_index.json", index)
    score = {e["src"]: e for e in index}
    handles = [p["handle"] for p in ppl["people"]]
    people, used = [], set()
    for p in ppl["people"]:
        cands = [x for x in p["photos"] if x["src"] in score or Path(x["src"]).suffix.lower() in VIDEO]
        named = lambda x: p["handle"] in {m.lower() for m in re.findall(r"@([A-Za-z0-9._]*[A-Za-z0-9_])", x["caption"])}
        lines = [x for x in [p.get("line")] + (p.get("lines") or []) if x]
        posts = [x.get("post") for x in lines]
        cands.sort(key=lambda x: (posts.index(x["src"]) if x["src"] in posts else len(posts), not named(x),
                                  len([w for w in x["with"] if w in handles]), Path(x["src"]).suffix.lower() in VIDEO,
                                  -(score.get(x["src"]) or {}).get("score", 0)))
        pick = next((x for x in cands if x["src"] not in used), None)
        src, still = None, None
        if pick:
            src = pick["src"]
            still = poster(src) if Path(src).suffix.lower() in VIDEO else prepare(src)
        if not still:
            print(f"no photo of @{p['handle']} could be opened; the card uses a group photo", file=sys.stderr)
            continue
        used.add(src)
        line = next((x for x in lines if x.get("post") == src), p.get("line"))
        people.append({"rank": p["rank"], "handle": p["handle"], "photo": still, "src": src, "with": pick["with"],
                       "ts": pick["ts"], "caption": pick["caption"], "line": line, **analyse(still)})
    groups = {}
    for p in ppl["people"]:
        for x in p["photos"]:
            g = groups.setdefault(x["src"], {"src": x["src"], "ts": x["ts"], "caption": x["caption"], "kind": x["kind"],
                                             "owner": x["owner"], "people": set()})
            g["people"].add(p["handle"])
    for g in groups.values():
        g["video"] = g["src"] if Path(g["src"]).suffix.lower() in VIDEO else None
        g["score"] = (score.get(g["src"]) or {}).get("score", 0.5 if g["video"] else 0)
    pool = sorted(groups.values(), key=lambda g: (-len(g["people"]), -g["score"]))
    portraits = {x["src"] for x in people}
    wall, covered = [], set()
    for g in pool:
        if len(wall) < 9 and len(g["people"]) >= 2 and g["people"] - covered and g["src"] not in portraits:
            wall.append(g)
            covered |= g["people"]
    for g in pool:
        if len(wall) < 9 and len(g["people"]) >= 2 and g not in wall and g["src"] not in portraits:
            wall.append(g)
    for g in pool:
        if len(wall) < 9 and g not in wall and (g["people"] - covered or len(wall) < 9):
            wall.append(g)
            covered |= g["people"]
    wall.sort(key=lambda g: g["ts"])
    tiles = []
    for g in wall:
        still = poster(g["src"]) if g["video"] else prepare(g["src"])
        if not still:
            continue
        tiles.append({"photo": still, "src": g["src"], "video": g["video"], "ts": g["ts"], "caption": g["caption"],
                      "people": [h for h in handles if h in g["people"]], "owner": g["owner"], **analyse(still)})
    rest = [g for g in pool if g not in wall and not g["video"]]
    opener = rest[0] if rest and len(rest[0]["people"]) >= 2 else (max(wall, key=lambda g: len(g["people"])) if wall else None)
    out = {"people": people, "wall": tiles, "chapters": {"people": [x["photo"] for x in people], "wall": [t["photo"] for t in tiles]},
           "focal": {}, "source_of": {}}
    op = (poster(opener["src"]) if opener["video"] else prepare(opener["src"])) if opener else None
    if not op:
        best = max((e for e in index if e["bright"] > 0.25), key=lambda e: e["score"], default=index[0])
        op = prepare(best["src"])
    out["chapters"]["opener"] = [op] if op else []
    for x in people + tiles:
        out["focal"][x["photo"]] = f"{x['focal'][0] * 100:.0f}% {x['focal'][1] * 100:.0f}%"
        out["source_of"][x["photo"]] = x["src"]
    _env.write_json("picks.json", out)
    missing = [h for h in handles if h not in {x["handle"] for x in people}]
    off_wall = [h for h in handles if not any(h in t["people"] for t in tiles)]
    print(f"indexed {len(index)} photos ({skipped} could not be opened); prepared {len(list(PHOTOS.glob('[!.]*.jpg')))} in R/photos/")
    for x in people:
        print(f"  {x['rank']}. @{x['handle']:<16} {Path(x['src']).name}  with {len(x['with'])} others  score {x['score']}")
    print(f"wall: {len(tiles)} photos, " + "; ".join(f"{len(t['people'])} people{' (reel)' if t['video'] else ''}" for t in tiles))
    if missing:
        print("no photo for: " + ", ".join(missing))
    if off_wall:
        print("not on the wall: " + ", ".join(off_wall))
    print("wrote R/picks.json and R/photo_index.json")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
