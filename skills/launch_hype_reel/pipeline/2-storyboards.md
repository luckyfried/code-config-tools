# 2. Storyboards: three different launch films, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`; the last frame is the board's ending, the product's name or its date).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns the place where the product's colors meet theirs into the film's grade (`build/grade.json`,
`design/grade.md`), grades their photos and the product's stills into `build/public/graded/` and writes three boards
that differ on structure, tone and clip use:

| board | structure | tone | still or clip first | generated clips |
|---|---|---|---|---|
| 1 the trilogy | tease, tease harder, reveal: the film sums up the three stories | quiet editorial (paper, soft serif) | clip-first | the product's world opens the reveal; its own footage is the hero moment |
| 2 the hype cut | 20 s built on their best hook line, the product cut on the beat | kinetic type, bold fields | still-first | light sweeps as the reveal transitions; its own footage is the hero |
| 3 the countdown | the countdown series opens the film: the days fall to the date, then the reveal | documentary (near-black, mono labels) | still-first | the product's world between the count and the reveal; its own footage after |

Each beat names its component (`Hook` their opening line, `Tease` a product still behind a mask that opens,
`DateCard` the days falling to the date, `ClipShot` a clip or a photo brought to life), its frames at 30 fps, its
transition preset (`design/transitions.json`), its photos, its words and its clip. Every board also carries the four
still formats in its own palette and type: `stories` (three 1080×1920 cards: tease, tease harder, reveal, each
showing more of the product than the one before), `countdown` (1080×1920, the date they gave) and `feed` (1080×1350,
the reveal).

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like `taste.md` (their case, their length, no
exclamation marks if they use none); keep the hype cut's opener their best hook word for word unless `said.hook`
names another; fix a clip prompt that does not fit their taste or the product's world. Keep the three boards
different. Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 15–30 s, a beat under 0.8 s, an unknown component or transition, a cut with no
transition named, a missing asset, a placeholder, a clip prompt without "no text", a product beat without a still
from the product's own assets, a board with no beat naming the product or no date beat, fewer than three stories,
a countdown card that does not carry the date given, a missing feed post, or three boards that do not differ.
`sheets` renders six frames per board with the real engine (about 25 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, a product still cropped past the product, colors that fight the product or their photos, a reveal
that shows nothing new; run `check` and `sheets` again.

## Done when

Three sheets that look like three different launch films, every one of them clearly theirs and clearly the product.
