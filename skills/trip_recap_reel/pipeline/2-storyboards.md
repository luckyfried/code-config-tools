# 2. Storyboard: the trip in three looks

Goal: `storyboards/1/` to `storyboards/3/`, each with `storyboard.md`, `storyboard.json`, three styleframes
(`frames/hook.png`, `frames/middle.png`, `frames/closer.png`) and `sheet.png`; `out/boards.png`, the three looks side
by side for the person; and a `storyboard.py check` that exits 0. The files named here are in the run's folder,
`build/<run>/`.

## The stops and their points

```
python3 S/scripts/storyboard.py points
```

The trip becomes stops: one per place in route order (`trip.json`), each with the photograph that shows it
(`picks.json`), the day, the date and time of that post, their caption, the place's coordinates and the name on
screen (`taste.json` `names` maps a place as the data spells it to the name the film sets; without an entry it is
the place's first part in their case). `points` writes `points.json` and `points.png`: for every stop's photograph,
its points in fractions of it:

- `near`: where they stood; the camera starts here.
- `far`: what the photograph looks at; the camera moves toward it, and the words on the beat sit away from it, so
  a line never covers the subject.
- `sees`: what the photograph shows, written as a cinematographer would see it: the subject, what in it would move if
  it came to life, and its light, in one or two sentences ("a steep cobbled lane between tiled walls, washing stirring
  on the lines overhead, low sun striking the far end"). The clip request for the photograph is written from it.

`near` defaults to the middle of the lower ground, `far` to where its detail and skin tones are, and `sees` is empty.
Open `points.png` and each photograph with the Read tool, correct `points.json` by eye and write every `sees`: these
points are the design's reason, and a move that ends on the sky makes a worse film.

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` matches the photographs to each other (exposure, contrast and color pulled together, so the stops read as one
set; the look's own grade is laid over the whole frame once, by the card), writes the stops to `source.json` and builds
three boards, `storyboards/1` to `3`, one story in three looks. By default the looks are cinematic-letterbox,
analog-home-movie and scrapbook (`S/styles/catalog.md` says each in a sentence); when `taste.json` `style` names the
look the person asked for, that look is board 1 and boards 2 and 3 take the two of those three that differ most from
it.

The story (`board_trip.py`): the hook is their first photograph under the trip's name and its dates; each later stop
is a beat of its own, their photograph filling its frame, the place's name and their own caption set on it in the
card's two faces, the camera moving through it from near toward far. Everything about how a beat looks is the card's
(`styles/<id>.json`): its move and the cut into it are picked from the card's allowlists by what the beat holds (a
portrait or a landscape, words or none, the peak, the people in it, a new city), never by its place in the order, and
never the same move twice running; its colors come from the card's palette rule applied to their photographs; its
easing and finish are the card's. A stop holds as long as its line takes to read, longer at the peak, with someone in
it, on a portrait or in a new city, and shorter with no words, so the shots run at different lengths. The words move
between the top, the middle and the bottom as the photographs ask.

The closer is the look's own and lands on the trip's name and dates, held still:

- cinematic-letterbox: the bars close over the last stop and the title card in their words sits between them;
- analog-home-movie: their own closing line, the last caption of the trip, under the projector flicker: a short line
  is said once, as the last thing on screen, and a line too long to read whole on a phone plays on its stop while the
  closer holds its last phrase;
- scrapbook: the book closes on its cover, the trip's name, the dates and their handle.

The board also names its five story cards (`stories`): settled frames at the rests, one for each of five stops spread
over a trip of five stops or more (the first and the last among them), and for a shorter trip each stop and the
closer. The cover the reel posts with is the closer's held still.

## Check

```
python3 S/scripts/storyboard.py check
```

`check` re-solves every board from its source and its card and exits 1 naming each fault:

- swap: two neighboring stops whose beats come out the same with their photographs traded, so the design does not
  answer its photographs;
- structure: a span outside 1 to 4 bars, or a hook with nothing sounding in its first 30 frames;
- look: a face not in the board's card, a move or a cut outside the card's allowlist, a color the card's palette rule
  did not make, the same move on two beats running, every shot within 10 % of one length, or the words in one place on
  more than 70 % of the beats that carry words;
- looks: two boards whose cards share more than 2 of their 6 axes (faces, palette rule, moves, easing, finish, closer).

Fix a fault at its input (a point, a name, a photograph's pick) and run `check` again; the boards are rebuilt from the
source, so an edit to `storyboard.json` does not survive a check.

## Look at the sheets

```
python3 S/scripts/storyboard.py sheets
```

`sheets` renders each board's hook, its middle (the stop whose line holds longest) and its closer with the real engine,
lays them out in `storyboards/N/sheet.png`, and puts the three looks side by side in `out/boards.png`. Open every sheet
and `out/boards.png` with the Read tool, then any frame full size that looks wrong: a move that misses what the
photograph looks at, type that collides, a photograph that does not fill its frame. Fix the cause and run `check` and
`sheets` again.

## Done when

`check` exits 0, `out/boards.png` shows three looks that are clearly different, and each is clearly their trip.
