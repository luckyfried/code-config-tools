---
name: transformation_reel
description: "Makes a finished before-and-after: a vertical 3D motion film of one subject the person has posted over time (their pottery, a renovation, a garden, their art, their training, themselves), every photo dated and in order from the first post to the latest with the milestones marked, a cover and story cards, a then/now card, a caption that states the span, and a review page (the same film square and wide only when they ask for them). Use for ANY request to show how something of theirs changed over time: 'before and after', 'my progress video', 'progress reel', 'a year of my art', 'my renovation before and after', 'my garden over the year', 'my fitness journey as a video', 'my transformation', 'glow-up reel', 'then and now', 'how far I've come', 'day 1 vs now', 'my journey reel', 'timelapse of my progress', 'side by side of my first and latest', 'a comparison of then and now', 'the evolution of my work'. With no subject named, the kit finds the one their feed tracks longest. They want the finished film, not advice: never answer with a plan or ideas; invoke this skill and make it, without asking questions."
---

# Transformation reel: the pipeline

Someone wants to show how one thing of theirs changed: a before and after, a progress video, a glow-up. Run
**every movement below, in order, every time**. Each one names the file to read and the commands to run; read the
file, the rules that matter live there.

**Ask the person one thing only: which of the three looks to make** (movement 3). Everything else is a sensible
assumption the scripts record in `brief.md`; keep going. They can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, a folder of progress posts they liked, your music sources.

## Paths

`S` below means this skill's folder: wherever you read this SKILL.md from. Every command runs in a fresh shell, so
shell variables and `cd` do not carry over: **write the folder out in full in every command**, for example
`python3 .claude/skills/transformation_reel/scripts/qa.py gate`, and run every command from the workspace root.

Everything a run writes is in `build/<run stamp>/` (`RUN` below); `build/RUN` names the current run, and its
`cut/` holds what the render made and `out/` the deliverables, published from `cut/` only on a green gate, with the
making-of, `brief.md`, beside them. `gather.py`
starts a run. Once a run's film is delivered (its `out/film.mp4` is there), the next movement that writes starts a new
run with this one's inputs carried (every path in them moved to the new run), so no rerun overwrites a delivered film;
until then every movement writes in the same run, the one fix's render included. A pick of another look is the one
exception: the person asked for that film instead, so it is made in this run and replaces what `out/` held.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks for Python with Pillow, ffmpeg, a Chromium browser and the kit's built film player, and installs
nothing. It prints what it found and `"ok": true`; without it nothing renders, and each missing thing gets one plain
sentence: tell the person that sentence. The render keeps its frames under `~/.cache/code-config/transformation_reel/`.

## The subject

When the person names it ("my pottery", "the kitchen", "my garden", "me"), pass their words to research:
`research.py --subject "my pottery"`. When they name nothing, run `research.py` with no subject: it picks the
subject with the longest dated run of posts and says which runs it weighed in `RUN/subject.json`.

## The length and the ending

