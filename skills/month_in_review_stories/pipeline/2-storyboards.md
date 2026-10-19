# 2. Storyboards: three different series, not three versions of one

Goal: `build/storyboards/1..3/`, each with `storyboard.md`, `storyboard.json` and a rendered style sheet
(`frames/01..06.png` and `sheet.png`: each card's static frame, then moments of the film).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns their palette into the grade (`build/grade.json`, `design/grade.md`), grades the month's photos into
`build/public/graded/` and writes three boards. Each board is one design system (type, colors, texture, motion,
the series mark) carried by a numbered series of three to five story cards, one idea per card, and one 15 s story
film that carries the whole month. The boards differ on the axis, on tone and on clip use:

| board | the axis | tone | clip use | generated clips |
|---|---|---|---|---|
| 1 the series | a series of five: the month, what changed, the three that hit, what it was about, in my words | kinetic type, bold fields | clip-first | an opener per card, the month's weather |
| 2 the film | a single 15 s film is the hero: the weather, the numbers, the three, the colors, the sign-off; three cards cut from it | documentary (near-black, mono labels) | weather-first | the weather, the three moments alive |
| 3 the diary | a diary page with type: the month at a glance, the three taped in, the colors as paint chips, their own lines | editorial (ruled paper, soft serif) | still-first | an opener per card, their stills animated |

Every card is its own set of beats, 15 s long, and names the one beat (`still`, with `from` naming the beat it is
drawn from) its static PNG comes from. Each beat names its component (`Opener`, `ClipShot`, `StatCard`, `Mosaic`,
`KineticType`, `PhotoLive`, `Closer`, `Diary`), its frames at 30 fps, its transition preset
(`design/transitions.json`), its photos, its words and its clip id (a string, resolved later from
`build/clips.json`).

When last month's `out/template.json` exists (or `--template FILE` names one), board 1 follows its direction and
card roles so the series matches from month to month.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any line that does not sound like `taste.md` (their case, their length, no
exclamation marks if they use none), swap a photo when another one of the month says it better, fix a clip prompt
that does not fit their taste. Keep the three boards different. Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board with fewer than three or more than five cards, a card or film that is not 15 s, a beat
under 0.8 s past its transition, a cut with no transition named, an unknown component or transition, a card with
no still, a missing asset, a placeholder, a clip prompt without "no text", or a clip with no photo to stand in for
it. `sheets` renders the six frames per board with the real engine (about 40 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool, then any frame that looks wrong full size. Fix text
that collides, a photo cropped past its subject, colors that fight their photos, two cards that say the same
thing; run `check` and `sheets` again.

## Done when

Three sheets that look like three different series, every one of them clearly theirs.
