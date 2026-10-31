---
name: trip_recap_reel
description: "Makes a finished trip recap from the person's own posts, photos and clips (or, with no photograph at all, their dated notes): a vertical motion film of one trip (1080x1920), stop by stop, each of their photographs filling the frame with the place's name and their own caption set on it, told in the look they pick from three (cinematic letterbox, analog home movie, scrapbook), cut to music made for that look, with a caption and a review page, saved to out/, plus the same film at 16:9 (1920x1080) or square (1080x1080) and five 1080x1920 story cards when the person asks for them. Use for ANY request to turn a trip, holiday or vacation into a video: 'recap my trip', 'trip recap', 'travel reel', 'Instagram reel of my trip', 'travel vlog', 'highlights of our trip', 'make a travel video', 'our Lisbon week as a video', 'vacation video from my posts', 'a reel of our honeymoon', 'turn my trip photos into a video', 'road trip video', 'travel montage'. The person names a trip by place, dates, album or folder, or names none and gets the most recent trip. They want the finished film, not advice: never answer with a plan; invoke this skill and make it."
---

# Trip recap reel: the pipeline

Someone wants a trip as a film they can post. Run **every movement below, in order, every time**. Each one names
the file to read and the commands to run; read the file, the rules that matter live there.

Ask the person one thing, which of the three looks they want (movement 3), and nothing else. Every other choice is a
sensible assumption the scripts record in `brief.md`; they can redirect once they have the film in their hands.

**Use anything and everything you already have access to**: their connected Instagram and Facebook accounts, a
signed-in browser, an export, their photo folders, your video model, your music sources.

## Paths

`S` below means this kit's folder: the folder you read this SKILL.md from. Write it out in full in every command.
Every command runs in a fresh shell, so a `cd` or a variable from one command is gone in the next: run every command
from the workspace root, for example `python3 /full/path/to/trip_recap_reel/scripts/qa.py gate`.

Every run has its own folder, `build/<run stamp>/`: `gather.py` starts it and writes its name to `build/RUN`, and
every later command works inside it. All the files the movements name (`trip.json`, `storyboards/`, `film.json`,
`frames/`) are in that folder, and the deliverables are in its `out/`. Running the pipeline again starts a new
folder, so nothing a person was given is ever overwritten. `TR_RUN=<stamp>` points the commands at an older run.
The render keeps its frames and its browser's profile under `~/.cache/code-config/trip_recap_reel/`, never in the kit
or the workspace.

## Which trip

Pass what the person named to `research.py`, in their words: `--place "lisbon"`, `--from 2026-10-03 --to
2026-10-08`, `--album "lisbon week"`, or `--folder DIR` (and `gather.py --photos DIR` for a folder of clips they
pointed at). Their words win over anything the data suggests. With nothing named, the most recent trip is used and
the brief says so.

## Start

```
python3 S/scripts/setup.py
```

`setup.py` checks that the machine can make a film (Python with Pillow, ffmpeg, a Chromium browser and the built
composition in `S/motion/dist`) and prints what it found. It changes nothing. When `"ok"` is false, it says on stderr
what is missing, in a plain sentence; tell the person that sentence and stop.

## The movements

| # | movement | read | commands (in order) | done when |
|---|---|---|---|---|
| 0 | gather | `S/pipeline/0-gather.md` | `gather.py --door ... [--pulled DIR] [--photos DIR]` | `library.json` |
| 1 | research | `S/pipeline/1-research.md` | `research.py [--place ... / --from ... --to ... / --album ... / --folder ...]`, then you write `taste.md` and fix `taste.json` | taste.md with its five headings |
| 2 | storyboard | `S/pipeline/2-storyboards.md` | `storyboard.py points`, look and correct, `storyboard.py draft`, `storyboard.py check`, `storyboard.py sheets`, look | three sheets, `out/boards.png`, a clean check |
| 3 | vote and pick | `S/pipeline/3-vote.md`, `S/critic/critic.md` | `vote.py ballot`, fill scores, `vote.py tally`, show `out/boards.png` and ask which look, `vote.py pick --board N --why "..."` | `winner.json` |
| 4 | produce | `S/pipeline/4-produce.md` | `music.py find` (a placed track, else a bed made for the look), `music.py analyze`, `storyboard.py snap`, movement 5, `music.py master`, `film.py render`, `film.py frames` | `out/film.mp4` (and the shapes they asked for) |
| 5 | clips, inside 4 after `snap` | `S/pipeline/5-clips.md` | `clips.py list`, generate with your video model, `clips.py normalize` | `clips.json` |
| 6 | critic, gate, deliver | `S/pipeline/6-deliver.md`, `S/critic/critic.md` | `qa.py check`, `vote.py cut`, score, `vote.py verdict` (fix once if told), write `caption.md`, `deliver.py` | green gate |

