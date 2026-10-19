# 1. Research: find the trip, then learn how they travel

Goal: `build/trip.json`, `build/taste.md` (one page, in prose) and `build/taste.json`, written before any
storyboard. Everything downstream reads taste first. The questions this kit's research answers: which trip, its
days and places in order, who was on it, the clips they shot, and how their travel posts look and sound against
their everyday ones.

## Run the counting

```
python3 S/scripts/research.py [--place "lisbon"] [--from 2026-10-03 --to 2026-10-08] [--album "..."] [--folder DIR]
```

Pass exactly what the person named; their words win over anything inferred. With nothing named, the most recent
trip is used. It runs `trip.py` (home is where they post month after month; a trip is a run of days away from it,
found from geotags, from albums and folders that span a few days, and from caption words when nothing is
geotagged; stops are places within a few kilometers, named by the place field, else the word their captions use
for it), then `picks.py` and `palette.py`, and counts:

- **the trip**: dates, each day with its places, items and its line (its strongest caption), the places in route
  order with their coordinates, the people tagged on it, their own clips from it;
- **travel against everyday**: the trip's palette against their everyday palette (and the colors only the trip
  has), brightness, saturation, caption length, posts a day, how fast their travel reels cut against their others;
- **voice**: caption length, case, emoji, punctuation, hashtags, sample lines from the trip;
- **likes**: the colors and themes of what they like and save;
- **music**: the tracks on their travel posts when the data names them, else the pace of their travel reels.

Output: `build/trip.json`, `build/research.json`, a machine draft of `build/taste.json`, and
`build/taste.draft.md` (the numbers under the five headings). Read `trip.json` `assumptions`: if the trip it chose
is not the one the person meant, run research.py again with what they named.

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md` and look at a dozen of the trip's photos (`build/photos/`) and a few everyday ones.
Then write `build/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** who they are on this trip: where they went, day by day, with whom, and what they chose to post.
- **You like** what their likes and saves have in common (palettes, subjects, pacing), with the accounts.
- **Your style is** how they travel on camera: the trip's colors against their everyday ones, light, texture,
  pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines from the trip.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their numbers, their places, their people and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (the type direction `editorial`,
`kinetic` or `documentary`, `pacing`, `texture`, `avoid`, `pillars`, each day's `line`, the trip's `name`). Keep
every place and every person the trip has; never add one it does not. Keep its keys; storyboard.py, grade.py and
the critics read them.

## Done when

`build/taste.md` has all five headings and `build/taste.json` matches it. storyboard.py refuses to run without
taste.md.
