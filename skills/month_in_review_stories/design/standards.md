# Motion standards

What every story film and every card from this kit is held to. The critics score against it; `qa.py gate` measures what can be measured.

| standard | how the kit meets it | measured by |
|---|---|---|
| no linear motion | every tween uses a preset from `easing.json` (enter, exit, move); entrances are springs; lines and prints stagger | the critics |
| every photo alive | each photo pushes, drifts or sits in parallax planes; taped prints settle on springs and keep breathing; grain moves; no still holds longer than 1.5 s | `freezedetect` (1.5 s) |
| a type system | two faces per direction from `type.json`, a fixed scale, tracking per face, headlines fit to balanced lines | the critics; `FONT_ERROR` in the render report |
| a grade from their palette | `grade.md`: one filter on every photo and clip | the critics |
| transitions that mean something | each cut names a preset from `transitions.json`; the preset's meaning is the reason it is there | `storyboard.py check` refuses an unknown preset |
| texture only when taste says so | grain, vignette and leaks read `taste.json` `texture` | the critics |
| cut to the music | `storyboard.py snap` moves each cut onto a downbeat within 0.45 s, else a beat within 0.3 s | the critics; `build/film.json` lists the snapped cuts |
| readable in the first second | one idea per card and per beat; the headline has settled within the first second of its beat; typed lines finish by a little past half the page and then hold | the critics |
| safe areas | type sits inside `safe-areas.json` for the format; the renderer logs `SAFE_BREACH` for any line box outside it or any clipped text | `qa.py gate` (safe) |
| no black or dead air | transitions overlap; no beat is ever empty (a missing clip is substituted) | `blackdetect` (0.4 s) |
| loudness | music mastered to −14 LUFS integrated, true peak −1.5 dB | `qa.py gate` (audio, ±1 LU) |
| one numbered series | three to five cards share one system (type, paper or field, palette) and carry the series mark (the month, "02 / 04", one progress segment per card); each card is one idea; the last card and the film close with their handle and a line that invites a reply | `qa.py gate` (cards, template); the critics |

Delivery: the film and every animated card at 1080×1920, 30 fps, H.264 high profile, yuv420p, CRF 18, AAC 192 kbps
at 48 kHz, 15 ±0.5 s (`qa.py gate`, film and cards). Every static card: one PNG at 1080×1920 drawn from the card's
still beat with the series mark full (`qa.py gate`, cards).
