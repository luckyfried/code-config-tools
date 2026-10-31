#!/usr/bin/env python3
"""The picked board's film, measured as a quick cut and then rendered in its three shapes, with the nine posts
designed in its style, the story card, the caption and the grid after.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py preview    # the reel at half size, measured: preview/film.mp4, preview/preview.json, strips
    python3 S/scripts/film.py render     # out/film.mp4, out/film-landscape.mp4, out/film-square.mp4, out/posts/,
                                         # out/story.png, out/caption.txt, out/grid-after.png, frames/<format>-<rest>.png

Both take the board storyboard.py pick made (board.json, named with its hash by winner.json) and refuse any other.
preview is the quick look before the full render: the cuts as planned and as the picture shows them, cuts per minute,
the luma line and its quiet seconds, and the hook event's frame. render first runs the swap test on the nine as placed
(critic.py swap), then renders the reel (1080x1920), the landscape film (1920x1080) and the square film (1080x1080)
from the built composition, lays the mastered music (the master music.json names, AAC 192 kbps) under each, takes
frames/ (the hook, the densest post and the closer of each format, at the film's own size) from the same composition,
and makes the rest of out/:
  posts/NN.png   each post as it will be posted, 1080x1350, laid out the way the board's style card lays a photograph
                 and its line: a photograph in a wide paper margin with its line set small under it (the card's
                 picture beside its line under it), a photograph over a row of cells, the place in one and the line in
                 the others, the cell beside the line in the accent on every other post (the line in a cell of its
                 own), a photograph to the edges with its line set large in the display face over a scrim that
                 darkens the picture under the words (a card that sets its line over its picture), or, on a card that
                 shows no photograph, the photograph over a block of the ground with the line slammed across it. The line is the post's caption as a cell sets it (plan.cell_words) and the label
                 the place it names; a post whose caption names neither shows the photograph alone in that layout.
  story.png      the reel's closer as a Story card (their profile with the posts in place, the handle, the bio, the ask)
  caption.txt    the reel's caption and each post's day and caption, to copy from
  grid-after.png their profile with the nine designed posts above the grid they have now, in the style's colors
render/film-report.json carries every finding the composition logged; render/film.json records what was rendered.
A render that was stopped resumes when the same command runs again. A render removes out/review.html,
render/film.json and render/film-report.json before it changes anything they speak for.
"""
import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import critic  # noqa: E402
import drive  # noqa: E402
import studio  # noqa: E402
from plan import cell_words  # noqa: E402

PUBLIC = Path("public")
POSTS = Path("out/posts")
AFTER = Path("out/grid-after.png")
STORY = Path("out/story.png")
CAPTION = Path("out/caption.txt")
FRAMES = Path("frames")
NAMES = {"reel": "film.mp4", "landscape": "film-landscape.mp4", "square": "film-square.mp4"}
ROWS_AFTER = 7
PW, PH = 1080, 1350


def board_of():
    board = _env.read_json("board.json")
    if not board:
        sys.exit("board.json is missing: run storyboard.py draft, sheets, then pick")
    if not board["check"]["pass"]:
        for f in board["check"]["faults"]:
            print("FAULT", f)
        sys.exit("the board fails its bounds check: fix the words or the plan, then run storyboard.py draft and pick")
    win = _env.read_json("winner.json") or {}
    if win.get("board") != board.get("letter") or win.get("hash") != board.get("hash"):
        sys.exit("board.json is not the board picked (winner.json): run storyboard.py pick A|B|C")
    return board


def cmd_preview(a):
    board = board_of()
    d = Path("preview")
    with studio.lock("preview") as run:
        # preview.json names the film it measured: it goes before the film changes and comes back after the measure
        (d / "preview.json").unlink(missing_ok=True)
        d.mkdir(exist_ok=True)
        rep = studio.render([studio.video(board["boards"]["reel"], d / "film.mp4", scale=0.5)], "preview", run)
        studio.publish("preview", rep)
        if rep["failed"]:
            sys.exit("the preview render failed (render/preview.log, render/preview-report.json); run film.py preview again to resume it")
        m = studio.measure(d / "film.mp4", board["cuts_at"], board["hook_frame"], run=run)
        m.update(hash=board["hash"], style=board["style"], findings=[x["text"][:200] for x in rep["findings"]])
        _env.write_json(d / "preview.json", m)
    print(f"preview: {m['seconds']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), hook at frame {m['hook_event_frame']}, "
          f"seconds under 0.5: {m['seconds_under_half']} -> {d / 'preview.json'}, strips {m['strip2']} and {m['strip12']}")
    return 0


