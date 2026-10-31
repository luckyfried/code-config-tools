#!/usr/bin/env python3
"""One person's year on Instagram as the "Download your information" export, made from a book and real photographs.

USAGE:
    python3 make_export.py BOOK DEST

BOOK is a JSON file in books/ (tomas.json: a year of travel; ines.json: a year at home); the photographs it names are
in photos/ beside it (photos/SOURCES.md names where each comes from). DEST is a workspace; it receives instagram-<handle>-<exported>/ in the export's JSON layout:
    personal_information/personal_information/personal_information.json     (username and name)
    your_instagram_activity/content/posts_1.json                             (every post, caption, media, time)
    logged_information/past_instagram_insights/posts.json                    (likes and comments per post)
    media/posts/YYYYMM/*.jpg

Every month of the book is `posts` posts. Its photograph is the month's own post, with the book's caption and likes:
the caption is what happened that month in the person's voice, the first sentence the line they would say, the people
tagged with @ and the places named, and it is the month's longest. The others are details of the same photograph
(crops of it), captioned shorter from the book's `more` list and liked less, so each month's own photograph is
unambiguous. The captions agree with the photographs: a book whose caption contradicts its photograph is fixed in the
book.
Strings are written the way Meta writes them (UTF-8 bytes escaped as latin-1). Needs Pillow.
"""
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

CROPS = [(0.0, 0.0, 0.62, 0.62), (0.38, 0.38, 1.0, 1.0), (0.2, 0.15, 0.8, 0.75), (0.0, 0.35, 0.6, 0.95),
         (0.4, 0.0, 1.0, 0.6), (0.1, 0.25, 0.9, 0.85)]


def meta(s):
    return s.encode("utf-8").decode("latin-1")


def stamp(year, month, day, hour):
    return int(dt.datetime(year, month, day, hour, tzinfo=dt.timezone.utc).timestamp())


def detail(src, box, dst):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im = im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    im.thumbnail((1080, 1080))
    im.save(dst, quality=86)


def main():
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2
    book, dest = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2])
    photos = Path(__file__).resolve().parent / "photos"
    year, handle = book["year"], book["handle"]
    root = dest / f"instagram-{handle}-{book['exported']}"
    shutil.rmtree(root, ignore_errors=True)
    posts, insights = [], []
    for mo in book["months"]:
        m, n = mo["month"], mo["posts"]
        folder = root / "media" / "posts" / f"{year}{m:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        src = photos / mo["photo"]
        days = [1 + (i * 27) // max(1, n) for i in range(n)]
        hero = n // 2
        for i in range(n):
            name = f"{year}{m:02d}{days[i]:02d}_{i:02d}.jpg"
            if i == hero:
                shutil.copyfile(src, folder / name)
                caption, likes = mo["caption"], mo["likes"]
            else:
                detail(src, CROPS[i % len(CROPS)], folder / name)
                more = mo.get("more") or [mo["caption"]]
                caption, likes = more[i % len(more)], int(mo["likes"] * (0.35 + 0.04 * (i % 9)))
            uri = f"media/posts/{year}{m:02d}/{name}"
            ts = stamp(year, m, days[i], 9 + (i * 5) % 12)
            posts.append({"media": [{"uri": uri, "creation_timestamp": ts, "title": ""}], "creation_timestamp": ts,
                          "title": meta(caption)})
            insights.append({"media_map_data": {"Media Thumbnail": {"uri": uri}},
                             "string_map_data": {"Likes": {"value": str(likes)}, "Comments": {"value": str(likes // 23)}}})
    act = root / "your_instagram_activity" / "content"
    act.mkdir(parents=True, exist_ok=True)
    (act / "posts_1.json").write_text(json.dumps(posts, indent=1))
    ins = root / "logged_information" / "past_instagram_insights"
    ins.mkdir(parents=True, exist_ok=True)
    (ins / "posts.json").write_text(json.dumps({"organic_insights_posts": insights}, indent=1))
    pi = root / "personal_information" / "personal_information"
    pi.mkdir(parents=True, exist_ok=True)
    (pi / "personal_information.json").write_text(json.dumps({"profile_user": [{"string_map_data": {
        "Username": {"value": handle}, "Name": {"value": meta(book["name"])}}}]}, indent=1))
    print(f"{root}: {len(posts)} posts over {len(book['months'])} months")
    return 0


if __name__ == "__main__":
    sys.exit(main())
