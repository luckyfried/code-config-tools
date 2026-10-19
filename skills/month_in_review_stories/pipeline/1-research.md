# 1. Research: the month against their year, before making anything

Goal: `build/taste.md` (one page, in prose) and `build/taste.json`, written before any storyboard. Everything
downstream reads taste first. The question this kit's research answers: what made this month theirs, set against
the rest of their year.

## Run the counting

```
python3 S/scripts/research.py
```

It runs `stats.py`, `picks.py` and `palette.py`, then counts the month against the twelve months that end with it:

- **change**: cadence (posts a week, posting days, the month's rank among the twelve), subjects (each theme's share
  of the month against the rest of the year, and the subjects new this month), the words that mark the month, the
  palette shift (the month's colors far from the year's) and the voice shift.
- **pillars**: the month's three or four subjects, with how many posts each carried.
- **moments**: the three that hit, their three most-liked posts of the month, each with how many times their usual
  likes it got, whether it beat the best post of the rest of the year, its subject, place, two strongest colors and
  what its caption says.
- **voice**, **palette**, **likes**, **reels**, **places**: their captions, colors, the like-graph, how their reels
  run and cut, and where the month went.

Output: `build/research.json`, a machine draft of `build/taste.json`, and `build/taste.draft.md` (the numbers under
the six headings).

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md` and look at a dozen of the month's photos (`build/photos/`) and the liked media if
`build/library/` has it. Then write `build/taste.md` yourself, one page, six paragraphs under these headings,
exactly:

- **## this month against your year**: what was different about this month, in numbers (posts against a usual
  month, posting days, the streak), the new subjects, the new colors, the three that hit and whether they beat the
  rest of the year.
- **## you are**: who they are this month and this year: what they post, where the month went, why each of the
  three worked (subject, color, caption).
- **## you like**: what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **## your style is**: their colors (the month's and the year's), light, texture, pacing.
- **## your voice is**: how they write: case, length, emoji, punctuation, two or three of their own lines quoted.
- **## avoid**: what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their numbers, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (the type direction `editorial`,
`kinetic` or `documentary`, `pacing.energy`, `texture` grain, vignette and leaks, `avoid`, `pillars`, `places`,
each moment's `why`). Never change which three hit: that is their numbers, in `build/stats.json`. Keep its keys;
storyboard.py, grade.py and the critics read them.

## Done when

`build/taste.md` has all six headings and `build/taste.json` matches it. storyboard.py refuses to run without
taste.md.
