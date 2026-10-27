# Deal Board

## What this makes

A one-person sales board as a web page: stages as columns, deals as cards, and a headline that is the weighted value of the pipeline (each open deal's value times its stage's probability). Dragging a deal to a later stage rolls the headline to its new total. A funnel and a ninety-day won-and-lost chart sit beside it, and the page has a sortable List and a Won and lost view with the win rate and the average cycle time. The deals live in the browser the page is opened in; Settings exports them to a file and imports them back.

## Run

From the person's project folder, before asking for anything personal, so they see the board working on the sample deals:

```sh
cd <project> && cp <agent-apps root>/deal-board/inputs.example.json deal-board.inputs.json   # only when deal-board.inputs.json is not there yet
cd <project> && python3 <agent-apps root>/deal-board/scripts/run.py
```

`scripts/run.py` reads `deal-board.inputs.json` from the project folder and writes the page to `out/deal-board/`. It needs only Python 3; nothing is built or downloaded. A missing or wrong key is named in one line and nothing is written.

## Check

The run prints `Wrote out/deal-board/ (… files).` Serve the folder (see Host) and open `http://localhost:8000/`: the board shows the stages from the inputs as columns, the headline shows the weighted total, and on the first visit the board replays its latest day of moves (a card sliding forward, a win flying off with confetti, a loss fading into the Lost drawer) while the headline rolls. Drag a card one stage to the right: the headline changes by the deal's value times the difference in the two stages' probabilities, and a reload keeps the move.

To read the deals back (for a weekly pipeline summary), ask the person to open Settings, choose Export the board, and hand you the `deal-board-<date>.json` file. Each deal in it carries its value, stage, next step, date, notes, and a log of every stage move with its time.

## Host

The page is a static folder. It must be served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/deal-board
```

and open `http://localhost:8000/`. Any static host (GitHub Pages, Netlify, Cloudflare Pages, a plain web server) can serve `out/deal-board/` as it is, at any path. The deals are kept in each visitor's own browser under `deal-board:v1`; nothing is sent anywhere.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete the `<script src="./badge.js" defer></script>` line from `out/deal-board/index.html` (or from `index.html` in this folder before a rebuild).

## Make it yours

Ask, in one message: "What stages does a deal go through for you, or shall I use five standard ones? What currency? What deals are open right now, with a rough value and stage each?" Then edit `<project>/deal-board.inputs.json` and run again. `inputs.example.json` explains every key in its `_notes`.

- `name`: the board's title.
- `currency`: an ISO code such as USD, EUR, or GBP.
- `stages`: each `{ "id", "label", "probability", "color" }`, in order; `probability` is 0 to 100 and `color` is `#rrggbb` (each theme keeps the lightness inside its own range; the example runs a dusk ramp from indigo through violet, rose, and coral to gold).
- `seedDeals`: each `{ "company", "value", "stage" }` and, when known, `contact`, `nextStep`, `date` (YYYY-MM-DD, or a number of days from today), `notes`, `daysInStage`, `openedDaysAgo`, and `from`. A `stage` of `won` or `lost` fills the ninety-day chart. Seed deals fill the board only the first time it opens in a browser; after that, Settings has Start over with the first deals.
- `theme`: `boardroom` (navy black, stage colors at full chroma, the headline in bone), `whiteboard` (white with indigo ink, stage colors at 80 % chroma, hairline columns), or `auto` (whiteboard or boardroom with the system's light or dark setting). Each theme is one file of shadcn color variables in `src/themes/`; a new theme is a new file there, named in the inputs.

None of the above needs Node. Changing what the page does (a new deal field, a new chart, a new view) is an edit under `src/`, and needs Node 22 or later: from this folder run `npm ci && npm run build`, check it with `npm test`, and commit the rebuilt `dist/` with the change. `node_modules/` is never committed.
