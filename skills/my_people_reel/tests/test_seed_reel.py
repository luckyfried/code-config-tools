"""A two-person year run from gather to the storyboard, one of its frames rendered by the studio.

A landscape photograph fills the frame of a look whose card lays it on the whole frame: at the frame where the camera
arrives on the card, the frame's foot is the photograph and no ground shows under it. A landscape photograph of them together opens the
film whole, a tag on each head. With no username in the data nothing stands in for one: no "@you" or "@me" in any
format's board (the story cards are its frames), the caption, the brief or the review page, and the page says where
the username goes. Each card is the post its person's comment was left on (the post the comment names, else the
person's latest post before it), and the card's line keeps the @name written in it. A framed photograph is mounted
the way its look's card says and never over a blurred copy of itself, the three looks mount it three ways, and in
the looks that fill the frame with it the photograph runs from side to side and down to the frame's foot. Each
look sets every line in its own card's two faces. Each clip request is one shot of its own photograph: the shot the
agent wrote for it, the lens, the height and the light measured from it, the camera move those choose, its beat's
length and a seamless loop, and never a person's words. The review page shows the two looks not picked and how
the film was made, and never a score: the critics' scores stay in brief.md.

    python3 -I -m unittest discover -s S/tests -p test_seed_reel.py
"""
import contextlib
import copy
import datetime as dt
import html
import io
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw, ImageStat

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import _env  # noqa: E402
import style  # noqa: E402

ANA = "best swim of the summer and the water was freezing"
BEN = "@ana.costa swore the river was warm, still worth every step"
LAKE = (1800, 1000)


def ts(m, d, h=12):
    return int(dt.datetime(2026, m, d, h, tzinfo=dt.timezone.utc).timestamp())


def face(dr, cx, cy, r):
    dr.ellipse([cx - r, cy - r * 1.2, cx + r, cy + r * 1.2], fill=(214, 168, 132))
    for ex in (cx - r * 0.4, cx + r * 0.4):
        dr.ellipse([ex - r * 0.12, cy - r * 0.35, ex + r * 0.12, cy - r * 0.11], fill=(30, 20, 20))


def landscape(path, size, fx, faces=1):
    """A mid-grey landscape, a face (or a row of them) from `fx` across, and a white stripe down each side."""
    w, h = size
    im = Image.new("RGB", size, (96, 96, 96))
    dr = ImageDraw.Draw(im)
    for i in range(faces):
        face(dr, int(w * (fx + 0.2 * i)), int(h * 0.4), int(h * 0.12))
    edge = w // 40
    dr.rectangle([0, 0, edge, h], fill=(255, 255, 255))
    dr.rectangle([w - edge - 1, 0, w, h], fill=(255, 255, 255))
    im.save(path, quality=92)


def portrait(path, shade):
    im = Image.new("RGB", (1080, 1350), shade)
    face(ImageDraw.Draw(im), 540, 520, 170)
    im.save(path, quality=92)


def seed(d):
    """pulled/items.json with no username: ana.costa's comment names the June lake post it was left on, and ben.ito's
    comment, the day after the March river post, names no post; each has a later portrait post of their own."""
    d.mkdir(parents=True)
    landscape(d / "lake.jpg", LAKE, 0.15)
    landscape(d / "river.jpg", (1600, 1000), 0.85)
    landscape(d / "two.jpg", (1600, 1000), 0.4, faces=2)
    portrait(d / "ana.jpg", (170, 60, 50))
    portrait(d / "ben.jpg", (50, 60, 160))
    for i in range(4):
        Image.new("RGB", (800, 1000), (40 + 50 * i, 90, 160 - 30 * i)).save(d / f"view{i}.jpg")

    def post(m, day, f, cap, tagged):
        return {"ts": ts(m, day), "caption": cap, "media": [f], "likes": 80, "comments": 2, "tagged": tagged}
    posts = [post(3, 10, "river.jpg", "first warm day at the river", ["ben.ito"]),
             post(4, 20, "ben.jpg", "@ben.ito fixing the bike again", ["ben.ito"]),
             post(6, 12, "lake.jpg", "the lake at dusk", ["ana.costa"]),
             post(7, 5, "ana.jpg", "@ana.costa and the best tomatoes", ["ana.costa"]),
             post(9, 1, "two.jpg", "the two of them @ana.costa @ben.ito", ["ana.costa", "ben.ito"])]
    posts += [post(1 + 2 * i, 3 + i, f"view{i}.jpg", f"the view, part {i + 1}", []) for i in range(4)]
    received = [{"account": "ana.costa", "text": ANA, "ts": ts(6, 13, 9), "on": "lake.jpg"},
                {"account": "ben.ito", "text": BEN, "ts": ts(3, 11, 9)}]
    import json
    (d / "items.json").write_text(json.dumps({"source": "instagram account", "posts": sorted(posts, key=lambda p: p["ts"]),
                                              "received": received}))


