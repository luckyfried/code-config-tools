"""qa.py's story-card check, on cards drawn for the test.

usage: python3 scripts/qa_test.py

In a scratch workspace under $TMPDIR, five different cards pass; a card repeated, a card that differs from another
by a pixel's noise, an empty card, a missing card, a card of the wrong size, and a film.json naming four story
beats each fail, with the reason in the detail.
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qa  # noqa: E402

FAILED = []
FILM = {"stories": ["hook", "a", "dense", "b", "closer"]}


def card(i, size=(1080, 1920)):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", size, (30 + 9 * i, 28, 26))
    d = ImageDraw.Draw(im)
    w, h = size
    d.rectangle((60 + 120 * i, 300 + 160 * i, 60 + 120 * i + 420, 300 + 160 * i + 560), fill=(230, 220, 200))
    d.ellipse((w - 300 - 90 * i, h - 500 - 40 * i, w - 100 - 90 * i, h - 300 - 40 * i), fill=(200, 90, 60))
    return im


def write(cards):
    out = Path("out")
    out.mkdir(exist_ok=True)
    for f in out.glob("story-*.png"):
        f.unlink()
    for n, im in enumerate(cards, 1):
        if im is not None:
            im.save(out / f"story-{n}.png")


def case(what, cards, want, film=FILM, says=None):
    write(cards)
    ok, detail = qa.stories_check(film)
    good = ok == want and (says is None or says in detail)
    print(("ok   " if good else "FAIL ") + f"{what}: {'pass' if ok else 'fail'} ({detail})")
    if not good:
        FAILED.append(what)


def main():
    from PIL import Image
    base = Path(os.environ.get("TMPDIR") or tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base, prefix="qa-test-") as ws:
        os.chdir(ws)
        five = [card(i) for i in range(5)]
        case("five different cards", five, True)
        case("a card repeated", five[:4] + [five[1]], False, says="the same picture: story-2.png and story-5.png")
        noisy = five[2].copy()
        noisy.putpixel((500, 900), (255, 255, 255))
        case("a card that differs from another by one pixel", five[:4] + [noisy], False, says="story-3.png and story-5.png")
        case("an empty card", five[:4] + [Image.new("RGB", (1080, 1920), (40, 38, 36))], False, says="empty frames ['story-5.png']")
        case("a missing card", five[:4] + [None], False, says="missing ['story-5.png']")
        case("a card of the wrong size", five[:4] + [card(4, (1080, 1080))], False, says="(1080, 1080)")
        case("film.json naming four story beats", five, False, film={"stories": FILM["stories"][:4]}, says="names 4 story beats")
    print(f"{'FAILED' if FAILED else 'passed'}: {len(FAILED)} failing")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
