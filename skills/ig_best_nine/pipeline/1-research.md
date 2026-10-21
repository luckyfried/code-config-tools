# 1. Research: learn who they are before making anything

Goal: the run's `taste.md` (one page, in prose) and `taste.json`, written before any storyboard. Everything
downstream reads taste first. The two questions this kit's research answers: which nine are theirs by their own
numbers, and why those nine worked.

## Run the counting

```
python3 S/scripts/research.py --run build/<stamp>
```

It runs `stats.py`, `picks.py` and `palette.py`, then counts: the year's palette and the palette of what they like
and save, caption statistics (length, case, emoji, punctuation, hashtags, openings and closings), the like-graph
(who gets their likes and what those accounts share), cadence, how long their reels run and how fast they cut,
their people and places, and the moments (busiest and quietest month, the top post, the post that changed their
numbers, the trip), then the two this kit needs most: **the nine** (their nine most-liked posts and reels of the
year, ties broken by comments then by the newer post; for each, how many times their usual likes it got, its
subject, its two strongest colors and what its caption says) and **the rhythm** (the nine's light and color in rank
order). `picks.py` also finds each photograph's focus point and its square crop, which every storyboard places it
by. Output, in the run: `research.json`, `picks.json`, a machine draft of `taste.json`, and `taste.draft.md` (the
numbers under the five headings).

## Read each photograph's line

drive cuts each photograph along its own strongest straight line: a rack's rail, a board's edge, the hem of a towel
over the dough. Look at each of the nine and write its line into `picks.json` as `line`, [u0, v0, u1, v1], two
points in fractions of the photograph's width and height. Prefer a line in the upper part of the picture that has
clutter above it: the field covers what lies above the edge. The field covers the subject too when it stands over
the line, so a line never runs under the subject (a surfer against the horizon, the mountains over a boat's bow);
leave `line` out where the photograph has no straight line, or none with its subject below it, and that photograph
is cut level. picks.py keeps the lines when it runs again.

## Read it like a creative director, then write taste.md

Open `taste.draft.md` and look at a dozen of their photos (the run's `library/posts/`, or the photo folder named in
`library.json`) and the liked media if the library has it. Then write the run's `taste.md` yourself, one page, five
paragraphs that start exactly:

- **You are** who they are this year: what they post, where the year went, and the nine: which they are and why
  each worked, in a sentence each (subject, color, caption), and what the nine share that the rest of the year does
  not.
- **You like** what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **Your style is** their colors (the year's and where their likes pull them), light, texture, pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their numbers, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

The run's `taste.json` is a draft. Rewrite `words.drive` (the lines the tone sets on
screen) in their voice: their case, their length, their punctuation. Correct `register`, each `nine[].why` and
`avoid` where your reading says otherwise. Never change which nine they are: that is their numbers, in the run's
`stats.json`. Keep its keys; the storyboards, the critics and deliver.py read them.

## Done when

`taste.md` has all five headings and `taste.json` matches it. storyboard.py refuses to run without taste.md.
