# 2. Storyboards: one dot carries the year, in three looks

Goal: in the run's folder, `storyboards/<style>/` for each of the three looks, with `board-reel.json`,
`board-landscape.json`, `board-square.json`, `plan.json`, `storyboard.md`, three styleframes (`frames/hook.png`,
`frames/stop.png`, `frames/closer.png`) and `sheet.png`; and `out/boards.png`, the three sheets one over another.

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` grades the cast into one look (`grade.py photos`: `public/photos/` and `public/photos.json`), writes
`source.json` (the places and the route in date order, the graded photographs of each visit with their focus, their
own line and their look, the handle, the asked length, and the person's case and the year's colors) and solves one
board per look from it (`board_drive.py`) in px of each format: the reel 9:16, the landscape 16:9 and the square
(`design/safe-areas.json`), each solved for its own frame and never scaled from another.

The three looks are the one `taste.json` `style` names and the two of the kit's three (swiss-grid,
cinematic-letterbox, scrapbook) that differ most from it, or those three when it names none. Each look is a style
card in `S/styles/`: its two faces, its colors (made from the year's colors by its palette rule), its easing, its
finish, the layout of a photograph on its card, the moves and cuts it allows, and its closer. The story is the same
in all three; the look is the card's.

The story runs from the hook to the closer. The film opens wide on the whole route of their year, every pin set out
and the dot on the first one, under the film's title, so the map and the route read in the first second. Then the
camera dives onto the first place as its photograph opens out of the pin. Every place the dot reaches opens out of its
pin into that place's card, laid out by the look: the photograph in its box on the card's ground, the place's name as
the label over their own line about what they did there (the visit's `line` in `taste.json` `moments`; a visit with
none shows its name under its month). When the camera moves on, it follows the dot along the next leg, the card folds
into a small print on its own pin, and the next place opens out of its pin. The type is theirs: lowercase when they
write lowercase, set in the look's faces.

The map is a Mercator crop of the region the route spans, north up, framed to the route with a margin, so a stranger
reads the country and its coast; the legs are drawn as great circles in that space, and its sea, land, coast and route
take the look's colors.

The film ends on the map their year drew, resolving into the look's closer: a poster of the year on the grid
(swiss-grid), a title card in their own words between the letterbox bars (cinematic-letterbox), or the book's cover
closing over the page (scrapbook). In each, the map shows through a window the closer leaves open on it, with every
place named beside its pin, over no other name or pin, the farthest from home, the first and the last first; a name
with no room left stays a dot. The closer's title is their year, its line the places in order, and their handle.
"Home" stands on a card only when they named their home themselves (their bio, or `places.py --home` from their own
words), and only on their first or last stop; nothing asks where they go next.

Each beat's move and the cut into it are picked from what the beat holds (a portrait, a landscape, the peak, a place
with words) among the moves and cuts the look allows, never the same move twice running. The builder computes every
projection, position and the count of places from the source and takes every word from it; nothing on a board is
typed by hand.

Each beat is counted in musical beats and holds on its moment for what its photograph carries: its words, its detail
against the set's and its change from the photograph before (`look` in `photos.json`), against its kind's pace (the
peak the curation marks 3.3 s, the hook and a place with their line 2 s, one with none 1.3 s). All the holds are scaled
by one factor so the film runs the length they asked for (`taste.json` `seconds`), or as near it as the stops make,
else at its own pace inside 20 to 42 s; a trip whose holds at their most fall short of 20 s runs that long. None is
shorter than its words take to come up and be read (0.3 s and 0.12 s a word), and the peak holds the most beats of any
stop. `draft` names the length made when it differs from the one asked. The closer is set in seconds: about two to
resolve, then the still. A stop the camera leaves across a leap over the water adds two beats for the travel, never to
its hold. The tempo is 90 bpm unless the track's own tempo is found; each beat states what its move reveals and what
it carries across the cut. The board places a sound cue where each beat lands (a hit as each place's words land, a
build into the peak and an impact on it, an impact as the map lands, and the stop where the picture and the music end
together; the camera's moves and the folding prints have no sound of their own) and names its rests: the hook, the
stop (the peak, else the middle stop) and the closer. `storyboard.md` carries all of it as tables: the beats, each
stop's photograph and their line, the move and the cut, what each reveals and carries, the music brief, the `Mixed:`
line `music.py master` fills, the sound cues, the cuts and cuts per minute, the hook's frame.

## Check

```
python3 S/scripts/storyboard.py check
```

`check` solves the boards from `source.json` again and refuses, in any format: a photograph enlarged past its own
pixels, type outside the safe area or under its floor (32.4 px on a 1080 px side), two closer names over each other or
a name off its pin, a pin outside the closer's window (`bounds.py`); a photograph shown at a place it was not taken in;
a format whose beats differ from the reel's; a beat that does not say what it reveals or carries; no stop cue, a cue
after it, or a stop less than a second before the end; a film outside its band (20 to 42 s, or from the longest its
stops make when that is under 20 s); a hook whose first event lands after frame 30; and, across the three looks, a move
or cut a card does not allow, a color its palette rule did not make, two boards in one look, or two boards laid out
alike. A refusal is fixed in the source (`places.py`, `cast.json`, `taste.json`) and `draft` runs again, never by
editing a board.

## Look at the sheets

```
python3 S/scripts/storyboard.py sheets
```

`sheets` renders each look's three styleframes at rest with the kit's composition, sets them side by side in its
`sheet.png`, and puts the three sheets one over another in `out/boards.png`, each named (first, second, third look and
the look's name) with its one sentence for the person under it. Open `out/boards.png` with the Read tool, then any
frame full size: the photograph owns its card and no word stands on its subject; the closer's names read, none over
another; the map reads as a place. Apply the swap test to every frame: it passes when their photographs, their places
and their words move the frame, and fails when another person's year would sit in it unchanged. A photograph that is
wrong for its place, two shots that repeat each other, a print whose subject is cropped: correct `cast.json` and run
`draft` and `sheets` again.

## Done when

Three sheets that are clearly theirs and clearly three looks, every place in them, `out/boards.png`, and `check`
clean.
