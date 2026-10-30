# The grade

One ffmpeg filter grades every photo in the film, so a photo from March and one from October sit in the same light.
`grade.py recipe` derives it from `B/taste.json` and writes it to `B/grade.json`; `grade.py photos` applies it
(`storyboard.py draft` runs both). ffmpeg writes the graded photo losslessly and PIL encodes its jpeg (quality 95, no
chroma subsampling), because ffmpeg's jpeg encoder rounds a clipped yellow's red down and its green up and turns a sun
lime.

Before the filter, each photo is matched to the others:

| part | what it does | the number |
|---|---|---|
| white balance | pulled part of the way to gray, the pull fading toward white so a sun or a lamp stays white, and fading as the cast grows strong, so a sunset keeps its gold and only a camera's tint is taken out | `WB` 0.45, faded by `1 − v²` and by `1 − chroma / CAST`, `CAST` 0.5 (the chroma of the photo's mean color) |
| exposure | pulled part of the way to one target, a night toward the night target | `EXPOSE` 0.6, `DAY` 0.47, `NIGHT` 0.30 |
| saturation | a photo louder than one mean is pulled part of the way to it, so a stock-blue sky calms; a quieter one keeps its own | `SAT` 0.4, the pull held to 0.5–1.0 |
| toning | a black-and-white photograph is toned in the hue of the year's average color, strongest in its mids and neutral at black and white, so it sits beside its colored neighbors as a toned print | `MONO` 4/255 (its mean chroma), `TONE` 30 (the chroma of its mid gray), carried in `B/grade.json` as `tone` |

Then the filter:

| part | what it does | where the number comes from |
|---|---|---|
| shadows | lean toward the hue of their darkest palette color | `colorbalance rs/gs/bs`, 0.9 of the way from neutral |
| midtones | lean toward the year's average hue, weighted by share | `colorbalance rm/gm/bm`, 0.45 of the way |
| highlights | lean toward their lightest palette color | `colorbalance rh/gh/bh`, 0.6 of the way |
| saturation | follows how saturated their palette is, never above the photos' own; turned about each pixel's lightness in RGB (`colorchannelmixer`), so a gray stays gray and a clipped yellow sun stays yellow, where a YUV saturation (`eq`) tints both green | `0.72 + 0.5 × mean saturation`, held to 0.78–1.0 |
| contrast | a film taste gets less, so the grain carries the texture; in RGB (`lutrgb`) about mid gray | 1.04 with grain in taste, else 1.08 |
| black lift, white roll | a film taste lifts the blacks and softens the whites | curves 0.05/0.95 with grain, else 0.015/0.985 |

The swatches each board carries come from the same palette the two share, so the grade and the board agree.

Texture is a separate pass in the renderer, never baked into the grade: grain (`B/public/fx/grain.png`, a 512 px
tile) and a vignette at each tone's own strength. A taste whose `texture.grain` is 0 (research sets it for a clean
taste; set it yourself when taste.md avoids grain or film) gets no grain in any tone.

To change the look, edit `taste.json` (`palette.year`, `texture`) and run `grade.py recipe` and `grade.py photos`
again; never hand-grade a single file.