def mux(run, silent, out, seconds, master):
    """The silent cut with the mastered music (`master`) under it; without music, the picture alone."""
    if master:
        run.spawn([_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a",
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}", "-movflags", "+faststart",
                   str(out)], check=True)
    else:
        shutil.copyfile(silent, out)
    return bool(master)


def fitted(path, crop45, w, h):
    """The photograph filling a w x h box: the widest crop of that shape, centered where the plan's 4:5 crop is."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    W, H = im.size
    x, y, cw = crop45
    ch = min(1.0, cw * W / (4 / 5) / H)
    a = w / h
    bw, bh = (H * a, H) if W / H > a else (W, W / a)
    left = min(max(0.0, (x + cw / 2) * W - bw / 2), W - bw)
    top = min(max(0.0, (y + ch / 2) * H - bh / 2), H - bh)
    return im.crop((round(left), round(top), round(left + bw), round(top + bh))).resize((w, h), Image.LANCZOS)


def face_of(kind):
    return compose.in_use()["faces"]["display" if kind == "display" else "text"]


def cased(text, kind):
    return text.upper() if face_of(kind).get("case") == "uppercase" else text


def wrapped(text, font, width):
    lines, cur = [], ""
    for w in text.split():
        nxt = (cur + " " + w).strip()
        if not cur or font.getlength(nxt) <= width:
            cur = nxt
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def setting(text, kind, size, width, most, floor):
    """The largest size from `size` down to `floor` at which `text` sets in `width` px on `most` lines or fewer, as
    (font, size, lines); None when it never does. A word wider than the width never sets."""
    text = cased(text, kind)
    while size >= floor:
        f = _env.pil_font(size, kind)
        lines = wrapped(text, f, width)
        if len(lines) <= most and all(f.getlength(ln) <= width for ln in lines):
            return f, size, lines
        size -= 2
    return None


def draw_line(d, x, y, text, font, size, fill, tracking=0.0):
    """One line with its baseline at y, tracked out by the face's tracking (a share of the size)."""
    if not tracking:
        d.text((x, y), text, font=font, fill=fill, anchor="ls")
        return
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill, anchor="ls")
        x += font.getlength(ch) + tracking * size


def draw_set(d, x, y, setting_, kind, fill):
    """A set block (`setting`) with its first baseline at y; returns the baseline below its last line."""
    f, size, lines = setting_
    face = face_of(kind)
    lead = size * face.get("lineHeight", 1.1)
    for ln in lines:
        draw_line(d, x, y, ln, f, size, fill, face.get("tracking", 0))
        y += lead
    return y


def post_words(p, kind, size, width, most, floor):
    """The post's line as a cell sets it and how it sets, or None: its caption, cut at a word to what fits."""
    fits = lambda t: setting(t, kind, size, width, most, floor) is not None
    words = cell_words(p.get("caption") or "", fits)
    return setting(words, kind, size, width, most, floor) if words else None


def post_layout(card):
    """How the card lays a photograph and its line, read from its photo layout: `type` when it shows no photograph,
    `over` when its line sets over the picture on a scrim, `cells` when its line stands in a cell beside the picture's
    edge, `margin` when the line sits under the picture."""
    lay = card["photo"]
    if not lay["picture"]["show"]:
        return "type"
    if lay["line"].get("scrim"):
        return "over"
    px, _, pw, _ = lay["picture"]["box"]
    return "cells" if lay["line"]["box"][0] >= px + pw * 0.5 else "margin"


# the over layout's side margin, the most lines its words take, and the smallest size they set at, px
OVER_M, OVER_LINES, OVER_FLOOR = 72, 5, 72
# the least share of the ink under the words of the over layout: the line's color reads on a bright photograph only
# over this much of the ink
OVER_SCRIM = 0.75


def one_size(board, line, width, most, floor, room=None):
    """The one size a layout sets every post's line at, so the nine read as one set: the largest from the card's size
    down to `floor` at which each caption sets whole in `width` px on `most` lines, its first line's cap and every line
    after it inside `room` px when given; `floor` when none does (the line then cut at a word to what fits)."""
    caps = [p["caption"] for p in board["nine"] if p.get("caption")]
    lead = face_of(line["face"]).get("lineHeight", 1.1)
    for size in range(line["size"], floor - 1, -2):
        sets = [setting(c, line["face"], size, width, most, size) for c in caps]
        if all(sets) and (room is None or all(size * (1 + lead * (len(t[2]) - 1)) <= room for t in sets)):
            return size
    return floor


