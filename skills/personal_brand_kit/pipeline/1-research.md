# 1. Research: here the research is the product

Goal: `build/taste.md` (one page, in prose), `build/taste.json`, `build/brand.json` and `out/plan.md`, written
before any storyboard. Every card, the film and the plan read these. Every finding carries a number and an example
from their own feed; nothing is guessed.

## Run the measuring

```
python3 S/scripts/research.py
```

It runs `stats.py`, `picks.py` and `palette.py`, then measures (see `research.py --help` for each): the palette
(the named colors their posts lead with and the share of posts each leads), the compositions they repeat, the
caption devices (each with its share and three real captions), the pillars (subjects clustered from their
captions, shares summing to 1), the cadence (weekdays and times), what their likes aspire to (palette and
subjects of the liked images and accounts, against their own), the posts that fall outside their system, and the
posts that landed best. Output: `build/research.json`, a draft of `build/taste.json` with the brand draft under
`brand`, and `build/taste.draft.md` (every finding under the five headings).

## Read it like a brand strategist, then write taste.md

Open `build/taste.draft.md`, look at a dozen of their photos (`build/photos/`) and the liked images if there are
any. Then write `build/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** what they post and how much of each (the pillars with their shares), and the one line that says it.
- **You like** what their likes and saves have in common (palette, subjects), with the accounts, and how far that
  is from their own feed.
- **Your style is** their palette by name and share, the compositions they repeat, light, texture, the type that
  fits.
- **Your voice is** how they write: case, length, emoji, the devices they lean on, three of their own lines quoted.
- **Avoid** what breaks the system: the posts outside it (say kindly what they do and how they landed), and
  anything the data says is wrong for them.

What the person said about themselves (their bio, the request) wins over inference: their own words go in first.
Use their numbers, their account names and their words. American spelling.

## Fix the brand block, then build the system

`build/taste.json` is a draft. Correct what your reading contradicts (the type direction `editorial`, `kinetic` or
`documentary`, `texture`, `avoid`), then edit its `brand` block in their words: the statement (one line), the
color names (plain names a person would say: "terracotta", never a hex), pillar names, the voice lines, the stop
list said kindly, the aspire line. Never change a measured share or hex. Then:

```
python3 S/scripts/brand.py system
python3 S/scripts/brand.py plan
```

`system` writes `build/brand.json`, validated against `S/design/brand.schema.json` (palette roles, pillar shares
summing to 1 within 0.01). `plan` writes `build/plan.json`: 30 days from tomorrow, a feed post on each cadence day
at its time and a story on the others, the pillars dealt in their proportions, every caption a draft marked
`"draft"` and built from their own pieces. Rewrite every caption in `build/plan.json` in their voice (their case,
their length, their devices, their hashtags), then run `brand.py plan` again: it renders `out/plan.md` and puts
the first seven days into `brand.json` as `first_week`, the tenth card.

## Done when

`build/taste.md` has all five headings, `build/brand.json` validates, and `out/plan.md` has 30 dated entries in
their voice. storyboard.py refuses to run without taste.md and brand.json.
