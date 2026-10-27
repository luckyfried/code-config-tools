# quick-draw

## What this makes

A two-player reaction duel on a western street at sundown, at `out/quick-draw/index.html`. Two people hold one phone sideways, a thumb on each half (or press A and L on a keyboard); the camera creeps in while a clock ticks, DRAW slams onto the screen, and the first tap fires. Time slows while the camera swings around the bullet, the loser's hat flies, and a wanted poster names the winner with their reaction time in milliseconds. Best of three, five, or seven; a tap before DRAW loses the round; and a solo mode against a stranger who draws at 400 ms and gets 20 ms quicker each round. The town's name is painted on the saloon's banner across the street.

## Run

Run this from the person's project folder before asking for any personal details, so they see the street right away:

```sh
cd <project> && python3 <agent-apps root>/quick-draw/scripts/run.py
```

It reads `quick-draw.inputs.json` from the project folder. If that file is not there yet, copy `inputs.example.json` from this app's folder to `<project>/quick-draw.inputs.json` first and run the line again. The run writes the page into `out/quick-draw/` and prints how to serve it. A missing or wrong key is named in one plain line, and nothing is written.

Then ask in one message: "What are the two players' names, what's the town called, and which time of day (sunset, noon, or midnight)?" Put the answers into `quick-draw.inputs.json` and run the same line again.

## Check

`out/quick-draw/` holds `index.html`, `theme.css`, and `config.js`, which contains both players' names and the town's name. Serve the folder (see Host) and open it: the title sits over the live street with the town's name on the banner, the sun low between the two gunslingers. Left alone for a few seconds, the town plays a demo duel: the wait, DRAW, the shot, and a wanted poster with a reaction time. Press Face off (or Space) to play: the round runs through the wait, DRAW, and the shot, and the winner's poster shows their time.

## Host

The page has to be served, not opened as a file, because browsers refuse to load its modules from a file. On the person's computer:

```sh
cd <project> && python3 -m http.server 8000 --directory out/quick-draw
```

and open `http://localhost:8000/`. To keep it running after the session, put the whole `out/quick-draw/` folder on any static host (GitHub Pages, Netlify, Cloudflare Pages, or a plain web server); it needs nothing else and calls nothing on the internet. The best solo time and the sound setting stay in each player's own browser and are never sent anywhere.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js"></script>` line from `out/quick-draw/index.html` (or from `site/index.html` in this app's folder, so every later run leaves it out).

## Make it yours

Every key in `quick-draw.inputs.json` changes the page with no other tools: edit it and run the Run line again.

- `title`: the name on the title card.
- `players`: two names, left then right, up to 14 characters each. The left player owns the left half of the screen (and the A key), the right player the right half (and L). Both can also be retyped on the title before a duel.
- `townName`: painted on the saloon's canvas banner across the street and named on the title and the posters, up to 28 characters.
- `theme`: `sunset` (an amber sun at the end of the street and long shadows), `noon` (white light, short shadows, and bleached ground), or `midnight` (a low moon, blue light, and lanterns on the porches). Each has its own light and dark look that follows the device's setting, and recolors the sky, the light, the town, the gunslingers, and the posters.
- `bestOf`: 3, 5, or 7, the series length the title starts on.

Deeper changes are plain files in this app's folder and need no build step:

- A new time of day: copy `site/themes/sunset.css` to a new name, change its values (the `--scene-*` tokens set the sky, the sun's height and color, the light, the fog, the ground, the paint on the buildings, and each gunslinger's coat and hat; the `--color-*` tokens set the page and the posters), and set `theme` to the new name.
- The street: `site/scene/` holds one file per part: `street.js` (the buildings, the saloon, and the banner), `props.js` (the windmill, water tower, church, wagon, poles, cacti, and mesas), `figures.js` (the two gunslingers), `effects.js` (tumbleweeds, dust devils, the bullet, and the hat), `sky.js`, `ground.js`, `post.js` (depth of field, bloom, and the heat shimmer), and `camera.js`.
- The rules: `site/game/state.js` holds the wait (two to six seconds) and the solo stranger's draw times; `site/game/duel.js` stages a round.
- The sounds are WAV files in `site/audio/`, rendered from the recipes in `site/audio/synth.js`. Changing a recipe needs Node and Playwright to render them again with `node scripts/bake_sounds.mjs`; replacing a WAV file with another of the same name needs nothing.

Three.js is MIT (`site/vendor/LICENSE`); Rye and Bitter are under the SIL Open Font License and Special Elite under the Apache License (`site/fonts/`).
