# 1. Research: learn who they are before making anything

Goal: `build/taste.md` (one page, in prose) and `build/taste.json`, written before any storyboard. Everything
downstream reads taste first. The two questions this kit's research answers: which nine are theirs by their own
numbers, and why those nine worked.

## Run the counting

```
python3 S/scripts/research.py
```

It runs `stats.py`, `picks.py` and `palette.py`, then counts: the year's palette and the palette of what they like
and save, caption statistics (length, case, emoji, punctuation, hashtags, openings and closings), the like-graph
(who gets their likes and what those accounts share), cadence, how long their reels run and how fast they cut,
their people and places, and the moments (busiest and quietest month, the top post, the post that changed their
numbers, the trip), then the two this kit needs most: **the nine** (their nine most-liked posts and reels of the
year, ties broken by comments then by the newer post; for each, how many times their usual likes it got, its
subject, its two strongest colors and what its caption says) and **the wall's rhythm** (each tile's light and
color in its slot, and the arrangement, number one kept top left, that sets lighter beside darker). Output: `build/research.json`, a machine draft of `build/taste.json`, and
`build/taste.draft.md` (the numbers under the five headings).

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md` and look at a dozen of their photos (`build/photos/`) and the liked media if
`build/library/` has it. Then write `build/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** who they are this year: what they post, where the year went, and the nine: which they are and why
  each worked, in a sentence each (subject, color, caption), and what the nine share that the rest of the year does
  not.
- **You like** what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **Your style is** their colors (the year's and where their likes pull them), light, texture, pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their numbers, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (the type direction `editorial`,
`kinetic` or `documentary`, `pacing.energy`, `texture` grain, vignette and leaks, `avoid`, `pillars`, `places`,
each `nine[].why`, and `wall.order` when your eye arranges the wall better). Never change which nine they are:
that is their numbers, in `build/stats.json`.
Keep its keys; storyboard.py, grade.py and the critics read them.

## Done when

`build/taste.md` has all five headings and `build/taste.json` matches it. storyboard.py refuses to run without
taste.md.
