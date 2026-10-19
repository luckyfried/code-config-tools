# 2. Storyboards: three different films, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns their palette into the film's grade (`build/grade.json`, `design/grade.md`), grades the photos it
uses into `build/public/graded/` and writes three boards that differ on structure, tone and clip use:

| board | structure | tone | generated clips |
|---|---|---|---|
| 1 month by month | chronological months | quiet editorial (paper, soft serif) | build the world: an establishing opener, the closer |
| 2 by the numbers | chapters of their numbers | kinetic type, bold fields | texture between chapters |
| 3 one thread | their trip or their busiest stretch | documentary (near-black, mono labels) | their stills brought to life, their own reels inside |

Each beat names its component (`Opener`, `StatCard`, `PhotoLive`, `Mosaic`, `KineticType`, `ClipShot`, `Closer`),
its frames at 30 fps, its transition preset (`design/transitions.json`), its photos, its words and its clip.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like `taste.md` (their case, their length, no
exclamation marks if they use none), swap a photo that is not their best (`grade.py photos FILE`, then
`"graded/<name>.jpg"` in the beat), fix a clip prompt that does not fit their taste. Keep the three boards different.
Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 45–75 s, a beat under 1.2 s, an unknown component or transition, a missing asset,
a placeholder, a clip prompt without "no text", or a board without 10 cards and 3 stories. `sheets` renders six
frames per board with the real engine (about 15 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, crops that lose the subject, colors that fight their photos; run `check` and `sheets` again.

## Done when

Three sheets that look like three different films, every one of them clearly theirs.
