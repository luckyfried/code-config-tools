---
name: birthday_tribute_reel
description: "Makes a finished birthday, anniversary or tribute video for one person in the user's life from the photos, videos and comments the two of them share on Instagram: a vertical motion film (1080x1920) of the length asked for, 20 to 60 s, in one of three looks (scrapbook, analog home movie, editorial quiet) the user picks from a sheet, a caption that names them and a review page, saved to out/, and the same film square (1080x1080) or wide (1920x1080) and stills when asked for. Use for ANY request for a video, reel or slideshow made for someone: 'make a birthday video for <name>', 'birthday reel for @handle', 'a video for my mom's 60th', 'my best friend turns 30, make them something', 'anniversary video for us', 'tribute reel for my friend', 'farewell video for my coworker', 'graduation video for my brother', 'retirement video for my dad'. The user names someone (a handle, a name or 'us') and maybe the occasion, the date and a look. They want the finished film, not advice: never answer with a plan; invoke this skill and make it. Runs a fixed pipeline (gather, find the named one and what the two share, research, three storyboards, the look, the timed read, production, critic, gate, deliver)."
---

# Birthday and tribute video: the pipeline

Someone wants a video for one person: a birthday, an anniversary, a farewell, a graduation, a retirement, a
tribute. Run **every movement below, in order, every time**. Each one names the file to read and the commands to
run; read the file, the rules that matter live there.

