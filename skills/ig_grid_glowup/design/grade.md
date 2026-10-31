# The grade

One ffmpeg filter grades every photo of the plan, so a photo from March and one from last week sit in the same
light. Before it, each photo is matched to the set, so the grade lands on photos that already agree. `storyboard.py draft`
derives the recipe from `taste.json` as it is at that moment, writes it and each photo's match to `grade.json`, and
grades the plan's photos into `public/graded/` (`grade.py photos` does it by hand); the board's hash covers
`grade.json`, so a taste change reaches the render. Their posts already on the grid are shown as posted.

| part | what it does | where the number comes from |
|---|---|---|
| shadows | lean toward the hue of their darkest palette color | `colorbalance rs/gs/bs`, 0.9 of the way from neutral |
| midtones | lean toward the year's average hue, weighted by share | `colorbalance rm/gm/bm`, 0.45 of the way |
| highlights | lean toward their lightest palette color | `colorbalance rh/gh/bh`, 0.6 of the way |
| saturation | follows how saturated their palette is | `0.82 + 0.55 × mean saturation`, held to 0.78–1.18 |
| contrast | a film taste gets less, so the grain carries the texture | 1.04 with grain in taste, else 1.08 |
| black lift, white roll | a film taste lifts the blacks and softens the whites | curves 0.05/0.95 with grain, else 0.015/0.985 |
| blues and cyans | a warm palette pulls them down, so a cold sky gives way to the feed's warmth | `huesaturation` on c+b, 3 × (red − blue) of the palette's mean, held to 0–0.6 |
| the match: saturation | each photo's saturation scaled toward the set's median | the median over the photo's own, held to 0.7–1.2 |
| the match: warmth | under a warm palette, a photo colder than the set's median is warmed toward it (a cool palette cools the warmer ones) | `colorbalance rm/bm`, 0.6 of the gap, at most 0.15 |

Texture is never baked into the grade: the film's grain, vignette and bloom are the picked style's own finish, drawn
over the whole frame.

To change the grade, edit `taste.json` (`palette`) and run `storyboard.py draft` and everything after it; never
hand-grade a single file.