Clips (5) run inside movement 4: after `snap`, which lists them from the timed film, and before the render,
which plays them. Every script is `python3 S/scripts/<name>.py`; each answers `--help` with its inputs, outputs and
options.

If `gather.py` exits 3, every door is closed: tell the person the one sentence it printed and stop.

## The look

`storyboard.py draft` tells the trip in three looks, one board each, and `storyboard.py sheets` puts them side by side
in `out/boards.png`. Show the person that picture and ask which look they want, in one plain sentence. Their answer is
`vote.py pick --board N --why "what they said"`. When `taste.json` carries `"ask": false`, the run goes on without
them: pick the look their taste points to and say why in one line, `vote.py pick --board N --taste --why "..."`.

- **Cinematic letterbox**: black bars, slow moves, a film's grade, their words set as a movie title; it closes on a
  title card with the trip's name and dates between the closing bars.
- **Analog home movie**: warm grain, a flickering frame, a date stamp and light leaking in; it closes on their own
  last line under the projector flicker, said once, as the last thing on screen.
- **Scrapbook**: their photos dropped onto paper like prints, taped down and doodled on; it closes as the book
  closes on its cover with the trip's name, the dates and their handle.

Whatever the look, each photograph fills its frame, there is one grade over the whole film (the look's), and each
beat's move is picked from the look's own moves by what the beat holds, never the same move twice running.

When they later say "make the second one" (or the third, or name a look), pick that board and run movement 4 from
`music.py find` and movement 6 again.

## Rules that win

- The trip is theirs: its days, places and people come from their own dates, geotags, captions and folder names
  (`trip.json`), and every place in it appears in the film. Never invent a place, a date or a person.
- Research comes first: nothing is drafted before `taste.md` exists, and every word on screen is in their voice
  (their case, their length, no exclamation marks if they use none).
- The film is about what they did: every stop is a moment of theirs, the photograph they took there with their own
  caption as its line, and the words on screen are the trip's name, their dates, the places' names and their
  captions. Nothing on screen is a count: no distance, no total, no posts and no likes.
- The storyboard is built from the trip, not written by hand: the builder solves the beats, their spans and the
  sound from the stops, the photographs' points and the look's card. You change a film through its inputs (the
  points, the names in `taste.json`, the music) and run the step again; `storyboard.py check` refuses a board whose
  design does not answer its photographs, or that steps outside its look, before anything is timed or rendered.
- Make what they asked for: the vertical film and the caption. The 16:9 and square films and the story cards render only
  when their words ask for them (`film.py render --also landscape square stories`, naming only those; the words are in
  `S/pipeline/6-deliver.md`, "What they asked for"). They are the same spans and cues, the camera framing each
  picture's own shape, never scaled to fit.
- Look at what you make: points.png, the sheets, the frame strips of every film rendered and any story cards, with
  the Read tool, before any score.
- The bar for a board and for the cut: a mean of 4.5 or more with no criterion under 4, cut down to two places, never
  rounded up. A cut still under the bar after its one fix is delivered as the best cut, its scores in `brief.md`,
  never on the review page.
- A clip that did not arrive is substituted, never left as a gap; `brief.md` says which.
- Do not hand-edit `film.json`, `clips.json` or anything in `out/`; change the input and run the step again.
- A film renders in chunks saved in the run (`render/chunks/`). When a render is interrupted (the machine restarted,
  the session died), run the same command again: the finished chunks are kept and only the missing ones render.
  Never start over and never delete `render/chunks/`; a changed cut sets its own chunks aside. Run `film.py preview`
  and a long render each in the foreground in one tool call with a 40-minute timeout on that call, never in the
  background, and read its progress in `render/<name>.log`; once the first chunks land, their time times the chunks
  still to go is the estimate to give the person.
- Done means `deliver.py` printed `GATE GREEN`. Your reply then names the reel first: its full path from the project's
  root, exactly as deliver.py printed it on its last line, in a sentence ("Your reel is at
  build/20261026-014049/out/film.mp4"), never a bare `film.mp4`. Then, in two or three plain lines, any shapes they
  asked for, the idea of the film in a sentence, and `review.html` in the same `out/` folder, which opens everything
  and shows the other two looks.
- A red gate is never a film to show: when deliver.py's last line says the gate failed, your reply says what failed
  and names no film, no path to one, and no review page.
