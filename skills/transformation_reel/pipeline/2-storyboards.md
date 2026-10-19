# 2. Storyboards: three different films, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns their palette into the film's grade (`build/grade.json`, `design/grade.md`), grades the posts the
film carries into `build/public/graded/` and writes three boards that differ on structure, tone and clip use:

| board | structure | tone | still or clip first | generated clips |
|---|---|---|---|---|
| 1 the timeline | a straight run from the first post to the latest, every photo dated, a progress rail with the milestones marked, ending on the pair | documentary (near-black, mono dates) | still-first | time-lapse bridges at the biggest changes, the opener |
| 2 then and now | the first and the latest side by side; the line between them becomes the wipe that carries the film through every date and back to the pair | quiet editorial (paper, soft serif) | clip-first | every key photo brought to life; their own reels play |
| 3 chapters | one chapter per milestone (day one, each milestone, now), each opened by their own caption on screen as the narration | kinetic type, bold fields | still-first | the opener, the closer, their reels |

Each beat names its component (`Opener`, `Dated`, `Split`, `Chapter`, `ClipShot`), its frames at 30 fps, its
transition preset (`design/transitions.json`), its photo, its words and its clip. A photo beat carries `post` and
`at`, the post's id and its date; a `Split` carries `posts`, the first and the latest. Every board also carries
`card`, the 1080x1350 then/now card, drawn by the same `Split` in the board's palette and type. The split runs left
and right or top and bottom, the way the progress posts they like are cut (`taste.json` `progress_style.lead`).

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like `taste.md` (their case, their length, no
exclamation marks if they use none), fix a clip prompt that does not fit their taste. You may drop a photo beat or
change its words; never move a post out of date order and never change its date. Keep the three boards different.
Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 30–60 s, a beat under 0.8 s, an unknown component or transition, a missing asset,
a placeholder, a clip prompt without "no text", and any break of the timeline: a photo beat that is not one of the
subject's posts or is dated otherwise, photo beats out of date order, a first photo beat that is not the earliest
post or a last that is not the latest, a split that does not pair the first and the latest, a board with no
then/now card. `sheets` renders six frames per board with the real engine (about 20 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, a photo cropped past its subject, colors that fight their photos; run `check` and `sheets` again.

## Done when

Three sheets that look like three different films, every one of them clearly theirs.
