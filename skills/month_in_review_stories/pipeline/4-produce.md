# 4. Produce: the timed read, then the board rendered by the studio

Goal: the run's `out/film.mp4` (the reel) and `out/cards/`: `NN-story.mp4` (each card as its own 15 s animated story)
and `NN-story.png` (each card's still); and `out/series.mp4` (every card in order) only when their `ask` says `series`.

## Music

```
python3 S/scripts/music.py make
```

`make` refuses until the vote has a winner (`winner.json`). A track the person placed as `music/source.<ext>` wins;
otherwise the studio's music engine makes the bed from the winning look's recipe and the music brief in
`taste.json` (`music`: the styles they named, and what to leave out), as long as the longer of the reel and the series. `music.json` names the file and
its origin, and the storyboard's Music line carries the origin. Every render's sound cues sit under the music: the effects stem is scaled
so its integrated loudness is 8 LU under the bed's, and `film.py render` writes both numbers and the cue count into
`music.json` and the storyboard's Mixed line, which `qa.py check` reads.

## Clips

```
python3 S/scripts/clips.py list
```

`list` writes `clips/requests.json` and prints, for every moment with a photograph, the clip an image-to-video model
would make from it: its use (the first is the hook's world, the others a still brought to life), the shot you wrote in
`taste.json` (subject, move, lens, height, light), its length, a seamless loop, the prompt and the file to save
(`clips/NN.mp4` in the run). A field printed "(not written)" is a shot to write in `taste.json` before the board is
drafted again. Generate each clip with the video model you have and save it there. Then:

```
python3 S/scripts/clips.py normalize --why "<why any did not arrive>"
```

`normalize` conforms every clip that arrived to its photograph's size and its beat's length and places it on its
card; every clip that did not arrive stands in, and the film makes the layered move the storyboard names for it on
the still photograph: the camera's hold (a push, a pull or a crane with the line) while the photograph eases about its
subject against it. `clips.json` records which, and `brief.md` lists them.

## Preview and the timed read

```
python3 S/scripts/film.py preview
```

`preview` renders the reel at half size with its mastered sound into `preview/film.mp4` and measures it into
`preview/preview.json`: the length, the cuts as planned and as the picture shows them, the hook frame, the luma line
and its quiet seconds, the loudness, and the 1 and 2 fps strips (`preview/film-strip.png`, `film-strip2.png`).

```
python3 S/scripts/vote.py timed
```

Read `S/critic/critic.md`, section "The timed read". Read the winning look's `storyboards/<style>/storyboard.md`, watch
`preview/film.mp4` with sound and look at both strips, then fill in `critic/timed.json`: the four reads, each `true`,
`false` or `"not read"` (when nobody in this session can make it), with at least 25 words on where it holds and where it
does not, or on why it cannot be made. Run `vote.py timed` again; it records what the reads found. A failing read has
its cause in the board: say so in the read, and the cut's critics carry it to the rule it costs.

## Render

```
python3 S/scripts/film.py render
```

`render` refuses a board drafted from another `taste.json` than the run's (a changed taste reaches the film only
through `storyboard.py draft`), and refuses until the timed read of this board is made; it prints any read that did
not pass and renders the board all the same, and the gate states each read. After every render it runs `qa.py check`,
so `qa/check.json` always describes the delivered film. One storyboard, one format, one bundle and one browser
(the compositions in `S/motion/studio`, on the motion system in `S/motion/system`):

- `out/film.mp4`: the reel, the Reel composition (`S/motion/studio/climb`), as long as the board's reel, its sound
  cues under the music, the picture and the music stopping together on the stop and holding to the end.
- `out/series.mp4`, only when they asked for it: the whole series, the Film composition (`S/motion/studio/story`),
  each card one camera over a moment on the same 3D stage, with every card's sound cues under the music. Unasked, the
  series still renders silent in the build folder, since every card is cut from it, and no `out/series.mp4` is made.
- `out/cards/NN-story.mp4`: each card cut from the series' render at its bounds, with the music's bars and that card's cues under it.
- `out/cards/NN-story.png`: each card's still, a settled frame of the card from the same composition.

Every file is made in `render/out/` and moves into `out/` once all of them are made, so a render that fails or is cut
off leaves `out/` as it was.

Every video is 1080x1920 at 30 fps, H.264 High, yuv420p, with AAC at 192 kbps and -14 LUFS under a peak limiter. On a
machine with an NVIDIA graphics card the browser draws on the card and the encoder runs there too; with another
graphics card on Linux the browser draws on it and the processor encodes; with neither, both run on the processor and
the files are the same to the eye. A frame drawn with a failed shader or a lost graphics context is never kept: the
renderer draws it again in a fresh browser.

### A render that is cut off resumes

`preview` and `render` draw every video in chunks saved in the run (`preview/chunks/` and `render/chunks/`): ten
frames each on a machine without an NVIDIA card, one chunk per video on a machine with one. They join the chunks into
the video once every chunk is whole. When a render is interrupted (the machine
restarted, the session died, the command was stopped), run the same command again: the finished chunks are kept and
only the missing ones render, and the command prints how many it kept, rendered and has to go. Never start over, and
never delete `preview/chunks/` or `render/chunks/`; a changed board renders into new chunks by itself. Two renders of
one folder never run at once: the second stops and names the first one's log.

Run the preview and the render each in the foreground in one tool call, and ask for a 40-minute timeout on that call, which the session allows; never start either in the background. Scratch files stay under the build folder, never `/tmp`, which other sessions share. Its progress is in `render/render.log`
(`preview/render.log` for the preview). Once the first chunks have landed, the time they took times the chunks still to
go is the estimate to tell the person.

`render` writes, in the run's build folder: `render-report.json` (every finding and failed job), `timeline.json`
(each video's figures), `timeline/film-strip.png`, `film-strip2.png` (and `series-strip.png` and `series-strip2.png`
when the series is made),
`cards.json`, `engine.json` and `film.json` (the rendered board). A render that fails writes none of these and leaves
`out/` as it was; what went wrong is in `render/render-report.json` and `render/render.log`.

## Look before the critics do

Open the film's and the series' strips, then every `out/cards/NN-*.png`, with the Read tool, and watch
`out/film.mp4` with sound. A frame where a field of color is the stage, a beat that holds still longer than its
words need, type cut off, a figure that does not match their month: the cause is in the board, so rerun movement 2,
then this one. Never edit anything in `out/` by hand.
