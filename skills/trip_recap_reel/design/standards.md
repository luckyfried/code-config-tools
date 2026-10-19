# Motion standards

What every film from this kit is held to. The critics score against it; `qa.py gate` measures what can be measured.

| standard | how the kit meets it | measured by |
|---|---|---|
| no linear motion | every tween uses a preset from `easing.json` (enter, exit, move); entrances are springs; lines stagger; the route draws itself along an eased path | the critics |
| every photo alive | each photo pushes, drifts or sits in parallax planes; a day's photos cut on the music; the postcard print drifts under its stamp; the map keeps drawing or drifting; no still holds longer than 1.5 s | `freezedetect` (1.5 s) |
| a type system | two faces per direction from `type.json`, a fixed scale, tracking per face, headlines fit to balanced lines | the critics; `FONT_ERROR` in the render report |
| a grade from their palette | `grade.md`: one filter on every photo and clip | the critics |
| transitions that mean something | each cut names a preset from `transitions.json`; the preset's meaning is the reason it is there | `storyboard.py check` refuses an unknown preset |
| texture only when taste says so | grain, vignette and leaks read `taste.json` `texture` | the critics |
| cut to the music | `storyboard.py snap` moves each cut onto a downbeat within 0.45 s, else a beat within 0.3 s | the critics; `build/film.json` lists the snapped cuts |
| readable in the first second | one idea per beat; the headline has settled within the first second of its beat | the critics |
| safe areas | type sits inside `safe-areas.json` for the format; the renderer logs `SAFE_BREACH` for any line box outside it or any clipped text | `qa.py gate` (safe) |
| no black or dead air | transitions overlap; no beat is ever empty (a missing clip is substituted) | `blackdetect` (0.4 s) |
| loudness | music mastered to −14 LUFS integrated, true peak −1.5 dB | `qa.py gate` (audio, ±1 LU) |
| a map from their own coordinates | the route is drawn in the trip's palette from `trip.json`'s places (equirectangular, fitted to the frame), each place labeled once and never over another; no tile is fetched from any service | the critics |
| every place in a beat | each place of the trip is named by a beat's words, its stamp, or a stop its map reaches | `storyboard.py check`; `qa.py gate` (places) |
| one storyboard, two frames | the 16:9 film is the same beats, frames and cuts as the 9:16 film, laid out for a wide frame (`safe-areas.json` landscape) | `qa.py gate` (landscape: 1920×1080, within 1 s) |
| an ending made to be posted | the film ends on the whole route with their handle, the trip's name and the people who were there; the five story cards read as a set | the critics |

Delivery: 1080×1920, 30 fps, H.264 high profile, yuv420p, CRF 18, AAC 192 kbps at 48 kHz, 30–60 s.
The wide cut: 1920×1080, the same codec, the same length within 1 s (`qa.py gate`, landscape).
The story cards: five PNGs at 1080×1920 (`qa.py gate`, stories).
