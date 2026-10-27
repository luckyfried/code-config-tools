# Home Hunt

## What this makes

A board of the homes you find for the person, in `out/home-hunt/`: tall photo cards in the columns new, yes, and
maybe, each with the price, the rooms and baths, the floor area, the neighborhood, the listing's link, and every fact
you checked with where you checked it. They mark each home yes, no, or maybe with a tap (a swipe on a phone, the keys
Y, N, and M on a desktop), leave notes, put two or three homes side by side in compare, and ask a question about any
home. Their choices come back to you through the app's inbox, and the homes and choices are kept in
`<project>/data/home-hunt/`.

## Run

Make the page first, before asking for anything personal. Copy `inputs.example.json` to `home-hunt.inputs.json` in
the project folder if it is not there, then run:

```sh
cd <project> && python3 <agent-apps folder>/home-hunt/scripts/run.py --serve --port 8000
```

That writes the page to `out/home-hunt/` and serves it, with the inbox, at `http://127.0.0.1:8000/` until stopped.
Without `--serve` it only writes the page. The homes, the person's choices, and the server's process id live in the
data folder, `<project>/data/home-hunt/`, which the first run makes. Running it again on the same inputs gives the
same page; a missing or wrong key prints one plain line per problem and stops.

How you work the board, each from the project folder:

1. **Add the homes you find.** Write them as a JSON list in a file and run
   `python3 <agent-apps folder>/home-hunt/scripts/run.py --add <file>`. A new home needs `id`, `title` (the street
   address or the listing's name), and `price`; give as well `image` and `photos` (https addresses), `source` (the
   listing's link), `color` (the card's paint while the photo loads, like `"#9fb39a"`), `period` (`"sale"` or
   `"month"`), `rooms`, `baths`, `area` (in the inputs' units, or null), `place` (neighborhood and city), `commute`
   (like `"24 min by bus to downtown"`, or null), `checked` (a list of `{"fact", "source"}`, one per fact you
   checked, with the link where you checked it; keep each fact to about 20 characters, like `"Roof inspected 2025"`,
   because the first one sits on the photo as a chip), `found_at`, and `agent_notes` (a list of sentences). The page shows
   new homes within five seconds.
2. **Add to a home already there** with the same command and only what you add: its `id` and, for example, more
   `checked` facts, `agent_notes`, or a question with its answer filled in (`{"question": "<the question as asked>",
   "answer": "<what they said>"}`). The person's status and notes stay as they are. The add is made at the home's
   current revision; give `"revision"` with the number you last read and a change the person made since then is
   refused with a line that names it, so nothing is overwritten.
3. **Read the person's choices** when they ask you to: run
   `python3 <agent-apps folder>/home-hunt/scripts/run.py --work`. It takes every waiting choice once and prints one
   line for each. A yes, no, or maybe moves the home and prints the move; a note is kept on the home. A yes means they
   like the home and nothing more: it never lets you contact anyone.
4. **Ask only on their word.** A question prints `Ask before: asking <the listing's site> about <the home>:
   <question>`. Nothing on the page reaches outside this computer. Tell the person in the conversation what you would
   send and to whom, send it only once they say so, and when the answer comes back put it on the home with `--add`
   (step 2). The answer then unfolds under the question on the card.

## Check

- `out/home-hunt/index.html`, `out/home-hunt/config.js`, and `out/home-hunt/theme.css` exist, and `config.js` holds
  the person's name and ask.
- `python3 <agent-apps folder>/home-hunt/scripts/run.py --check`, run from the project folder, prints the data folder,
  the inbox counts, and `ok: yes`, and exits 0.
- With `--serve` running, `http://127.0.0.1:8000/` shows "<name>'s home hunt", the homes in their columns, and a
  choice made there appears as one file in `<project>/data/home-hunt/inbox/`; the same choice twice is still one file.

## Host

On this computer, `--serve` keeps the board and its inbox running for as long as the command runs; stop it with
Ctrl+C or by its process id in `<project>/data/home-hunt/server.pid`. Choices need `--serve`. The page alone, with the
sample homes and the choices turned off, also runs from any static host: serve the folder with
`cd <project> && python3 -m http.server 8000 --directory out/home-hunt`, or copy `out/home-hunt/` to a static host the
person names. For a cloud agent, put the output folder `out/home-hunt` online.

## Make it yours

Ask for the personal things in one message: their first name, where they want to live, whether they are buying or
renting, the budget, how many rooms, what they can't do without, the look, and whether you may send their questions
once they say so on each one or should only write them for them to send. These keys in
`<project>/home-hunt.inputs.json` need no Node, only another run:

- `name`: their first name; the board's title is "<name>'s home hunt". Ask for it.
- `ask`: where, buy or rent, the budget, the rooms, and the must-haves, in one or two sentences, shown at the top so
  you and they agree on it. Ask for it.
- `currency`: the prices' currency as a three-letter code. Default `USD`.
- `units`: floor area in `sqft` or `m2`. Default `sqft`.
- `compare_rows`: which facts compare shows, in order, from `price`, `price_per_area`, `rooms`, `baths`, `area`,
  `commute`, and `place`. Default all seven.
- `theme`: `open-house` is airy white with sage and brass, `after-dark` is deep navy with a warm window glow, and
  `auto` follows the device between the two. Default `auto`.
- `sample`: the homes the page shows before `--serve` runs. Default the twelve in `inputs.example.json`.
- `sampleInbox`: choices the sample shows, each with `action`, `target`, `status`, and `at`. Optional.

The words on the board come from these keys and the homes, and the colors come from `src/themes/<name>.css`, which
`run.py` copies, so neither needs Node. A new component, a change to a page, or a new dependency needs Node, in two
folders in this order: edit `src/`, run `cd <agent-apps folder>/home-hunt && npm ci && npm run build` in the app
folder, then run the Run command above from the project folder.
