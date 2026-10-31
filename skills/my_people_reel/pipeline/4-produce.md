# 4. The timed cut: the storyboard on the music

Goal: `R/render/proof-cut.mp4`, the half-size proof of the cut: the storyboard timed to the music in 9:16 with the
mastered music under it, rendered at half size because every critic round before deliver reads the proof, and what
the critics read it by: `R/frames/film-strip.jpg` (12 fps), `R/frames/NN-<beat>.png` (each beat at rest),
`R/frames/cues/` (the frames around each sound cue over the waveform of the film's sound) and `R/clips/requests.json`
(the shots the film asks a video model for).
The full-size cut, `R/render/cut.mp4`, and the film (and any other format the person asked for) render only after
the proof passes movement 5.

## Music

The music is theirs: the track they chose, else a bed composed for the picked look. `find` takes them in that order:

1. A track the person gave you or asked for: save it as `R/music/source.<ext>` and run
   `music.py find --origin "<where it came from>"`.
2. Otherwise `find` runs `make`, which composes the bed on real instruments from the picked look's own recipe (the
   card's `music`): its key from the palette's leading color, its tempo from the brief's (`R/taste.json` `music`),
   else the middle of the recipe's range, its sections turning where the board lands its impacts. The brief's
   `styles` words can name another recipe and its `avoid` words take out an instrument, the drums or a groove.
   `music.json`'s origin says which recipe and why.

```
python3 S/scripts/music.py find
python3 S/scripts/music.py analyze
```

`analyze` finds the onsets, the tempo, the beat grid and the downbeats.

## Cut to the music, master, render the cut

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/music.py master
python3 S/scripts/film.py cut --proof
```

- `snap` cuts the picked board (`R/winner.json`) and refuses with no pick. It sets the board on the
  music's tempo (halved or doubled to the one nearest the board's own) from its first downbeat, and writes `R/film.json`,
  so every cut lands on the grid.
- `master` trims the music to the film from that downbeat, cuts it on the board's stop (the closer settles there with
  its impact), brings it to -14 LUFS integrated by one gain, in float so no peak is cut (`cut` masters the music and
  the effects together, through one limiter), writes its loudness to `R/music.json` and its
  energy, one number a frame, to `R/music/energy.json`, and writes `storyboard.md` again with the film's length and
  tempo. The music carries no effects: `cut` lays them over it.
- `cut --proof` is the cut of every critic round before deliver. It renders the cut at half size (540x960) as
  `R/render/proof-cut.mp4` and never writes over `R/render/cut.mp4` or `R/out/film.mp4`; the strip, the beats at rest
  and the cue tiles in `R/frames/` come out at the size the full cut gives them. `qa.py check` and `vote.py cut` read
  the proof while it is the newest cut, and every size they report is in board units, the same numbers the full-size
  cut gives. Without `--proof`, `cut` is the full-size cut (1080x1920) that `film.py render` and deliver take
  (movement 5), and it takes the proof away.
- `cut` lays the board out in 9:16 at the film's tempo, renders it through the kit's built composition
  (`S/motion/dist/`, drawn in Chromium with no window; on the graphics card when the machine has one), lays the board's effects (`scripts/sfx.py`: on the music's grid
  and in its key) over the music under it, and writes the strip and the beats at
  rest and the cue tiles. A board that has not changed since the last cut is not rendered again; `--again` runs the render anyway. The
  renderer tries a job again when the card's context is lost or a shader fails to compile, and a film that still
  comes back with white frames fails the command, naming its white seconds.

## The clips

```
python3 S/scripts/clips.py list
```

`list` writes `R/clips/requests.json`: one shot per clip the board asks for (the hook's photograph as the world the
film opens in, and each person's photograph brought to life), each naming its subject, the camera's move, the lens, the light read
from the photograph, its length and a seamless loop, no two in a row moving the camera the same way, with the photograph to make it from and the file to save it as. When this
session has an image-to-video model, make each clip from its photograph with its prompt and save it where the request
says. A ComfyUI server with Wan 2.2's image-to-video models is such a model: `python3 S/scripts/i2v.py --requests R/clips/requests.json --server <its address>` makes every clip and saves it there, a minute or two a clip, and names any model file the server lacks. A card whose photograph is the poster of a clip the person recorded (cast.json's `clip`) asks for nothing: its
request names the recording and the seconds of it the card plays, one shot the length of the beat from its strongest
seconds, silent. Then:

```
python3 S/scripts/clips.py normalize --why "<why any clip did not arrive, for example: no video model in this session>"
```

`normalize` conforms what arrived and the person's own recordings, and records the rest as stand-ins in
`R/clips.json`; the film plays each on its card with the card's own arrival and move, and a clip that did not arrive
stands in as the card's own layered move. When any clip arrived, run `film.py cut --proof` again so the cut carries it.

## A render renders in chunks and resumes

`film.py cut` and `film.py render` render every film in chunks (60 frames each on a machine without an NVIDIA card,
the whole film at once on one with one), each saved in `R/render/chunks/` as it finishes. When a render is interrupted (the machine restarted, the session died, the command was stopped), run the
same command again: the finished chunks are kept and only the missing ones render. Never start over and never delete
`R/render/chunks/`; a changed cut renders into chunks of its own.

Run the cut and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Its progress is in `R/render/cut.log` (or
`R/render/final.log`): every chunk logs its progress and its time, and the command's last lines say how many chunks
were kept, rendered and still to go. Once the first chunks land, a chunk's time multiplied by the chunks still to go
is the estimate to give the person.

The standards the film is held to are in `S/motion/system/standards.md`. To change the film, edit the picked look's
`R/storyboards/<style>/storyboard.json` (order, lengths, which of their own lines) or `R/cast.json`, then run `check`, `snap` and
`cut --proof` again; never edit `R/film.json` by hand.

## Look before the critics do

Open `R/frames/film-strip.jpg` and every `R/frames/NN-*.png` with the Read tool. A face cut by its crop, a line
hard to read, a beat that looks unfinished: fix it in the storyboard or the cast and cut again now.
