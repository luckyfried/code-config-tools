#!/usr/bin/env python3
"""Build a second invented person's 2026 from a folder of real photographs: what an agent pulls from a connected
Instagram account, as gather.py's items.json with the photographs beside it.

USAGE:
    python3 make_seed_person.py DEST PHOTOS

PHOTOS is the seed media folder (scripts/demos/seeds/media in the configurator repository, CC0 photographs named by
subject). DEST is a workspace; it receives pulled/items.json and a copy of every photograph and clip a post names.
Run the kit with `gather.py --pulled pulled`. Nothing in PHOTOS is changed.

The person, Noor Haddad (@noor.haddad), lives in Lisbon and posts the sea, food and friends. Every caption is
written from the photograph it is posted with (the folder's own subject for that file), so a line on screen never
names what the picture under it does not show. The account's people, the photographs that show them, and the intended order:

    person        shown in                                  stretch        voice
    tomas.surf    surf, sunset-beach (never from the front) July-August    short, lowercase, the sea
    joana.lima    selfie (own face)                         March-April    loud, emoji
    rita.clay     hands-pottery, tomatoes (hands only)      May-June       plain, a potter
    lena.reads    portrait (own face)                       January-Feb    dry, books
    ze.do.largo   man-portrait (his face)                   Sep-October    never comments
    ines.e.leo    wedding, couple-beach                     September      a couple, far below

The group photograph is concert (a front row from behind, hands up): tomas, joana, rita and lena tagged in it.
"""
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

