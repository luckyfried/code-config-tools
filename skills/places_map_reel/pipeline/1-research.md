# 1. Research: learn where they went and who they are before making anything

Goal: `build/places.json` (every place of the year, in order, with coordinates), `build/taste.md` (one page, in
prose) and `build/taste.json`, written before any storyboard. Everything downstream reads them. The two questions
this kit's research answers: where did they go, in what order and how far, and what does their travel look like
against their everyday.

## Run the counting

```
python3 S/scripts/research.py
```

It runs `places.py`, `stats.py`, `picks.py` and `palette.py`, then counts. **The places** (`places.py --help` has
the rules): geotags first, then the places named in captions, albums, folder names and check-ins, merged into one
list in visit order, each with its coordinates, date span, visits, posts, stories and photos, and where it came
from; the route between them with each leg in kilometers and the total; home; the region the map is drawn at and
the far trips; the places named once and left off (`mentioned`); and the rows that name no place (`unplaced`).
**The palettes**: the travel palette (photos away from home) against the everyday palette (photos at home) and how
far apart they read, with the palette of what they like and save. Then caption statistics (length, case, emoji,
punctuation, hashtags, the words they use about each place), the like-graph, cadence, how long their reels run and
how fast they cut, their people, and the moments (the busiest month, the far trip, the longest stay, the places they
went back to). Output: `build/research.json`, a machine draft of `build/taste.json`, `build/taste.draft.md` (the
numbers under the five headings), `build/places.json`, `build/picks.json` (each place's best photos and reels) and
the map's land shapes in `build/public/map/land.json`.

## Check the places against their own words

Open `build/places.json` and read its `assumptions`, `mentioned` and `unplaced`. Their own words win over inference:

- they say where home is (in the request or their bio): `places.py --home <place>`;
- a place they went that has no geotag and is named once (`mentioned`): `places.py --add <place>` (or
  `--add "Name@lat,lon"` for a place the gazetteer lacks);
- a place they did not go (a caption that names a place they miss): `places.py --drop <place>`;
- a geotag that names the wrong town (a suburb for the city they mean): `places.py --rename "Suburb=City"`.

Each correction is kept and replayed on every later run. Run `research.py` again after a correction so the picks
and the palettes follow the places.

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md` and look at a dozen of their photos (`build/photos/`), some from away and some from home,
and the liked media if `build/library/` has it. Then write `build/taste.md` yourself, one page, five paragraphs
that start exactly:

- **You are** who they are this year: where the year went (the places in order, the far trip, the places they went
  back to, the distance), what they photograph when they travel, and what they say about the places.
- **You like** what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **Your style is** their colors (the travel palette against the everyday one, and where their likes pull them),
  light, texture, pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, a map-tile look, whatever
  the data says).

Use their numbers, their place names and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (the type direction `editorial`,
`kinetic` or `documentary`, `pacing.energy`, `texture` grain, vignette and leaks, `avoid`, `pillars`, the words of
each place in `places`). Never change the count or the places there: they come from `build/places.json`, which you
change only through `places.py`. Keep its keys; storyboard.py, grade.py and the critics read them.

## Done when

`build/places.json` lists the places they went, `build/taste.md` has all five headings and `build/taste.json`
matches it. storyboard.py refuses to run without taste.md.
