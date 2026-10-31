---
name: month_in_review_stories
description: "Makes a finished Instagram month in review: a reel of the month's diary (the three or four best things that happened, each shown once as its photograph with their own words, the peak first and the rest in date order, onto a wall of the month's posts, with its own sound), a series of three or four 1080x1920 story cards on the same 3D system (one moment a card, each a still and a 15 s animated story), a caption and a review page, in out/, and a template.json in build/ that keeps next month matching, in the look they pick of three (editorial quiet, scrapbook, swiss grid). The month is the one the person names, else the last full month. Use for ANY request to recap someone's month: 'my month in review', 'month in review stories', 'september recap', 'monthly wrap-up', 'monthly reel', 'month highlights', 'photo dump', 'september dump', 'my october photo dump', 'what I posted this month', 'recap my month', 'last month in stories'. The person wants the finished film and stories, not advice: invoke this skill and make them. Runs a fixed pipeline (gather, research, three storyboards, vote and their pick, a timed read of the preview, the render on the 3D motion system, critic, gate, deliver)."
---

# Month in review stories: the pipeline

Someone wants their month as something they can post tonight: a reel of the month, and a series of story
cards, one idea per card, each animated and still.

The reel is the month's diary, in one camera on the 3D motion system (`S/motion/system/three`), each moment shown
once, told as one line, "my september, in four stories", which lands word by word inside the first second: the
month's peak opens it, then each other moment follows in date order, each flying onto the wall with its
photograph on a band of the frame, in its own color, and the line rising across it to above its subject, their own
words on the ground under the band (the day, the place, their caption), the photograph setting into its post's cell
of the wall as the camera moves on; and the closer pulls back to the whole wall: every one of the month's posts with
a photograph and nothing else, each in a cell with its day beneath it, the grid fitted to how many there are, the
moments standing out furthest, "my september, in four stories", where picture and music stop together and hold still,
silent for more than a second. No word stands on a photograph, in the reel or on a card. The closer never draws a calendar or a cell
without a photograph. Every photograph takes one grade toward the set's median lightness first, so the set reads as
one. The story is the kit's; the look is one of three, each with its own type, palette, moves, cuts, closing page and
music: editorial quiet (a serif on wide white space, felt piano), scrapbook (prints on paper, a hand-lettered face, a
book cover to close, ukulele and glockenspiel) and swiss grid (a grotesk and a mono on a strict grid, one accent, a
poster to close, a pulse). The run draws all three and they pick one.

**The kit makes 9:16, 1080x1920 at 30 fps, and no other format**: the reel, every card and every still is vertical.
It makes no square or 4:5 feed posts and no landscape video.

Run **every movement below, in order, every time**. Each one names the file to read and the commands to run; read
the file, the rules that matter live there.

**Ask them one thing only: which look.** Where they can answer you (a conversation), show them `out/boards.png` and
ask which of the three they want (movement 3). Everything else is a sensible assumption the scripts record in the
run's `brief.md`; keep going. Where nobody can answer, pick the look yourself by their taste and say why in one line.
They can redirect once they have the stories in their hands: "make the second one" renders another look.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, tables of their posts, their own notes of what they posted (written as a posts table,
`S/pipeline/0-gather.md`).

## Paths

`S` below means this skill's folder: the folder you read this SKILL.md from, wherever that is. Every command runs in
a fresh shell, and shell variables do not survive between commands, so **write the path out in full in every
command**, for example `python3 /path/to/month_in_review_stories/scripts/qa.py gate`. Run every command from the
workspace root. Each run writes everything under its own build folder, `build/<UTC stamp>/`
(`build/latest` names it), so a rerun never overwrites an earlier one; the deliverables land in the run's `out/` and,
on a green gate, in the workspace's `out/`.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks for what a film needs: python3 with Pillow, ffmpeg, a Chromium (Chromium or Google Chrome, or the
browser in `CHROME_PATH`), and the kit's built composition in `S/motion/dist/`. It installs nothing and takes about a
second. When it prints `"ok": true`, go on. Otherwise it says on its last lines what is missing, one sentence each;
tell the person those sentences and stop, since the stories cannot render without them.