**Ask the person one thing only: which look.** Everything else is a sensible assumption the scripts record in
`B/brief.md`; they can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser (and through it the named one's own profile), an export, their photo folders.

## Paths and commands

`S` below means this skill's folder: the folder you read this SKILL.md from, wherever that is. Every command runs in
a fresh shell, so nothing set in one command (a variable, a `cd`) reaches the next: **write S out in full in every
command**, for example `python3 /path/to/birthday_tribute_reel/scripts/qa.py gate`, and run every command from the
workspace root.

Every run works in a folder of its own, `build/<run stamp>/` (UTC, for example `build/20261020T151200Z/`), called
`B` in these files; `build/latest` names it and every script finds it there. `gather.py` starts a run. A delivered
run is never written again: the next script copies it to a new stamp and works there, so a rerun never overwrites
an earlier build. The deliverables of the latest delivered run are in `out/`. The render keeps its frames and its
browser profile under `~/.cache/code-config/birthday_tribute_reel/`, never in the workspace.

## Start

```
python3 S/scripts/setup.py
mkdir -p out build
```

`setup.py` installs nothing. It checks for Python with Pillow, ffmpeg, a Chromium the render can start and the
built film in `S/motion/dist/`, and prints them as JSON with `"ok": true`. With `"ok": false` it names what is
missing in a plain sentence, and no film can be made until that is fixed.

## The film

The kit makes one film, "the year with you": the moments the two had this year, one card each, in the order they
happened. Each photograph flies onto a wall of the year and, as it lands, the moment's name, in the words of its own
caption, rises on the photograph, with the rest of that caption, or the line the two traded under the post, under
it; the photograph settles into its place on the wall, and at the close a sheet carrying the whole wall falls shut
with the giant age cut through it (an anniversary's years; the name for a farewell, a graduation, a retirement or a
tribute, whose hook names the occasion), the last figure punches through it, the wish rises and the picture and
sound stop.

The film is drawn in three looks, from the same photographs and words: A **scrapbook** (taped prints on paper,
hand-lettered), B **analog home movie** (warm grain, a flickering frame, light leaks) and C **editorial quiet** (a
serif, wide margins, slow fades). When the person names a style (`B/taste.json` `style`), that style is A and the two of these three that
differ most from it are B and C. Each look's style card decides the faces, colors, finish, easing, music recipe
and the moves and cuts it allows; each card's move is chosen for what its photograph holds.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--feed DIR] [--photos DIR]` | `B/library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py --who "..." [--occasion "..."] [--date ...] [--words "..."] [--line "..."] [--seconds N]`, then you write `B/taste.md` and fix `B/taste.json` (a style the person named goes in its `style`) | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, look at the hook, write each photograph's subject box and each clip's shot, `storyboard.py check`, `storyboard.py sheets`, look | three boards, their sheets and `out/boards.png` |
| 3 | the look | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally`; show `out/boards.png` and ask which look, then `vote.py pick N --reason "..."` | `B/winner.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py make`, `storyboard.py snap`, `clips.py list`, `clips.py normalize`, `music.py master`, `film.py preview`, `vote.py timed`, read its 24 frames and fill the four reads, `qa.py timed`, `film.py render [--also ...]`, `film.py frames` | `out/film.mp4`, `out/post.png`, `out/story.png` (and only the asked-for square, wide or stills) |
| 5 | critic, gate, deliver | `S/pipeline/5-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, read its 24 frames and score, `vote.py verdict` (below the bar: fix the worst thing it quotes, once), write `B/caption.md`, `deliver.py` | `GATE GREEN` (or `GATE OPEN` once the fix is spent) |

Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed and this run makes no film: tell the person that, then the one
sentence it printed, and stop.

## The look

After `vote.py tally`, show the person `out/boards.png` (the three looks side by side: the hook, a card and the
closer of each) and ask which look they want, in one line, naming the tally's pick as the default. Their answer is
`vote.py pick N --reason "<their words>"`. When `B/taste.json` has `"ask": false`, pick by taste
instead and say why in one line: `vote.py pick N --by taste --reason "<one line>"`. Then movement 4 makes that look.

The review page offers the other two looks. When the person later says "make the second one" (or the third), run
`vote.py pick N` for that look, then movement 4 from `music.py make` and movement 5 again: the run copies itself to
a new stamp, and the music, preview, reads, render and delivery are made again for the new look; nothing from the
other look is reused.

## Rules that win

- The person's own words win: who the film is for, what the occasion is, the look, and anything they said about the
  named one. Pass them to `research.py` as they said them (`--who "@dani.reyes"`, `--who "my mom"`, `--who us`,
  `--occasion "turns 30"`, their own line for the wish as `--line "..."`); the data fills in only what they did not
  say. The age (an anniversary's years) is shown only when the person said it; a caption never supplies it, and with
  none the name they call them takes its place. No pronoun is ever assumed for either of them.
- The film runs the length the person asked for, from 20 to 60 s: pass it as `--seconds N`. With none asked, the
  photographs set it inside that range. Outside it, `research.py` prints `not delivered: <n> s is outside the 20–60 s
  this kit makes, ...` and makes nothing: tell the person that line and stop; never make a film of another length in
  its place.
- Each card holds as long as its photograph asks (the time to take it in, its people, its words), the peak of the
  year longest after a fast run of the three cards before it, and the cards share the length in proportion to those
  holds: no beat grid (`pipeline/2-storyboards.md`).
- The photographs that show the named one lead and close the film: a post that tags them or their own post of the
  two first, then a caption that names them. When nothing in the posts tags or names them, every photo is used and
  research prints an `assumption:` line naming which photos and why; `deliver.py` repeats it as `assumed: ...`, and
  the reply says it.
- Every photo on screen is one the two of them share: a post that tags or mentions the named one, a story with
  them, one of the named one's own posts of the two or that the two talked under. Never a photo of the person
  alone or of someone else.
- Every word on screen is one the two of them wrote: a caption, a comment, an answer, set as they wrote it, plus
  the closer's wish, name, number, date and sender. Never write a line for either of them. Research comes first:
  nothing is drafted before `B/taste.md` exists.
- Every card is a moment of the two: a thing they did, made or went to, a place they stood, the people they were
  with, in their own words. The one number on screen is the one they would say out loud, the age (an anniversary's
  years, none for any other occasion); posts, likes, comments and days are never shown.
- A beat the storyboard wants as a generated clip carries the clip's request (subject, what moves, the camera, the
  lens, the light) in `storyboard.json`. When no video model made it, the beat shows its photograph and is called a
  still, never a clip.
- Look at what you make: `out/boards.png` and the sheets, the hook's photograph, each clip's photograph, the 24
  frames `vote.py timed` cuts from the preview, the 24 frames `vote.py cut` cuts from the film, `out/post.png`,
  `out/story.png` and any stills that were asked for, each with the Read tool, before any read or score. A read or a
  score names the frames it was made from.
- The reel renders alone. `film.py render --also landscape square stories` adds the wide film, the square film and
  the stills, each only when the person's words asked for it (`S/pipeline/5-deliver.md` says which words); the gate
  fails on any of them in `out/` that nobody asked for.
- Do not hand-edit `B/film.json` or anything in `out/`; change the storyboard or taste and run the step again.
- A film renders in chunks saved in the run. A render that was interrupted (the machine restarted, the session died)
  is resumed by running the same command again: the finished chunks are kept and only the missing ones render. Never
  start over and never delete `B/render/chunks/`; a changed cut renders new chunks of its own. Run `film.py preview`
  and a long render each in the foreground in one tool call with a 40-minute timeout on that call, never in the
  background, and read its progress in `B/render/<name>.log`; each chunk's frames and the seconds and percent on its
  lines are the estimate to tell the person.
- Done means `deliver.py` printed `GATE GREEN`: every check passed and the critics scored the cut at the bar (a mean
  of 4.5, none under 4). `GATE OPEN` means the best cut is delivered below the bar (or with a read that could not be
  made), with its scores in `B/brief.md` only: say so in one plain line and never call it ready. Then tell the person
  in three or four plain lines. The first names the reel by the full path from the workspace root that deliver.py
  printed on its last line, copied exactly, for example "Your reel is at build/20261020T151200Z/out/film.mp4"; never
  the bare name `film.mp4`. Then the review page (`out/review.html`) may be named, with the other two looks it
  offers, and the idea of the film in a sentence.
  A red gate's last line is `not delivered: the gate failed on <checks>`: then say what failed and name no film.