def over_size(board, line):
    """The over layout's one size for every post's line (one_size, in its margins, on OVER_LINES lines)."""
    return one_size(board, line, PW - 2 * OVER_M, OVER_LINES, OVER_FLOOR)


# the margin layout's side and top margin and the picture's height, px
MARGIN_M = round(PW * 0.09)
MARGIN_PH = round(PH * 0.66)


def margin_size(board, line, lab_size):
    """The margin layout's one size for every post's line: on up to three lines under the label's place, its last
    line clear of the post's foot by half the margin."""
    room = PH - MARGIN_M // 2 - (MARGIN_M + MARGIN_PH + round(MARGIN_M * 0.75) + lab_size) - 0.25 * line["size"]
    return one_size(board, line, PW - 2 * MARGIN_M, 3, 40, room)


def over_post(p, src, line, label, place, colors, size):
    """A photograph to the edges with the post's line set over it in the display face at `size` (over_size), its last
    baseline at the foot of the card's line box, over a scrim of the ink that rises from clear above the words to the
    card's scrim strength (OVER_SCRIM at least) under them; the place sits small above the line in the line's color."""
    from PIL import Image, ImageDraw
    m = OVER_M
    im = fitted(src, p["crop45"], PW, PH)
    words = post_words(p, line["face"], size, PW - 2 * m, OVER_LINES, OVER_FLOOR)
    if not (words or place):
        return im
    _, ly, _, lh = line["box"]
    foot = round(min(ly + lh, 0.94) * PH)
    lead = words[1] * face_of(line["face"]).get("lineHeight", 1.1) if words else 0
    first = foot - lead * (len(words[2]) - 1) if words else foot
    lab = min(56, max(30, label["size"]))
    top = first - (words[1] if words else 0) - (round(lab * 1.6) if place else 0)
    rise = round(PH * 0.16)
    mask = Image.new("L", (1, PH), 0)
    strength = round(255 * max(OVER_SCRIM, line["scrim"]))
    for y in range(PH):
        u = min(1.0, max(0.0, (y - (top - rise)) / rise))
        mask.putpixel((0, y), round(strength * u * u * (3 - 2 * u)))
    im = Image.composite(Image.new("RGB", (PW, PH), colors["ink"]), im, mask.resize((PW, PH)))
    d = ImageDraw.Draw(im)
    fill = colors[line["color"]]
    if place:
        y = first - (words[1] if words else 0) - round(lab * 0.6) if words else foot
        draw_line(d, m, y, cased(place, label["face"]), _env.pil_font(lab, label["face"]), lab, fill,
                  face_of(label["face"]).get("tracking", 0) + 0.08)
    if words:
        draw_set(d, m, first, words, line["face"], fill)
    return im