def said(beat):
    """The type a beat puts on screen, line by line, and its tags."""
    words = [x["text"] if isinstance(x, dict) else x for la in beat["layers"] if la["kind"] == "Words" for x in la["lines"]]
    return words, [t["text"] for la in beat["layers"] if la["kind"] == "Tags" for t in la.get("tags", [])]


class SeedReel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = Path(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")))
        cls.addClassCleanup(shutil.rmtree, cls.ws, True)
        seed(cls.ws / "pulled")
        env = dict(os.environ, MPR_WORKSPACE=str(cls.ws))
        env.pop("MPR_RUN", None)

        def step(script, *args):
            p = subprocess.run([sys.executable, "-I", str(KIT / "scripts" / script), *args], cwd=cls.ws, env=env,
                               capture_output=True, text=True)
            if p.returncode:
                raise AssertionError(f"{script} {' '.join(args)}: exit {p.returncode}\n{p.stdout[-1500:]}{p.stderr[-1500:]}")
        step("gather.py", "--year", "2026", "--door", "instagram_account=open: pulled for the test")
        step("research.py", "--people", "ana.costa,ben.ito")
        cls.run_dir = cls.ws / "build" / (cls.ws / "build" / "current").read_text().strip()
        shutil.copyfile(cls.run_dir / "taste.draft.md", cls.run_dir / "taste.md")
        step("cast.py", "draft")
        step("cast.py", "match")
        step("storyboard.py", "draft")

    def setUp(self):
        cwd = os.getcwd()
        os.chdir(self.run_dir)
        self.addCleanup(os.chdir, cwd)

    def board(self, kind, look="scrapbook"):
        import boards
        import storyboard
        ctx = boards.Ctx()
        return ctx, boards.layout(storyboard.load(look), ctx, kind)

    def test_a_landscape_photograph_fills_the_frame_to_its_foot(self):
        tools = _env.tools()
        if not (tools.get("chromium") and tools.get("dist")):
            self.skipTest("no Chromium or no built composition here")
        import boards
        import studio
        # a look whose card lays a landscape photograph on the whole frame
        _, board = self.board("reel", "analog-home-movie")
        i = next(i for i, beat in enumerate(board["beats"]) if beat.get("person") == "ana.costa")
        # the camera standing on the card as it arrives, before its slow push toward the tag
        start = sum(beat["frames"] for beat in board["beats"][:i])
        job = studio.still(board, start + 3, Path("frames-test/ana.png"))
        rep = studio.render([job], "seed-test")
        self.assertEqual(rep.get("failed"), 0, rep)
        frame = Image.open(job["out"]).convert("L")
        W, H = frame.size
        # the lake's grey runs down to the frame's foot: the rows just over the foot read as the rows under the face
        def luma(y0, y1):
            return ImageStat.Stat(frame.crop((W // 2 - 120, round(y0 * H), W // 2 + 120, round(y1 * H)))).mean[0]
        lake, foot = luma(0.80, 0.84), luma(0.92, 0.96)
        self.assertLess(abs(foot - lake), 30, f"foot {foot:.0f}, lake {lake:.0f}")

    def test_a_landscape_group_opens_the_film_whole_with_a_tag_on_each_head(self):
        _, board = self.board("reel")
        hook = board["beats"][0]
        cut = next(la for la in hook["layers"] if la["kind"] == "Cut")
        self.assertEqual(cut["photo"]["role"], "group")
        # the scrapbook tapes it to the page as a print, the width it shows inside the frame
        self.assertGreaterEqual(cut["crop"][0], 0)
        self.assertLessEqual(cut["crop"][1], 1080)
        self.assertEqual(sorted(said(hook)[1]), ["@ana.costa", "@ben.ito"])

    def test_a_year_with_no_username_prints_no_stand_in_for_one(self):
        import deliver
        import gather
        import qa
        for text in ("@you · 2026", "@me · 2026"):
            self.assertIsNotNone(qa.PLACEHOLDER.search(text), text)
        for text in ("with @youssef", "with @me.lissa"):
            self.assertIsNone(qa.PLACEHOLDER.search(text), text)
        lib = _env.read_json("library.json")
        self.assertIsNone(lib.get("handle"))
        self.assertIn(gather.NO_HANDLE, lib["assumptions"])
        for kind in ("reel", "square", "wide"):
            _, board = self.board(kind)
            texts = [t for beat in board["beats"] for part in said(beat) for t in part]
            self.assertEqual([m.group(0) for t in texts for m in qa.PLACEHOLDER.finditer(t)], [], kind)
            self.assertEqual(said(board["beats"][0])[0][0], "2026", kind)
        _env.write_json("winner.json", {"board": "scrapbook", "name": "tagged", "look": "Scrapbook", "by": "the person", "why": ""})
        _env.write_json("cards.json", {"cards": []})
        Path("out").mkdir(exist_ok=True)
        Path("out/film.mp4").write_bytes(b"the reel render made")
        with mock.patch.object(deliver.qa, "gate", lambda run: []), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.deliver(types.SimpleNamespace(spawn=subprocess.run)), 0)
        page = Path("out/review.html").read_text()
        self.assertIn("my people 2026", page)
        self.assertIn(html.escape(gather.NO_HANDLE), page)
        # out/ holds the deliverables alone, and the page is the film's cover; how it was made stays in the run
        self.assertLessEqual({p.name for p in Path("out").iterdir()}, qa.DELIVERABLES)
        self.assertIn('poster="cover.png"', page)
        self.assertNotIn("storyboards/", page)
        for f in ("out/review.html", "out/caption.md", "brief.md"):
            self.assertIsNone(qa.PLACEHOLDER.search(Path(f).read_text()), f)

    def test_the_review_page_shows_the_other_two_looks_and_never_a_score(self):
        import deliver
        import storyboard
        looks = storyboard.looks()
        for t in looks:
            Image.new("RGB", (360, 210), "#557799").save(storyboard.sb_path(t).parent / "sheet.png")
        scores = {r: 4 for r in ("R1", "R2", "R3", "R4", "R5", "R6")}
        _env.write_json("critic/cut-1.json", {"round": 1, "film": "abc", "critics": {
            c: {"boards": {"film": {"scores": scores, "paragraph": " ".join(["the cut reads this way from its strip, its rests, its cue tiles and its requests"] * 3)}}} for c in ("motion_designer", "person")}})
        _env.write_json("vote/order.json", {"order": list(looks), "totals": {t: 100 - i for i, t in enumerate(looks)}})
        self.addCleanup(shutil.rmtree, self.run_dir / "critic", True)
        self.addCleanup(os.unlink, self.run_dir / "vote" / "order.json")
        _env.write_json("winner.json", {"board": looks[0], "name": "tagged", "look": "Scrapbook", "by": "taste",
                                        "why": "Their feed is paper, tape and handwriting"})
        _env.write_json("cards.json", {"cards": []})
        Path("out").mkdir(exist_ok=True)
        Path("out/film.mp4").write_bytes(b"the reel render made")
        with mock.patch.object(deliver.qa, "gate", lambda run: []), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(deliver.deliver(types.SimpleNamespace(spawn=subprocess.run)), 0)
        page = Path("out/review.html").read_text()
        self.assertIn("Prefer another look? Say 'make the second one'", page)
        for t in looks[1:]:
            self.assertTrue(Path("out/looks", f"{t}.png").exists(), t)
            self.assertIn(html.escape(style.card(t)["name"]), page)
        self.assertFalse(Path("out/looks", f"{looks[0]}.png").exists())
        self.assertIn("How it was made", page)
        self.assertIn("chosen because their feed is paper, tape and handwriting", page)
        for word in ("critic", "score", "panel", " of 30", "R1", "the bar"):
            self.assertNotIn(word, page, word)
        # the scores stay in the run, with the person who asked how it was made
        brief = Path("brief.md").read_text()
        self.assertIn("R1 4", brief)
        self.assertIn("against the bar", brief)

    def test_each_look_sets_every_line_in_its_cards_two_faces_and_every_line_rests_level(self):
        """Each look's display face for the stamps and the title, and for every person's words the face its card's
        line names, in every format: the scrapbook hand-letters them; every line rests level but the scrapbook's
        captions and title, which turn with the hand as its card says, and a month stamped low beside its keepsake,
        which turns the other way from the keepsake; the three looks share no face."""
        import board_drive as bd
        import style
        files = {}
        for look in ("scrapbook", "analog-home-movie", "kinetic-type"):
            card = style.card(look)
            faces, spec = card["faces"], card["photo"]["line"]
            turn = {0, spec.get("rotate") or 0}
            for kind in ("reel", "square", "wide"):
                _, board = self.board(kind, look)
                lines = [ln for beat in board["beats"] for la in beat["layers"] if la["kind"] == "Words" for ln in la["lines"]]
                words = {ln["file"] for ln in lines if ln.get("name", "").startswith("said-")}
                self.assertEqual(words, {faces[spec["face"]]["file"]}, (look, kind))
                self.assertLessEqual({ln["file"] for ln in lines}, {faces["display"]["file"], faces["text"]["file"]}, (look, kind))
                self.assertLessEqual({ln.get("rotate") or 0 for ln in lines if not ln.get("low")}, turn, (look, kind))
                self.assertLessEqual({abs(ln["rotate"]) for ln in lines if ln.get("low")}, {bd.KEEPSAKE_STAMP_TURN}, (look, kind))
                files.setdefault(look, set()).update(ln["file"] for ln in lines)
        self.assertEqual(files["scrapbook"] & files["analog-home-movie"], set())
        self.assertEqual(files["scrapbook"] & files["kinetic-type"], set())
        self.assertEqual(files["analog-home-movie"] & files["kinetic-type"], set())

    def test_each_card_is_the_post_its_comment_was_left_on_and_keeps_the_name_in_it(self):
        ctx, board = self.board("reel")
        cards = {beat["person"]: beat for beat in board["beats"] if beat.get("comp") == "person"}
        self.assertEqual(sorted(cards), ["ana.costa", "ben.ito"])
        for h, day, line, month in (("ana.costa", "2026-06-12", ANA, "june"), ("ben.ito", "2026-03-10", BEN, "march")):
            words, tags = said(cards[h])
            role = next(la for la in cards[h]["layers"] if la["kind"] == "Cut")["photo"]["role"]
            src = Path(ctx.cast["people"][h][int(role.rsplit("-", 1)[1])]["file"])
            self.assertTrue(src.name.startswith(day), f"{h}'s card is {src.name}")
            self.assertIn(line, " ".join(words))
            self.assertIn(month, words)
            self.assertEqual(tags, [f"@{h}"])

    def test_a_framed_photograph_is_mounted_the_way_its_looks_card_says_and_never_over_its_blur(self):
        """ana's landscape photograph is framed: the scrapbook's print carries the band the photograph spans and its
        mount; the kinetic and home-movie cards lay the band itself edge to edge over the whole frame, so none of its blur
        shows; no card has a blurred backing, and the three looks frame it three ways."""
        ways = set()
        for look in ("scrapbook", "analog-home-movie", "kinetic-type"):
            ctx, board = self.board("reel", look)
            cut = next(la for beat in board["beats"] for la in beat["layers"] if la["kind"] == "Cut" and beat.get("person") == "ana.costa")
            photo = cut["photo"]
            self.assertNotIn("backing", photo, look)
            ways.add((photo.get("mount"), cut["say"], cut["field"]))
            if look == "scrapbook":
                self.assertIn("band", photo, look)
                self.assertIn("mount", photo, look)
            else:
                b0, b1 = ctx.photos.band[photo["role"]]
                x, y, w, h = cut["place"]
                self.assertLessEqual(x, 0, look)
                self.assertGreaterEqual(x + w, 1080, look)
                self.assertLessEqual(round(y + b0 * h), 0, look)
                self.assertGreaterEqual(round(y + b1 * h), 1919, look)
        self.assertEqual(len(ways), 3, ways)

    def test_each_clip_request_is_one_shot_of_its_own_photograph(self):
        """Each beat but the closer asks for one shot of its own photograph, opening on the shot the cast wrote for it,
        each with its lens, light, length and loop and the camera move its own lens, height and light choose; nothing
        asks for a shot of a blurred field."""
        import board_drive
        shot = "hair lifting off the shoulders in the wind off the water as the dusk light fades"
        cast = _env.read_json("cast.json")
        self.addCleanup(_env.write_json, "cast.json", copy.deepcopy(cast))
        cast["people"]["ana.costa"][0]["shot"] = shot
        _env.write_json("cast.json", cast)
        ctx, board = self.board("reel")
        clips = board["clips"]
        beats = {b["id"]: b for b in board["beats"]}
        shots = clips
        self.assertEqual([c["beat"] for c in shots], [b["id"] for b in board["beats"] if b["id"] != "closer"])
        self.assertEqual(shots[0]["role"], "the world the film opens in")
        self.assertFalse(any("backing" in c["image"] for c in clips))
        prompts = [c["prompt"] for c in clips]
        self.assertEqual(len(set(prompts)), len(prompts))
        ana = next(c for c in shots if beats[c["beat"]].get("person") == "ana.costa")
        self.assertTrue(ana["prompt"].startswith(shot), ana["prompt"])
        for c in clips:
            self.assertEqual(c["seconds"], round(beats[c["beat"]]["frames"] / 30, 1))
            for part in ("mm lens", " light", f"{c['seconds']} seconds", "seamless loop"):
                self.assertIn(part, c["prompt"], c["prompt"])
            for words in (ANA, BEN, "the person this photograph's tag points at"):
                self.assertNotIn(words, c["prompt"])
        for c in shots:
            self.assertIn("the camera ", c["prompt"])
        for c in shots:
            moves = [m for m in board_drive.CLIP_MOVES.values() if m[1:] in c["prompt"]]
            self.assertEqual(len(moves), 1, c["prompt"])

    def test_the_light_a_clip_asks_for_is_measured_from_its_photograph(self):
        """The light in a clip request reads the photograph: a gray one is black and white, a picture lit from its left
        says so, a dark one with a bright rim is lit from behind, a warm bright one is warm and bright, and a stage lit
        violet beside a warm spot names both colors, never the red between them; no two of them read the same."""
        import board_drive
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        gray = Image.linear_gradient("L").resize((200, 300)).convert("RGB")
        side = Image.new("RGB", (200, 300), (40, 60, 90))
        ImageDraw.Draw(side).rectangle((0, 0, 70, 300), fill=(230, 220, 200))
        rim = Image.new("RGB", (200, 300), (230, 200, 150))
        ImageDraw.Draw(rim).rectangle((25, 25, 175, 275), fill=(30, 25, 20))
        warm = Image.new("RGB", (200, 300), (250, 200, 120))
        stage = Image.new("RGB", (200, 300), (120, 60, 200))
        ImageDraw.Draw(stage).rectangle((100, 0, 200, 300), fill=(240, 180, 90))
        said = {}
        for name, im in (("gray", gray), ("side", side), ("rim", rim), ("warm", warm), ("stage", stage)):
            im.save(d / f"{name}.jpg")
            said[name] = board_drive.light_of(str(d / f"{name}.jpg"), (0.0, 1.0))
        self.assertIn("black-and-white", said["gray"])
        self.assertIn("from the left", said["side"])
        self.assertIn("from behind", said["rim"])
        self.assertIn("bright warm", said["warm"])
        self.assertIn("magenta and warm amber", said["stage"].replace("warm amber and magenta", "magenta and warm amber"))
        self.assertNotIn("red", said["stage"])
        self.assertEqual(len(set(said.values())), 5, said)


if __name__ == "__main__":
    unittest.main()