HANDLE, NAME = "noor.haddad", "Noor Haddad"
# (month, day, file, caption, tagged, likes, comments): every caption written from its photograph
POSTS = [
    (1, 9, "portrait.jpg", "wrapped in a blanket in the yellow flowers, laughing at something past me @lena.reads", ["lena.reads"], 212, 9),
    (1, 21, "bookshop.jpg", "lost @lena.reads between these shelves for two hours, the bulbs were worth it", ["lena.reads"], 164, 6),
    (2, 3, "living-room.jpg", "the bright flat with every pillow color at once, @lena.reads hosting", ["lena.reads"], 131, 4),
    (2, 14, "snow.jpg", "a wooden cabin in the snow, two days of nothing", [], 140, 3),
    (2, 26, "dolomites.jpg", "out on the green lake in a wooden boat with @lena.reads, mountains all round", ["lena.reads"], 188, 7),
    (3, 6, "selfie.jpg", "@joana.lima grinning at my texts out on the street", ["joana.lima"], 236, 12),
    (3, 18, "coffee.jpg", "the flat white @joana.lima poured, a perfect leaf", ["joana.lima"], 150, 6),
    (3, 29, "birthday-cake.jpg", "chocolate shavings, cherries and two pink candles because @joana.lima refuses to count past two", ["joana.lima"], 201, 10),
    (4, 2, "kids-party.jpg", "a bunch of polka dot balloons against the brick, tied by hand @joana.lima @rita.clay", ["joana.lima", "rita.clay"], 174, 5),
    (4, 15, "flowers.jpg", "red tulips in rows all the way to the sky", [], 122, 2),
    (4, 27, "alfama.jpg", "the painted walls on the way up to the castle", [], 109, 2),
    (5, 8, "hands-pottery.jpg", "@rita.clay's hands on the wheel, that pot is mine now", ["rita.clay"], 227, 11),
    (5, 22, "garden.jpg", "the kitchen garden rows before the heat, @rita.clay knows every bed", ["rita.clay"], 133, 4),
    (6, 4, "tomatoes.jpg", "@rita.clay handing over a bowl of tomatoes, garden gloves still on", ["rita.clay"], 205, 9),
    (6, 19, "picnic.jpg", "white and purple globe flowers, a whole field of them", [], 98, 1),
    (6, 30, "concert.jpg", "front row, hands up and my ears still ringing @tomas.surf @joana.lima @rita.clay @lena.reads",
     ["tomas.surf", "joana.lima", "rita.clay", "lena.reads"], 298, 16),
    (7, 6, "surf.jpg", "@tomas.surf inside the barrel while i screamed from the sand", ["tomas.surf"], 341, 18),
    (7, 14, "ramen.jpg", "shio ramen after the dawn session, @tomas.surf ate two bowls", ["tomas.surf"], 176, 7),
    (7, 25, "road-trip.jpg", "the empty road down to the coast @tomas.surf @joana.lima", ["tomas.surf", "joana.lima"], 190, 6),
    (8, 3, "sunset-beach.jpg", "@tomas.surf walking out with the board in the last light", ["tomas.surf"], 312, 15),
    (8, 12, "desert.jpg", "the sun coming up over the dunes, @tomas.surf awake first", ["tomas.surf"], 158, 5),
    (8, 24, "sneakers.jpg", "green clogs left on the sand, @tomas.surf went in without them", ["tomas.surf"], 117, 4),
    (8, 30, "lisbon-tram.jpg", "the old tram climbing our street", [], 145, 3),
    (9, 5, "wedding.jpg", "@ines.e.leo, the veil and that kiss", ["ines.e.leo"], 260, 14),
    (9, 7, "couple-beach.jpg", "@ines.e.leo alone on the white sand the day after", ["ines.e.leo"], 142, 4),
    (9, 16, "man-portrait.jpg", "the razor man on our corner since before i was born, cap on, pink packets out @ze.do.largo",
     ["ze.do.largo"], 248, 13),
    (9, 28, "market.jpg", "a cart of cabbages under the blue umbrella at the market", [], 120, 2),
    (10, 4, "cat.jpg", "the snowshoe cat on our corner, head tilted", [], 166, 5),
    (10, 11, "graca.jpg", "red roofs all the way to the river from graca", [], 139, 3),
    (2, 8, "city-night.jpg", "rain on the corner at night, every light doubled", [], 101, 1),
    (3, 11, "bairro-alto.jpg", "the fountain in rossio lit up at night", [], 112, 2),
    (5, 1, "bakery.jpg", "the bread wall at the bakery, one of everything", [], 128, 3),
    (5, 15, "belem.jpg", "the tower at belem under a big sky", [], 104, 1),
    (6, 10, "fes.jpg", "a carpet stall in fes, every color hanging", [], 119, 2),
    (7, 2, "mountain-hike.jpg", "blue ridges all the way to the lake", [], 96, 1),
    (8, 18, "rooftop-garden.jpg", "a rooftop garden straight down from the top floor", [], 93, 1),
    (9, 21, "sintra.jpg", "pena palace in yellow and blue tiles", [], 135, 2),
    (10, 1, "skyline.jpg", "the tower lit pink over the city at night", [], 99, 1),
    (10, 8, "train.jpg", "the train window and two empty seats", [], 88, 1),
    (1, 30, "bicycle.jpg", "someone crossing the canal on a bike, black and white", [], 91, 1),
    (6, 25, "dog.jpg", "a black dog pulling at the lead across the grass", [], 107, 2),
]
REELS = [
    (7, 20, "clip-surf.mp4", "@tomas.surf in the barrel, slowed right down", ["tomas.surf"], 402, 21),
    (8, 30, "clip-tram.mp4", "the tram coming down the hill", [], 160, 3),
    (9, 28, "clip-market.mp4", "market morning, the cart rolling past", [], 133, 2),
]
STORIES = [  # (month, day, file, tagged)
    (1, 12, "portrait.jpg", ["lena.reads"]), (2, 20, "dolomites.jpg", ["lena.reads"]),
    (3, 8, "selfie.jpg", ["joana.lima"]), (3, 30, "birthday-cake.jpg", ["joana.lima"]), (4, 3, "kids-party.jpg", ["joana.lima", "rita.clay"]),
    (4, 20, "coffee.jpg", ["joana.lima"]),
    (5, 9, "hands-pottery.jpg", ["rita.clay"]), (6, 5, "tomatoes.jpg", ["rita.clay"]), (5, 23, "garden.jpg", ["rita.clay"]),
    (7, 7, "surf.jpg", ["tomas.surf"]), (7, 15, "ramen.jpg", ["tomas.surf"]), (8, 4, "sunset-beach.jpg", ["tomas.surf"]),
    (8, 13, "desert.jpg", ["tomas.surf"]), (8, 25, "sneakers.jpg", ["tomas.surf"]),
    (9, 17, "man-portrait.jpg", ["ze.do.largo"]), (10, 2, "cat.jpg", ["ze.do.largo"]), (10, 12, "market.jpg", ["ze.do.largo"]),
]
TAGGED_IN = [  # their posts that tag the account: (account, month, day, file, caption, also tagged)
    ("tomas.surf", 7, 26, "road-trip.jpg", "road to the swell with these two", ["joana.lima"]),
    ("tomas.surf", 8, 13, "desert.jpg", "sunrise crew", []),
    ("tomas.surf", 8, 4, "sunset-beach.jpg", "last one out again", []),
    ("joana.lima", 4, 3, "kids-party.jpg", "BALLOONS 🎈🎈", ["rita.clay"]),
    ("joana.lima", 3, 19, "coffee.jpg", "latte art queen (me) ☕", []),
]
RECEIVED = {  # comments each one wrote on the account's posts
    "tomas.surf": ["that wave was all mine and you know it", "dawn patrol tomorrow, no excuses", "you scream louder than the sea",
                   "next swell you're paddling out with me", "two bowls and i'd eat a third", "salt in my hair until october at least",
                   "salt in my ears for a week", "i was inside it and you were screaming, both true", "you're on the sand, i'm in the water, same as always",
                   "best summer the sea ever gave us", "worth the cold water", "sand in the car forever"],
    "joana.lima": ["who said you could post this without asking me 😭", "i'm framing this one for the kitchen", "the leaf was an accident and i'm taking credit ☕",
                   "two candles is the correct number forever 🎂", "my face when i read your texts, every single time 😂",
                   "you take the best photos of me and i hate it", "BALLOONS. obsessed 🎈", "this is my favorite one of us",
                   "never stop texting me paragraphs", "the road trip playlist was mine, for the record"],
    "rita.clay": ["the pot has a crack and i love it more now", "my hands haven't been clean since march", "clay under my nails for a week",
                  "you hold the pot like it might bite you", "tied every balloon with these hands", "come back, the garden misses you",
                  "dirt on my gloves, sun on my neck, perfect", "made with my hands for your table"],
    "lena.reads": ["page 212 and i still don't trust the narrator", "you read faster than me and it's rude", "blanket weather is my whole personality",
                   "two hours was not enough in there", "i rowed, you took the photo, fair trade", "every pillow had a reason"],
    "ines.e.leo": ["we can't stop looking at these"],
}
HER_COMMENTS = {  # comments the account wrote on each one's posts (replies @mention them)
    "tomas.surf": ["see you at the break", "the sunrise one is my favorite", "i'll bring the ramen", "@tomas.surf you were incredible out there",
                   "@tomas.surf only if you carry my towel", "dry board, wet hair, explain", "@tomas.surf next time i'm paddling", "salt forever"],
    "joana.lima": ["queen of balloons", "@joana.lima framing it right now", "you're the best thing on my phone", "@joana.lima paragraphs incoming",
                   "the leaf is perfect", "@joana.lima credit granted"],
    "rita.clay": ["the pot lives on my table now", "@rita.clay the crack is the best part", "save me the tomatoes", "@rita.clay i'm coming back"],
    "lena.reads": ["@lena.reads tell me who did it", "next shelf, next week", "@lena.reads fair trade"],
    "ze.do.largo": ["the best corner in lisbon", "bom dia, ze"],
}
LIKED = ["portra.lisbon", "salt.and.board", "clay.studio.lx", "tasca.diaries", "the.lisbon.light", "film.and.sea"]


