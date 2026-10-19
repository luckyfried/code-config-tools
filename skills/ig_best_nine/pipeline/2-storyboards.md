# 2. Storyboards: three different films, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`; the last frame is the board's ending on the whole wall).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns their palette into the film's grade (`build/grade.json`, `design/grade.md`), grades the nine into
`build/public/graded/` and writes three boards that differ on how the grid assembles, on tone and on clip use:

| board | how the grid assembles | tone | still or clip first | generated clips |
|---|---|---|---|---|
| 1 on the beat | the wall builds tile by tile on the beat, then the top three | kinetic type, bold fields | still-first | the transitions between tiles |
| 2 nine to one | a countdown, one tile at a time, ending on the whole wall | quiet editorial (paper, soft serif) | clip-first | each tile's photo brought to life (their own reel where the tile is one) |
| 3 one camera | one continuous camera across the 3x3 wall, then the pull back | documentary (near-black, mono labels) | still-first | the wall's world (the opener), their reels playing in their tiles |

Each beat names its component (`Opener`, `ClipShot`, `Countdown`, `Grid`), its frames at 30 fps, its transition
preset (`design/transitions.json`), its tiles or photo, its words and its clip. Every board also carries `wall` (the
1080×1080 best-nine image) and `story` (the 1080×1920 card), drawn by the same `Grid` in the board's palette and type.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like `taste.md` (their case, their length, no
exclamation marks if they use none), rearrange the wall when another order reads better (`taste.json` `wall.order`, then `draft` again), fix a clip prompt that does not fit their taste. Keep the three boards different.
Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 15–30 s, a beat under 1.2 s, an unknown component or transition, a missing asset,
a placeholder, a clip prompt without "no text", a tile or rank that is not one of the nine, or a wall or story
card that does not carry all nine. `sheets` renders six frames per board with the real engine (about 25 s for all
three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, a tile cropped past its subject, colors that fight their photos, a wall where two neighbors read
as one; run `check` and `sheets` again.

## Done when

Three sheets that look like three different films, every one of them clearly theirs.
