# 4. Film: timed before it is finished, then rendered as the reel and what they asked for

Goal: in `RUN/cut/` (the set `deliver.py` publishes to `RUN/out/` once the gate passes), `film.mp4` (1080x1920), 30 fps, H.264 High, the length they asked for, or as near it as the photographs make (at most 60 s),
with the music under it; `cover.png` (1080x1920, the reel at the closer's rest, the poster); three story cards
`stories/01-hook.png`, `02-dense.png` and `03-closer.png` (1080x1920); `then-now.png` (1080x1080, day one and the
latest as two prints side by side at their own proportions, their words for the span over them in the look's display
face, each date under its print in the look's text face, on the look's ground); and only when the person asked for
them `film-square.mp4` (1080x1080) and `film-16x9.mp4` (1920x1080). All of it is rendered from the kit's built film
player (`S/motion/dist/`) in a Chromium browser by `S/scripts/render.py`: the 3D stage of `S/motion/system/three`
(the camera, the travel blur, the type) driven by `S/motion/studio/drive`, in the picked board's look.

## Music

The music is the person's: a track they chose, or a bed made for this film from their music brief (`RUN/taste.json`
`music`). In order:

1. A track the person chose: save it as `RUN/music/source.<ext>` and run `music.py find --origin "<where it came from>"`.
2. Otherwise `music.py find` runs `make`, which composes a bed on real instruments from the picked look's own music
   recipe, steered by the brief, at the board's tempo, as long as the storyboard needs and four seconds more. The
   origin line in `RUN/music.json`, `brief.md` and `storyboard.md` says which.

```
python3 S/scripts/music.py find
```

For a track the person chose, `music.py analyze` then finds its beat grid; a composed bed carries its own.

