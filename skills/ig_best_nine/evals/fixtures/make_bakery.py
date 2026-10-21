#!/usr/bin/env python3
"""A small bakery's 2026 on Instagram, as the "Download your information" export, naming photographs it does not hold.

USAGE:
    python3 make_bakery.py DEST PHOTOS

DEST is a folder (a workspace). It receives instagram-cornerloaf-2026-10-18/ with the account's username, its posts
(posts_1.json) and their likes and comments (past_instagram_insights/posts.json). Every post names a photograph of
PHOTOS by its file name and no media is copied, so the run finds the photographs only through BEST_NINE_PHOTOS (or
gather.py --photos) pointing at PHOTOS: the case of a person whose posts and photographs live in different places.

The nine most-liked are the bakery's nine in S/tests/cornerloaf.json, with their captions, days and likes; the two at
188 likes are told apart by comments (peach tart 12, spring menu 9). Every other photograph in PHOTOS is one more post
of the year, under 150 likes, so the nine are unambiguous. Only the file names of PHOTOS are read.
"""
import datetime as dt
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
COMMENTS = {7: 12, 8: 9}
FILLER = ["tuesday bake", "new flour came in", "the morning rack", "back from the market", "rye is back",
          "the counter at 7", "out of the oven", "the shop at noon", "saturday line", "a slow proof"]


def stamp(year, doy, hour=12):
    return int((dt.datetime(year, 1, 1, hour, tzinfo=dt.timezone.utc) + dt.timedelta(days=doy - 1)).timestamp())


def main():
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2
    dest, photos = Path(sys.argv[1]), Path(sys.argv[2])
    book = json.loads((KIT / "tests" / "cornerloaf.json").read_text())
    year, handle = book["year"], book["handle"].lstrip("@")
    nine = {Path(p["file"]).name: p for p in book["posts"]}
    names = sorted(f.name for f in photos.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic"))
    missing = sorted(set(nine) - set(names))
    if missing:
        sys.exit(f"{photos} does not hold {missing}")
    root = dest / f"instagram-{handle}-2026-10-18"
    act = root / "your_instagram_activity" / "content"
    ins = root / "logged_information" / "past_instagram_insights"
    pi = root / "personal_information" / "personal_information"
    for d in (act, ins, pi):
        d.mkdir(parents=True, exist_ok=True)
    rows = []
    others = [n for n in names if n not in nine]
    for name, p in nine.items():
        rows.append((stamp(year, p["doy"]), name, p["caption"], p["likes"], COMMENTS.get(p["rank"], round(p["likes"] / 30))))
    for i, name in enumerate(others):
        doy = 12 + i * 280 // max(1, len(others))
        rows.append((stamp(year, doy, 9), name, FILLER[i % len(FILLER)], 48 + (i * 37) % 95, 1 + i % 5))
    rows.sort()
    posts = [{"media": [{"uri": f"media/posts/{dt.datetime.fromtimestamp(ts, dt.timezone.utc):%Y%m}/{name}",
                         "creation_timestamp": ts, "title": cap}], "creation_timestamp": ts, "title": cap}
             for ts, name, cap, _, _ in rows]
    insights = [{"media_map_data": {"Media Thumbnail": {"uri": p["media"][0]["uri"], "creation_timestamp": ts}},
                 "string_map_data": {"Likes": {"value": str(likes)}, "Comments": {"value": str(comments)}}}
                for p, (ts, _, _, likes, comments) in zip(posts, rows)]
    (act / "posts_1.json").write_text(json.dumps(posts, indent=1))
    (ins / "posts.json").write_text(json.dumps({"organic_insights_posts": insights}, indent=1))
    (pi / "personal_information.json").write_text(json.dumps(
        {"profile_user": [{"string_map_data": {"Username": {"value": handle}, "Name": {"value": "Corner Loaf"}}}]}, indent=1))
    print(f"wrote {root}: {len(posts)} posts, the nine naming photographs in {photos}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
