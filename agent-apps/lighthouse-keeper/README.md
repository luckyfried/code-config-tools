# Lighthouse Keeper

## What this makes

A night at the person's own lighthouse, as one folder of static files. Ghost ships drift in through rolling fog
toward the rocks, dark silhouettes with green lanterns, and the lighthouse beam is the only thing that stops them:
held on a ship, it lights the hull, then burns the ship away, sails first, along a glowing edge. The sea rolls under a
moon, rain streaks past, thunder lights the sky, and a flare lights the whole sea for two seconds. Every thirty
seconds the fog thickens and the ships come faster, then two at a time; keeping them off the rocks until dawn saves
the night, and the best night is kept on the player's device. The title screen plays the night live behind the
lighthouse's name. It plays on phones (drag anywhere to swing the beam, tap the lamp for a flare) and on desktops
(the mouse or the Left and Right keys, Space for a flare), with a synthesized sea, foghorn, thunder, and burning that
can be switched off.

## Run

Make `lighthouse-keeper.inputs.json` in the person's project folder (copy `inputs.example.json` from this folder and
change the values; every key is explained in its `"_notes"`), then:

```
cd <project> && python3 <agent-apps root>/lighthouse-keeper/scripts/run.py
```

It writes `out/lighthouse-keeper/` in the project and prints the line to serve it. A missing or wrong key stops the
run with one plain line naming the key; fix the file and run it again. Running it twice on the same inputs gives the
same files.

## Check

- `out/lighthouse-keeper/index.html`, `out/lighthouse-keeper/config.js`, and `out/lighthouse-keeper/theme.css` exist.
- `out/lighthouse-keeper/config.js` holds the `lighthouseName` and the `playerName` from the inputs.
- Serve the folder (Host, below) and open `http://localhost:8000/`: the lighthouse's name is shown large over a live
  sea, the beam sweeps, a ship burns in it within a few seconds, and the browser console shows no errors.
- Press Light the lamp, then move the mouse (or drag on a phone): the beam follows, and a ship held in it burns away.

## Host

The page is served, never opened as a file, because browsers refuse to load its modules from a file address.

```
cd <project> && python3 -m http.server 8000 --directory out/lighthouse-keeper
```

Then open `http://localhost:8000/`. Any static host takes the `out/lighthouse-keeper/` folder as it is: everything the
game needs, the 3D library and the fonts included, is in that folder, and it loads nothing from anywhere else.

## Make it yours

Ask the person, in one message: "What's your lighthouse called, what's your name, and which night do you want (night,
storm, or dawn)?"

1. **The lighthouse's name.** `"lighthouseName"` (up to 40 characters) is painted around the tower and shown large
   on the title.
2. **Their name.** `"playerName"` is the keeper's name on the dawn card and the lost card.
3. **Which night.** `"theme"` is `night` (a clear moonlit night, white beam), `storm` (purple-grey, heavier rain, and
   more thunder), or `dawn` (a pink horizon, thinner fog, and a gold beam). Each has a light look at blue hour and a
   dark one at deep night, following the player's device.
4. **Optional:** `"nightMinutes"` (1 to 30, default 5) is how long until dawn, `"shipsToLose"` (1 to 10, default 3)
   is how many ships on the rocks end the night, and `"title"` (default "Lighthouse Keeper") is the small line above
   the lighthouse's name.

No accounts or keys are needed. Write the answers into `lighthouse-keeper.inputs.json`, run the Run line again, and
serve it.

Changes past the inputs are plain files in `site/`: each night's colors and weather are tokens in
`site/themes/<name>.css` (the `--sky-*`, `--sea-*`, `--fog*`, `--beam`, and `--rain-amount` tokens color and fill the
scene, the `--color-*` tokens the cards and the HUD), the ships are built in `site/scene/ships.js`, the lighthouse and
its rocks in `site/scene/lighthouse.js`, the sounds are made in `site/audio/synth.js`, how fast a ship burns is
`HOLD_SECONDS` in `site/game/paths.js`, and how the night hardens is `site/game/waves.js`. Run the Run line after any
change, since it copies `site/` fresh each time.
