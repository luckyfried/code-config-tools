# Pad Synth

## What this makes

A web page that is an instrument: a grid of glowing pads in the scale and key the person likes, four voices (pluck,
pad, bass, and keys), a step ring that plays a pattern under them, and a recorder that keeps what they play as
loops. Every press sends colored waves across the whole screen, so a chord draws its own interference pattern.
Loops and patches stay in the browser on their device and save as WAV and JSON files. It works on a phone, a tablet,
and a desktop, where the keyboard plays the pads too.

## Run

From the person's project folder, before asking for anything personal, run:

```sh
cd <project> && python3 <agent-apps root>/pad-synth/scripts/run.py
```

It reads `pad-synth.inputs.json` in the project folder. When the person has none yet, copy this app's
`inputs.example.json` there as `pad-synth.inputs.json` first; the example plays as is. The page is written to
`out/pad-synth/` in the project folder. A missing or wrong key is named in one line and nothing is written.

## Check

`out/pad-synth/index.html` exists, and `out/pad-synth/config.js` carries the scale, key, grid, and theme from the
inputs. Serve the folder (see Host) and open `http://localhost:8000/`: the pads light in a chord, waves cross the
screen, and the step ring turns. Open `http://localhost:8000/?selftest=1` and the browser console prints the peak
level of a C major scale rendered offline; a working page reads above 0.1. Sound starts with the first tap or key.

## Host

The page is a folder of plain files and must be served, not opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/pad-synth
```

Then open `http://localhost:8000/`. Any static host serves `out/pad-synth/` as it is. The page calls no service, so it
keeps working wherever the folder is hosted; each visitor's loops stay in their own browser.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens
this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js" defer>`
line from `index.html` (or from the app's `site/index.html`, so every run leaves it out).

## Make it yours

Ask the person, in one message: which scale and key they like to play in, how big a grid they want, what tempo the
step ring should run at, and whether they want aurora, ember, or ink. Write the answers into
`pad-synth.inputs.json` and run again. Every key:

- `name`: the title on the page.
- `scale`: `major`, `minor`, `dorian`, `mixolydian`, `lydian`, `phrygian`, `harmonic-minor`, `major-pentatonic`,
  `minor-pentatonic`, `blues`, or `chromatic`.
- `key`: `C` through `B`, with sharps or flats (`F#`, `Bb`).
- `voices`: which of `pluck`, `pad`, `bass`, and `keys` to offer, in the order they appear.
- `grid`: `"5x8"` (40 pads) or `"6x10"` (60 pads).
- `bpm`: the step ring's tempo, 50 to 200.
- `theme`: `aurora` (polar green and violet), `ember` (gold and crimson), or `ink` (indigo and vermilion). Each has
  a light and a dark side that follows the device's setting.

Scale, key, voice, tempo, and the ring's steps can also be changed on the page; those changes are kept on the device
until the inputs change. A new look is a new file in `site/themes/` with the same tokens as `aurora.css`; the wave
field reads `--field-bg`, `--field-a`, `--field-b`, and `--field-mode` from it. Each voice is one file in
`site/audio/` that exports `create(ctx)`. Nothing needs to be built: edit, run again, and reload.
