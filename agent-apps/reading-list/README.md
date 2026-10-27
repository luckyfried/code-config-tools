# Reading List

## What this makes

A front page of the stories you find for the person, in `out/reading-list/`: a broadsheet grid with the lead story
across the top and the rest packed tall, wide, and small, each picture in its topic's color. They send a story to
read later, skip it, ask for more like it, or ask you to go deeper, with a swipe or a long press on a phone and a
hover or the keys L, S, M, and D on a desktop. Their choices come back to you through the app's inbox, and the
stories, the topics, and the choices are kept in `<project>/data/reading-list/`.

## Run

Make the page first, before asking for anything personal. Copy `inputs.example.json` to `reading-list.inputs.json`
in the project folder if it is not there, then run:

```sh
cd <project> && python3 <agent-apps folder>/reading-list/scripts/run.py --serve --port 8000
```

That writes the page to `out/reading-list/` and serves it, with the inbox, at `http://127.0.0.1:8000/` until
stopped. Without `--serve` it only writes the page. The stories, the person's choices, and the server's process id
live in the data folder, `<project>/data/reading-list/`, which the first run makes.

How you keep the paper, each from the project folder:

1. **Add what you found.** Read each story before you add it. Write the stories as a JSON list in a file, each with
   `id` (letters, digits, and hyphens), `headline`, `source` (the publication's name), `link`, `image` (an https
   address for the story's picture), `color` (the topic's color), `topic` (a topic id from the inputs), `summary`
   (three sentences of your own), `minutes` (the read time), `published_at`, `found_at`, and `agent_notes` (a list
   of sentences on why it is there), then run `python3 <agent-apps folder>/reading-list/scripts/run.py --add <file>`.
   Keep to the person's favored and left-out publications and to `per_day` stories a day. The page shows new
   stories within five seconds.
2. **Read the person's choices** when they ask you to: run `python3 <agent-apps folder>/reading-list/scripts/run.py
   --work`. It takes every waiting choice once and prints one line for each:
   - `<headline>: kept for later.` or `<headline>: skipped.` The story has moved; nothing more to do.
   - `More like: <headline> (<source>)`. Find stories like it in the conversation, and add each with `--add`,
     with `"like"` set to the asking story's id; the page says which story it was found for.
   - `Go deeper: <headline> (<link>)`. Read the story and the other coverage of it, and write a longer brief: run
     `--add` with `[{"id": "<its id>", "deep": {"paragraphs": [...], "coverage": [{"headline", "source", "link"}],
     "at": "<now>"}}]`. Until `deep` is there the card says "The agent is writing the brief."; once it is, the card
     opens into a long read.
3. **Change a story you added** with `--add` and its id, sending only what changes (`deep`, `agent_notes`); the
   person's choice on it stays. Give `"revision"` with the number you last read, and a person's change since then is
   refused with a line naming it, so nothing is overwritten.
4. **Stay on this computer.** A choice on the page never reaches outside this machine on its own: the page writes to
   the inbox, and only you act on it, in the conversation. A line that starts `Ask before:` means ask the person
   first.

## Check

- `out/reading-list/index.html`, `out/reading-list/config.js`, and `out/reading-list/theme.css` exist, and
  `config.js` holds the person's name and topics.
- `python3 <agent-apps folder>/reading-list/scripts/run.py --check`, run from the project folder, prints the data
  folder, the inbox counts, and `ok: yes`, and exits 0.
- With `--serve` running, `http://127.0.0.1:8000/` shows the person's name in the masthead and their stories on the
  front page, and a choice made there appears in `<project>/data/reading-list/inbox/`; `--work` then prints a line
  for it.

## Host

On this computer, `--serve` keeps the page and its inbox running for as long as the command runs; stop it with
Ctrl+C or by its process id in `<project>/data/reading-list/server.pid`. Choices need `--serve`. The page alone,
showing the sample stories with the choices turned off, also runs from any static host: serve the folder with
`cd <project> && python3 -m http.server 8000 --directory out/reading-list`, or copy `out/reading-list/` to a static
host the person names. For a cloud agent, put the output folder `out/reading-list` online.

## Make it yours

Ask for the personal things in one message: the person's first name, their topics, the publications they trust and
the ones they skip, how many stories a day, and the look. These keys in `<project>/reading-list.inputs.json` need
no Node, only another run:

- `name`: their first name; the masthead reads "<name>'s Reading List". Ask for it.
- `topics`: their sections in order, each `{"id", "name", "color"}`; the color tints that topic's pictures. Ask for
  them. Default Planet, Cities, Science, and Culture.
- `sources`: `{"favor": [...], "leave_out": [...]}`, the publications you look in first and the ones you never add.
- `per_day`: the most stories you add in a day. Default 12.
- `theme`: `broadsheet` is light newsprint, `late-edition` is the dark night paper, `auto` follows the device
  between the two. Default `auto`.
- `sample`: the stories the page shows before `--serve` runs: `articles`, the choices on them (`inbox`), and one
  brief that lands while the page plays (`landing`). Default the twelve in `inputs.example.json`.

The words on the page come from these keys and the stories you add, and the colors come from
`src/themes/<name>.css`, which `run.py` copies, so neither needs Node. A new component, a change to a page, or a new
dependency needs Node, in two folders in this order: edit `src/`, run
`cd <agent-apps folder>/reading-list && npm ci && npm run build` in the app folder, then run the Run command above
from the project folder.
