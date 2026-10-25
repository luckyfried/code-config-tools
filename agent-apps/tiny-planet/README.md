# Tiny Planet

## What this makes

A small planet grown from a seed word, as one folder of static files. A round explorer walks it with the horizon
curving under their feet: continents, mountains, forests, and seas, trees and grass swaying in the wind. Crystals are
hidden across the land, each sending a tall beam of light into the sky, and a compass ring points toward the nearest
one. The sun sets in real time over the run, from noon blue through an amber sunset to a night of stars and a rising
moon, and night ends the run. Finding every crystal before dark saves the planet; the time is the score, kept as the
best time on the player's device. The title screen shows the planet live, with the explorer strolling on its own.
It plays on phones (a thumb stick on the left, drag on the right to look, tap or the round button to jump) and on
desktops (WASD or the arrow keys, Shift to run, Space to jump, drag to look), with synthesized wind, footsteps,
chimes, and crickets that can be switched off in the pause menu.

## Run

Make `tiny-planet.inputs.json` in the person's project folder (copy `inputs.example.json` from this folder and change
the values; every key is explained in its `"_notes"`), then:

```
cd <project> && python3 <agent-apps root>/tiny-planet/scripts/run.py
```

It writes `out/tiny-planet/` in the project and prints the line to serve it. A missing or wrong key stops the run with
one plain line naming the key; fix the file and run it again. Running it twice on the same inputs gives the same
files.

## Check

- `out/tiny-planet/index.html`, `out/tiny-planet/config.js`, and `out/tiny-planet/theme.css` exist.
- `out/tiny-planet/config.js` holds the `planetName` and the `seed` from the inputs.
- Serve the folder (Host, below) and open `http://localhost:8000/`: the title card shows the planet's name, the planet
  appears behind it with sea, trees, and crystal beams within a few seconds, and the browser console shows no errors.
- Press Start exploring, then hold W (or push the thumb stick): the explorer walks, the horizon curves away ahead,
  and a crystal beam stands in front of the start.

## Host

The page is served, never opened as a file, because browsers refuse to load its modules from a file address.

```
cd <project> && python3 -m http.server 8000 --directory out/tiny-planet
```

Then open `http://localhost:8000/`. Any static host takes the `out/tiny-planet/` folder as it is: everything the game
needs, the 3D library and the fonts included, is in that folder, and it loads nothing from anywhere else.

## Make it yours

Ask the person, in one message: "What's your planet called, what's your name, and which world do you want (meadow,
tundra, or ember)?"

1. **The planet's name.** `"planetName"` is shown large on the title card and on the result card.
2. **Their name.** `"playerName"` is the explorer's name on the result card.
3. **Which world.** `"theme"` is `meadow` (green continents and blue seas), `tundra` (snowfields, ice, and dark
   pines), or `ember` (dark rock and glowing lava seas). Each has a light title screen at midday and a dark one at
   sunset, following the player's device.
4. **The seed word.** `"seed"` is any word; the same word always grows the same planet with the crystals in the same
   places. Use the planet's name in lower case unless they want another.
5. **Optional:** `"daySeconds"` (30 to 1800, default 120) is how long the day lasts, `"crystals"` (1 to 24, default
   7) is how many are hidden, and `"title"` (default "Tiny Planet") is the small line above the planet's name.

No accounts or keys are needed. Write the answers into `tiny-planet.inputs.json`, run the Run line again, and serve it.

Changes past the inputs are plain files in `site/`: each world's colors are tokens in `site/themes/<name>.css` (the
`--world-*` and `--sky-*` tokens color the planet and the sky, the `--color-*` tokens the cards and the HUD), each kind
of tree, rock, and grass is one function in `site/scene/flora.js` (swapping a tree is replacing `tree()`), the
explorer is built in `site/scene/explorer.js`, the sounds are made in `site/audio/synth.js`, and the walking speeds and
jump are constants at the top of `site/game/walking.js`. Run the Run line after any change, since it copies `site/`
fresh each time.
