# 1. Research: learn who they are, and read their photographs, before making anything

Goal: `build/taste.md` (one page, in prose), `build/taste.json`, and `build/picks.json` with every month's
photograph read: its line and its scene.
Everything downstream reads them.

## Run the counting

```
python3 S/scripts/research.py
```

It runs `stats.py` (what the export holds, month by month), `picks.py` (every month's photograph as the film draws
it, its focus and its line: the photograph its moment names, else the post with the most to say, never the most
liked) and `palette.py`, then reads: the year's palette and the palette of what they like and save, caption
statistics (length, case, emoji, punctuation, hashtags, openings and closings), the like-graph, cadence, their reels,
their people and places, and a first draft of the moments, one a month: the month's photograph, the date, their own
line from its caption, the people it tags and the place it names. Output: `build/research.json`, a machine draft of
`build/taste.json`, and `build/taste.draft.md` (the reading under the five headings).

## Read the photographs: each month's line and scene

The film opens each month along its photograph's own line: the horizon, a rail, a sill, a pier, a road's edge, the
rim of a bowl. `picks.py` finds the straight edge with the most consistent step of light or color across it and
draws it on `build/picks-sheet.jpg`. Open the sheet with the Read tool. A drawn line that misses the photograph's
own edge, or runs through the subject, is rewritten in `build/picks.json` (that month's `line`, `[u0, v0, u1, v1]`
as fractions of the photograph, with `"line_from": "read"`). A photograph with no line of its own gets a level
line, `[0, v, 1, v]`, at the height that keeps its main feature (the nearest flower head, the face) whole on one side.
Judge each line drawn on the part of the photograph the film shows, the 9:16 crop around its `focus`, at full size. The line is laid exactly where it is written, at
any slope, and the month's words stand over it inside the type area, so it lies between about 0.39 and 0.65 of the
crop's height, where the name and their line have room above it: `storyboard.py draft` refuses a line with no room above
it for the words, and that month's line is chosen again. Run `picks.py` again after editing a line: it keeps every
line marked read and redraws the sheet, so read the sheet once more.

Each month's `focus` (`[u, v]`, fractions of the photograph) is where its subject is: the film's crop keeps it in the
frame and the month's words stand clear of the box around it. `picks.py` finds it from detail and color, and it can miss
a subject that is not the busiest part of the photograph: the faces above a stall of produce, a person at the edge of
a wide view. Where the subject in the photograph opened at full size is not where the focus says, rewrite that month's
`focus` at the subject's middle (between the faces of a group) with `"focus_from": "read"`; `picks.py` keeps every
focus marked read.

Then write each month's `scene` in `build/picks.json`: what its photograph shows, in a few plain words, from the
photograph itself, opened at full size (`build/public/` and the month's `file`) with the Read tool ("cherry tomatoes in a
bowl, gloved hands"). The sheet's small copies hide the detail a scene names: a fern in a latte's foam reads as a heart,
and a lit theatre as a lit fountain. The storyboard names every photograph by its
scene and the clip prompt starts from it. A caption says what the person felt and often not what is in the frame
("picnic" under a photograph of globe flowers), so the scene is written from the photograph, never copied from the
caption; `storyboard.py draft` refuses a month without one.

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md` and look at a dozen of their photographs (`build/public/photos/`). Then write
`build/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** who they are this year: what they did, where the year went, who was there, the moment it turned on.
  Then curate `taste.json` `moments`, one a month, from their photographs and captions: what happened (`photo`, any
  of that month's photographs, by its path), with whom (`people`), where (`place`), and `line`, their own words for it
  as the month says them on screen (their caption's first sentence, or another sentence of the same caption; an empty
  line leaves the month wordless, and nothing is ever written for them). Mark the story's peak, the month the year
  turns on, with `"peak": true`; it holds longest. A moment that names another of
  the month's photographs takes it when `picks.py` runs again.
- **You like** what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **Your style is** their colors, light, texture, pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their photographs, their people, their places and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (`register`, `pillars`, `places`, `avoid`).
The film's words are `words`, each replacing the kit's default in their case and voice (`words.<style id>` holds a
line for one look alone):

| key | default | where it stands |
|---|---|---|
| `signoff` | see you in 2027 (the next year) | the ending's last line |

`style` names a look when the person asked for one (an id in `S/styles/`): the three looks are then that one and the
two that differ from it most. `ask` is true where you can ask the person which look to make, false where no one can
answer and you pick by taste. `length` holds the seconds they asked for, if they asked.

`music` is the brief the film's bed is made from (`music.py find`) when the person gave no track. With no brief the
bed is the picked look's own sound; correct it only from what you read about them:

| key | what it holds |
|---|---|
| `styles` | genre and instrument words, only when they name a sound they love (an export's music attribution gives genre words only) |
| `tempo` | beats per minute, only when they ask for one |
| `avoid` | what the music should never have, each written as a noun ("vocals", "big drops") |

Never an artist, a band or a song: a name is not a taste.

## Done when

`build/taste.md` has all five headings, `build/taste.json` matches it (its `moments` curated, one peak), every line on `build/picks-sheet.jpg`
lies on its photograph's own edge, and every month has a scene written from its photograph. storyboard.py refuses to run without taste.md.
