# 4. The cut: the winner timed to the music and rendered silent for the critics

Goal: `film.json` (the winner cut to the music), the music master (`music.json` names it), `clips.json`, and the
timed cut `film.silent.mp4` with its strips in `frames/` and its checks in `qa/cut.json`, all passing, which `cut.json`
certifies. Nothing is rendered
with sound, and no still is made, until the critics have read this cut (movement 5).

## Music

The music is theirs: `taste.json` `music` is its brief. `music.py find` takes, in order:

1. A track the person gave you for this film, saved as `music/source.<ext>` in the run; pass
   `--origin "<where it came from>"`.
2. Else a bed `music.py make` composes on real instruments from the picked look's own music recipe (its style
   card's `music`), at the board's tempo, unless the words of their brief name another recipe; `music.json` `origin`
   names the recipe and why it was chosen.

```
python3 S/scripts/music.py find
python3 S/scripts/music.py analyze
```

`analyze` finds onsets, tempo, beats and downbeats. A film with no music at all still cuts and renders, on the
board's tempo, silent.

## Cut to the music, master, account for the clips

```
python3 S/scripts/storyboard.py snap
python3 S/scripts/music.py master
python3 S/scripts/clips.py list
python3 S/scripts/clips.py normalize [--why "no video model in this session"]
```

- `snap` cuts every beat on the music's downbeats and writes `film.json`, the composition's props: each beat's
  frames, its pulse and its hits (the musical beats where it lands, each a sound `master` lays), and `cards`, the frames the
  stills are taken from (the cover: the reveal at rest; the feed post: the closer laid for 1080×1350; and for a launch
  the three stories, the hook, the first beat of the build and the reveal at rest, a hook whose words land one a beat
  showing its whole line at rest, and on a board of the hook, the reveal and the closer, the reveal halfway to its rest
  and at rest; and the countdown card, the closer at rest). When the music's tempo is far from the
  board's, it says so: make the board's music and analyze it, then snap again.
- `master` trims the music to the film (`music/bed.wav`) and writes the board's sound (`sound` in `film.json`: one cue
  where each beat lands, the build into the reveal and the stop) as `music/fx.wav`, scaled by its loudness to 8 LU
  under the bed's. It prints both numbers, writes them to `music.json` and to the board's `storyboard.md`, sums the
  two, and brings the sum to −14 LUFS integrated, true peak under −1.5 dB. The gate's audio row is red when the effects
  sit less than 7 LU under the music.
- `list` writes `clips/requests.json` and prints each clip the board asks for, one per beat on a photograph, written
  as a cinematographer writes a shot: the subject (what the photograph shows, kept as it is), the camera's move (the
  beat's own move), the lens, the light, the beat's length and a seamless loop. The hook's is its world, each build
  beat's a still brought to life, the reveal's the subject answering. With an image-to-video model in the session,
  make each clip from its photograph and save it where `list` says.
- `normalize` conforms each clip that arrived to its photograph's size, 30 fps and its beat's length, and the film
  plays its frames on that photograph's print; a clip that did not arrive stands in, and the film makes the move the
  board names for it on the still photograph. `clips.json` records each as generated or stand-in, with the reason.

## The timed cut

```
python3 S/scripts/film.py cut
```

It renders `film.json` silent to `film.silent.mp4` (1080×1920, 30 fps, H.264 High; on the graphics card when the
machine has one, about half a minute for a 20 s film; on the CPU a few minutes), writes the strips the critics read
(`frames/strip-<beat>.png`, 12 frames across each beat; `frames/film-strip.png`, the whole film at 2 fps) and runs
the picture's checks and figures into `qa/cut.json`. While `storyboard.py check` finds anything on `film.json`, it
renders nothing and exits with one line per finding (`film.json is not rendered: <the finding>`). Two figures the critics
read, never passed or failed:

- **still**: each second's change (its first frame against its last, both box-downscaled to 135x240, mean absolute
  difference), the seconds under 0.5 and the longest run of them;
- **cuts**: the cuts and the cuts a minute (the beat boundaries joined with the scene changes).

The checks:

- **hook**: something arrives inside the first 30 frames;
- **frame0**: the first frame, the film's cover in the feed, shows a picture or words, never a flat field;
- **board**: every finding of `storyboard.py check` on `film.json`;
- **safe**, **black**, **frozen**, **film**: no font, image, shader or render error in the render report, no black
  stretch but a cut through black or the closer's title on black, no frozen stretch before the board's stop cue but
  the closer's ease into its hold over its last beat, the format.

The film renders in chunks kept in the run (`render/chunks/`: 60 frames each on a machine without an NVIDIA card,
the whole film as one chunk on one), and the chunks are joined into `film.silent.mp4`. A cut that was interrupted
(the machine restarted, the session died) is resumed by running `film.py cut` again: the chunks already finished are
kept and only the missing ones render, so never start over and never delete `render/chunks/`. A changed `film.json`
renders into chunks of its own, so nothing of an older cut is reused. Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Scratch files stay under the build folder, never `/tmp`, which other sessions share. Its
progress is in `render/render-report.log`: it opens with `render render-report: K jobs to render` (each job one chunk) and
logs each chunk's progress as it renders, so the time of the first chunks times the chunks to go is the estimate to give
the person. The command ends with `render render-report: N chunks kept, M rendered, L to go`.

A failing check is fixed in the picked board (`winner.json`), the cast or the music, then `snap`, `master` and
`film.py cut` again.

To change the film, edit the winner's `storyboards/N/storyboard.json` (words, order, bars, items) or the cast
(`looks.json`, then `storyboard.py draft`), and run from the vote again: `snap` cuts only a board that won it, as the
vote stored it in `winner.json` (an edit after the vote never reaches the film), and a new draft removes the old
winner, the scores and `film.json`. Never edit `film.json` by hand. The rules the film is held to are in
`S/motion/system/standards.md`.