## Snap, master, time the cut

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/music.py master
python3 S/scripts/film.py draft
```

- `snap` lines the board's bars up with the music's grid and writes `RUN/film.json`: the board, its
  seconds, and the track's start and tempo (the track is brought to the board's tempo when its own is within a
  quarter of it, and starts on its first downbeat).
- `master` lays the board's sound cues (a hit where each beat lands, the riser into the closer, the impact its words
  land on) under the bed: the effects stem sits at least 8 LU under the bed by integrated loudness
  (`music.FX_UNDER_BED_LU`), never by its peak. It stops everything on the board's stop, brings the mix to -14 LUFS
  integrated, true peak -1.5 dB, and writes both loudness numbers to `RUN/music.json` and the `Mixed:` line of
  `storyboard.md`; the gate's audio row is red when the effects sit less than 8 LU under the bed.
- `draft` renders the timed cut at half size with its sound (`RUN/draft/film.mp4`) and writes what the timing
  round reads: `RUN/frames/strip-<beat>.png` (12 frames across each beat), `RUN/frames/film-strip.png` (one frame a
  second) and `RUN/draft/check.json` (the figures: length, cuts, the rest line, the hook frame, the sound cues and the
  last one before the stop). It also writes the board's six shot requests to `RUN/clips/requests.json` (the hook's
  world, the stills brought to life, the texture between chapters, each naming its lens, light, move, length and a
  seamless loop).

## The clips

When this session can make video, make each shot in `RUN/clips/requests.json` from its `image` and `prompt` with the
session's video model and save it at its `save_as` path (`RUN/clips/<id>.mp4`). `film.py render` conforms every clip
saved there (`clips.py normalize`) and plays it on its photograph's card over its beat; `RUN/clips.json` records each
request as generated or as the photograph. A beat with no clip plays its photograph with the card's own move, and a
photograph is never called a clip: not in `brief.md`, not on the review page, not in your reply. A render that
played no clip was made by a session with no video model, so the verdict counts no lever for the shots in that run.

## The timing round

```
python3 S/scripts/vote.py timing
```

As the motion designer, open every strip and the film strip full size with the Read tool, watch `RUN/draft/film.mp4` with its sound, and read the figures in
`RUN/draft/check.json`. Fill in `read` in `RUN/critic/timing.json` with the four reads (`S/critic/critic.md`), a
sentence or more each, from the frames you saw: `carried`, `sound`, `belongs` and `held`; then `repeats` (the beats that read the same as
the one before) and `verdict` (pass or fix). Run `vote.py timing` again. It passes when the read says pass, nothing
repeats, and the first event lands in the first 30 frames. A read of `sound` from the cue table alone is not a
read: when nobody in the session can hear the draft, put `sound` in `not_read`, and the round says it was not heard. When it does not pass, the fault is in what the builder
read (the posts, the captions, the music): fix it there, run movements 2 to 4 again, and name what failed in
`brief.md`.

## Render

```
python3 S/scripts/film.py render
python3 S/scripts/film.py render --also landscape square    # naming only what they asked for
```

`render` refuses until the timing round passes for this board. It lays the board out for each format from the same
posts (a photograph box that fits 9:16 is placed again for square and wide, never scaled to fit), renders the reel,
its cover and its story cards (the reel at the board's rest moments), makes the then/now card from day one's and the
latest's photographs in the look's type and colors, and lays the mastered music under each film. `--also` adds the 16:9 film
and the square film, each only when the person asked for it: `square` when they say square, 1:1, or a film for the
feed; `landscape` when they say wide, landscape, horizontal, 16:9, or a film for YouTube or a screen. A render replaces `RUN/cut/` whole, so nothing an earlier render made and this one was not asked for stays, and `RUN/render/report.json` `made` records what was asked. Every font or photograph that failed to load
(`FONT_ERROR`, `IMAGE_ERROR`) and every job that failed is printed. Every film reaches `cut/` only once all of them and
the cards are made, so a failed or killed render leaves `cut/` as it was. `RUN/render/report.json`, which the gate
reads, is the report of the films in `cut/`: it goes before the first of them changes and comes back after the last,
so a render stopped between two files leaves no report, and the gate refuses until a render finishes. Last, render
runs `qa.py check` on the new cut, so the figures the critics read are always the cut's own.

It renders on the graphics card when the machine has an NVIDIA one and on the processor otherwise; `render.py`
decides both, and how many browser pages draw at once, from the machine. An attempt that loses its graphics context or
comes out one flat colour renders again in a fresh browser, up to three attempts. `RUN/render/report.json` names
where the film rendered.

Every film, the draft's too, renders in chunks saved in the run under `RUN/render/chunks/` (60 frames each on the
processor, the whole film as one chunk on an NVIDIA card), and is joined from them once every chunk is whole. A chunk that
renders longer than ten minutes is cancelled and rendered again, up to three attempts. An interrupted draft or render (the machine restarted, the session
died) is resumed by running the same command again: the finished chunks are kept and only the missing ones render,
and the printout says how many (`render report: 120 chunks kept, 264 rendered, 0 to go`). Never start over, and
never delete `RUN/render/chunks/`: a changed cut, a re-cropped photograph or an updated kit renders into chunks of
its own by itself. One render runs in a run at a time; a second one exits and names the running one's log.

Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Scratch files stay under the build folder, never `/tmp`, which other sessions share. Its progress is in
`RUN/render/report.log` (`RUN/render/draft.log` for the draft): each chunk logs its progress as it renders, and the
chunks already made are the `<first>-<last>.mp4` files under `RUN/render/chunks/`. Once the first chunks land, their
time times the chunks still to go is the estimate to tell the person.

## Look before the critics do

Open `cut/then-now.png`, `cut/cover.png` and every `cut/stories/*.png` with the Read tool. Text cut off, a photograph cropped, a date that
is not the post's, a card where day one and the latest do not read as a pair: the builder made it from the posts,
so the fault is in the posts it read; fix the research and run movements 2 to 4 again.
