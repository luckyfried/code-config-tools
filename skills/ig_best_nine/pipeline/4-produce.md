# 4. Produce: the timed cut, read before it renders, then the film

Goal, in the run's `out/`: `film.mp4` (the reel, 1080x1920, 30 fps H.264 High with AAC 192 kbps at -14 LUFS) and
the best-nine image `best-nine.png` (1080x1080), and only when the person asked for them `film-square.mp4`
(1080x1080), `film-wide.mp4` (1920x1080) and the story card `story.png` (1080x1920). All of it is rendered by the
kit's studio composition (`S/motion/studio`) from the one cut storyboard.

## Music

The music is theirs: the track they chose, else a bed made for this film from their music brief (`taste.json`
`music`). `find` takes them in that order:

1. A track the person gave you or asked for: save it as the run's `music/source.<ext>` and run
   `music.py find --origin "<where it came from>"`.
2. Otherwise `find` runs `make`: a bed composed here on real instruments in the picked look's own sound (its card's
   music recipe), unless the brief's `styles` name another, without what its `avoid` names, at the brief's tempo or the
   story's. `music.json`'s origin says which recipe and why.

```
python3 S/scripts/music.py find --run build/<stamp>
python3 S/scripts/music.py analyze --run build/<stamp>
```

`analyze` finds onsets, tempo, beats and downbeats in a track they gave; a bed `make` wrote carries its own.

## The generated clips

```
python3 S/scripts/clips.py list --run build/<stamp>
python3 S/scripts/clips.py normalize --run build/<stamp> [--why "<why a clip did not arrive>"]
```

Run these after `snap`. `list` prints every clip the storyboard asks for, with its prompt, length, photograph and the
file to save. Generate each with the platform's image-to-video model from the named photograph and save it where
`list` says. `normalize` conforms what arrived to its photograph's size and its beat's length, and the film plays it
on that photograph's card. A clip that did not arrive stands in: the film makes the camera or depth move the
storyboard names on the still photograph, and `clips.json` and `brief.md` say which.

## Cut to the music, and read the cut before it renders

```
python3 S/scripts/storyboard.py snap --run build/<stamp>
python3 S/scripts/film.py preview --run build/<stamp>
python3 S/scripts/vote.py timed --run build/<stamp>
```

- `snap` cuts the look picked (`winner.json`) and refuses with none. It times the storyboard at the music's tempo
  (or half or double it, whichever the nine fit at the asked length nearest the story's own tempo), so every cut lands on a beat and the film runs the length asked, and writes `film.json`.
- `preview` renders the reel at half size into `preview/film.mp4` with its strips and measures it: the cuts as
  planned and as the picture shows them, cuts per minute, the luma line, the hook event's frame.
- `timed` writes `critic/timed.json`. As the editor (`S/critic/critic.md`, "The timed cut"), open
  `preview/film-strip2.png` (two frames a second) and fill in the monotony read: does the cut vary its sizes and its
  rhythm, or settle into one shot repeated. A read that fails names the beat; change that beat's layout, move or
  length in `taste.json` `beats` and run again from `storyboard.py draft`.

```
python3 S/scripts/qa.py timed --run build/<stamp>
python3 S/scripts/music.py master --run build/<stamp>
python3 S/scripts/film.py render --run build/<stamp>
```

- `qa.py timed` checks the cut before it renders: the bounds check on all three formats, the asked length within 1 s, the hook
  in the first 30 frames, a preview of this cut, the template check (no layout twice, no move twice in a row, varied
  lengths, words in more than one place; it fails a template however clean each frame is) and the monotony read. It prints `TIMED GREEN`; `film.py render`
  refuses a cut it has not passed. Beside the checks it prints two figures from the preview, the cuts per minute
  and the luma line's seconds under 0.5, which the editor reads with the strip; neither passes or fails.
- `master` lays the storyboard's sound cues under the music (`hit`, `riser` and `impact`, played in the bed's own
  instruments where their beats land), the effects scaled by loudness to `FX_UNDER_BED_LU` (8) LU under the bed, trims the mix to the
  film and brings it to -14 LUFS integrated, true peak about -1.5 dB. It prints both loudness numbers and writes them
  to `music.json` and to `storyboard.md`'s `Mixed:` line; the gate's audio row is red when the effects sit less than
  7 LU under. A board's `stop` cue cuts the music where the picture stops: the last hit rings out over the held grid
  and the rest of the film is silent. `music/bed.wav` is the music trimmed to the film, `music/fx.wav` the cues alone.
- `render` renders the reel and the best-nine image (the square board's closer at rest); `render --also landscape
  square stories` adds the wide film, the square film and the story card (the reel's closer at rest), each only when
  the person asked for it, and takes away any extra an earlier render left in `out/` that this one was not asked
  for. The words that turn each one on: `square` when they say square, 1:1, or a film for the feed;
  `landscape` when they say wide, landscape, horizontal, 16:9, or a film for YouTube or a screen;
  `stories` when they say story, stories, or story card. It lays the music under each film.
  The run's `frames/` holds the hook, the densest beat and the closer of every rendered format.
  `render/film-report.json` lists every failed job, text outside its safe area and font that failed, and `made`
  records what was asked. On a Linux machine with a graphics card the render
  draws on the card (an NVIDIA card encodes too); elsewhere it runs on the processor, and the film is the same either
  way.

`preview` and `render` render each film in chunks kept in `render/chunks/` (60 frames each on the processor, the whole
film on an NVIDIA card), then join them into the film.
Each prints `render <name>: N chunks kept, M rendered, K to go`.

- An interrupted render (the machine restarted, the session died) resumes when you run the same command again: the
  finished chunks are kept and only the missing ones render. Never start over and never delete `render/chunks/`; a
  changed cut renders its own chunks by itself.
- Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Scratch files stay under the build folder, never `/tmp`, which other sessions share. Its progress is in `render/preview.log` or
  `render/film.log`. After the first chunks land, their time times the chunks still to go is the estimate to tell the
  person.
- One render runs in a run at a time: a second one exits at once and names the log of the one running.

The standard the film is held to is `S/motion/system/standards.md`. To change the film, change `taste.json` (the
words, or a beat's layout, move or length in `beats`) and run the steps again from `storyboard.py draft`; never edit `film.json`, a board or anything in `out/` by hand.

## Look before the critics do

Open every `frames/<format>-<rest>.png`, `out/best-nine.png` and, when it was asked for, `out/story.png` with the Read tool. Text cut off, a
photograph cropped past its subject, a beat that looks unfinished: fix the cause and render again now.
