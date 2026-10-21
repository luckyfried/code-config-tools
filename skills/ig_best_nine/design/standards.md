# Motion standards

What every film from this kit is held to. The critics score against it; `qa.py` measures what can be measured.

| standard | how the kit meets it | measured by |
|---|---|---|
| no linear motion | the camera travels between cards on `easing.json`'s move curve, pulling back and banking on the way; type lands on its enter curve and cards fly and peel on eased curves; the ink bars stand one after another | the critics |
| every photograph alive | each photograph arrives cut along its own line and holds its cut still under moving grain; the camera eases between beats | `freezedetect` (1.0 s at -80 dB: no stalled render) |
| rhythm with contrast | beats vary in length, a fast run is followed by a held composition, and a hold is designed to be held | the critics, reading the strip beside two figures `qa.py` prints and never passes or fails: the luma line's seconds under 0.5 (each second's change, read at an eighth of the frame, where grain averages out and a move does not) and the cuts per minute |
| a type system | two faces per direction from `type.json`, a fixed scale, tracking per face, headlines fit to balanced lines | the critics; `FONT_ERROR` in the render report |
| a layout from their numbers | each count is sized by the square root of its share of the top post's likes, each ink bar stands as tall as its share with its count on its face, and each cut lies along its photograph's own strongest line, so the camera turns with it; each composition passes the swap test | the critics (`vote/scores.json` `swap`) |
| photographs whole | at rest the cut photograph runs off the frame under its edge by design and never carries type, and each of the closer's slices shows at least 240 px on its short side in the reel and 180 in the square and wide; no bar hides a count | `storyboard.py check` (the bounds check) |
| texture held low | film grain at 0.04, no light leaks | the critics |
| cut to the music | `storyboard.py snap` times the storyboard at the music's tempo, so every cut lands on a beat | the critics; `film.json` names the tempo |
| a hook | the hook event lands in the first 30 frames | `qa.py timed` (hook) |
| readable in the first second | one idea per beat; the headline has settled within the first second of its beat | the critics |
| safe areas | at rest, type sits inside `safe-areas.json` for the format and is never cut by the frame | `storyboard.py check` (the bounds check) |
| no black or dead air | no beat is ever empty | `blackdetect` (0.4 s) |
| loudness | music mastered to -14 LUFS integrated, true peak -1.5 dB | `qa.py check` (audio, 1 LU) |
| an ending made to be posted | the film ends on all nine, each shown whole or as a slice, with their handle and their likes; the story card asks which one is their followers' favorite | the critics |

Delivery: three films of one storyboard, the reel 1080x1920, the square 1080x1080 and the wide 1920x1080, each 30 fps
H.264 High, yuv420p, AAC 192 kbps at 48 kHz. Length: 15 to 30 s for nine posts; with fewer the floor is 15 x posts/9
s. On the processor the films are encoded by x264 at CRF 18; on an NVIDIA graphics card by NVENC at constant quality
14, which keeps film grain at 1:1.
The best-nine image: one PNG at 1080x1080, the square's closer at rest, every post shown whole or as a slice at least 180 px on its short side (`qa.py check`, stills).
The story card: one PNG at 1080x1920, the reel's closer at rest (`qa.py check`, stills).
