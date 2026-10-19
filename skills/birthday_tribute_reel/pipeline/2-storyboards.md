# 2. Storyboards: three different films, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`; the last frame is the board's ending).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns the shared palette into the film's grade (`build/grade.json`, `design/grade.md`), grades every shared
photo into `build/public/graded/` and writes three boards that differ on structure, tone and clip use:

| board | structure | tone | still or clip first | generated clips |
|---|---|---|---|---|
| 1 first to now | a timeline: the first photo together, each era with its date on a rule running toward now, the latest photo, the wish | warm editorial (paper, serif) | clip-first | the opener and closer in the shared palette, the first and the latest photo brought to life |
| 2 things i love about you | the big number (the age or the years), then a numbered list in heavy type over their photos, each line one the person already wrote to them | kinetic and loud | still-first | two short bridges of light in the shared colors |
| 3 in your words | a documentary cut: the comments the two traded play as captions over the photo they were written under, the person's lines left, the named one's answers right, their own videos between | documentary (near-black, mono dates) | their footage first | the opener and closer; their own videos play as they are |

Each beat names its component (`Opener`, `PhotoLive`, `KineticType`, `Exchange`, `ClipShot`, `Closer`), its frames
at 30 fps, its transition preset (`design/transitions.json`), its photos, its words and its clip. One board makes
both films: the beats are rendered at 1080×1920 and again at 1080×1080, so a clip prompt keeps its subject in the
middle square. Every board also carries `card`, its closing beat held still, which becomes the 1080×1350 card.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like whoever said it (taste.md), swap a photo for a
better shared one (any file named in `build/picks.json` `shared`, as `graded/<name>.jpg`), reorder the love lines,
fix a clip prompt that does not fit them. Keep the three boards different. Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 30–60 s, a beat under 0.8 s, an unknown component or transition, a missing asset,
**any photo that is not one the two share**, an exchange with no lines, a placeholder, a clip prompt without
"no text", or a board with no card. `sheets` renders six frames per board with the real engine (about 10 to 20 s
for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, a photo cropped past the two of them, colors that fight their photos; run `check` and `sheets`
again.

## Done when

Three sheets that look like three different films, every one of them clearly the two of them.