def design_post(board, p, card, colors, size=None):
    """One post, 1080x1350, in the card's layout (see the module's posts/ row); `size` is the line's size, the same on
    every post of a margin or over layout (margin_size or over_size when None); the label's place is kept on a post
    without one, so every line starts on one baseline."""
    from PIL import Image, ImageDraw
    lay = card["photo"]
    line, label = lay["line"], lay["label"]
    ground, ink = colors[lay["ground"]], colors[line["color"]]
    lab_color, lab_size = colors[label["color"]], max(30, label["size"])
    place = drive.place_in(p.get("caption") or "")
    src = PUBLIC / p["file"]
    kind = post_layout(card)
    im = Image.new("RGB", (PW, PH), ground)
    d = ImageDraw.Draw(im)
    if kind == "margin":
        m, size = MARGIN_M, margin_size(board, line, lab_size) if size is None else size
        words = post_words(p, line["face"], size, PW - 2 * m, 3, 40)
        ph = MARGIN_PH if (words or place) else PH - 2 * m
        im.paste(fitted(src, p["crop45"], PW - 2 * m, ph), (m, m))
        y = m + ph + round(m * 0.75) + lab_size
        if place:
            draw_line(d, m, y, cased(place, label["face"]), _env.pil_font(lab_size, label["face"]), lab_size, lab_color,
                      face_of(label["face"]).get("tracking", 0) + 0.08)
        y += round(size * 1.25)
        if words:
            draw_set(d, m, y, words, line["face"], ink)
    elif kind == "over":
        im = over_post(p, src, line, label, place, colors, over_size(board, line) if size is None else size)
    elif kind == "cells":
        m, g = 60, 24
        cw = (PW - 2 * m - 2 * g) // 3
        ph = round((PH - 2 * m - g) * 0.7)
        im.paste(fitted(src, p["crop45"], PW - 2 * m, ph), (m, m))
        row = m + ph + g
        rh = PH - m - row
        block = board["places"].get(str(p["n"])) == "calm"
        if block:
            d.rectangle((m, row, m + cw, row + rh), fill=colors["accent"])
        if place:
            pad, size = (24, lab_size + 8) if block else (0, lab_size)
            draw_line(d, m + pad, row + pad + size, cased(place, label["face"]), _env.pil_font(size, label["face"]),
                      size, ground if block else lab_color, face_of(label["face"]).get("tracking", 0))
        words = post_words(p, line["face"], line["size"], 2 * cw + g, 4, 40)
        if words:
            draw_set(d, m + cw + g, row + round(words[1] * 0.78), words, line["face"], ink)
    else:
        busy = board["places"].get(str(p["n"])) == "busy"
        words = None if busy else post_words(p, line["face"], line["size"], PW - 2 * 72, 3, 64)
        if busy or not (words or place):
            im.paste(fitted(src, p["crop45"], PW, PH), (0, 0))
        else:
            ph = round(PH * 0.56)
            im.paste(fitted(src, p["crop45"], PW, ph), (0, 0))
            if words:
                draw_set(d, 72, ph + 56 + words[1] * 0.8, words, line["face"], ink)
            if place:
                draw_line(d, 72, PH - 64, cased(place, label["face"]), _env.pil_font(min(56, lab_size + 14), label["face"]),
                          min(56, lab_size + 14), lab_color, face_of(label["face"]).get("tracking", 0))
    return im


def posts(board, into):
    """Each post of the plan as posted, drawn into the folder `into` (the module's posts/ row)."""
    shutil.rmtree(into, ignore_errors=True)
    into.mkdir(parents=True)
    compose.use(board["style"])
    card = compose.card(board["style"])
    colors = board["boards"]["reel"]["system"]["colors"]
    kind, line = post_layout(card), card["photo"]["line"]
    lab_size = max(30, card["photo"]["label"]["size"])
    size = {"over": lambda: over_size(board, line), "margin": lambda: margin_size(board, line, lab_size)}.get(kind, lambda: None)()
    for p in board["nine"]:
        design_post(board, p, card, colors, size).save(into / f"{p['n']:02d}.png")


