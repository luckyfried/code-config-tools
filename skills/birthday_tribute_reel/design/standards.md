# Motion standards

What every film from this kit is held to. The critics score against it; `qa.py gate` measures what can be measured.

| standard | how the kit meets it | measured by |
|---|---|---|
| no linear motion | every tween uses a preset from `easing.json` (enter, exit, move); entrances are springs; lines and words stagger | the critics |
| every photo alive | every photo pushes, drifts or sits in parallax planes; a beat with several photos cuts between them on the beat; no still holds longer than 1.5 s | `freezedetect` (1.5 s) |
| a type system | two faces per direction from `type.json`, a fixed scale, tracking per face, headlines fit to balanced lines | the critics; `FONT_ERROR` in the render report |
| a grade from their palette | `grade.md`: one filter on every photo and clip | the critics |
| transitions that mean something | each cut names a preset from `transitions.json`; the preset's meaning is the reason it is there | `storyboard.py check` refuses an unknown preset |
| texture only when taste says so | grain, vignette and leaks read `taste.json` `texture` | the critics |
| cut to the music | `storyboard.py snap` moves each cut onto a downbeat within 0.45 s, else a beat within 0.3 s | the critics; `build/film.json` lists the snapped cuts |
| readable in the first second | one idea per beat; the headline has settled within the first second of its beat | the critics |
| safe areas | type sits inside `safe-areas.json` for each shape (reel for 9:16, feed for 1:1); the renderer logs `SAFE_BREACH` for any line box outside it or any clipped text | `qa.py gate` (safe) |
| no black or dead air | transitions overlap; no beat is ever empty (a missing clip is substituted) | `blackdetect` (0.4 s) |
| loudness | music mastered to −14 LUFS integrated, true peak −1.5 dB | `qa.py gate` (audio, ±1 LU) |
| one cut, two shapes | the 1:1 film renders the same beats and the same cuts, the type a step smaller, the subject of every clip kept in the middle square | `qa.py gate` (square: same length within 1 s) |
| only the two of them | every photo on screen is one the two share | `qa.py gate` (shared) |
| an ending made to be sent | the film ends on the wish over the latest photo of the two of them, with the named one's handle; the card says the same on its own | the critics |

Delivery: 1080×1920, 30 fps, H.264 high profile, yuv420p, CRF 18, AAC 192 kbps at 48 kHz, 30–60 s.
The square cut: 1080×1080, the same codec and sound, the same length within one second (`qa.py gate`, square).
The card: one PNG at 1080×1350 (`qa.py gate`, card).
