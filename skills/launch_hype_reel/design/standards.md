# Motion standards

What every film from this kit is held to. The critics score against it; `qa.py gate` measures what can be measured.

| standard | how the kit meets it | measured by |
|---|---|---|
| no linear motion | every tween uses a preset from `easing.json` (enter, exit, move); entrances are springs; lines stagger | the critics |
| every photo alive | each product still and photo pushes, drifts or sits in parallax planes; a tease's mask keeps opening; the days of a date beat fall on the beat; no still holds longer than 1.5 s | `freezedetect` (1.5 s) |
| a type system | two faces per direction from `type.json`, a fixed scale, tracking per face, headlines fit to balanced lines | the critics; `FONT_ERROR` in the render report |
| a grade where the palettes meet | `grade.md`: one filter on every photo and clip, built from where the product's colors meet theirs; the product's own colors are never graded away | the critics |
| transitions that mean something | each cut names a preset from `transitions.json`; the preset's meaning is the reason it is there | `storyboard.py check` refuses an unknown preset |
| texture only when taste says so | grain, vignette and leaks read `taste.json` `texture` | the critics |
| cut to the music | `storyboard.py snap` moves each cut onto a downbeat within 0.45 s, else a beat within 0.3 s | the critics; `build/film.json` lists the snapped cuts |
| readable in the first second | one idea per beat; the headline has settled within the first second of its beat; the hook is their own line | the critics |
| safe areas | type sits inside `safe-areas.json` for the format (reel, story, feed); the renderer logs `SAFE_BREACH` for any line box outside it or any clipped text | `qa.py gate` (safe) |
| no black or dead air | transitions overlap; no beat is ever empty (a missing clip is substituted) | `blackdetect` (0.4 s) |
| loudness | music mastered to −14 LUFS integrated, true peak −1.5 dB | `qa.py gate` (audio, ±1 LU) |
| the product, by its own assets | every product beat and card shows a still or clip from the product's folder or link when it has any | `qa.py gate` (product) |
| an ending made to be remembered | the film ends on the product, its name and the date they gave; the countdown card carries that date | the critics; `qa.py gate` (date) |

Delivery: 1080×1920, 30 fps, H.264 high profile, yuv420p, CRF 18, AAC 192 kbps at 48 kHz, 15–30 s.
The three teaser stories: PNGs at 1080×1920, each showing more than the one before (`qa.py gate`, stories).
The countdown card: one PNG at 1080×1920 carrying the date (`qa.py gate`, countdown and date).
The feed post: one PNG at 1080×1350 (`qa.py gate`, feed).
Every caption names the product (`qa.py gate`, captions).
