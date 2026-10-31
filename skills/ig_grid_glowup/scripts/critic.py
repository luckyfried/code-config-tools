#!/usr/bin/env python3
"""The kit's critic as a check: the swap test on the board's nine as placed.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/critic.py swap      # the nine as the board places them -> critic/swap.json; exit 1 on an objection

The swap test, on the nine as placed: a photograph placed by what it is cannot be swapped for another.
  place     the plan sets a calm photograph and a busy one on alternate cells; every calm photograph is calmer than
            each busy photograph beside it (above, below, left or right); a pair that breaks it could swap.
Detail is the mean edge strength of the photograph as the grid shows it (its 3:4 cell crop), 120x160 grey. Each
objection names the frame the calm post lands on in the reel. film.py render runs the test before it renders anything;
the critics' scores of the boards and the film are their own, written by eye (vote.py).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402


def detail(path, crop=None):
    """Mean edge strength of the photograph, or of its [x, y, w] 3:4 crop, at 120x160 grey (0 to 1)."""
    _env.need("PIL")
    from PIL import Image, ImageFilter, ImageStat
    im = Image.open(path).convert("L")
    if crop:
        W, H = im.size
        x, y, w = crop
        h = min(1.0, w * W * 4 / 3 / H)
        im = im.crop((round(x * W), round(y * H), round((x + w) * W), round((y + h) * H)))
    im = im.resize((120, 160), Image.BILINEAR).filter(ImageFilter.FIND_EDGES)
    return round(ImageStat.Stat(im.crop((1, 1, 119, 159))).mean[0] / 255, 4)


def beside(slot, m):
    """The slots beside a slot of the nine (or fewer) on a three-column grid: above, below, left and right."""
    r, c = divmod(slot, 3)
    out = [slot - 3, slot + 3] + ([slot - 1] if c > 0 else []) + ([slot + 1] if c < 2 else [])
    return [s for s in out if 0 <= s < m]


def swap(photos, lands=None):
    """The swap test on the nine: photos are {n, file, place, crop}; post n sits on slot m - n; lands maps n to the
    frame it lands on."""
    obj, nums = [], {}
    m = len(photos)
    at = lambda n: f"frame {lands[n]} (post {n} lands)" if lands and n in lands else f"post {n}"
    by_slot = {m - p["n"]: p for p in photos}
    for p in photos:
        nums[p["n"]] = {"detail": detail(p["file"], p.get("crop")), "place": p.get("place")}
    for slot, b in by_slot.items():
        if b.get("place") != "busy":
            continue
        for s in beside(slot, m):
            c = by_slot.get(s)
            if c and c.get("place") == "calm" and nums[c["n"]]["detail"] >= nums[b["n"]]["detail"]:
                obj.append({"test": "place", "at": at(c["n"]),
                            "text": f"post {c['n']} (calm, {nums[c['n']]['detail']:.3f}) is no calmer than post {b['n']} beside it (busy, {nums[b['n']]['detail']:.3f}): the two could swap"})
    return nums, obj


def photos_of(board):
    return [{"n": p["n"], "file": str(Path("public") / p["file"]), "place": board["places"].get(str(p["n"])), "crop": p["crop34"]}
            for p in board["nine"] if (Path("public") / p["file"]).exists()]


def lands_of(board):
    """The frame each post of the plan lands on its cell in the reel: its seat, in the reel's beats."""
    reel = board["boards"]["reel"]
    pulse = reel["format"]["fps"] * 60 / reel["bpm"]
    return {b["layers"][0]["n"]: round(b["layers"][0]["times"]["seat"] * pulse) for b in reel["beats"] if b["id"].startswith("post-")}


def run_swap(board):
    nums, obj = swap(photos_of(board), lands_of(board))
    res = {"pass": not obj, "swap": nums, "objections": obj}
    _env.write_json("critic/swap.json", res)
    return res


def cmd_swap(a):
    board = _env.read_json("board.json")
    if not board:
        sys.exit("board.json is missing: run storyboard.py draft, sheets and pick first")
    res = run_swap(board)
    for o in res["objections"]:
        print(f"OBJECTS  {o['test']:8s} {o['at']}: {o['text']}")
    print(f"critic swap: {len(res['swap'])} photographs placed by detail; " + ("passes" if res["pass"] else f"{len(res['objections'])} objections")
          + " -> critic/swap.json")
    return 0 if res["pass"] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["swap"])
    a = ap.parse_args()
    _env.enter_run()
    return cmd_swap(a)


if __name__ == "__main__":
    sys.exit(main())
