# 2. Three looks of one idea, "tagged"

Goal: for each of three looks, `R/storyboards/<style>/` with `storyboard.json`, `storyboard.md`, `check.json` and three
sheets (`sheet.png` 9:16, `sheet-square.png`, `sheet-wide.png`): the hook, the densest beat and the closer at rest,
rendered by the composition that renders the film; and `R/out/boards.png`, the three looks one over another.

## Draft

```
python3 S/scripts/storyboard.py draft [--style ID]
```

The idea is "tagged": the tag that marks each of their people in their own photographs finds them one by one, in the
order `R/taste.json` lists them, and the year's cut of each closes into one wall of their people. The hook is the
photograph of them together with a tag beside every head it holds and the title standing on a level edge; each
person's beat is the photograph of the two of them, their tag, the stamp of where and when it was taken falling onto
the edge and their own words rising over it; the closer is the wall, every person in a slice of their photograph,
with the last across its foot. The wall holds every person the film names, however many: in rows of two across in
9:16 and 1:1 and four across in 16:9, inside the frame while those rows stand tall enough, and past that taller than
the frame, the camera running down it with the tag to rest on its foot.

The idea is drawn in three looks, each a style card in `S/styles/` (`S/styles/catalog.md` names each in a sentence):
scrapbook, analog home movie and kinetic type, A, B and C in that order. When the person named a style (`taste.json`
`style`, or `--style`), that style is A and the two of those three that differ most from it are B and C.
`R/storyboards/looks.json` keeps the order. The card decides the two faces and their scale, the colors (made from
their photographs), each beat's move and the cut into it (chosen from what the beat shows: a portrait or a landscape
photograph, words or none, a place, the last person), how a landscape photograph is mounted, the finish over the
picture, the closer's last shape and the music. The story, the people and their words are the same in all three.

Every stamp is the photograph's own month and its place: the one its caption names, none when it names none
(`R/taste.json`, each person's `when` and `where`). The hook runs two seconds, each person two to three and a half
with their best line (their words decide: four beats for up to three words, five up to seven, six up to twelve, seven
past that; a beat that would run as long as the one before it runs one more, and the last person's, the one the film
closes on, is the longest of all by one), and the closer four and a half, so one person makes a film of about 9 s,
five about 20 to 25 s, and each person after the fifth 2 to 3.5 s more.

When no wall can show every face the cast names whole, `draft` prints a FAIL line that names the photograph and exits
1: correct that photograph's `face` in `R/cast.json` (brow to chin) or give the person another of their photographs, run
`cast.py match`, and draft again.

A `storyboard.json` is format-free: beats that each name a composition (`comp`), a person, one of their own lines
where the composition sets one, and a length in pulses (beats of the tempo). `storyboard.md` is the same board as a
table you can read, then, per beat, what its move reveals and what it carries across the cut, then the music (its
origin, the person's music brief and the `Mixed:` line `music.py master` fills with the two loudness numbers), then
every sound cue with its time: one where each beat lands (the camera landing on the hook, the hit as each person's
stamp lands, the impact as the wall settles whole), the build into the wall, and the tag landing on the last face as
the stop; tags pop, words rise and the camera travels without a sound of their own.

## Make the boards better than the draft

Read each `storyboard.md`. You may reorder beats, change a beat's length, and give a person a different one of their
own lines from `R/people.json` (or one of the person's replies to them); never write words for anyone. Keep every
person in every board. Then:

```
python3 S/scripts/storyboard.py check && python3 S/scripts/storyboard.py sheets
```

`check` lays each board out in all three formats and refuses: type outside the format's safe area (on a card, as the
camera's lens sees type standing in front of the photograph) or under its edge onto the photograph, type under 28 px
cap height, a line of type running into another, a tag outside the safe area or into the type, type or a tag over the
face the cast names (or the frame cutting it), a print on the wall that cuts its face or shows less than half of its
photograph's shorter side, a line that is not that person's own, a person in no beat, and a first event later than
frame 30. It also holds the three against their cards: a face, move, transition or color the card does not give, two
looks that share more than two of the six axes, every shot within 10 % of one length, the same move twice in a row.
`sheets` renders the three frames in each format for each look, then `R/out/boards.png`.

## Look at the sheets

Open `R/out/boards.png` and every sheet with the Read tool, then any frame in `R/storyboards/<style>/frames/` full
size. Read each frame with the swap test: if its photograph could be swapped for another without changing the design,
the frame is a template. Read the three looks against each other with the photographs covered: each must be its own
film in its type, its color, its motion and its mount. A face badly placed, a tag over a face, a photograph that does
not show its person, a line that does not sound like them, a line that names what its photograph does not show (a
hill over a beach): fix it in the cast or the board (another of their lines, another of their photographs), then run
`check` and `sheets` again.

## Done when

The three boards pass `check`, their sheets are clearly about their people, and `R/out/boards.png` shows three films
that could not be mistaken for each other.
