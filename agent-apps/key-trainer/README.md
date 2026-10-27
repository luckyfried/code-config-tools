# Key Trainer

## What this makes

A typing trainer page for prose or code. The passage runs as one line, an on-screen keyboard in your own layout lights the next key, and after each drill the keyboard becomes a heat map of your error rate per key. A weak-keys drill is built from that map, and speed and accuracy are kept per day with a thirty-day chart.

## Run

Run this from the project folder before asking for anything personal; it uses `key-trainer.inputs.json` there, so copy `inputs.example.json` to that name first when it is missing:

```sh
cd <project> && cp -n <agent-apps root>/key-trainer/inputs.example.json key-trainer.inputs.json
cd <project> && python3 <agent-apps root>/key-trainer/scripts/run.py
```

It writes the page into `out/key-trainer/` and prints the line to serve it. A missing or wrong key in the inputs is named in one plain line, and nothing is written.

Then ask, in one message: "Which keyboard layout do you use? Prose or code? Paste a couple of passages you'd like to practice, or I'll use the built-in set." Put the answers in `key-trainer.inputs.json` and run the same line again.

## Check

Serve the folder as Host says and open `http://localhost:8000/`. The page opens on a sample run: the line types itself, the next key lights on the keyboard, and the results card slides in with the keyboard warming into a heat map. Press any key (or tap the line on a phone) to take over. Finish a drill and you see your words per minute and accuracy, the heat map, and a new point on the thirty-day chart; reload and the drill is still in History. `out/key-trainer/config.js` holds the layout and passages you chose.

## Host

The page is served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/key-trainer
```

Then open `http://localhost:8000/`. Any static host can serve the `out/key-trainer/` folder as it is. Drill results stay in the browser the page is opened in; Export and Import in Settings move them to another browser.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js"></script>` line from `out/key-trainer/index.html` (or from `site/index.html` so every run leaves it out).

## Make it yours

Every key in `key-trainer.inputs.json`; change it and run the Run line again:

- `name`: the name in the greeting.
- `layout`: `qwerty`, `qwertz`, `azerty`, `dvorak`, or `colemak`. The keyboard is drawn from `site/layouts/<layout>.json`.
- `mode`: `prose`, or `code` to keep indentation, brackets, and symbols; Enter ends each line.
- `passages`: your own texts, one string each. Leave it `[]` for the built-in set.
- `drillSeconds`: how long one drill runs, from 15 to 600; 60 is a minute.
- `theme`: `auto` (Paper when the device is light, Terminal when it is dark), `terminal` (black, phosphor green caret, graphite keycaps), or `paper` (white, ink caret, keycaps in bone).

Nothing here needs Node or a build step. Colors live only in `site/themes/*.css`; a new theme is a copy of one of those files with new values, named in `theme`. A new layout is a JSON file in `site/layouts/` in the same shape as the others, plus its name in `LAYOUTS` in `scripts/run.py` and `site/app/layout.js`. The built-in passages and the word list for weak-keys drills are in `site/app/text.js`. The person can also change the layout, mode, drill length, and theme in Settings; those choices stay in their browser.
