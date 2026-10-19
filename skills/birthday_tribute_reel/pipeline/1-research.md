# 1. Research: who the film is for, and everything the two share

Goal: `build/taste.md` (one page, in prose) and `build/taste.json`, written before any storyboard. Everything
downstream reads taste first. The questions this kit's research answers: who exactly the film is for, what the
occasion is, which photos and videos the two share, what they say to each other and how, and how the friendship
changed over time.

## Find the named one and count

```
python3 S/scripts/research.py --who "<their words for who it is for>" [--occasion "<their words>"] [--date YYYY-MM-DD] [--words "<anything else they said about them>"]
```

Pass the person's own words: a handle (`"@dani.reyes"`), a name (`"Dani"`, `"my mom, Ana"`), or `"us"` for an
anniversary. `research.py` runs three steps and then reads the result:

- `shared.py` finds the named one. An exact handle wins; a name is matched against tagged accounts, mentions,
  comment authors and feed names; "us", "my partner" or no match takes the account the person shares the most
  photos with and records that as an assumption. It writes the runner-up and the account the person talks to
  most, so a busy commenter is never mistaken for the named one. Then it collects **every photo and video the two
  share** (posts and reels that tag or mention them, stories with them, the named one's own posts that tag the
  person), **the comments they traded** (both sides, paired into a line and its answer) and the voice of each side,
  **the occasion** (their words first, then a caption such as "dani turns 30 on october 24"), **the first and the
  latest photo together**, **the eras** (chapters of the friendship by place and months) and **the love lines**
  (the person's own short lines to or about them). Output: `build/shared.json`, `build/ask.json`.
- `picks.py` prepares the shared photos (`build/photos/`, `build/picks.json` with each photo's era, its source and
  its analysis, plus the opener, first, latest and best chapters).
- `palette.py` reads three palettes: the person's own, the named one's (from their feed), and the one the two
  share, from the photos of them together. The film's colors come from the shared palette.

Output: `build/research.json`, a machine draft of `build/taste.json`, and `build/taste.draft.md` (the numbers
under the five headings).

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md` and look at a dozen of the shared photos (`build/photos/`) and a few of the named
one's own posts. Then write `build/taste.md` yourself, one page, five paragraphs that start exactly:

- **You are** the two of them: who the film is for, how you know (their words, the tags, the comments), the
  occasion, and the story of the friendship from the first photo to the latest, chapter by chapter.
- **You like** what the two do together and what their photos are of; the shared palette and where each side's
  palette pulls it.
- **Your style is** the colors, light, texture and pacing the film should have, from both feeds.
- **Your voice is** how each of them writes, with two or three of their own lines quoted from each side.
- **Avoid** what would be wrong for them (cold grading, neon, jokes at the named one's expense, stock gloss,
  whatever the data says).

Use their numbers, their account names and their words. American spelling.

## Fix taste.json where the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (`occasion` label and title, the type
direction `editorial`, `kinetic` or `documentary`, `pacing`, `texture`, `avoid`, `pillars`, the `love_lines` list
in the order they should play). Keep its keys; storyboard.py, grade.py and the critics read them. Once you edit it,
change `written_by`, so a rerun of research.py leaves your version alone.

## Done when

`build/taste.md` has all five headings and `build/taste.json` matches it. storyboard.py refuses to run without
taste.md.
