# The grade

One ffmpeg filter grades every photograph of the person's that the films cast, so a photograph from March and one from
September sit in the same light beside the subject. It reads the person's palette and the subject's at equal weight:
the photographs live where the two meet. The subject's own stills and footage never take this filter; the
film is built around their color. `grade.py recipe` derives the filter from `taste.json` and writes it to `grade.json`;
`storyboard.py draft` applies it to each cast photograph in `public/photos/<part>.jpg`, after two steps of its own
(cast.py): white balance part of the way toward the person's warm white (none for night and a low sun, which keep their
color) and the photograph's mean light brought halfway to the film's. The board records all three per photograph
(`cast[].grade`).

| part | what it does | where the number comes from |
|---|---|---|
| shadows | lean toward the hue of the darkest color of the two palettes (theirs and the subject's, at equal weight) | `colorbalance rs/gs/bs`, 0.9 of the way from neutral |
| midtones | lean toward the average hue of the two palettes, weighted by share | `colorbalance rm/gm/bm`, 0.45 of the way |
| highlights | lean toward the lightest color of the two palettes | `colorbalance rh/gh/bh`, 0.6 of the way |
| saturation | follows how saturated the two palettes are | `0.82 + 0.55 × mean saturation`, held to 0.78–1.18 |
| contrast | a film taste gets less, so the grain carries the texture | 1.04 with grain in taste, else 1.08 |
| black lift, white roll | a film taste lifts the blacks and softens the whites | curves 0.05/0.95 with grain, else 0.015/0.985 |

The colors the type sits on come from the look's style card, its palette rule applied to the swatches of both
palettes, so the type and the subject agree. The finish over the whole frame (its grade, grain, vignette, bars or
page) is the card's too, the same for every film made in that look.

To change the grade, edit `taste.json` (`palette.year`, `palette.subject`) and run `grade.py recipe`, then
`storyboard.py draft` again; never hand-grade a single file.
