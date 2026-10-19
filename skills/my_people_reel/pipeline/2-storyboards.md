# 2. Storyboards: three different films of the same people, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json` and a six-frame style sheet
(`frames/01..06.png` and `sheet.png`, settled moments spread from the first beat to the last).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns their palette into the film's grade (`build/grade.json`, `design/grade.md`), grades every photo the
boards use into `build/public/graded/` and writes three boards that differ on structure, on tone and on clip use:

| board | structure | tone | still or clip first | generated clips |
|---|---|---|---|---|
| 1 the board | a leaderboard that builds person by person to the beat, up to number one, then the whole board held | kinetic type, bold fields | still-first | the texture between people |
| 2 portraits | one portrait per person in the order they owned the year, a line of theirs set as type, ending on the party wall | quiet editorial (paper, soft serif) | clip-first | each portrait's photo brought to life, every face kept as it is |
| 3 the party wall | one continuous camera across a 3x3 wall of the photos with the most of them in it, then the pull back | documentary (near-black, mono labels) | still-first | the wall's world (the opener), their own reels playing in their tiles |

Each beat names its component (`Opener`, `ClipShot`, `Leaderboard`, `Portrait`, `Grid`), its frames at 30 fps, its
transition preset (`design/transitions.json`), its photos or tiles, its words and its clip. Every board also carries
`cards`: one story card per person (1080×1920, a `Portrait` of their best photo and their line), drawn in the
board's palette and type.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any of your own words that do not sound like `taste.md` (their case, their
length, no exclamation marks if they use none); a person's line stays one of their own lines from
`build/people.json`. Swap a photo that does not show the person well (see `picks.py --help`), fix a clip prompt that
does not fit their taste. Keep the three boards different and keep every person in every board.
Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board outside 30–60 s, a beat under 0.8 s, an unknown component or transition, a missing asset,
a placeholder, a clip prompt without "no text", a party wall without nine distinct photos, a board without cards,
and a person with a card who is in no beat of the film. `sheets` renders six frames per board with the real engine
(about 20 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, a face cropped out of its photo, colors that fight their photos, a board row that is hard to read;
run `check` and `sheets` again.

## Done when

Three sheets that look like three different films, every one of them clearly about their people.
