# 4. Produce: the picked look, cut to the music

Goal, in the run's `out/`: `film.mp4` (1080×1920, 30 fps, H.264 high, AAC 192 kbps, −14 LUFS), its cover
`cover.png` (1080×1920, the closer's held still: the look's own closer with the trip's name and dates) and, only when the
person asked for them, the same film as `film-16x9.mp4` (1920×1080) and `film-square.mp4` (1080×1080), each within
1 s of the film's length, and five story cards `story-1.png` .. `story-5.png` (1080×1920), all rendered by the kit's
motion composition (`S/motion/dist`) from one storyboard. Movement 5 (`5-clips.md`) runs between `snap` and `render`: its clips list is read from `film.json`,
and the render plays what arrived.

## Music

The music is the person's. `music.py find` takes, in order:

1. A track they chose or you fetched, saved as `music/source.<ext>`; run `music.py find --origin "<where it came from>"`.
2. Else a bed composed here for the picked look: the look's own music recipe (`music` in its card), unless their
   music brief (`taste.json` `music`) names another; its key from the board's leading color.

```
python3 S/scripts/music.py find
python3 S/scripts/music.py analyze
```

`analyze` finds onsets, tempo, beats and downbeats.

## Cut to the music, master, render

```
python3 S/scripts/storyboard.py snap
# movement 5: clips.py list, generate, clips.py normalize
python3 S/scripts/music.py master
python3 S/scripts/film.py render
python3 S/scripts/film.py frames
```

- `snap` cuts the picked board (`winner.json`) and refuses with none picked. It times the board on the music,
  from the track's first downbeat: the track's tempo is doubled or halved into the octave around the board's own (the middle of
  its look's music recipe), and every span starts on a downbeat. It writes `film.json`, `film-landscape.json` and
  `film-square.json` (one storyboard timed once: the same spans, sound cues and photographs, the camera framing each
  picture's own shape) and the clips the film asks for. The film is as long as the trip needs: about half a minute
  for five stops, longer at a slower tempo. Before anything renders it reads the timed cut for monotony and exits 1
  when every span is one length, or when a span holds more than two bars with nothing sounding; change the board's
  inputs and run `check` and `snap` again.
- `master` trims the music to the film from its first downbeat, scores the board's sound cues under it (a hit where
  the first photograph opens and where each stop lands, a riser into the closer's impact, the stop where
  the bed cuts on the beat and the hit on it ends before it rings), writes the effects stem 8 LU under the bed's loudness, and brings the whole
  to −14 LUFS integrated, true peak under −1.5 dB. It prints the bed's and the effects' loudness and the cue and beat
  counts, and writes them to `music.json` and the storyboard's `Mixed:` line.
- `render` renders the reel and its cover; `render --also landscape square stories`, naming only what the person asked for (the
  words that ask for each are in `6-deliver.md`, "What they asked for"), renders the 16:9 film, the square film and
  the five story cards beside it. It lays the mastered music under each picture, takes away any extra an earlier
  render left in `out/` that this one was not asked for, and writes `render/film-report.json` (every finding the
  composition logged with its prefix, `FONT_ERROR`, `IMAGE_ERROR` or `RENDER_ERROR`, a job that failed, and `made`,
  what it rendered). The story cards are settled frames of the 9:16 film at the rests the board names in
  `stories`. On a machine with an NVIDIA card the render draws and encodes on the card, a few minutes for all
  three films; with another graphics card on Linux it draws on that card and x264 encodes; elsewhere it runs on the
  processor and takes longer.
- Every film renders in chunks saved in the run under `render/chunks/` (60 frames each on the processor, the whole
  film as one chunk on an NVIDIA card), joined into the film once all of them are whole. An attempt that draws no
  frame for 90 s, or runs ten minutes, is stopped and tried again, and a shader error or a lost WebGL context fails
  the attempt, so a white chunk is never kept. An interrupted render (the machine restarted, the session died) is
  resumed by running the same command again: the finished chunks are kept and only the missing ones render, and the
  render prints `render <name>: N chunks kept, M rendered, K to go`. Never start over and never delete
  `render/chunks/`; a changed cut renders into new chunks by itself. Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Scratch files stay under the build folder, never `/tmp`, which other sessions share. Its progress is
  in `render/film.log` (`render/preview.log`);
  after the first chunks land, their time times the chunks still to go is the estimate to tell the person. A render
  started while another runs in the same run exits at once and names the running one's log.
- `frames` writes `frames/strip-<beat>.png` (twelve frames across each span) and `frames/film-strip.png` (the whole
  film at one frame a second) from `out/film.mp4`; `film.py frames --film out/film-16x9.mp4 --out frames-16x9` and
  `--film out/film-square.mp4 --out frames-square` do the same for the other two shapes when they were rendered.

`film.py preview` renders the reel at half size with its strips and measured figures before a full render, when you
want to look first.

The standard the film is held to is `S/motion/system/standards.md`, against the picked look's card. To change the film, change its inputs (the points,
the names, the music) and run the steps from `storyboard.py check` again; never edit `film.json` by hand.

## Look before the critics do

Open `frames/film-strip.png`, every `frames/strip-<beat>.png`, and the wide and square strips and the story cards
when they were rendered, with the Read tool. In every shape and at every moment the photograph fills its frame: bare
ground at an edge, a move that misses what the photograph looks at, type cut off or over a face, a hold that stands
still, a card that is not a finished picture: fix the cause and render again now.
