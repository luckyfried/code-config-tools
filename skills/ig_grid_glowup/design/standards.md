# Standards

What every grid and film from this kit is held to. The critics score against it; `qa.py gate` measures what can be
measured.

| standard | how the kit meets it | measured by |
|---|---|---|
| the nine are a better version of their feed | made from their own photos (a generated still only where none fits), one grade from their palette, arranged by a direction the audit and their numbers point to | the critics, against the real grid on each sheet |
| no two alike side by side | the nine never take two photos from one post, two near copies, or more than two of one scene while other scenes remain; the calm ones sit between the busy ones | the critics; `qa.py gate` (posts: nine different pictures) |
| every crop on its subject | each photo is placed by its focal point at 4:5 | the critics |
| a type system | two faces per direction from `type.json`, a fixed scale, their own words; headlines fit to balanced lines | the critics; `FONT_ERROR` in the render report |
| no linear motion | every tween uses a preset from `easing.json`; the nine land on springs, one per cut | the critics |
| nothing still too long | the grid scrolls, the posts drift, the profile settles; no still holds longer than 1.5 s | `freezedetect` (1.5 s) |
| transitions that mean something | each cut names a preset from `transitions.json` | `storyboard.py check` refuses an unknown preset |
| cut to the music | `storyboard.py snap` moves each cut onto a downbeat within 0.45 s, else a beat within 0.3 s | the critics |
| safe areas | type sits inside `safe-areas.json`; the renderer logs `SAFE_BREACH` for any line box outside it or any clipped text | `qa.py gate` (safe) |
| no black or dead air | transitions overlap; a missing clip is substituted | `blackdetect` (0.4 s) |
| loudness | music mastered to −14 LUFS integrated, true peak −1.5 dB | `qa.py gate` (audio, ±1 LU) |

Delivery: the nine posts as PNGs at 1080×1350; `grid-after.png` at 1080 wide; the film at 1080×1920, 30 fps, H.264
high profile, yuv420p, CRF 18, AAC 192 kbps at 48 kHz, 15 s ±0.5 s.
