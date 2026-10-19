#!/usr/bin/env python3
"""Movement 4: the story film and the card series, each card animated and static, rendered from build/film.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py render            # out/film.mp4, out/cards/NN-<role>.mp4 and out/cards/NN-<role>.png
    python3 S/scripts/film.py render --only film|cards
    python3 S/scripts/film.py frames            # one settled frame per card into build/frames/NN-<role>.png, six of the
                                                # film into build/frames/film-NN.png, and build/frames/sheet.png
    python3 S/scripts/film.py stills            # the stills route (no node): the same film.json as composed stills

The engine is the Remotion project in S/motion (setup.py installs it). The film and every animated card are the
Film composition (1080x1920, 30 fps, H.264 high, CRF 18) over their own beat set, each 15 s; an animated card
carries the series mark ("SEPTEMBER 2026  02 / 05" and one progress segment per card). Every static card is the
Card composition drawing the card's still beat at its settled frame, with the mark full. The mastered music
(build/music/master.wav from music.py, AAC 192 kbps) is laid under the film and under every animated card.
Every SAFE_BREACH (text that left its safe box), FONT_ERROR and render error lands in build/render-report.json,
which qa.py gate reads. build/timeline.json carries each set's beats (start and length) for qa.py and the frame
extraction; build/cards.json names every card's static and animated file.
When setup.py reports engine "stills", render runs the stills route instead and build/engine.json says so.
"""
import argparse
import copy
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

FPS = 30
PUBLIC = Path("build/public")
CARDS_OUT = Path("out/cards")
BASE = ("id", "name", "handle", "year", "month", "format", "system")


def clip_for(beat, clips):
    """A beat's clip id resolved from build/clips.json; a clip with no file plays its substitute image."""
    c = beat.get("clip")
    if not c:
        return None
    if isinstance(c, dict):
        return c
    got = clips.get(c) or {}
    return {"id": c, "file": got.get("file"), "frames": got.get("frames", 0),
            "image": got.get("image") or (beat.get("photos") or [None])[0], "status": got.get("status", "pending")}


def base_of(board):
    return {k: copy.deepcopy(board[k]) for k in BASE if k in board}


def series_of(board, card):
    return {"n": card["n"], "of": len(board["cards"]), "role": card["role"], "title": card["title"]}


def props_for(board, beats, series=None):
    """Film composition props: the board's design system over one beat set, every clip id resolved."""
    clips = (_env.read_json("build/clips.json") or {}).get("clips", {})
    bs = copy.deepcopy(beats)
    for bt in bs:
        bt["clip"] = clip_for(bt, clips)
    return {"board": {**base_of(board), "beats": bs, "series": series}}


def still_props(board, card):
    """Card composition props: the card's still beat, no clip, with the series mark."""
    still = copy.deepcopy(card["still"])
    still["clip"] = None
    return {"board": {**base_of(board), "beats": [still], "series": series_of(board, card)}, "beat": still, "format": "story"}


def render_jobs(jobs, report, concurrency=None):
    t = _env.tools()
    if t.get("engine") != "remotion":
        sys.exit("the motion engine is not installed (setup.py reports engine 'stills'); run film.py stills")
    spec = {"publicDir": str(PUBLIC.resolve()), "report": str(Path(report).resolve()), "jobs": jobs,
            "bundleDir": str(Path(os.environ.get("TMPDIR") or Path("build/.bundle").resolve()) / "mr-bundle")}
    if concurrency:
        spec["concurrency"] = concurrency
    jf = Path("build/render") / f"{Path(report).stem}.jobs.json"
    _env.write_json(jf, spec)
    node = t["node"]
    env = dict(os.environ, PATH=f"{Path(node).parent}{os.pathsep}{os.environ.get('PATH', '')}")
    r = subprocess.run([node, str(Path(t["motion"]) / "render.mjs"), str(jf.resolve())], env=env)
    return _env.read_json(report) or {"failed": len(jobs), "findings": [{"text": f"render.mjs exited {r.returncode}"}]}


def timeline(beats):
    out, start = [], 0
    for i, b in enumerate(beats):
        t = (b.get("transition") or {}).get("frames", 0) if i else 0
        start = start - t if i else 0
        out.append({"id": b["id"], "kind": b["kind"], "start": start, "frames": b["frames"], "transition": t,
                    "start_s": round(start / FPS, 3), "seconds": round(b["frames"] / FPS, 3),
                    "shots": [0] + list((b.get("data") or {}).get("cuts") or []) + [b["frames"]]})
        start += b["frames"]
    return out


