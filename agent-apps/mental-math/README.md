# mental-math

## What this makes

A daily mental math drill for one person or a whole household: ninety seconds of problems at a level that adapts as
you answer, a score, and a thirty-day curve for each player. Kid players get untimed drills, bigger keys, rounded
type, and confetti. The page is one folder you can open on a phone or a computer; results stay in the browser it was
opened in, with Export and Import on History to move them or hand them to an agent.

## Run

Run this from the project folder before asking anyone for their names or levels; it uses the person's
`mental-math.inputs.json` when that file is there:

```sh
cd <project> && python3 <agent-apps root>/mental-math/scripts/run.py
```

When `mental-math.inputs.json` is not in the project folder yet, copy `inputs.example.json` from this folder to
`<project>/mental-math.inputs.json` first, then run the line above. It writes the page to `<project>/out/mental-math/`
and prints the line that serves it. A missing or wrong key stops the run with one plain line naming it.

Then ask, in one message: "Who will use it, and roughly what level is each (early school, confident, sharp)? Which
operations? Timed at ninety seconds, or untimed?" Write the answers into `mental-math.inputs.json` and run again.

## Check

Serve the folder (see Host) and open `http://localhost:8000/`. The page opens on the chalkboard working problems by
itself above the number pad, its streak plate climbing and bursting with each right answer, with each player in the
row at the top. Press Go (or Enter), answer ten problems, and
the Results screen shows the score ring, the level badge, and the thirty-day curve with today's point; reload and the
score is still there under that player's name on History. A kid player shows the pad with larger keys and no timer
bar. `out/mental-math/config.js` holds the players and operations from the inputs file.

## Host

The page must be served, not opened as a file, because the browser refuses its modules from a `file://` address:

```sh
cd <project> && python3 -m http.server 8000 --directory out/mental-math
```

Open `http://localhost:8000/` on this computer, or this computer's address on the same network from a phone. Any
static host serves `out/mental-math/` as it is, at any path. Results live in each browser's own storage under
`mental-math:v1`; use Export on History to keep a copy or move it to another device.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds; a tap opens
this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js" defer>` line
from `site/index.html` and run again.

## Make it yours

Every key in `mental-math.inputs.json` changes without touching code; `inputs.example.json` explains each one in
`_notes`:

- `players`: one or more `{ "name", "level", "kid" }`. `level` is where a player starts, 1 (early school) to 10
  (sharp); the drill steps it up after 90 % right over ten answers and down at 60 %, and anyone can nudge it with the
  minus and plus beside the badge on Start. `kid: true` drops the timer (ten problems instead), enlarges the keys,
  uses the rounded type, and celebrates every finish.
- `operations`: any of `add`, `subtract`, `multiply`, `divide`, `percent`, `squares`. Each player can switch some off
  on Start, and the page remembers that per player.
- `seconds`: the drill length; `0` means untimed.
- `theme`: `chalk` (a blackboard), `candy` (cream and bright keys), `slate` (gray with one accent), or `auto` (slate by
  day, chalk at night, candy for kid players). Every theme has a light and a dark look that follows the device.

Colors live only in `site/themes/<name>.css`; layout lives in `site/styles/` and names no color. After changing
`slate.css`, `chalk.css`, or `candy.css`, run `python3 scripts/make_auto_theme.py` from this folder to rebuild
`auto.css` from them. The problems for each level are tables at the top of `site/game/problems.js`. No step needs
Node or a build: edit, run `run.py` again, and reload.

Results are stored as `{ "<player>": [{ "date", "score", "level", "accuracy" }] }`; an exported file has exactly that
shape, so an agent asked how the week went can read it directly.
