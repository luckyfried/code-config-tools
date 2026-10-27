# Radio Dial

## What this makes

A radio page built like a vintage tuner, written into `out/radio-dial/` in your project. A brushed brass plate holds a backlit frequency strip behind frosted glass; the needle rides a spring from station to station, the lamp warms up when the page opens, and its glow brightens when a station locks. The station's name burns in Nixie tubes with a slight flicker, two VU needles and a spectrum glass move with the music, and tuning plays a burst of static (pink noise through a sweeping filter, made in the browser) that fades as the stream comes in. A stream that does not allow its sound to be read drives the meters with a breathing pulse, so the panel never goes still. On a first open the dial scans its presets once.

Find searches the Radio Browser station directory by name, genre, or country and slides results in as paper index cards: Tune, Add to dial, or star. Favorites keeps the starred stations, with Export and Import. A station that does not answer is marked on the dial and the radio tunes to the next one. Arrow keys tune, space plays, F stars, S scans, and Ctrl+K (Cmd+K on a Mac) opens the command palette. On a phone the strip slides under a fixed needle and the lock screen carries the station. Favorites, added stations, the last station, and the volume stay in the browser under `radio-dial`.

Ask the person, in one message: "Which stations do you listen to (names or stream links)? Any countries or genres to load onto the dial? Walnut, bakelite, or black steel?" Then copy `inputs.example.json` from this folder to `radio-dial.inputs.json` in the project folder and set `name`, `theme` (`walnut`, `bakelite`, or `black-steel`), and `presets`: one entry per station with `name` and an `https` stream `url`, plus `homepage`, `country`, `about` (the line under the station name), and `logo` (an `https` address or a picture file in the project folder) when you have them. For a station named without a link, or a country or genre, look it up at `https://de1.api.radio-browser.info/json/stations/search?name=KEXP&hidebroken=true&order=votes&reverse=true&limit=10` (or `tag=jazz`, or `country=Japan`) and use `url_resolved` from rows that start with `https://`. `_notes` explains every key.

## Run

```
cd <project> && python3 <app>/scripts/run.py
```

It checks `radio-dial.inputs.json`, names any key that is missing or wrong in one line each, and writes `out/radio-dial/`. Running it again gives the same files.

## Check

Serve the folder (below) and open it. The panel warms up, the needle springs to the first preset and its glow brightens, and the station's name lights in the tubes; `config.js` lists every preset and each one sits on the dial. Press play: a burst of static, then the stream, and the VU needles move. Press the right arrow: the needle glides to the next station. Star a station and reload: the star and the station are still there. Type a genre in Find: index cards slide in.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/radio-dial
```

Then open http://localhost:8000/. The folder is static, so any file host serves it from any path. Host it on `https` so every stream plays.

## Make it yours

No Node needed: every input key, the theme, and the copy. Change `radio-dial.inputs.json` and run `run.py` again. A theme is a file in `src/themes/` (`walnut.css`, `bakelite.css`, `black-steel.css`) holding the colors and the panel's materials (wood, plate, lamp, glass, tubes, meters, paper); copy one, change it, and name it in `theme`.

Needs Node: a component, a page, or a dependency (the dial, the meters, the card index, a new screen). Edit `src/`, then in this folder run:

```
npm ci
npm run build
rm -rf node_modules
```
