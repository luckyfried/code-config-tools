"""One person's run, as storyboard.py draft leaves it before the boards: studio.json with the story and its
photographs (drawn here, small), taste.json, library.json and palette.json. make(dir, **changes) writes it into `dir`;
`changes` replace taste.json keys. The photographs are drawn only when Pillow is here (HAVE_PIL)."""
import importlib.util
import json
from pathlib import Path

HAVE_PIL = importlib.util.find_spec("PIL") is not None

# (photo, line, pillar, likes, ground rgb, subject (x, y), portrait)
MOMENTS = [
    ("2026-03-19-026-0", "sunday table: lemons, butter, bread.", "table", 140, (186, 95, 69), (0.42, 0.55), True),
    ("2026-09-22-089-0", "laundry lines, shutters, blue doors.", "walk", 119, (114, 114, 58), (0.30, 0.40), True),
    ("2026-01-20-006-0", "first coffee: rain outside, a cornetto, a cortado.", "coffee", 160, (87, 58, 41), (0.55, 0.62), False),
    ("2026-08-18-079-0", "at the market: peaches, figs, green almonds.", "market", 172, (223, 212, 186), (0.50, 0.48), True),
]
HOOK = ("2026-10-06-095-0", (186, 95, 69), (0.30, 0.47))
FEED = [{"hex": "#BA5F45", "name": "terracotta", "share": 0.38}, {"hex": "#DFD4BA", "name": "cream", "share": 0.26},
        {"hex": "#72723A", "name": "olive", "share": 0.19}, {"hex": "#573A29", "name": "chocolate", "share": 0.13}]
CAPTIONS = ["market morning: green almonds, cherries, quince.\n\nwhat's in season where you are?\n#marketmornings",
            "from the table: anchovies, bread, white beans.\n\nwhat are you cooking this week?\n#fromthetable"]


def draw(path, ground, subject, portrait):
    from PIL import Image, ImageDraw
    w, h = (96, 120) if portrait else (120, 96)
    im = Image.new("RGB", (w, h), ground)
    d = ImageDraw.Draw(im)
    x, y = subject[0] * w, subject[1] * h
    d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=tuple(max(0, c - 70) for c in ground))
    d.rectangle((0, 0, w, h // 6), fill=tuple(min(255, c + 40) for c in ground))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=85)


def studio(moments=MOMENTS):
    photos, story = {}, []
    for name, line, pillar, likes, ground, subject, portrait in moments:
        photos[name] = {"file": f"studio/photos/{name}.jpg", "posted": f"studio/posted/{name}.jpg", "aspect": 1.25 if portrait else 0.8, "subject": list(subject), "plain": False}
        story.append({"date": name[:10], "line": line, "pillar": pillar, "people": [], "place": None, "likes": likes, "photo": name})
    photos[HOOK[0]] = {"file": f"studio/photos/{HOOK[0]}.jpg", "posted": f"studio/posted/{HOOK[0]}.jpg", "aspect": 1.25, "subject": list(HOOK[2]), "plain": True}
    return {"handle": "maren.okafor", "name": "Maren Okafor",
            "bio": "home cooking, market mornings and the walk home, three posts a week from my table",
            "statement": "table, market, walk and coffee.", "pillars": ["table", "market", "walk", "coffee"],
            "voice": {"case": "lowercase"}, "photos": photos, "story": story, "hook": HOOK[0]}


def make(d, moments=MOMENTS, **changes):
    d = Path(d)
    if HAVE_PIL:
        for kind in ("photos", "posted"):
            for name, line, pillar, likes, ground, subject, portrait in moments:
                draw(d / "public" / "studio" / kind / f"{name}.jpg", ground, subject, portrait)
            draw(d / "public" / "studio" / kind / f"{HOOK[0]}.jpg", HOOK[1], HOOK[2], True)
    taste = {"ask": True, "style": None, "hook": None, "question": None, "signoff": None,
             "register": {"lowercase": True, "hashtags": ["#fromthetable"]}, "palette": {"feed": FEED},
             "music": {"words": [], "avoid": []}} | changes
    files = {"studio.json": studio(moments), "taste.json": taste, "palette.json": {"feed": FEED},
             "library.json": {"handle": "maren.okafor", "posts": [{"caption": c, "likes": 200 - 10 * i} for i, c in enumerate(CAPTIONS)]}}
    for name, obj in files.items():
        (d / name).write_text(json.dumps(obj))
    return d
