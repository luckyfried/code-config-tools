"""The board builder: their month (month.json, with the moments the agent picked into taste.json) composed into the
boards the studio compositions render. A run drafts three boards, one a style (compose/style.py: TRIO, or the style the
person named and the two that differ most from it); each is this kit's story of the month, the reel
(compose/reel.py) and the story cards (compose/stories.py), one card a moment, every size and position computed from
their photographs, their words and their days, drawn in one card's faces, colors, moves, easing, finish, music and
closer (compose/look.py)."""
from . import look, style
from .common import FPS, H, W, tempo_of
from .month import Month
from .style import TRIO, trio


def board(name, month):
    """The board of one style: the system, the story cards with their shots, and the reel."""
    from .reel import reel
    from .stories import cards
    c = style.card(name)
    m = month if isinstance(month, Month) else Month(month)
    look.dress(m, c, m.look, m.given_swatches)
    m.bpm_music, m.bpm = tempo_of(c)
    sysd, beats = cards(m)
    b = {"id": f"mir-{name}", "style": name, "name": f"{m.label} in review, {c['name'].lower()}", "handle": m.handle,
         "month": m.period.key,
         "moments": [{"day": p.day, "photo": p.photo, "line": p.said, "peak": p is m.peak} for p in m.moments],
         "ask": {"counts": m.counted, "seconds": m.seconds, "series": m.series},
         "bpm": m.bpm, "music": {"recipe": c["music"], "bpm": m.bpm_music},
         "format": {"width": W, "height": H, "fps": FPS}, "system": sysd, "beats": beats}
    b["reel"] = reel(m)
    b["look"] = {"given": m.look, "colors": dict(m.colors), "made": list(m.made), "theme": m.theme, "font": (m.look or {}).get("font"),
                 "font_used": m.faces["family"], "font_note": m.font_note, "numbering": m.numbering}
    return b


def boards(month, named=None):
    """The three boards, in board order, keyed by style id."""
    m = month if isinstance(month, Month) else Month(month)
    return {s: board(s, m) for s in trio(named)}
