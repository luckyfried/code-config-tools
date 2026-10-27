# Tournament Bracket

## What this makes

A bracket page for a league or an office pool: 4 to 64 entrants, single elimination, seeds and byes. On load the connector lines draw themselves and the results so far play out in order: each winner's chip slides along its line into the next round, an upset flashes the seed that fell, the pool standings reorder as points land, and the champion's name springs up letter by letter under canvas confetti. The page has four screens: Bracket, Picks (each person picks every match, one at a time, then passes the device on), Results (tap a winner, type the score), and Pool (points, correct picks, the most a person can still reach, and their champion). A pick is worth 1 point in round one and doubles each round. Big screen mode, or `?tv=1` on the address, fills a TV with the whole bracket and the standings and pans slowly across a bracket taller than the screen. A phone shows one round at a time with snap scrolling and the whole bracket under pinch zoom.

## Run

Write `tournament-bracket.inputs.json` in the project folder (copy `inputs.example.json` from this folder to start), then:

```
cd <project> && python3 <agent-apps root>/tournament-bracket/scripts/run.py
```

It prints the match count and writes `out/tournament-bracket/`. Running it again replaces that folder with the same files. If a key is missing or wrong, it prints one plain line for each problem, exits with code 2, and writes nothing.

## Check

- The run prints `<n> entrants: <m> matches, <b> byes.` with `m` one less than `n`.
- `out/tournament-bracket/config.js` carries the title, entrants, people, results, and picks from the inputs file.
- `out/tournament-bracket/theme.css` is the theme the inputs name.
- Served and opened, the lines draw, the results play out, and the champion's banner lands when the final has a result. Every match the inputs decide shows its winner and score, and the pool standings match the picks.
- Reloading the page keeps every pick and result entered on it.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/tournament-bracket
```

Then open http://localhost:8000/, or http://localhost:8000/?tv=1 on the TV. To keep it online, upload the `out/tournament-bracket/` folder to any static host. Picks and results entered on the page stay in that browser; Export downloads them as a file, and Import loads that file on another device.

## Make it yours

Ask the person, in one message: "What is the tournament called? Who are the entrants, best seed first? Who is in the pool? Any results so far? Which look: auto, court, pitch, paper, or broadcast?" Then write `tournament-bracket.inputs.json`:

- `title`: the tournament's name, shown large at the top.
- `entrants`: every entrant in seed order, best first, 4 to 64 names, each once. A field that is not a power of two gives byes to the top seeds.
- `people` (optional): who is making picks. Leave it out for a bracket with no pool.
- `results` (optional): one entry per finished match, like `{"match": "R1-1", "winner": "Harbor Hawks", "score": "64-41"}`, with the score written winner first. Match ids are `R<round>-<number>`, numbered top to bottom in each round; round one counts only real matches, not byes. A match's result needs the results of the matches that feed it.
- `picks` (optional): each person's picks, like `{"Maya": {"R1-1": "Harbor Hawks"}}`.
- `colors` (optional): a hex color for each entrant's chip, like `{"Harbor Hawks": "#1f6feb"}`. An entrant with none gets one from a built-in set.
- `theme` (optional): `auto` (paper on a light device, broadcast on a dark one), `court` (hardwood, light), `pitch` (grass at night, dark), `paper` (graph paper, light), or `broadcast` (a TV graphics package in the dark, each chip filled with its entrant's color). Default `auto`.
- `copy` (optional): every word on the page by key (`bracket`, `picks`, `results`, `pool`, `champion`, `upset`, and the rest in `inputs.example.json`), to rename or translate it. A key left out keeps its default.

When people enter picks and results on the page, Export downloads `tournament-bracket.json`; copy its `results` and `picks` into the inputs file and run the Run line again to make them part of the page everyone opens.

Every key above, the theme, and the copy change with the Run line alone; no Node is needed. A change to the page itself (a new screen, a component, a scoring rule, double elimination, a dependency) is an edit in `src/` followed by three commands: the two below in this folder, then the Run line:

```
npm ci && npm run build
```

`npm ci` installs the exact packages in `package-lock.json`, and `npm run build` type-checks and rebuilds `dist/`, which the Run line copies.
