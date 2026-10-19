# Motion standards

What every film from this kit is held to. The critics score against it; `qa.py gate` measures what can be measured.

| standard | how the kit meets it | measured by |
|---|---|---|
| no linear motion | every tween uses a preset from `easing.json` (enter, exit, move); entrances are springs; lines and card parts stagger | the critics |
| every photo alive | each photo pushes, drifts or sits in parallax planes; every card rises on a spring over a field that keeps moving; the swipe and the poster camera never stop between cards; no still holds longer than 1.5 s | `freezedetect` (1.5 s) |
| a type system | two faces per direction from `type.json`, a fixed scale, tracking per face, headlines fit to balanced lines | the critics; `FONT_ERROR` in the render report |
| a grade from their palette | `grade.md`: one filter on every photo and clip | the critics |
| transitions that mean something | each cut names a preset from `transitions.json`; the preset's meaning is the reason it is there | `storyboard.py check` refuses an unknown preset |
| texture only when taste says so | grain, vignette and leaks read `taste.json` `texture` | the critics |
| cut to the music | `storyboard.py snap` moves each cut onto a downbeat within 0.45 s, else a beat within 0.3 s | the critics; `build/film.json` lists the snapped cuts |
| readable in the first second | one idea per beat; the headline has settled within the first second of its beat | the critics |
| safe areas | type sits inside `safe-areas.json` for the format; the renderer logs `SAFE_BREACH` for any line box outside it or any clipped text | `qa.py gate` (safe) |
| no black or dead air | transitions overlap; no beat is ever empty (a missing clip is substituted) | `blackdetect` (0.4 s) |
| loudness | music mastered to −14 LUFS integrated, true peak −1.5 dB | `qa.py gate` (audio, ±1 LU) |
| an ending made to be posted | the film ends on the statement and the first week (or the whole poster) with their handle | the critics |
| every finding measured | each card's numbers come from `build/brand.json`, every color it names is in the palette there | `qa.py gate` (brand, colors) |

Delivery: 1080×1920, 30 fps, H.264 high profile, yuv420p, CRF 18, AAC 192 kbps at 48 kHz, 20–30 s.
The guide: ten PNGs at 1080×1350, numbered 01-palette .. 10-week, ten different images (`qa.py gate`, cards).
