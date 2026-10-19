---
name: birthday_tribute_reel
description: "Makes a finished birthday, anniversary or tribute video for one person in the user's life, from the photos, videos and comments the two of them share on Instagram: a 30-60 s vertical motion film (1080x1920), the same cut square for the feed (1080x1080), one 1080x1350 card, a caption that names them, and a review page, saved to out/. Use for ANY request for a video, reel or slideshow made for someone, however it is phrased: 'make a birthday video for <name>', 'birthday reel for @handle', 'a video for my mom's 60th', 'my best friend turns 30, make her something', 'anniversary video for us', 'something for our five years', 'a reel for our anniversary', 'tribute reel for my friend', 'a tribute video for my dad', 'a video of me and <name> for her birthday', 'happy birthday post with our photos', 'make a montage of us for <name>', 'farewell video for my coworker', 'a thank-you video for my sister'. The user names someone (a handle, a name, or 'us') and maybe the occasion and the date. They want the finished film, not advice: never answer with a plan or ideas; invoke this skill and make it. Runs a fixed pipeline (gather everything you can reach, find the named one and everything the two share, research, three storyboards, a critic vote, Remotion motion production with generated clips, critic, gate, deliver) without asking questions."
---

# Birthday and tribute video: the pipeline

Someone wants a video for one person: a birthday, an anniversary, a tribute. Run **every movement below, in
order, every time**. Each one names the file to read and the commands to run; read the file, the rules that matter
live there.

**Never ask the person a question.** Make the sensible assumption, let the scripts record it in `out/brief.md`,
and keep going. They can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser (and through it the named one's own profile), an export, their photo folders, your video model,
your music sources.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually
`.claude/skills/birthday_tribute_reel`). Shell variables do not survive between commands, so **write the path out
in full in every command**, for example `python3 .claude/skills/birthday_tribute_reel/scripts/qa.py gate`. Run
every command from the workspace root. Deliverables go in `out/`; everything else goes in `build/`.

## Start

```
python3 S/scripts/setup.py
mkdir -p out build
```

`setup.py` finds or installs Pillow (a venv in the skill folder when pip is locked), ffmpeg, node (a portable one
under `S/.cache/` when there is none) and the Remotion project's packages and browser. The first run takes a minute
or two; later runs take a second. It prints `"engine": "remotion"`, or `"stills"` when node cannot run here.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--feed DIR] [--photos DIR]` | `build/library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py --who "..." [--occasion "..."] [--date ...] [--words "..."]`, then you write `build/taste.md` and fix `build/taste.json` | taste.md with its five headings |
| 2 | storyboards | `S/pipeline/2-storyboards.md` | `storyboard.py draft`, edit, `storyboard.py check`, `storyboard.py sheets`, look | three sheets |
| 3 | vote | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally` | `build/winner.json` |
| 5 | clips | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `build/clips.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` or `make`, `music.py analyze`, `storyboard.py snap`, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4`, `out/film-square.mp4`, `out/card.png` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `build/caption.md`, `deliver.py` | green gate |

Clips (5) run before the render of movement 4 because the film places them. Every script is
`python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## Rules that win

- The person's own words win: who the film is for, what the occasion is, and anything they said about the named
  one. Pass them to `research.py` as they said them (`--who "@dani.reyes"`, `--who "my mom"`, `--who us`,
  `--occasion "her 30th"`); the data fills in only what they did not say.
- Every photo on screen is one the two of them share: a post that tags or mentions the named one, a story with
  them, one of the named one's own posts of the two. Never a photo of the person alone or of someone else.
- Research comes first: nothing is drafted before `build/taste.md` exists. Every word on screen is in the voice of
  whoever said it: the person's lines in their case and length, the named one's answers as they wrote them.
- Look at what you make: the style sheets, the frames of both films and the card, with the Read tool, before any
  score.
- A clip that did not arrive is substituted, never left as a gap; `brief.md` says which.
- Do not hand-edit `build/film.json`, `build/clips.json` or anything in `out/`; change the storyboard or taste
  and run the step again.
- Done means `deliver.py` printed `GATE GREEN`. Then tell the person, in three or four plain lines, where the film
  is (`out/review.html` opens everything), the idea of the film in a sentence, and that "do the second one" makes
  the runner-up.
