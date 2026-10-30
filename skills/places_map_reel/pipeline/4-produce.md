# 4. Produce: the chosen look on the music, read as a timed cut, then rendered

Goal: in the run's `out/`, `film.mp4` (1080×1920), `film-16x9.mp4` (1920×1080) and `film-square.mp4` (1080×1080), each
30 fps H.264 with AAC 192 kbps at −14 LUFS, `post.png` (1080×1080, the image to post) and `story.png` (1080×1920, the
story card), all in the look `vote.py pick` chose, drawn by the kit's built composition (`S/motion/dist/`) in a
windowless Chromium and encoded with ffmpeg.

## Music

The music is theirs: the track they chose, else one made for this film from their music brief (`taste.json`
`music`). `find` takes them in that order:

1. A track the person gave you or asked for: save it as `music/source.<ext>` in the run's folder and run
   `music.py find --origin "<where it came from>"`. `find` on its own takes a track placed there since `music.json`
   was written, else keeps the track `music.json` names.
2. Otherwise `find` runs `make`: a bed composed on real instruments from the chosen look's music recipe, or the
   recipe the brief's `styles` words name, with its `avoid` words taken out, at the brief's tempo or the board's, in
   a key from the year's leading color. The seed is the run's folder name, so a rerun makes the same bed. `make`
   writes the bed's own beats, downbeats and sections into `music.json`, and its origin says which recipe and why.

```
python3 S/scripts/music.py find
python3 S/scripts/music.py analyze
```

`analyze` finds the onsets, the tempo, the beats and the downbeats of a track they brought; a bed `make` composed
already carries its own.

## Cut to the music and master

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/storyboard.py sheets
python3 S/scripts/music.py master
```

- `snap` sets the storyboard's tempo from the track (its tempo, half or double it: the one nearest 90 bpm that keeps the film inside its band), starts every
  beat on the frame nearest its musical beat, checks the three formats' boards again and writes `film.json`: the tempo, the
  length, where the music starts, the hook's frame, the cuts, the rests, the story beats, the sound cues and the three
  boards. The boards are solved again at that tempo, so the sheet rendered from the old ones goes, and `sheets` renders
  it again.
- `master` lays the board's sound cues (`hit`, `riser`, `impact`, each where its beat lands, played in the recipe's
  own instruments) under the bed, the effects scaled by loudness to `FX_UNDER_BED_LU` (8) LU under it, cuts the bed at the `stop` so
  the last hit rings out into silence, and brings the mix to −14 LUFS with the true peak under −1.5 dBTP. It prints
  both loudness numbers and writes them to `music.json` and to `storyboard.md`'s `Mixed:` line; the gate's audio row
  is red when the effects sit less than 7 LU under. `music/bed.wav` is the music trimmed to the film, `music/fx.wav`
  the cues alone.

## The clips

```
python3 S/scripts/clips.py list
python3 S/scripts/clips.py normalize [--why "..."]
```

- `list` writes `clips/requests.json`: one shot per stop, each for one use (the hook's world on the first stop, the
  texture between chapters on a stop the trip leaps to or from, a still brought to life on the rest), written from
  the shot's `about` (its `texture` for the texture between chapters) and `camera` in `cast.json`, with the camera
  move of the beat's own move in the look, said in camera words (a slow anamorphic push, a lateral dolly, a grid
  snap, a page drifting), the beat's seconds and a seamless loop. Read the requests: a request that names only the place means that shot has no `about`,
  `texture` or `camera`; write them (movement 1) and run `storyboard.py draft` and the steps after it.
- With an image-to-video model in this session, make each clip from the photograph `list` names and save it where
  `list` says (`clips/NN.mp4`). Without one, make none.
- `normalize` conforms every clip that arrived to its photograph and its beat, and records each one that did not
  as a stand-in (`--why` says why, for example "no video model in this session"): the film makes the layered move the
  request names on the still photograph in its place.

## The timed cut, before the render

```
python3 S/scripts/film.py preview
python3 S/scripts/vote.py timed
python3 S/scripts/qa.py timed
```

- `preview` renders the reel at half size to `preview/film.mp4` and measures it into `preview/preview.json`: the cuts
  as planned and as the picture shows them, cuts per minute, the luma line and its quiet seconds, the hook's frame,
  and the strips at 1, 2 and 12 frames a second (`preview/film-strip12-NN.jpg`, 12 across and 3 down, every frame a
  move spends).
- A preview that fails (it prints "the preview render failed", for example when the graphics card loses its context
  under another program's load) writes no `preview.json`. Run `film.py preview` again, up to three tries in all, and
  go on once it passes; that is this step, not a new run. After a third failure, stop and tell the person what it printed.
- Before the critic, look at the strips yourself and read them for the four things the film is held to, one by one:
  one element (the dot) carried across every move; a sound where each beat lands and nowhere else, under the music;
  motion that belongs to the photograph (every hold moves: the photograph drifts toward its focus along its own line
  while the camera turns across it, each at its own rate); one held thing per beat. Fix what fails before the critic reads it.
- Open the strips with the Read tool beside `storyboard.md`, and as the editor (`S/critic/critic.md`, "The timed cut")
  fill in `critic/timed.json`: the monotony read and whether it passes. Check every move in the 12 fps strips against
  the composition rule: the outgoing print and the arriving photograph fill the frame between them, and the map shows
  as the paper between two prints, never as the ground under one small one.
- `qa.py timed` passes the cut when the boards are clean, the length and the hook are in range, the preview is for this
  cut and the monotony read passed.

## Render

```
python3 S/scripts/film.py render
```

`render` refuses until `qa.py timed` has passed this cut. It renders the three films of the chosen look,
`post.png` (the square film's closer at rest), `story.png` (the reel's closer at rest) and `frames/<format>-<rest>.png`
(the hook, the stop and the closer of every format at rest), and lays the mastered music under each film. Its last
step is `qa.py check` on what it made, which prints `CHECKS GREEN` or the checks that failed, so `qa/check.json` always
describes the films in `out/`; a render that ends red has a cause to fix in its source before the critics watch. The
film is drawn frame by frame in a Chromium with no window, on an NVIDIA graphics card when there is one and on the
processor otherwise, and encoded with ffmpeg; the pictures are the same either way. A frame that is not ready in 30 s
stops the render and names the frame; a browser that stops answering, a lost graphics context or a flat render costs
one of three tries. `render/film-report.json` carries every finding, `engine.json` the wall time.

Both `preview` and `render` draw each film in chunks kept in the run under `render/chunks/` (with an NVIDIA card a film is one chunk), and join the film from them. A render attempt
whose frames stop coming for 90 s, or that runs past ten minutes, is cancelled and tried again. An interrupted render (the machine restarted, the session died) resumes when you run the same
command again: the finished chunks are kept and only the missing ones render. Never start over and never delete
`render/chunks/`; a changed cut renders chunks of its own. Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Scratch files stay under the build folder, never `/tmp`, which other sessions share. Its progress is
in `render/preview.log` or `render/film.log`; once the first chunks have landed, their time times
the chunks still to go is the estimate to tell the person. A second render started in the same run while one runs
exits and names the running one's log.

To change the film, change its source (`places.py`, `cast.json`, `taste.json`) and run `storyboard.py draft`, the
vote and the pick, `snap`, `clips.py list` and `normalize`, `music.py master`, `film.py preview`, the timed read and
`film.py render` again; never edit `film.json` by hand.