def grid_after(board, drawn, out):
    """Their profile with the plan in place, saved at `out`, in the style's colors and faces: a header with the handle,
    then three columns of 3:4 cells, the newest post top left (each designed post as the grid shows it, its middle
    3:4), then the grid they have now; with no feed, the new posts alone."""
    from PIL import Image, ImageDraw, ImageOps
    compose.use(board["style"])
    colors = board["boards"]["reel"]["system"]["colors"]
    cw, ch, gap, top = 358, 477, 3, 132
    cells = [("next", p) for p in sorted(board["nine"], key=lambda p: -p["n"])] + [("before", b) for b in board["before"]]
    cells = cells[:ROWS_AFTER * 3]
    im = Image.new("RGB", (1080, top + -(-len(cells) // 3) * (ch + gap)), colors["paper"])
    d = ImageDraw.Draw(im)
    d.text((40, 44), board["handle"], font=_env.pil_font(46, "display"), fill=colors["ink"])
    d.text((40, 96), "the next posts above the grid you have now" if board["before"] else "your profile with the next posts in place",
           font=_env.pil_font(26, "text"), fill=colors["muted"])
    for i, (kind, c) in enumerate(cells):
        if kind == "next":
            pic = ImageOps.fit(Image.open(drawn / f"{c['n']:02d}.png").convert("RGB"), (cw, ch), Image.LANCZOS)
        elif c.get("file"):
            pic = ImageOps.fit(Image.open(PUBLIC / c["file"]).convert("RGB"), (cw, ch), Image.LANCZOS)
        else:
            pic = Image.new("RGB", (cw, ch), c["plate"][0])
        im.paste(pic, ((i % 3) * (cw + gap), top + (i // 3) * (ch + gap)))
    im.save(out)


def cmd_render(a):
    board = board_of()
    # the re-exec for Pillow happens here, before the lock: an exec would drop the lock's file
    _env.need("PIL")
    with studio.lock("film") as run:
        return rendered(board, run)


def caption(plan, handle):
    """caption.txt: what to write under the reel, then each post's day and caption, in posting order."""
    film = plan.get("film") or {}
    said = [x.strip().rstrip(".") + "." for x in (film.get("hook"), film.get("ask")) if (x or "").strip()]
    L = ["The reel", "", " ".join(said) if said else f"@{handle}, the next posts.", ""]
    for s in plan.get("slots") or []:
        L += [f"Post {s['n']}, {s.get('date', '')}", "", (s.get("caption") or "").strip(), ""]
    return "\n".join(L).rstrip() + "\n"


def story(src, out):
    """story.png: the reel's closer at the film's size, the Story that sends people to the new grid."""
    shutil.copyfile(src, out)


def rendered(board, run):
    """The render under the run lock: every format and the frames, then the films with their music, the posts and the
    grid after, each made under render/. render/film.json, render/film-report.json and out/review.html go first: they
    speak for the films, and the films are about to change. The made files reach out/ last, each moved onto its name
    once every one is made, the reel last; the report and then render/film.json are published after them, so out/
    never holds a film, a post or a grid of a render that failed or was stopped as if it were finished. The music is
    the master music.json names (music.py master)."""
    sw = critic.run_swap(board)
    if not sw["pass"]:
        for o in sw["objections"]:
            print(f"OBJECTS  {o['test']:8s} {o['at']}: {o['text']}")
        sys.exit("the critic objects to the nine as placed (critic/swap.json): change the plan's places, then storyboard.py draft, pick and render")
    formats = [fmt for fmt in NAMES if fmt in board["boards"]]
    Path("render/film.json").unlink(missing_ok=True)
    Path("render/film-report.json").unlink(missing_ok=True)
    _env.unready()
    Path("out").mkdir(exist_ok=True)
    silent = Path("render/silent")
    silent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(FRAMES, ignore_errors=True)
    FRAMES.mkdir()
    jobs = [studio.video(board["boards"][fmt], silent / NAMES[fmt]) for fmt in formats]
    for fmt in formats:
        for rest, fr in board["rests"].items():
            jobs.append(studio.still(board["boards"][fmt], fr, FRAMES / f"{fmt}-{rest}.png", scale=1))
    rep = studio.render(jobs, "film", run)
    if rep["failed"]:
        studio.publish("film", rep)
        sys.exit("a render job failed (render/film.log, render/film-report.json); run film.py render again to resume it")
    master = (_env.read_json("music.json") or {}).get("master")
    music = False
    muxed = {fmt: silent / f"{Path(NAMES[fmt]).stem}.muxed.mp4" for fmt in formats}
    for fmt in formats:
        music = mux(run, silent / NAMES[fmt], muxed[fmt], board["seconds"], master)
    reel = hashlib.sha256(muxed["reel"].read_bytes()).hexdigest()[:16]
    drawn, after, card, words = Path("render/posts"), Path("render/grid-after.png"), Path("render/story.png"), Path("render/caption.txt")
    posts(board, drawn)
    grid_after(board, drawn, after)
    story(FRAMES / "reel-closer.png", card)
    _env.write_text(words, caption(_env.read_json("plan.json") or {}, board.get("handle")))
    POSTS.mkdir(exist_ok=True)
    names = sorted(f.name for f in drawn.iterdir())
    for name in names:
        os.replace(drawn / name, POSTS / name)
    os.replace(after, AFTER)
    os.replace(card, STORY)
    os.replace(words, CAPTION)
    for fmt in sorted(formats, key=lambda f: f == "reel"):
        os.replace(muxed[fmt], Path("out") / NAMES[fmt])
    studio.publish("film", rep)
    _env.write_json("render/film.json", {"style": board["style"], "board": board["letter"], "hash": board["hash"], "formats": formats, "seconds": board["seconds"],
                                         "render_seconds": rep.get("seconds"), "music": music, "posts": len(board["nine"]), "reel": reel})
    for f in POSTS.iterdir():
        if f.name not in names:
            f.unlink()
    for f in rep.get("findings", []):
        print("finding:", f["text"][:400])
    print(f"wrote {', '.join(str(Path('out') / NAMES[f]) for f in formats)}, out/posts/01..{len(board['nine']):02d}.png, {STORY}, "
          f"{CAPTION}, {AFTER} and {FRAMES}/"
          + ("" if music else " (music.json names no master: the films are silent)"))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    a = ap.parse_args()
    _env.enter_run()
    return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
