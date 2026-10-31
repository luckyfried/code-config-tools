"""What the reel and the story cards share: the frame, its safe area, a card's length, and the pulse a board is timed
in: its music's tempo, doubled when that tempo is under SLOW so a slow song's boards still cut on its half beats."""
W, H, FPS = 1080, 1920, 30
SAFE = {"top": 250, "bottom": 340, "left": 72, "right": 72}
CARD = 450  # frames: a card is 15 s
SLOW = 90


def tempo_of(card):
    """The music's tempo for a card (the middle of its recipe's range, whole) and the pulse its board is timed in."""
    import json
    from pathlib import Path
    book = json.loads((Path(__file__).resolve().parents[2] / "music" / "recipes.json").read_text())
    rid = card["music"] if card["music"] in book["recipes"] else book["default"]
    lo, hi = book["recipes"][rid]["tempo"]
    bpm = round((lo + hi) / 2)
    return bpm, bpm * 2 if bpm < SLOW else bpm
