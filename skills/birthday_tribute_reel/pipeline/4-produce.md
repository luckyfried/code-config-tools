# 4. Produce: the film, cut to its music

Goal: `out/film.mp4` (1080×1920), 30 fps H.264 High with AAC 192 kbps at −14 LUFS and the length the person asked for (20–60 s; within 1 s of the board's length), rendered from the
kit's film (`S/motion/studio`, built into `S/motion/dist/`) by `scripts/render.py`, with `out/post.png` (1080×1080, the closer laid out for the feed) and
`out/story.png` (1080×1920, the hook at rest, the review page's cover). Only when the person asked for them: `out/film-square.mp4` (1080×1080) and
`out/film-wide.mp4` (1920×1080), held to the same, and `out/stills/<format>-<beat>.png`, the settled frames of the
board's hook, peak card (the middle card when no moment is the peak) and closer in each rendered format.

## Music

The music belongs to the look: the track the person chose, else a bed the music engine makes for the chosen look.

1. A track the person gave you or asked for: save it as `B/music/source.<ext>`, run
   `music.py find --origin "<where it came from>"`, then `music.py analyze` to read its tempo, beats and downbeats.
2. Otherwise `music.py make`: the engine plays the chosen style card's music recipe, turned by the person's music
   brief (`taste.json` `music`: its `styles` words can name another recipe, its `avoid` words take instruments out),
   in the key of the colors the two share, at the tempo of the recipe's range nearest the board's own. It writes its
   own beats and downbeats, and the sound effects in the recipe's voices. `music.json`'s origin names the recipe,
   the key and the tempo.

```
python3 S/scripts/music.py make
```

## Time, clips, master, preview, the timed read, render

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/clips.py list
python3 S/scripts/clips.py normalize [--why "..."]
python3 S/scripts/music.py master
python3 S/scripts/film.py preview
python3 S/scripts/vote.py timed
python3 S/scripts/qa.py timed
python3 S/scripts/film.py render
python3 S/scripts/film.py frames
```

`film.py render` makes the reel alone. Add `--also` with what the person's words asked for, and nothing else:
`landscape` for the wide film, `square` for the square film, `stories` for the stills (for example
`film.py render --also square`). The words that turn each one on are in `S/pipeline/5-deliver.md`.

- `snap` cuts the board that won the vote (`B/winner.json`) and refuses with no winner. It times the board to the
  music: the track's tempo, folded by octaves into 108–132 bpm (the board's own tempo when it cannot be folded in), keeps the board's length at that tempo: the hook's hit and the closer's fall and punch land on its beats, and the cards share the rest by their holds,
  and writes `B/film.json` with the reel's sound cues, one where each beat lands: a hit as the age and each moment's name land, the riser and impact of the closer's cover, a hit as the last figure punches home and the stop on the wish. Before it writes anything a
  beat the panel named in the swap test is refused while unchanged, and the board's checks run again at the new
  tempo in all three formats (the frame, the length, the hook inside the first 30 frames, the words, the
  photographs). It also refuses while the board's sheets read a line under the floor. Change what it names in the
  board's `storyboard.json` and run it again.
- `clips.py list` writes `B/clips/requests.json`, the three clips the timed board asks for (the hook's world,
  texture between chapters, a still brought to life), each a prompt written from its beat's `shot` with the lens,
  height, light and length measured from its photograph, and the file to save it as. When this session has an
  image-to-video model, make each clip from its named photograph with its prompt and save it there. Then `normalize`
  conforms what arrived and places it on its card; a clip that did not arrive stands in as the card's layered move
  over its still photograph, and `--why` says why (for example `--why "no video model in this session"`).
- `master` lays the sound cues under the music (`hit`, `riser`, `impact`, each synthesised where its beat lands), the
  effects scaled by loudness to `FX_UNDER_BED_LU` (8) LU under the bed, trims it to the film and brings it to −14 LUFS
  integrated, true peak about −1.5 dB. It prints both loudness numbers and writes them to `music.json` and to
  `storyboard.md`'s `mixed:` line; the gate's audio row is red when the effects sit less than 7 LU under.
  `B/music/bed.wav` is the music trimmed to the film, `B/music/fx.wav` the cues alone.
- `preview` renders the reel at half size and measures it: the cuts as planned and as the picture shows them, cuts a
  minute, each second's change, the hook event's frame, with a 1 fps and a 2 fps strip (`B/preview/`).
- `vote.py timed` is the editor's read of the timed cut, before anything renders at full size: it cuts 24 frames of
  the preview at equal spacing into `B/critic/timed-<cut>/`. Read the storyboard's moves (`storyboard.md`, what each
  move reveals and what it carries across the cut), open every one of the 24 frames with the Read tool and the strip,
  and fill in `B/critic/timed.json` with the four reads (`S/critic/critic.md`, "The timed read"), each a pass or a fail
  and the words naming the beats and the frames; a read you cannot make from what is here is "not made" with the
  reason. `qa.py timed` passes when the board, the preview and the four reads are all for this cut and no read fails;
  `render` refuses until it has.
- `render` lays the timed board out for the reel and each format `--also` names, renders those films, the posted
  image and the story card (and with `stories` the stills of each) through `S/motion/studio` in one browser session, then lays the music under each film;
  a film or still in `out/` from an earlier render that this one did not make is removed. With an NVIDIA graphics card
  (`/dev/nvidia0`) the browser draws on it and the card encodes H.264 High at constant quality 14 (well under a minute
  for the reel); with another graphics card on Linux the browser draws on it and x264 encodes; with neither the
  processor draws and x264 encodes at CRF 18 (several minutes). Any font or photograph that failed to load and any job
  that failed after three tries are in `B/render/film-report.json`, which render writes only once all of out/ is the
  new render (a render that fails leaves them in `B/render/film-report.part.json`); `vote.py cut` and the gate refuse
  while it is missing.
- `frames` writes the settled frames of the 9:16 film's three rest moments, the hook, the peak card and the closer,
  into `B/frames/NN-<beat>.png`; the 1 and 2 fps strips of the whole reel are `B/qa/film-strip.png` and
  `B/qa/film-strip2.png`.

`preview` and `render` render each film in chunks kept in `B/render/chunks/` (the whole film as one chunk on a machine
with an NVIDIA card, 60 frames each without one), and join them into the film once every chunk is whole. A render
that brings no new frame for a minute and a half, or is still running after ten minutes, is cancelled and tried
again. When a render is interrupted (the machine restarted, the session died), run the same command again: the chunks
already finished are kept and only the missing ones render. Never start over and never delete `B/render/chunks/`; a
changed cut renders new chunks of its own. Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Scratch files stay under the build folder, never `/tmp`, which other sessions share. Its progress is in `B/render/preview.log` or `B/render/film.log`: each chunk's lines name its frames (`<first>-<last>`) and
end `<percent>% (N s)`, which against the film's frames give the estimate to tell the person; when the render ends it
prints the chunks kept, rendered and still to go. A second render started in the same run while one is running stops at once and names the running one's log.

The standards the film is held to are in `S/motion/system/standards.md`; the safe areas are `S/design/safe-areas.json`. To
change the film, edit the board's `storyboard.json` (photographs, order, beat lengths) and run `snap` and `render`
again; never edit `B/film.json` by hand.

## Look before the critics do

Open every `B/frames/NN-*.png`, `out/post.png`, `out/story.png`, and the stills in `out/stills/` when they were asked
for, with the Read tool. Text cut off, a face cut by a crop, a beat that looks unfinished: fix it in the storyboard
and render again now.