def ts(m, d, h=12):
    return int(dt.datetime(2026, m, d, h, tzinfo=dt.timezone.utc).timestamp())


def main():
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2
    dest, photos = Path(sys.argv[1]) / "pulled", Path(sys.argv[2])
    names = {f for _, _, f, *_ in POSTS + REELS + STORIES} | {f for _, _, _, f, _, _ in TAGGED_IN}
    missing = sorted(n for n in names if not (photos / n).exists())
    if missing:
        sys.exit(f"{photos} does not hold {missing}")
    dest.mkdir(parents=True, exist_ok=True)
    for n in sorted(names):
        shutil.copyfile(photos / n, dest / n)
    post = lambda r: {"ts": ts(r[0], r[1]), "caption": r[3], "media": [r[2]], "likes": r[5], "comments": r[6], "tagged": r[4]}
    received, comments = [], []
    for who, lines in RECEIVED.items():
        mine = [p for p in POSTS + REELS if who in p[4]] or POSTS
        for i, text in enumerate(lines):
            p = mine[i % len(mine)]
            received.append({"account": who, "text": text, "ts": ts(p[0], p[1], 14 + i % 6)})
    for who, lines in HER_COMMENTS.items():
        for i, text in enumerate(lines):
            m = 1 + (i * 3 + len(who)) % 10
            comments.append({"account": who, "text": text, "ts": ts(m, 3 + i, 20)})
    items = {
        "source": "instagram account", "handle": HANDLE, "name": NAME,
        "posts": sorted((post(r) for r in POSTS), key=lambda r: r["ts"]),
        "reels": [post(r) for r in REELS],
        "stories": [{"ts": ts(m, d, 9), "media": [f], "tagged": t} for m, d, f, t in STORIES],
        "tagged_in": [{"account": a, "ts": ts(m, d, 18), "caption": c, "media": [f], "tagged": [HANDLE] + t} for a, m, d, f, c, t in TAGGED_IN],
        "likes": [{"account": LIKED[i % len(LIKED)], "ts": ts(1 + i % 10, 1 + i % 27)} for i in range(60)],
        "comments": comments, "received": received,
        "followers": [{"account": a, "ts": ts(1, 1)} for a in list(RECEIVED) + ["ze.do.largo"] + LIKED[:3]],
        "following": [{"account": a, "ts": ts(1, 1)} for a in list(RECEIVED) + ["ze.do.largo"] + LIKED],
    }
    (dest / "items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    print(f"{dest}/items.json: {len(items['posts'])} posts, {len(items['reels'])} reels, {len(items['stories'])} stories, "
          f"{len(items['tagged_in'])} tagged in, {len(received)} comments received, {len(comments)} written; {len(names)} files copied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
