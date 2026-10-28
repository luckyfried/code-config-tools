# Shard Storm

## What this makes

A bullet-hell survival game at `out/shard-storm/index.html`: one small ship, eight hand-built patterns that sweep the
screen in waves, and a score that rewards grazing the shards as closely as you dare. A run is sixty seconds, then the
storm speeds up for a high-score chase. The title card carries your name, the ship flies in your color, and the best
score and longest graze streak stay in the player's browser.

## Run

From the project folder, before asking for any personal details, run the app on the person's inputs file, or on a
copy of the example when there is none yet:

```sh
cd <project> && test -f shard-storm.inputs.json || cp <agent-apps root>/shard-storm/inputs.example.json shard-storm.inputs.json
cd <project> && python3 <agent-apps root>/shard-storm/scripts/run.py
```

It reads `shard-storm.inputs.json` in the project folder and writes the game to `out/shard-storm/`. A missing or
wrong key is named in one line and nothing is written. Running it again on the same inputs writes the same files.

## Check

- `out/shard-storm/index.html`, `out/shard-storm/config.js`, `out/shard-storm/theme.css`, and
  `out/shard-storm/vendor/three.module.min.js` exist.
- `config.js` holds the `playerName` and `title` from the inputs.
- Served (see Host) and opened in a browser, the title card is on screen from the first frame over a storm of
  glowing shards; within a second it gives way to an autopilot run with the full HUD: the clock counting down, the
  score and multiplier climbing, the graze streak rising with each graze, and slow time opening a lens around the
  ship every few seconds. A wave name such as "Vortex" lands within the first ten seconds, and the title comes back
  between stretches of the autopilot run. One tap, a click on Play, or Space starts your own run; shards are on screen
  within two seconds and the wave name appears.

## Host

The game is a static folder. Serve it, never open it as a file (browsers refuse its modules from a file address):

```sh
cd <project> && python3 -m http.server 8000 --directory out/shard-storm
```

Then open `http://localhost:8000/`. To keep it running after the session ends, put the whole `out/shard-storm/`
folder on any static host (GitHub Pages, Netlify, Cloudflare Pages, or your own server); it works under a subpath
too, and it calls no outside service.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds.
A tap on it opens this app's page on code-config.com. It sends no data anywhere. To remove it, delete the
`<script src="./badge.js" defer></script>` line from `out/shard-storm/index.html` (or from `site/index.html` in the
app folder, so every later run leaves it out).

## Make it yours

Ask in one message: "What's your name for the scoreboard, which look do you want (neon, ember, or ice), and what
color should your ship be?" Then set these keys in `shard-storm.inputs.json` and run again:

- `playerName`: the name on the best-score line, the result card, and the copied score.
- `theme`: `neon` (magenta and cyan), `ember` (orange and gold), or `ice` (white and blue). Each theme has a dark
  version with bloom and a light version in ink on paper; the player's device setting picks between them.
- `shipColor`: the ship and its wake, as a hex color such as `#3dff8b`.
- `title`: the name on the title card and the browser tab (default "Shard Storm").
- `runSeconds`: the length of a run before the storm is cleared and overtime begins (default 60).
- `patterns`: which patterns a run cycles through, by name (default all eight).

Nothing here needs a build step. Deeper changes, each one file:

- A theme is `site/themes/<name>.css`, tokens only. The page and the 3D scene both read it, so one file recolors the
  type, the shards, the sparks, the stars, and the grid. Copy one, change the colors, and name it in `theme`.
- A new pattern is one exported function in `site/game/patterns.js` plus one line in `PATTERNS`; its name then works
  in `patterns`.
- The look of the shards, halos, sparks, and stars lives in `site/scene/materials.js`.
- The sounds are files in `site/audio/`, rendered by `python3 scripts/sounds.py` (standard library); change a sound
  there and run it again to rewrite the files.