When the person names a length ("a 30 second reel", "make it 15 seconds"), write it in `RUN/taste.json` `seconds`
as a number of seconds; with none named, leave it `null` and the film runs at its own pace. A reel runs the length
asked when it is inside the range its photographs make well: at the short end every photograph is on screen long
enough to be seen (about 0.8 s, 1.2 s for day one, a milestone or the latest) and for its line to be read (0.3 s and
0.12 s a word), with the camera's move to the next and the closer's 2.7 s; at the long end an ordinary photograph holds
at most 3.5 s, a chapter 5.9 s, and the closer 4.8 s; and no reel runs past 60 s. Nine photographs with a short line
each make about 15 to 48 s. `storyboard.py draft` prints the range for the set it read. Every line set is read, so
when a long set's lines would not all be read inside 60 s, some ordinary posts pass over their date alone and draft
prints one plain line naming them; give the posts that matter least `"line": ""` in `RUN/taste.json` to choose which.
An ask outside it is made as near as the photographs allow: the film runs the nearest end of the range, and draft
prints one plain line with the length made and why ("You asked for 45 s; these 4 photographs carry at most 28.2 s, so
the film is 28.2 s."), which `brief.md` carries and your reply tells the person.

The film ends on their own words: the wall of every photograph with their words for the span, or their two dates.
It asks the viewer for nothing unless the person asked for that: only then write their words ("follow for part
two") in `RUN/taste.json` `call_to_action`, and the closer sets them under the dates.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR] [--likes DIR]` | `RUN/library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py [--subject "their words"]`, then you write `RUN/taste.md` and fix `RUN/taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, `storyboard.py sheets`, look at each look's styleframes | check 0 findings, `out/boards.png` |
| 3 | vote and the look | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores and the swap test, `vote.py tally`, show `out/boards.png` and ask which look, `vote.py pick <style>` | `RUN/winner.json` names the look |
| 4 | film | `S/pipeline/4-film.md` | `music.py find`, `storyboard.py snap`, `music.py master`, `film.py draft`, `vote.py timing` (read, fill, again), make the clips `RUN/clips/requests.json` asks for, `film.py render` | `cut/film.mp4`, `cut/cover.png`, `cut/stories/`, `cut/then-now.png` (and the formats they asked for) |
| 5 | critic, gate, deliver | `S/pipeline/5-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `RUN/caption.md`, `deliver.py` | `GATE GREEN` |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed; if `storyboard.py draft` exits 2, the posts make no before and after
(fewer than two dated posts, or all on one day), or the photographs need more than 60 s to be seen and read (`not
delivered: `). Tell the person the one sentence it printed and stop.

## The look

`storyboard.py draft` makes three boards of the same story, one per look (A, B and C: by default cinematic letterbox,
editorial quiet and kinetic type; with `style` in `RUN/taste.json`, that look and the two that differ most from it),
and `storyboard.py sheets` puts them side by side in `RUN/out/boards.png`, each with its name and one sentence. After
`vote.py tally`, show the person `boards.png`, say which one the vote recommends, and ask which look to make; then run
`vote.py pick <style>` with the look they chose. When `RUN/taste.json` has `"ask": false` (nobody to ask), pick the
look by their taste instead, `lean` in taste.json or the vote's recommendation, and say why in one line:
`vote.py pick <style> --why "their captions are short and lowercase, so the quiet look"`.

**"Make the second one."** When, after the film, the person asks for another look ("make the second one", "the
kinetic one", "try the first"), the number is the look's place on `boards.png` and on the review page. Run
`vote.py pick <that look's style>` in the same run: it clears the cut, the music and the delivered film made for the
other look (`out/boards.png` stays), so nothing of it is reused. Then run movement 4 from `music.py find` and movement 5 again, in this run folder, exactly as the
first time.

## Rules that win

- The timeline is theirs: every photo on screen is one of the subject's posts, dated as they posted it, and the
  photos run oldest to latest from the first dated post to the latest; the closer is the wall of every one of them
  from day one to the latest, and the then/now card pairs day one with the latest. The board builder lays every film out from the posts, and `storyboard.py check` and the
  gate refuse anything else.
- The film is the story of what they made, in their own words: every photograph carries the line curated for it in
  `RUN/taste.json` `moments` (what happened, in their caption's words), day one, the milestones and the latest their
  next line too, and a photograph with no curated line is a wordless beat. The closer sets the span in their own words
  when a caption says it ("fourteen months in"), and otherwise their first and latest dates. The only numbers on
  screen are the dates they posted on and a number in their curated words; no count of days, posts, followers or
  anything else is shown.
- Their own words about what changed win over anything inferred from the photos: a caption that says "milestone",
  "first", "finally" marks a milestone before any measured change does.
- Research comes first: `storyboard.py draft` refuses to run before `RUN/taste.md` exists.
- Look at what you make: the styleframes, the strips of the timed cut, the cover, the story cards and the then/now
  card, with the Read tool, before any score; score from those frames, never from a description of the film.
- Make what they asked for: the vertical film with its cover and story cards, the then/now card and the caption.
  The square and 16:9 films render only when they ask for them (`film.py render --also landscape square`, naming
  only those): `square` when they say square, 1:1, or a film for the feed; `landscape` when they say wide,
  landscape, horizontal, 16:9, or a film for YouTube or a screen.
- Design before timing, timing before the finish: a board with a swappable styleframe does not go on to the film, and
  `film.py render` refuses until the timing round passes.
- Do not hand-edit `RUN/storyboards/*/storyboard.json`, `RUN/film.json` or anything in `cut/` or `out/`; the builder decides
  the layout from the posts. Change the posts' subject or taste and run the movement again.
- A film renders in chunks saved in the run, and an interrupted render (the machine restarted, the session died) is
  resumed by running the same command again: `film.py draft` and `film.py render` keep every finished chunk and
  render only the missing ones. Never start over, and never delete `RUN/render/chunks/`; a changed cut gets chunks
  of its own by itself. Run `film.py draft` and a long render each in the foreground in one tool call with a 40-minute timeout on that call, never in the background, and read its progress in
  `RUN/render/<name>.log` (`draft.log`, `report.log`) and the finished chunks under `RUN/render/chunks/`; once the
  first chunks land, their time times the chunks still to go is the estimate to tell the person.
- Generated clips: `film.py draft` writes the shots the film asks for to `RUN/clips/requests.json`. When this session
  can make video, make each one from its photograph and prompt and save it at its `save_as` path before `film.py
  render`, which conforms every saved clip and plays it on its photograph's card. A beat with no clip plays its
  photograph; never call a photograph a clip, to the person or in a caption.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, first where the
  reel is, its full path from the workspace root copied from the last line `deliver.py` printed ("Your reel is at
  build/20261026-014049/out/film.mp4", never the bare `film.mp4`), then that `out/review.html` opens everything, the
  span it covers, the idea of the film in a sentence, and that the other two looks are on the review page if they
  would rather have one of those.
- A gate that has not passed ends `deliver.py` on `not delivered: the gate failed on ` and the failing checks' names,
  with no path: fix them and deliver again, and if you stop there, say what failed and name no film and no path.
