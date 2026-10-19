# 2. Directions: three different grids, not three versions of one

Goal: `build/storyboards/1..3/` each with `storyboard.md`, `storyboard.json`, its style sheet `sheet.png` (their
profile with the next nine in place above their real grid) and six frames of its film (`frames/01..06-<beat>.png`
and `frames.png`).

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` turns their palette into a grade (`build/grade.json`, `design/grade.md`), picks each direction's nine from
the library photos that never had a grid spot of their own (never two from one post, never two near copies, never
more than two of one scene while other scenes remain), grades them into `build/public/graded/`, and writes three
boards that differ on how the nine are arranged, on tone and on type:

| board | the nine | tone and type | film |
|---|---|---|---|
| 1 tonal and quiet | one warm grade; the calm photos on the corners and the center, the detailed ones between them so two busy frames never touch; no type | editorial (paper, soft serif) | calm, 84 bpm |
| 2 color-blocked | each row of three leans one color of their palette, light at the top to dark at the bottom; a color tile with their line in the middle | kinetic (bold sans, color fields) | driving, 118 bpm |
| 3 photo and type | a checkerboard: five photos, four posts set in their own words | documentary (near-black and paper, mono labels) | cinematic, 92 bpm |

Post n is the n-th to go up: post 1 lands at the bottom right of the nine and post 9 at the top left. Every board's
film is the same six beats in its own look: the opener (generated clip 01), their real grid with the findings
drawn on it, the reveal (generated clip 02), the nine landing in posting order over the real grid, three of the
nine full size, the whole profile.

## Stills for the spots no photo fits

A board names a post `still: true` with a `still_prompt` when no photo of theirs fits that spot (most often a
color row in board 2). If you have an image model, make each one with exactly its prompt at 4:5 (1080×1350) and
save it as `build/stills/<still_id>.png`, then:

```
python3 S/scripts/clips.py stills
```

A still that did not arrive is painted in the spot's color (late light through a window on a plain wall), so the
grid still reads as one palette. `build/stills.json` records each as generated or painted; the plan and the brief
say which posts they are.

## Make each board better than the draft

Read each `storyboard.md`. Rewrite any words that do not sound like `taste.md` (the type posts, the color tile, the
film's lines). Swap a photo when a better one of theirs is in `build/picks.json` (`grade.py photos FILE`, then name
the graded file in that post). Keep the three boards different. Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` refuses a board without nine posts numbered 1 to 9, a photo used twice, an unknown component, a missing
asset, a placeholder, a clip prompt without "no text", or a film outside 14.5–15.5 s. `sheets` renders the three
style sheets and the six frames of each film with the real engine (about 15 s for all three).

## Look at the sheets

Open each `build/storyboards/N/sheet.png` with the Read tool: the nine above the line, their real grid below.
Ask of each: does it look like this person's feed on its best week; do two neighbors read as one; does a busy
photo sit beside another; does any type look like a default. Then open `frames.png`. Fix what you see in the
storyboard and run `check` and `sheets` again.

## Done when

Three sheets that look like three different grids, every one of them clearly theirs.
