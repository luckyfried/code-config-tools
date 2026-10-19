# The critics

Three critics judge the grid directions (movement 3); two of them judge the finished nine and the film (movement
6). Each one is a voice you take on in turn, with its own eye. Score what a person scrolling their profile would
notice, and say why in plain words.

## The panel

**The designer.** An art director who has built feeds for photographers and brands. Looks at craft, post by post
and as a grid: is each photo cropped to its subject at 4:5; does the grade hold the nine together; is any type a
system (two faces, a scale, consistent placement, their own words) or a default; do the nine sit well above the
real grid, as its next chapter and not a different account; does anything collide or crop badly.

**The editor.** Cuts social films and plans feeds. Looks at rhythm and story: do calm and busy alternate; do two
neighbors read as one; does the posting order build the grid well day by day, not only once all nine are up; does
the before-and-after film show the change plainly, with cuts on the music and an ending worth sharing.

**The person.** Speaks in the first person, from `build/taste.md`, their captions and `out/audit.md`: "is this me?"
Their photos, their colors, their voice, nothing on the avoid list, nothing their own numbers say their followers
pass over. Would I post these nine, in this order, next week? The person breaks a tie in the vote.

## The seven criteria (1–5 each)

| key | criterion | a 5 | a 3 or lower |
|---|---|---|---|
| `professional` | the nine look like a professional art director designed them | every crop on its subject, one grade, a grid you would screenshot | a template feel, a crop that loses the subject, a post that looks unfinished |
| `them` | it is unmistakably them | their photos carry it, their palette, their words, the patterns their numbers favor | stock mood, a voice that is not theirs, something from their avoid list |
| `rhythm` | the grid reads as one feed | calm and busy alternate, no two near copies touch, rows hold together | two busy frames side by side, the same scene three times, a row that jumps |
| `palette` | the colors hold together and sit well above the real grid | one family of color across the nine that answers the audit's palette finding | a clash the audit already named, a cold post in a warm feed |
| `type` | where there is type it is a system in their words | two faces, a scale, their own lines, the same placement everywhere; no type at all is a 4 when the direction has none | default fonts, a stray size, words that are not theirs, a placeholder |
| `film` | the before-and-after film shows the change plainly | the findings read on the real grid, the nine land on the beat, the end holds the whole profile | findings you cannot read, cuts off the beat, a beat that looks empty |
| `post` | they would post these nine, in this order, next week | yes, without changing a thing; the captions sound like them | they would swap posts, reorder them or rewrite the captions |

## The directions (movement 3)

For each board look at `build/storyboards/N/sheet.png` (the nine above the line, the real grid below), its
`frames.png`, and read its `storyboard.md`. Score it as each critic in turn in `build/vote/scores.json`. Judge the
nine against the real grid and against `out/audit.md`: a direction that repeats a problem the audit names (more
text when screenshots broke the grid, a clashing color, busy beside busy) scores low on `rhythm`, `palette` or
`them`. Write one paragraph per board per critic, at least 25 words: what works, what fails, the one change you
would make. The three directions are meant to be different; the scores should show which suits this person.

## The cut (movement 6)

The designer and the person score what ships. Look, actually look:

- `out/grid-after.png`, the nine in place over the real grid;
- every `out/posts/NN.png` full size with the Read tool;
- `out/plan.md`, the order and the captions;
- every `build/frames/NN-*.png`, one per beat of the film;
- `build/qa/check.json` (the measured checks) and `build/render-report.json`.

Never score from memory of the storyboard. Fill in `build/critic/cut-N.json` and run `vote.py verdict`. When a
score is below 4, name the one change that fixes the worst thing in the paragraph, using the levers below.

## The levers

- Which photo goes in which post, the words on a type post or a tile, the film's lines, beat lengths, transitions,
  clip prompts: the winner's `build/storyboards/N/storyboard.json`, then `storyboard.py check`, `snap`,
  `film.py render`.
- A photo: `grade.py photos FILE`, then `"graded/<name>.jpg"` in the post.
- A caption or the order's dates: `build/plan.json`, then `plan.py check` and `snap`.
- The grade and texture: `taste.json` (`palette`, `texture`), `grade.py recipe`, `grade.py photos`, `clips.py
  normalize`.
- The music: another track at `build/music/source.<ext>`, or `music.py make --mood calm|drive|film --bpm N`, then
  `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`.
