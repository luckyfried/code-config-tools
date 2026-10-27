# Fish Tank

## What this makes

A living aquarium as one folder of static files. Schools of fish swim together with real flocking (they keep apart,
line up, gather, and turn away from the glass), each fish built in code with a tail and fins that ripple as it swims.
Light ripples across the sand and the plants, two rays fall from the surface, the plants sway, and bubbles rise from
the bubbler. Tapping the water drops food that sinks; the nearest fish swirl in to eat it, grow a little, and drop
pearls that glint on the sand until a tap gathers them or they gather on their own. Fish keep earning while the page
is closed, up to two days, and a card says what they made on the next visit. Pearls buy new fish, decor, and bigger
tanks in a glass shop where every fish swims live in its card. The tank follows a real day, bright at noon, amber at
dusk, and deep blue at night with the tank lamp on and the fish slowed down. A first visit opens mid-meal, with food
drifting into the school and pearls already on the sand. It works on phones (tap to feed and gather) and desktops (F
feeds, S opens the shop, Space gathers every pearl), and the tank is saved on each visitor's device.

## Run

Make `fish-tank.inputs.json` in the person's project folder (copy `inputs.example.json` from this folder and change
the values; every key is explained in its `"_notes"`), then:

```
cd <project> && python3 <agent-apps root>/fish-tank/scripts/run.py
```

It writes `out/fish-tank/` in the project and prints the line to serve it. A missing or wrong key stops the run with
one plain line naming the key; fix the file and run it again. Running it twice on the same inputs gives the same
files.

## Check

- `out/fish-tank/index.html`, `out/fish-tank/config.js`, and `out/fish-tank/theme.css` exist.
- `out/fish-tank/config.js` holds the `title` and the `theme` from the inputs.
- Serve the folder (Host, below) and open `http://localhost:8000/`: the tank's name is on the plate, at least three
  fish are swimming within a second, and the browser console shows no errors.
- Tap the water (or press F): food sinks and fish turn toward it within two seconds.
- Open `http://localhost:8000/tests/economy.html` and `http://localhost:8000/tests/boids.html`: each says "All
  checks pass" (eight hours of two clownfish and a blue tang make 272 pearls, and the school stays in the glass).

## Host

The page is served, never opened as a file, because browsers refuse to load its modules from a file address.

```
cd <project> && python3 -m http.server 8000 --directory out/fish-tank
```

Then open `http://localhost:8000/`. Any static host takes the `out/fish-tank/` folder as it is: everything the tank
needs, the 3D library, the fonts, and the sounds included, is in that folder, and it loads nothing from anywhere else.

## Make it yours

Ask the person, in one message: "What should your tank be called, and which tank do you want: a coral reef, a river,
or the deep sea?"

1. **The tank's name.** `"title"` is shown on the plate in the corner and as the page title.
2. **Which tank.** `"theme"` is `reef` (white sand, coral, and tropical fish), `river` (driftwood, ferns, tetras, and
   koi), or `deep` (dark water, a vent, tube worms, and fish that glow). Each has a light look and a dark look that
   follow the visitor's device; a dark first visit opens at night.
3. **Optional:** `"startingFish"` names 1 to 6 fish from that tank (the notes list them), `"cycleMinutes"` (5 to 1440,
   default 60) is how long a day in the tank lasts, `"pearlRate"` is `calm`, `normal`, or `fast`, and `"sound"` is
   `true` or `false`.

No accounts or keys are needed. Write the answers into `fish-tank.inputs.json`, run the Run line again, and serve it.

Changes past the inputs are plain files in `site/`: each tank's colors are tokens in `site/themes/<name>.css` (the
`--scene-*` tokens light the water, sand, and plants at noon, dusk, and night; the `--color-*` tokens dress the bar,
the shop, and the cards), every fish, piece of decor, and price is a row in `site/sim/catalog.json` (a fish's shape,
fins, colors, and markings are its `body`, `tail`, `dorsal`, and `colors`), the pearl math is `site/sim/economy.js`,
the flocking is `site/sim/boids.js`, and each kind of decor is one builder in `site/scene/decor.js`. Run the Run line
after any change, since it copies `site/` fresh each time.
