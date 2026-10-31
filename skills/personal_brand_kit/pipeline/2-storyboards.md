# 2. Storyboards: one story, three looks

Goal: `storyboards/a/`, `storyboards/b/` and `storyboards/c/` in the run folder, each one look of the same story with
`storyboard.md`, a board per format (`board-reel.json`, `board-square.json`, `board-wide.json`), `plan.json` and a
sheet (`sheet.png`), and `out/boards.png`, the three looks side by side to show the person.

## Draft

```
python3 S/scripts/storyboard.py draft
```

`draft` runs `material.py` first: it grades their photographs to one light, finds where each photograph's subject
sits, and writes `studio.json`, the facts every board reads: the photographs and the story, the moments in the order
the film plays them (the curated `taste.json` `moments`, or the drafted story while `taste.json` is still the draft;
`S/pipeline/1-research.md` says how each is chosen). The shares stay in `brand.json` and the written guide; the film
shows none of them.

Their photographs are their posts' own pictures. When the person named a folder of their photographs to use instead,
set `BRAND_PHOTOS` to it on this command (`BRAND_PHOTOS=/path/to/folder python3 S/scripts/storyboard.py draft`): each
photograph is cast to the pillar whose words its file name carries, the rest shared out by pillar share, and the
draft writes `cast.json` with `cast.png`. Open `cast.png`, move a photograph to the pillar it shows in `cast.json`,
and draft again; the cast is kept while the folder is the same.

Then it writes three looks, each from one style card (`S/styles/<id>.json`; `S/styles/catalog.md` says what each
looks like in plain words): kinetic-type, editorial-quiet and swiss-grid, or, when `taste.json` `style` names another
card, that look first beside the two defaults that differ most from it. Each look takes everything it shows from its
card: its two faces, its palette rule applied to their feed's colors, its moves and cuts, its easing, its finish, its
photo layout, its closer and its music. The three looks share no more than two of the six axes (family, palette,
camera, transition, finish, music), so the person chooses between three different films.

The story is the same in all three, and every word in it is theirs:

- **the hook**: their opening line (`taste.json` `hook`, else the first phrase of their bio) over a photograph of
  theirs the story does not play, with their handle; it lands inside the first second;
- **the moments**, in order, each on its own photograph with its pillar as the label and their own caption line, the
  last one the moment that matters most, held longest;
- **the ask**: their question to the viewer (`taste.json` `question`, else the question their best-liked caption
  asks), over the last moment's photograph, held long enough to read twice;
- **the closer**: their sign-off (`taste.json` `signoff`, else their name) and their handle, in the look's closer,
  held still at the end.

Each beat's move, and the cut into it, is chosen from what the beat shows (a title, a photograph with words or
without, portrait or landscape, the last moment, people in it, a place named) among the moves and cuts the card
allows, never the same move twice running. Each beat lasts the card's pace at its tempo, so a slow look plays fewer
moments: the moments that do not fit in 28 seconds are left out, the least liked first, the last one always kept.
The layout is solved again for each frame (1080×1920, 1080×1080, 1920×1080), never scaled.

`storyboard.md` says, per beat, when it starts, how long it holds, its move, the cut into it and its words, then the
music and the sound cues (where a line lands, the sign-off, and the stop on a look whose cuts are hard).

## Check and look

```
python3 S/scripts/storyboard.py check
python3 S/scripts/storyboard.py sheets
```

`check` holds every board in every format to its card and the frame: a line outside the type area or the card's line
box, a line too long for the box, a length outside 12 to 30 s, a hook after frame 30, a face, move, cut or color the
card did not make, the same move twice in a row, or two looks sharing more than two axes. It prints each finding and
exits 1 on any. A finding is fixed at its source (the words or the moments in `taste.json`, or the cast), then
`draft` and `check` again; a board is never edited by hand.

`sheets` renders the hook, a middle beat and the closer of each look's reel at rest onto `storyboards/<letter>/sheet.png`,
and the three looks side by side onto `out/boards.png`, each headed by its letter and its plain name. Open
`out/boards.png` and each sheet with the Read tool.

## Done when

`check` passes for all three looks in all three formats, and `out/boards.png` shows three different films of their
photographs and their words.