The film is drawn frame by frame in that Chromium, with no window, and encoded with ffmpeg. Working files (the frames,
the browser's profile) go under `~/.cache/code-config/month_in_review_stories/`, never into this folder.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--month M] [--pulled DIR]` | the run's `library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py`, then you write the run's `taste.md` | `month.json`, taste.md with its five headings, the ask, the moments with each one's shot, and the music brief in taste.json |
| 2 | storyboard | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, `storyboard.py check`, `storyboard.py sheets`, look | three boards green, each with its reel sheet and rest sheet, and `out/boards.png` |
| 3 | vote and pick | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally`, show `out/boards.png` and ask, `vote.py pick N` | `winner.json`, the look they picked |
| 4 | produce | `S/pipeline/4-produce.md`, `S/critic/critic.md` | `music.py make`, `clips.py list` and `normalize`, `film.py preview`, `vote.py timed` (the four reads), `film.py render`, look | `out/film.mp4`, `out/cards/` (and `out/series.mp4` when asked) |
| 5 | critic, gate, deliver | `S/pipeline/5-deliver.md`, `S/critic/critic.md` | `vote.py cut`, score the seven rules, `vote.py verdict` (fix once if told), write `caption.md`, `deliver.py` | `GATE GREEN` |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop. If
`research.py` exits 4, the month has fewer than three posts to tell it with: tell the person the sentence it printed
and stop. A month with posts and few photographs is still told: a post with no photograph is a type card, and a
month with none is a set of type cards whose reel closes on its words with no wall.

## Rules that win

- The month is the one they named (pass it as `--month`); otherwise the last full month.
- What they asked for goes into `taste.json` `ask`, from their own words: `counts` true when they ask for their top
  posts, their best performers or their numbers; `seconds` the reel's length when they name one; `series` true only
  when they ask for the cards as one video. Anything they did not say stays false or null.
- The story is their moments: three or four posts, picked by you into `taste.json` `moments` under "You are", each
  named by its photograph (or by its day, when the post has none) with the line it says on screen, one of them the
  peak. A moment is picked for what happened, read from their captions: what they did, made, went to, pulled off, or
  a person they did it with; likes and comments never choose it. The month decides the shape: a month of one big
  event and quiet days around it is told that way, a month of steady days another. When the ask is for their top
  posts or their numbers, each card also shows that post's count, exactly as `month.json` carries it; otherwise no
  likes, comments, followers or totals reach the screen. The board builder composes each card and its count from `month.json` and the picked
  moments; never type a number or a word into a board, and nothing on screen is invented.
- A moment with no photograph is a type card: its words (or its count, when the ask is for them) set big on the same
  ground every card shares. Never make a stand-in picture for it, a flat or tinted field included.
- The look is theirs when they give one: a `template.json` in the workspace (a palette, a font, a numbering such as
  "1/4"), or last month's `build/template.json` when they say "same look as last month". Every card and the reel then
  take that palette, that font and that numbering. A font the kit cannot set is set in the closest family it ships,
  and you name the substitute in your reply (draft and deliver print it). With no look, the colors are read from
  their photographs: a light or dark ground from their median lightness, the accent from their dominant hue.
- The handle on the cards is their username, only when the account or the export gather.py read carries one. With
  none, no card carries a handle line, and nothing else (a name, an email address or its domain) stands in for it.
- Research comes first: nothing is drafted before `taste.md` exists, and every word on screen is in their register
  (lowercase, no exclamation marks).
- The music is the track they placed in `music/`, else made for this film by the studio's music engine from the
  picked look's recipe and their music brief (`taste.json` `music`: the styles they named, empty unless they said,
  and what to leave out; never an artist, band or song), and the sound effects sit under it: one where each beat
  lands, 8 LU under the music.
- The reel shows each moment once, a beat each: the peak first (the first moment by date when there is no peak),
  then the others in date order, each held for what its photograph carries (its words and how busy it is); the peak
  holds longest. The kit makes a reel of 12 to 30 s. When they name a length in that range, the reel runs it to the
  frame, the holds scaled to fit it; with none, it runs 15 s (450 frames), the holds scaled to fit that. A length outside it is refused: draft prints "not delivered: this kit makes a reel of 12 to 30 s,
  and the ask is for N s. Ask for a length in that range." and makes nothing; tell the person that line and stop.
  Every move reveals the moment, and the line carries across every cut.
- Their numbers reach the screen only when the ask is for them, and then every count counts up from zero over its
  hold.
- One card a moment, three or four of them, in date order and numbered as a series: each card the moment's
  photograph on a band (or its type), the line climbing it, the day and place, and its line on the ground under it, each card's shots cut to what its
  photograph carries; the first carries the series' line (and the handle, when there is one), the last signs off into
  next month. Each card is a 15 s animated story and a still from the same
  composition. `out/series.mp4`, every card as one video, is delivered only when their `ask` says `series`.
- The words on screen are the moments' lines in `taste.json`, in their own words; a line is fixed there, never on the
  board.
- Each moment with a photograph carries its `shot` in `taste.json`, written by you from looking at the photograph:
  its subject, the camera's move, the lens, the height and the light. The clip requests carry it whole.
- Look at what you make: the sheets and the strips, with the Read tool, before any score; watch the preview with
  sound before the timed read.
- Do not hand-edit anything in `out/`; run the step again.
- A film renders in chunks saved in the run. An interrupted render (the machine restarted, the session died) is
  resumed by running the same command again: finished chunks are kept and only the missing ones render. Never start
  over, and never delete `preview/chunks/` or `render/chunks/`; a changed board invalidates its chunks by itself. Run `film.py preview` and a long render each in the foreground in one tool call with a 40-minute timeout on that call, never in the background, read its progress in `render/render.log`, and once the first
  chunks land, tell the person their time times the chunks still to go.
- The critics score the cut on the seven rules (R1 to R7, `S/critic/critic.md`) against the bar: a mean of 4.5 with
  none under 4. Under the bar after the first cut you make the one fix `vote.py verdict` names; after it, or when no
  rule under the bar has a lever, the cut is delivered as the best one, and brief.md states every score against the
  bar. The review page is theirs: the film, the cover, the caption, the other two looks and how it was made in plain
  words, never a score, a rule or a critic. A score never blocks the render or the gate.
- Done means `deliver.py` printed `GATE GREEN`; the gate must pass before the film is called ready. Then tell the
  person in three or four plain lines. The first names the reel by the full path from the workspace root that
  deliver.py printed on its last line, copied exactly, for example "Your reel is at
  build/20261026T005754Z/out/film.mp4"; never the bare name `film.mp4`. Then the review page (`out/review.html`,
  which opens the stories too) may be named, the idea of the reel in a sentence, and the order to post the cards.
- "Make the second one" (or the first, or the third, or a look by name) after the film: `vote.py pick N` with that
  number in `out/boards.png`, then movement 4 from `music.py make` and movement 5, in the same run folder.
  A red gate's last line names the failing checks and no film: then say what failed and name no film.
