# 1. Research: read the grid and the person before making anything

Goal: `audit.md` when there is a feed (one page in plain words on what their grid is doing), `taste.md` (one page, in prose)
and `taste.json`, written before anything is planned. Everything downstream reads taste and the audit
first. The three questions this kit's research answers: what are their last 30 posts doing wrong as a grid, what do
their likes and saves say they want it to look like, and which visual patterns work best by their own numbers.

## Run the counting

```
python3 S/scripts/research.py
```

It runs `picks.py` and `palette.py`, then reads:

- **the grid**: the last 30 posts as their profile shows them (`grid.json`, drawn numbered in
  `grid-sheet.png`): runs of posts whose color clashes with the rest, screenshots and text cards, busy photos
  packed side by side, posts the 4:5 grid crops, rows that jump from light to dark;
- **their numbers**: warm against cool, quiet against bold, calm against busy, near their palette against far from
  it, photo against text, each with its post count and its average likes and saves;
- **their likes**: the themes and color words of the accounts they like, save and follow;
- **their captions and cadence**: case, length, emoji, hashtags, sample lines, the weekday and hour they post.

Output: `research.json`, `audit.json` (the audit's source), `audit.md`, `grid-before.png`, a
machine draft of `taste.json`, and `taste.draft.md` (the numbers under the five headings). With no feed (an empty
grid) there is nothing to audit: no `audit.md` and no `grid-before.png` are made, and the eye pass is skipped.

## The eye pass on the audit

Open `grid-sheet.png` with the Read tool. The numbers cannot see everything: a close crop among wide shots,
a face cut at the chin, a post that repeats its neighbor, a color that only reads wrong beside another. Edit
`audit.json`: add each finding only an eye sees to `findings` (a plain `title`, a plain sentence in
`plain`, the grid `positions` it covers counted from 0 at the top left, and `kind` "tight", "crops" or another
short word), correct anything the numbers got wrong, and keep the strongest three to five. Every finding says what
it does to the grid in words a person would use, never a measurement. Then:

```
python3 S/scripts/research.py audit
```

## Read it like a creative director, then write taste.md

Open `taste.draft.md` and look at a dozen of their photos (`photos/`) and the liked media if
the run's `library/` has it. Then write `taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** who they are on the grid: the things they do, the places they go and the people they go with, in
  the words they posted with them, and what the audit found pulling the grid apart.
- **You like** what their likes and saves have in common (palettes, subjects, the grids they save), with the
  accounts.
- **Your style is** their colors (the grid's and where their likes pull them), light, texture, how their photos
  are framed.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, screenshots on the grid, whatever the data says).

Use their numbers, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

`taste.json` is a draft: correct anything your reading contradicts (`palette`, `pillars`, `avoid`,
`register`, `texture`, `grid`, `music`). Keep its keys; grade.py, plan.py, storyboard.py, music.py and the critics read them.

`music` is the brief `music.py find` reads when the person placed no track. The bed is composed from the recipe
of the look they pick (each style has its own instruments, tempo and key), so the brief only steers it, from what you
read about them (their register, pacing and texture, the places and eras they post, their pillars):

| key | what it holds |
|---|---|
| `mood` | a word for the feeling the film should carry (`calm`, `warm`, `bright`), which the critics hear the bed against |
| `styles` | empty, which keeps the picked look's own recipe; or the person's own words for a sound they asked for ("lo-fi", "piano"), which choose the recipe that fits them |
| `avoid` | what the music should never have, each written as a noun ("vocals", "big drops", "drums"); an instrument named here leaves the bed |

Write `styles` only from what the person said; your reading of them goes in `mood` and `avoid`.

Never an artist, a band or a song: a name is not a taste.

## Done when

`audit.md` names at least three findings (when there is a feed), `taste.md` has all five headings and `taste.json`
matches it. plan.py refuses to draft without taste.md.
