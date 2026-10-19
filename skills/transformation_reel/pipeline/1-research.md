# 1. Research: find the subject's timeline and learn who they are

Goal: `build/subject.json` (the subject, its dated posts, the first, the latest, the milestones, the span) and
`build/taste.md` (one page, in prose) with `build/taste.json`, written before any storyboard. Everything downstream
reads them. The questions this kit's research answers: what the subject is, when it started and where it is now,
what changed along the way in their own words, how their voice changed, and what the progress posts they like
look like.

## Run the counting

```
python3 S/scripts/research.py --subject "<the subject in their words>"     # when they named one
python3 S/scripts/research.py                                             # when they named nothing
```

It runs `timeline.py`, `picks.py` and `palette.py`, then reads:

- **the subject.** A named subject is matched to their captions and hashtags (`--terms clay,kiln` adds words).
  With nothing named, every subject their captions track is weighed, and the one with the longest dated run of
  posts wins; `build/subject.json` lists the runs it weighed.
- **the timeline.** The subject's first dated post, its latest, and the milestones between: the posts whose
  captions say so ("milestone", "first", "finally", "sold") first, and where their words name fewer than two, the
  biggest visible changes between consecutive photos. The span is the time from the first post to the latest
  ("14 months").
- **the voice over time.** The captions of the oldest third against the newest third: length, how sure they
  sound, two or three lines of each.
- **what changed.** Their own lines about it ("taller", "a year ago", "now"). These win over anything inferred.
- **the progress posts they like.** How each splits the frame (left and right, top and bottom, a grid, one photo),
  measured from the image, and how their captions mark time ("day 1 vs now", "then / now").
- the subject's palette against the palette of what they like, caption statistics, how long their reels run and
  how fast they cut.

`picks.py` chooses the posts the film carries (`build/picks.json`): the first, every milestone and the latest,
then the posts that best fill the longest gaps, in date order. Output: `build/research.json`, a machine draft of
`build/taste.json`, and `build/taste.draft.md` (the numbers under the five headings).

## Read it like a creative director, then write taste.md

Open `build/taste.draft.md`, look at the first and the latest photo and a few between (`build/photos/`), and the
liked progress posts (`build/library/likes/`). Then write `build/taste.md` yourself, one page, five paragraphs that
start exactly:

- **You are** who they are as the maker of this thing: the subject, when it started, the milestones in their own
  words, where it is now, and how their captions changed from the first months to the last.
- **You like** what the progress posts they like have in common: how they split the frame, how they mark time.
- **Your style is** their colors, light, texture and pacing.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted, early
  and recent.
- **Avoid** what would be wrong for them (cold grading, neon, shouting type, stock gloss, whatever the data says).

Use their dates, their numbers and their words. American spelling.

## Fix what the reading says otherwise

`build/taste.json` is a draft: correct anything your reading contradicts (the type direction `editorial`,
`kinetic` or `documentary`, `pacing.energy`, `texture`, `avoid`, `progress_style.lead` `lr` or `tb`). If the
subject is wrong (the person named something else, or the longest run is not what they meant), run `research.py
--subject "..."` again. Never change a post's date or reorder the timeline: that is their feed, in
`build/subject.json`. Keep taste.json's keys; storyboard.py, grade.py and the critics read them.

## Done when

`build/taste.md` has all five headings and `build/taste.json` matches it. storyboard.py refuses to run without
taste.md.
