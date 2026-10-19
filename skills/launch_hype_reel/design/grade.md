# The grade

One ffmpeg filter grades every photo, product still and clip in the film, so a generated clip, a product still and a
photo from March sit in the same light. It reads the person's palette and the product's at equal weight: the film
lives where the two meet, and the product never drifts far from its own color. `grade.py recipe` derives it from `build/taste.json` and writes it to `build/grade.json`;
`grade.py photos` and `clips.py normalize` apply it.

| part | what it does | where the number comes from |
|---|---|---|
| shadows | lean toward the hue of the darkest color of the two palettes (theirs and the product's, at equal weight) | `colorbalance rs/gs/bs`, 0.9 of the way from neutral |
| midtones | lean toward the average hue of the two palettes, weighted by share | `colorbalance rm/gm/bm`, 0.45 of the way |
| highlights | lean toward the lightest color of the two palettes | `colorbalance rh/gh/bh`, 0.6 of the way |
| saturation | follows how saturated the two palettes are | `0.82 + 0.55 × mean saturation`, held to 0.78–1.18 |
| contrast | a film taste gets less, so the grain carries the texture | 1.04 with grain in taste, else 1.08 |
| black lift, white roll | a film taste lifts the blacks and softens the whites | curves 0.05/0.95 with grain, else 0.015/0.985 |

The colors the type sits on come from the same palette (`storyboard.py` builds each board's color roles from the
taste palettes), so the grade and the type agree.

Texture is a separate pass in the renderer, never baked into the grade: grain (`build/public/fx/grain.png`, a 512 px
tile at the opacity `taste.json` `texture.grain` names), a vignette (`texture.vignette`), light leaks only when
`texture.leaks` is true. A taste that lists "grain" or "film" under avoid gets none.

To change the look, edit `taste.json` (`palette.year`, `palette.product`, `texture`) and run `grade.py recipe`, `grade.py photos`,
then `clips.py normalize` again; never hand-grade a single file.
