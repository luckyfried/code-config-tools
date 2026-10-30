# 1. Research: find the subject's timeline and learn who they are

Goal: `RUN/subject.json` (the subject, its dated posts, the first, the latest, the milestones, the span) and
`RUN/taste.md` (one page, in prose) with `RUN/taste.json`, written before any storyboard. The board builder lays
the films out from `subject.json`; the critics judge them against `taste.md`, and the caption is written in the
voice it describes. The questions this kit's research answers: what the subject is, when it started and where it
is now, what changed along the way in their own words, how their voice changed, and what the progress posts they
like look like.

## Run the research

```
python3 S/scripts/research.py --subject "<the subject in their words>"     # when they named one
python3 S/scripts/research.py                                             # when they named nothing
```

It runs `timeline.py` and `palette.py`, then reads:

- **the subject.** A named subject is matched to their captions and hashtags (`--terms clay,kiln` adds words).
  From a folder of photos (`--photos`), every dated photo in the folder is the subject, whatever its caption says.
  With nothing named, every subject their captions track is weighed, and the one with the longest dated run of
  posts wins; `RUN/subject.json` lists the runs it weighed.
- **the timeline.** The subject's first dated post, its latest, and the milestones between: the posts whose
  captions say so ("milestone", "first", "finally", "sold", "proud", "100th") first, and where their words name
  fewer than two, the biggest visible changes between consecutive photos. The span is the time from the first post
  to the latest, in their own words when a caption says it ("fourteen months in"), else their two dates.
- **the voice over time.** The captions of the oldest third against the newest third: length, how sure they
  sound, two or three lines of each.
- **what changed.** Their own lines about it ("taller", "a year ago", "now"). These win over anything inferred.
- **the progress posts they like.** How each splits the frame (left and right, top and bottom, a grid, one photo),
  measured from the image, and how their captions mark time ("day 1 vs now", "then / now").
- the subject's palette against the palette of what they like, caption statistics, how long their reels run and
  how fast they cut.

Output: `RUN/research.json`, a machine draft of `RUN/taste.json`, and `RUN/taste.draft.md` (under "you are" the
moments in their own captions with their dates: day one, every milestone, the latest, what they say changed).

## Read it like a creative director, then write taste.md

Open `RUN/taste.draft.md`, look at the first and the latest photo and a few between (`RUN/photos/`), and the liked
progress posts (`RUN/library/likes/`). Then write `RUN/taste.md` yourself, one page, five paragraphs that start
exactly:

- **You are** who they are as the maker of this thing: the subject, when it started, the milestones in their own
  words, where it is now, and how their captions changed from the first months to the last.
- **You like** what the progress posts they like have in common: how they split the frame, how they mark time.
- **Your style is** their colors, light, texture and pacing, and the music under it.
- **Your voice is** how they write: case, length, emoji, punctuation, two or three of their own lines quoted, early
  and recent.
- **Avoid** what would be wrong for them (cold color, neon, shouting type, stock gloss, whatever the data says).

Use their dates and their words. American spelling.

Then curate `RUN/taste.json` `moments`, the film's words: one moment for each dated photograph, matched by its
`photo` path, with `line`, what happened in their own words as the card says it on screen (the draft takes the
first clause of the caption's first sentence; rewrite it from the same caption when another clause says the moment
better), and on a chapter (day one, a milestone, the latest) `next`, the line that follows it. A caption whose only
line is a posting or engagement figure ("finally 1000 followers", "100 posts!") gets `"line": ""`: the photograph
holds without words, with its date. Nothing is ever written for them. `said_span` is the clause of theirs that names
the span ("fourteen months in") or `""`; with `""` the closer carries their first and latest dates. A line that only
repeats it gives way to its `next`, so the span is said once, on the closer. Every line set is read on screen, so a
reel of many posts sets fewer: when the lines would not all be read inside 60 s, the draft leaves the line off some
ordinary posts (they pass over their date alone) and names them. Give `"line": ""` to the posts that matter least to
choose which, and the draft keeps the rest.

`seconds` is the length they asked for, in seconds (`30` for "a 30 second reel"), or `null` when they named none.
`call_to_action` is the words they asked the film to end on ("follow for part two"), or `""`: the film asks the viewer
for nothing they did not ask for.

`music` is the brief the film's music is made from when the person has not chosen a track:
`{"mood", "styles", "avoid"}`. `mood` is how the person would describe the feel ("calm", "driving", "cinematic");
`styles` is three to six genre and instrument words that fit this person and this story of day one to the latest
("warm felt piano", "brushed drums"); `avoid` is what would be wrong under it. The bed is composed from the picked
look's own recipe at the board's tempo, and `styles` and `avoid` steer it. The draft takes the mood from their texture
and pace (film grain gives cinematic, a calm pace calm, anything else driving). Music their export or their reels carry gives genre words
only: never an artist, a band or a song, which the music model refuses and which is not a taste.

## Fix what the reading says otherwise

`RUN/taste.json` is a draft: correct anything your reading contradicts (`register`, `pacing.energy`, `texture`,
`avoid`, `music`). If the subject is wrong (the person named something else, or the longest run is not what they meant),
run `research.py --subject "..."` again. Never change a post's date or reorder the timeline: that is their feed, in
`RUN/subject.json`. Keep taste.json's keys; deliver.py drafts the caption from them when you write none.

A caption that says something its photograph does not show (a street named over a cafe, a night walk over
daylight) is fixed where it was written: in the person's export, or for a fixture or seed set in the file that
writes its captions (`evals/fixtures/make_person.py`), each caption written from its photograph. Never correct it
downstream in taste.md, the board or the film's words; the board shows the caption as the post carries it.

## Done when

`RUN/taste.md` has all five headings and `RUN/taste.json` matches it, its `moments` curated. `storyboard.py draft` refuses to run without
taste.md.
