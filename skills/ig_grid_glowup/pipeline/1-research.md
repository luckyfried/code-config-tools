# 1. Research: read the grid and the person before making anything

Goal: `out/audit.md` (one page in plain words on what their grid is doing), `build/taste.md` (one page, in prose)
and `build/taste.json`, written before any direction is drafted. Everything downstream reads taste and the audit
first. The three questions this kit's research answers: what are their last 30 posts doing wrong as a grid, what do
their likes and saves say they want it to look like, and which visual patterns work best by their own numbers.

## Run the counting

```
python3 S/scripts/research.py
```

It runs `picks.py` and `palette.py`, then reads:

- **the grid**: the last 30 posts as their profile shows them (`build/grid.json`, drawn numbered in
  `build/grid-sheet.png`): runs of posts whose color clashes with the rest, screenshots and text cards, busy photos
  packed side by side, posts the 4:5 grid crops, rows that jump from light to dark;
- **their numbers**: warm against cool, quiet against bold, calm against busy, near their palette against far from
  it, photo against text, each with its post count and its average likes and saves;
- **their likes**: the themes and color words of the accounts they like, save and follow;
- **their captions and cadence**: case, length, emoji, hashtags, sample lines, the weekday and hour they post.

Output: `build/research.json`, `build/audit.json` (the audit's source), `out/audit.md`, `out/grid-before.png`, a
machine draft of `build/taste.json`, and `build/taste.draft.md` (the numbers under the five headings).

## The eye pass on the audit

Open `build/grid-sheet.png` with the Read tool. The numbers cannot see everything: a close crop among wide shots,
a face cut at the chin, a post that repeats its neighbor, a color that only reads wrong beside another. Edit
`build/audit.json`: add each finding only an eye sees to `findings` (a plain `title`, a plain sentence in
`plain`, the grid `positions` it covers counted from 0 at the top left, and `kind` "tight", "crops" or another
short word), correct anything the numbers got wrong, and keep the strongest three to five. Every finding says what
it does to the grid in words a person would use, never a measurement. Then:

```
python3 S/scripts/research.py audit
```

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md` and look at a dozen of their photos (`build/photos/`) and the liked media if
`build/library/` has it. Then write `build/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** who they are on the grid: what they post, what their best posts share, and what the audit found
  pulling the grid apart.
- **You like** what their likes and saves have in common (palettes, subjects, the grids they save), with the
  accounts.
- **Your style is** their colors (the grid's and where their likes pull them), light, texture, how their photos
  are framed.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, screenshots on the grid, whatever the data says).

Use their numbers, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (`palette`, `pillars`, `avoid`,
`register`, `texture`, `grid`). Keep its keys; storyboard.py, grade.py, plan.py and the critics read them.

## Done when

`out/audit.md` names at least three findings, `build/taste.md` has all five headings and `build/taste.json`
matches it. storyboard.py refuses to run without taste.md.
