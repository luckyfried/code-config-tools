# Daily Word

## What this makes

A one-page daily word game on the person's own topic: six guesses at a five-letter word that changes every midnight,
drawn in order from a word list you write for them (their field, their family, their team's in-jokes). The tiles turn
over like real slabs, the keyboard lights up green and amber, a win sets off confetti, and the page keeps a streak,
a guess distribution, a share grid of colored squares, an endless mode, and hard mode. The output is a folder,
`out/daily-word/`, that any static host can serve.

## Run

From the person's project folder, before asking for anything personal, so they see the sample game first:

```sh
cd <project> && cp -n <agent-apps root>/daily-word/inputs.example.json daily-word.inputs.json; python3 <agent-apps root>/daily-word/scripts/run.py
```

With `daily-word.inputs.json` already in the project, `cp -n` leaves it alone and the run uses it; otherwise the
sample (a kitchen word list) is copied in first. The script checks every key and every word, then writes the page to
`out/daily-word/` and prints the line that serves it. A word that is not five letters, or holds anything but
letters, is named in one line and nothing is written.

## Check

- `out/daily-word/index.html`, `config.js`, and `theme.css` exist, and `config.js` holds the title, the launch date,
  and every word in the list.
- Serve it (Host below) and open `http://localhost:8000/`. A first visit plays one short round on the board by
  itself; a tap or any key starts the real game. Typing today's word and Enter wins.
- `http://localhost:8000/test/words.html` reads "All 12 passed": the scoring rule with repeated letters, hard mode,
  the day count, and a share grid that never spells the word.

## Host

The page is served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/daily-word
```

and the person opens `http://localhost:8000/`. Any static host takes the `out/daily-word/` folder as it is, at any
path. Stats and settings stay in the player's own browser and are never sent anywhere.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds; a
tap opens this app's page on code-config.com. It sends no data. To remove it, delete the
`<script src="./badge.js" defer></script>` line from `site/index.html` and run again.

## Make it yours

Ask in one message for the game's name, its topic, the launch date that counts as day 1, and a palette (paper,
night, or candy). Then write the word list yourself: 60 to 365 common five-letter words on that topic, no plurals
made by adding S, nothing crude or hurtful, nothing a player could not be expected to know. Show the first ten for
approval, then write `daily-word.inputs.json`:

- `title`: the game's name, up to 40 characters; it heads the page and the share grid.
- `topic`: one line about the words, shown under the name and on the how-to-play sheet.
- `words`: the answers in play order, one a day; the list starts over at its end.
- `launchDate`: `YYYY-MM-DD`; day 1 is this date.
- `allowExtra`: guesses to accept beyond everyday English (names, jargon, in-jokes). The answers are always accepted.
- `theme`: `paper` (cool paper, ink, and sage), `night` (deep green with emerald and amber light), or `candy`
  (bubblegum, mint, and sunshine). Each has a light side and a dark side that follow the device; players can also
  pick light, dark, or another palette in settings.
- `hardMode`: `true` starts games in hard mode; players can still change it before their first guess.

Run again after any change. Nothing here needs a build step or a network: new colors go in `site/themes/<name>.css`
(color tokens only), and the sounds are rendered by `python3 scripts/make_sounds.py`, which rewrites the files in
`site/sound/`.