def set_seconds(tl):
    return (tl[-1]["start"] + tl[-1]["frames"]) / FPS if tl else 0


def card_files(card):
    return CARDS_OUT / f"{card['id']}.mp4", CARDS_OUT / f"{card['id']}.png"


def write_records(board):
    tl = {"fps": FPS, "film": timeline(board["film"]["beats"]), "cards": {c["id"]: timeline(c["beats"]) for c in board["cards"]}}
    tl["seconds"] = set_seconds(tl["film"])
    _env.write_json("build/timeline.json", tl)
    rows = []
    for c in board["cards"]:
        mp4, png = card_files(c)
        rows.append({"n": c["n"], "id": c["id"], "role": c["role"], "title": c["title"], "animated": str(mp4), "static": str(png),
                     "seconds": set_seconds(tl["cards"][c["id"]]), "still": c["still"]["id"], "from": c["still"].get("from"), "kinds": [b["kind"] for b in c["beats"]]})
    _env.write_json("build/cards.json", {"of": len(rows), "cards": rows, "film": "out/film.mp4", "seconds": tl["seconds"]})
    return tl


def mux(silent, out, seconds):
    ff = _env.ffmpeg()
    master = Path("build/music/master.wav")
    if master.exists():
        cmd = [ff, "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}",
               "-movflags", "+faststart", str(out)]
    else:
        cmd = [ff, "-y", "-v", "error", "-i", str(silent), "-c:v", "copy", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return master.exists()


def cmd_render(a):
    board = _env.read_json("build/film.json")
    if not board:
        sys.exit("build/film.json is missing: run storyboard.py snap first")
    if _env.tools().get("engine") != "remotion":
        return cmd_stills(a)
    CARDS_OUT.mkdir(parents=True, exist_ok=True)
    silent = Path("build/render").resolve()
    silent.mkdir(parents=True, exist_ok=True)
    jobs, videos = [], []
    if a.only in (None, "film"):
        f = silent / "film.silent.mp4"
        jobs.append({"type": "video", "composition": "Film", "props": props_for(board, board["film"]["beats"]), "out": str(f), "crf": 18})
        videos.append((f, Path("out/film.mp4")))
    if a.only in (None, "cards"):
        for c in board["cards"]:
            mp4, png = card_files(c)
            mp4.unlink(missing_ok=True)
            png.unlink(missing_ok=True)
            jobs.append({"type": "still", "composition": "Card", "frame": 0, "scale": 1, "props": still_props(board, c),
                         "out": str(png.resolve())})
            f = silent / f"{c['id']}.silent.mp4"
            jobs.append({"type": "video", "composition": "Film", "props": props_for(board, c["beats"], series_of(board, c)),
                         "out": str(f), "crf": 18})
            videos.append((f, mp4))
    t0 = time.time()
    rep = render_jobs(jobs, "build/render-report.json")
    tl = write_records(board)
    music = False
    for src, dst in videos:
        if src.exists():
            music = mux(src, dst, tl["seconds"])
    _env.write_json("build/engine.json", {"engine": "remotion", "node": _env.tools().get("node"),
                                          "seconds": round(time.time() - t0, 1), "jobs": len(jobs)})
    for f in rep.get("findings", []):
        print("finding:", f["text"][:400])
    print(f"rendered {len(jobs) - rep.get('failed', 0)} of {len(jobs)} jobs in {time.time() - t0:.1f} s: "
          f"{len(videos)} videos of {tl['seconds']:.1f} s{' with music' if music else ' (no music track)'}, "
          f"{len(board['cards']) if a.only != 'film' else 0} static cards -> out/film.mp4, {CARDS_OUT}/")
    return 1 if rep.get("failed") else 0


def settled(t, out=0):
    """The settled moment of a beat's longest shot: past its entrance, before the next cut or the transition out."""
    edges = list(t.get("shots") or [0, t["frames"]])
    edges[-1] = max(edges[-2] + 1, edges[-1] - out)
    lo, hi = max(zip(edges, edges[1:]), key=lambda e: e[1] - e[0])
    lo = max(lo, t["transition"])
    return (t["start"] + lo + max(0, hi - lo) * 0.7) / FPS


def outs(tl):
    """Each beat's transition out: the next beat's transition in."""
    return [tl[i + 1]["transition"] if i + 1 < len(tl) else 0 for i in range(len(tl))]


def cmd_frames(a):
    tl = _env.read_json("build/timeline.json")
    cards = (_env.read_json("build/cards.json") or {}).get("cards")
    if not tl or not cards or not Path(a.film).exists():
        sys.exit("out/film.mp4, build/timeline.json and build/cards.json are needed: run film.py render first")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    ff = _env.ffmpeg()

    def grab(src, t, dst):
        subprocess.run([ff, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", str(dst)], check=True)
        return dst

    shots = []
    for c in cards:
        beats = tl["cards"][c["id"]]
        # the beat the static card is drawn from, at its settled moment, so the two versions can be compared
        i = next((k for k, b in enumerate(beats) if b["id"] == c.get("from")), len(beats) // 2)
        shots.append(grab(c["animated"], settled(beats[i], outs(beats)[i]), out / f"{c['id']}.png"))
    film = tl["film"]
    pick = sorted({round(i * (len(film) - 1) / 5) for i in range(6)}) if len(film) > 6 else range(len(film))
    for k, i in enumerate(pick, 1):
        shots.append(grab(a.film, settled(film[i], outs(film)[i]), out / f"film-{k:02d}.png"))
    _env.need("PIL")
    from PIL import Image
    ims = [Image.open(f).convert("RGB").resize((360, 640)) for f in shots]
    cols = max(len(cards), 6)
    rows = 2
    sheet = Image.new("RGB", (cols * 370 + 10, rows * 650 + 10), "#111111")
    for i, im in enumerate(ims[:len(cards)]):
        sheet.paste(im, (10 + i * 370, 10))
    for i, im in enumerate(ims[len(cards):]):
        sheet.paste(im, (10 + i * 370, 660))
    sheet.save(out / "sheet.png")
    print(f"{len(cards)} card frames and {len(shots) - len(cards)} film frames -> {out}/, sheet {out / 'sheet.png'}")
    return 0


# ------------------------------------------------------------------ the stills route (no node)
def cmd_stills(a):
    """Each beat as one composed still under an eased push, cut with crossfades; same film.json, same out/ names."""
    _env.need("PIL")
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    board = _env.read_json("build/film.json")
    if not board:
        sys.exit("build/film.json is missing: run storyboard.py snap first")
    s = board["system"]
    col = s["colors"]
    W, H = 1080, 1920
    sa = s["safe"]["story"]
    fonts = {k: str(_env.SKILL / s[k]["file"]) for k in ("display", "text")}
    ff = _env.ffmpeg()
    work = Path("build/stills")
    work.mkdir(parents=True, exist_ok=True)

    def font(kind, size):
        return ImageFont.truetype(fonts[kind], size)

    def first_photo(bt):
        data = bt.get("data") or {}
        clip = bt.get("clip") if isinstance(bt.get("clip"), dict) else None
        for p in [(clip or {}).get("image"), *(bt.get("photos") or []),
                  *[q for g in data.get("groups", []) + data.get("pages", []) for q in g.get("photos") or []]]:
            if p and (PUBLIC / p).exists():
                return p
        return None

    def wrap(d, text, f, maxw):
        lines, cur = [], ""
        for wd in str(text).split():
            nxt = (cur + " " + wd).strip()
            if d.textlength(nxt, font=f) <= maxw or not cur:
                cur = nxt
            else:
                lines.append(cur)
                cur = wd
        return lines + [cur] if cur else lines

    def compose(bt, series=None):
        im = Image.new("RGB", (W, H), col["bg"])
        p = first_photo(bt)
        if p:
            im = ImageOps.fit(Image.open(PUBLIC / p).convert("RGB"), (W, H), Image.LANCZOS)
            shade = Image.linear_gradient("L").resize((W, H))
            im = Image.composite(Image.new("RGB", (W, H), col["bg"]), im, shade.point(lambda v: int(max(0, v - 110) * 1.4)))
        d = ImageDraw.Draw(im)
        top = sa["top"] + (92 if series else 0)
        if series:
            lab = font("text", 30)
            d.text((sa["left"], sa["top"]), f"{board['month']['name'].upper()} {board['year']}", font=lab, fill=col["ink"])
            d.text((W - sa["right"], sa["top"]), f"{series['n']:02d} / {series['of']:02d}", font=lab, fill=col["accent"], anchor="ra")
            seg = (W - sa["left"] - sa["right"] - 8 * (series["of"] - 1)) / series["of"]
            for i in range(series["of"]):
                x = sa["left"] + i * (seg + 8)
                d.rectangle((x, sa["top"] + 48, x + seg, sa["top"] + 54), fill=col["ink"] if i < series["n"] else col["accent2"])
        t = dict(bt.get("text") or {})
        data = bt.get("data") or {}
        if not t.get("headline"):
            t["headline"] = next((x.get("value") for x in data.get("stats", [])), None) or \
                next((r.get("text") for r in data.get("rows", [])), None) or \
                next((pg.get("headline") for pg in data.get("pages", [])), None) or data.get("signoff")
        maxw = W - sa["left"] - sa["right"]
        blocks = [(k, sz, c) for k, sz, c in (("kicker", 34, col["accent"]), ("headline", 112, col["ink"]), ("line", 44, col["ink"])) if t.get(k)]
        laid = []
        for k, size, c in blocks:
            f = font("display" if k == "headline" else "text", size)
            laid.append((f, wrap(d, t[k], f, maxw), size, c))
        y = max(top, H - sa["bottom"] - sum(len(ln) * int(sz * 1.1) + 24 for _, ln, sz, _ in laid))
        for f, lines, size, c in laid:
            for ln in lines:
                d.text((sa["left"], y), ln, font=f, fill=c)
                y += int(size * 1.1)
            y += 24
        return im

    def video(name, beats, series=None):
        parts = []
        for i, bt in enumerate(beats):
            f = work / f"{name}-{i + 1:02d}.png"
            compose(bt, series).save(f)
            clip = work / f"{name}-{i + 1:02d}.mp4"
            z = "1+0.06*(1-pow(1-on/{n},3))".format(n=bt["frames"])
            subprocess.run([ff, "-y", "-v", "error", "-loop", "1", "-i", str(f), "-t", f"{bt['frames'] / FPS:.3f}", "-vf",
                            f"scale={W * 2}:{H * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={bt['frames']}:s={W}x{H}:fps={FPS},format=yuv420p",
                            "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-r", str(FPS), str(clip)], check=True)
            parts.append((clip, bt["frames"] / FPS, (bt.get("transition") or {}).get("frames", 0) / FPS))
        inputs = [x for clip, _, _ in parts for x in ("-i", str(clip))]
        flt, last, offset = [], "0:v", parts[0][1]
        for k in range(1, len(parts)):
            tr = max(0.1, parts[k][2])
            offset -= tr
            flt.append(f"[{last}][{k}:v]xfade=transition=fade:duration={tr:.3f}:offset={offset:.3f}[v{k}]")
            last = f"v{k}"
            offset += parts[k][1]
        silent = work / f"{name}.silent.mp4"
        mapping = ["-filter_complex", ";".join(flt), "-map", f"[{last}]"] if flt else []
        subprocess.run([ff, "-y", "-v", "error", *inputs, *mapping, "-c:v", "libx264", "-profile:v", "high", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-r", str(FPS), str(silent)], check=True)
        return silent

    clips = (_env.read_json("build/clips.json") or {}).get("clips", {})
    for bs in [board["film"]["beats"]] + [c["beats"] for c in board["cards"]]:
        for bt in bs:
            bt["clip"] = clip_for(bt, clips)
    tl = write_records(board)
    CARDS_OUT.mkdir(parents=True, exist_ok=True)
    music = mux(video("film", board["film"]["beats"]), Path("out/film.mp4"), tl["seconds"])
    for c in board["cards"]:
        mp4, png = card_files(c)
        ser = series_of(board, c)
        mux(video(c["id"], c["beats"], ser), mp4, tl["seconds"])
        compose(c["still"], ser).save(png)
    _env.write_json("build/engine.json", {"engine": "stills", "why": "node could not be installed on this machine"})
    _env.write_json("build/render-report.json", {"failed": 0, "findings": [], "engine": "stills"})
    print(f"stills route: film and {len(board['cards'])} cards, {tl['seconds']:.1f} s{' with music' if music else ''} -> out/")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["render", "frames", "stills"])
    ap.add_argument("--only", choices=["film", "cards"])
    ap.add_argument("--film", default="out/film.mp4")
    ap.add_argument("--out", default="build/frames")
    a = ap.parse_args()
    return {"render": cmd_render, "frames": cmd_frames, "stills": cmd_stills}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
