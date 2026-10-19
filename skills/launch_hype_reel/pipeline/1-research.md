# 1. Research: learn who they are, and who answers them, before making anything

Goal: `build/taste.md` (one page, in prose) and `build/taste.json`, written before any storyboard. Everything
downstream reads taste first. The questions this kit's research answers: which of their posts their audience
answered most (comments and saves), which opening lines did it, what the product looks like, and where its colors
meet theirs.

## Run the counting

```
python3 S/scripts/research.py
```

It runs `stats.py`, `picks.py` and `palette.py`, then counts:

- **response**: the posts that drew the most comments plus saves, how many times their usual response each drew,
  and what those posts share that the rest do not (hook style, subject, place, whether they name the product);
- **hooks**: the opening lines of those posts ranked by response, and the hook styles (question, confession, list,
  statement) ranked by the mean response of the top posts in each. The best hook leads the hype cut;
- **the launch**: the product, the date as they wrote it and as a day (the days to go), the assets (a folder, a
  link, or only their posts) and the posts already about it;
- **the two palettes**: their year's colors, the product's colors from its own stills, and where the two meet;
- their caption statistics (length, case, emoji, punctuation, hashtags, openings and closings), the like-graph,
  cadence, how long their reels run and how fast they cut, their people and places.

Output: `build/research.json`, a machine draft of `build/taste.json`, and `build/taste.draft.md` (the numbers under
the six headings).

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md`, look at a dozen of their photos (`build/photos/`) and every product still
(`build/library/product/stills/`). Then write `build/taste.md` yourself, one page, six sections headed exactly:

- `## you are`: who they are this year, and the posts their audience answered most: which, why each worked in a
  sentence (subject, hook, color), and what those posts share that the rest do not.
- `## you like`: what their likes and saves have in common (palettes, subjects, pacing, humor), with the accounts.
- `## your style is`: their colors, light, texture, pacing.
- `## your voice is`: how they write: case, length, emoji, punctuation, two or three of their own lines quoted, and
  their best hooks word for word.
- `## the launch`: the product, the date as they gave it, what its assets show, its palette against theirs and the
  colors the film will live in, and what they themselves said about it or their audience.
- `## avoid`: what would be wrong for them (neon, shouting type, stock gloss, whatever the data says), and for the
  product (its colors are never graded away).

Use their numbers, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (the type direction `editorial`,
`kinetic` or `documentary`, `pacing.energy`, `texture` grain, vignette and leaks, `avoid`, `pillars`, `places`).
Put what the person said in the request in `said`: `said.product` (how they describe it), `said.audience` (who it
is for), `said.hook` (a line of theirs they asked to lead with); their words replace anything inferred. Never
change the hooks' order or the launch's date: those are their numbers and their words, in `build/stats.json` and
`build/library.json`. Keep its keys; storyboard.py, grade.py and the critics read them.

## Done when

`build/taste.md` has all six headings and `build/taste.json` matches it. storyboard.py refuses to run without
taste.md.
