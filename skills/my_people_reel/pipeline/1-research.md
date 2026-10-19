# 1. Research: learn who their people are before making anything

Goal: `build/taste.md` (one page, in prose) and `build/taste.json`, written before any storyboard. Everything
downstream reads taste first. The two questions this kit's research answers: who their people are, by their own
words or by every signal counted together, and what each of those people was to their year.

## Run the counting

```
python3 S/scripts/research.py [--people a,b,c] [--top N]
```

`--people` when the request names people, as handles in the order they named them (when they used first names,
run `research.py` once without it and take each one's handle from the ranked list in `build/people.json`). `--top N` when they asked for a number
of people. Neither: five people, by the count. A `build/people.txt` (one handle per line) works the same as
`--people`.

It runs `people.py`, `picks.py` and `palette.py` first, then reads the year: palette, captions, likes, cadence,
reels, places, and the two this kit needs most:

- **the people**: the order, every signal behind it in plain words (tagged in so many posts, so many of their
  posts tag them, so many comments each way, stories), each person's stretch of the year (the months they lead),
  their best line and where it came from, their voice, the exchanges between them and the person, who came next,
  and the order each signal alone would give;
- **the photos**: each person's best photo, nine group photos for the wall (every person in at least one), and the
  opener (the photo with the most of them in it).

Output: `build/people.json`, `build/picks.json`, `build/photos/`, `build/research.json`, a machine draft of
`build/taste.json`, and `build/taste.draft.md` (the numbers under the five headings).

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md` and look at each person's photo and a dozen of the group photos (`build/photos/`).
Then write `build/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** who they are this year and who they spent it with: each person in a sentence (what they were to the
  year, their stretch of it, the photo, the line), and how the year moved from one of them to the next.
- **You like** what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- **Your style is** their colors, light, texture and pacing.
- **Your voice is** how they write, and how each of their people writes: case, length, emoji, punctuation, two or
  three of their own lines quoted.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their numbers, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (the type direction `editorial`,
`kinetic` or `documentary`, `pacing.energy`, `texture` grain, vignette and leaks, `avoid`, `pillars`, `places`,
each person's `line` when another of their own lines in `build/people.json` says more). Never change who the people
are or their order: that is their own list or their numbers, in `build/people.json`. Never write a line for anyone.
Keep its keys; storyboard.py, grade.py and the critics read them.

## Done when

`build/taste.md` has all five headings and `build/taste.json` matches it. storyboard.py refuses to run without
taste.md.
