# The grade

One ffmpeg filter grades every photo and every clip in the film, so a generated clip and a photo from March sit in
the same light. `grade.py recipe` derives it from `build/taste.json` and writes it to `build/grade.json`;
`grade.py photos` and `clips.py normalize` apply it.

| part | what it does | where the number comes from |
|---|---|---|
| shadows | lean toward the hue of their darkest palette color | `colorbalance rs/gs/bs`, 0.9 of the way from neutral |
| midtones | lean toward the month's average hue, weighted by share | `colorbalance rm/gm/bm`, 0.45 of the way |
| highlights | lean toward their lightest palette color | `colorbalance rh/gh/bh`, 0.6 of the way |
| saturation | follows how saturated their palette is | `0.82 + 0.55 × mean saturation`, held to 0.78–1.18 |
| contrast | a film taste gets less, so the grain carries the texture | 1.04 with grain in taste, else 1.08 |
| black lift, white roll | a film taste lifts the blacks and softens the whites | curves 0.05/0.95 with grain, else 0.015/0.985 |

The colors the type sits on come from the same palette (`storyboard.py` builds each board's color roles from the
taste palettes), so the grade and the type agree.

Texture is a separate pass in the renderer, never baked into the grade: grain (`build/public/fx/grain.png`, a 512 px
tile at the opacity `taste.json` `texture.grain` names), a vignette (`texture.vignette`), light leaks only when
`texture.leaks` is true. A taste that lists "grain" or "film" under avoid gets none.

To change the look, edit `taste.json` (`palette.month`, `texture`) and run `grade.py recipe`, `grade.py photos`,
then `clips.py normalize` again; never hand-grade a single file.
