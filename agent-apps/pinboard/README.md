# Pinboard

## What this makes

A wall of visual pins, each an image with a title, its source link, a note, tags, and a board, laid out as a masonry
that fills a phone in two columns and a desktop in four or five. The person keeps, sets aside, moves, or asks for more
like any pin with one tap; you read those choices, sort the pins, and add what you find. Every pin and every choice is
kept on this machine in the project's data folder, `<project>/data/pinboard/`.

## Run

Make the page from the project folder. With no `pinboard.inputs.json` there yet, copy `inputs.example.json` to it
first; it runs as is.

```
cd <project> && python3 <agent-apps folder>/pinboard/scripts/run.py
```

It writes the page to `<project>/out/pinboard/`. To let the person make choices on it, serve it with its inbox:

```
cd <project> && python3 <agent-apps folder>/pinboard/scripts/run.py --serve
```

This serves the page and the inbox at `http://127.0.0.1:8765/` (`--port N` picks another port) and keeps the pins
and the person's choices in the data folder, `<project>/data/pinboard/`. Leave it running in its own terminal.

The loop, each time the person asks you to look at their board:

1. Read their choices: `cd <project> && python3 <agent-apps folder>/pinboard/scripts/run.py --work`. It takes every
   pending choice once and prints one line for each: `Kept: <title>`, `Set aside: <title>`, `Moved: <title> to
   <board>`, or `Find more like: <title> (<source>)`.
2. For each `Find more like` line, find a few things like that pin with your own tools (a search, a page you read),
   then write them to a JSON list of pins and add them:
   `cd <project> && python3 <agent-apps folder>/pinboard/scripts/run.py --add finds.json`.
   A pin is `{"id", "title", "image", "source", "note", "tags", "board", "color", "agent_notes", "found_for"}`:
   `image` is an https address of the picture, `source` the page it came from, `color` a hex color close to the
   picture's, `board` the asking pin's board, `found_for` the asking pin's id (the find sits beside it on the wall),
   and `agent_notes` one line on why you picked it. An id already on the board updates that pin; when the person
   changed it since you read it, the line says `Conflict` and nothing is overwritten: read it again and add it once
   more.
3. Say in the conversation what you added and what the person's choices did.

Every action on this board changes only this machine. You never reach outside this machine on a choice alone: if a
pin needs something done elsewhere (buying it, booking it, writing to someone), ask the person in the conversation
first. No one wakes you when a choice lands; the person asks you to look, and each card shows its choice as pending until you do.

## Check

- `<project>/out/pinboard/index.html`, `config.js`, and `theme.css` exist, and the page shows "<name>'s boards" with
  the sample pins on their boards.
- `cd <project> && python3 <agent-apps folder>/pinboard/scripts/run.py --check` prints `ok: yes`, the data folder,
  and the inbox counts, and exits 0.
- With `--serve` running, a tap on a pin's keep shows "Keep, pending" on the card; after `--work` the card says
  "Keep, completed: Kept", and a reload shows the same.

## Host

Choices need the page's own server: `cd <project> && python3 <agent-apps folder>/pinboard/scripts/run.py --serve`,
then open `http://127.0.0.1:8765/` on this machine. Stopping it and starting it again changes nothing; the pins and
choices stay in `<project>/data/pinboard/`.

To show the board without taking choices, serve the output folder as it is:
`cd <project> && python3 -m http.server 8000 --directory out/pinboard`, then open `http://localhost:8000/`. Served
that way the page shows the sample pins, and each card says "View only" where its choices would be. Any static host takes the
`out/pinboard/` folder as it is.

## Make it yours

The inputs file is `<project>/pinboard.inputs.json`. Ask the person, in one message, what their boards are for and
what kinds of things to look for; default the rest.

- `name`: whose boards these are; the page reads "<name>'s boards". Ask.
- `boards`: the starting board names, like `["Kitchen", "Kyoto trip", "Studio brand"]`. Ask.
- `theme`: `auto` (Gallery in a light room, Dusk in a dark one), `gallery` (white walls, thin lines, a red dot on a
  kept pin), or `dusk` (deep warm gray, amber highlights). Default `auto`.
- `sample`: the pins the page shows when it is served without `--serve`. Keep the example's, or put a few of the
  person's own; a picture in the project folder is copied into the page's `media/` folder.

None of that needs Node: change the inputs, the theme, or the copy in `config.js`, then run the Run line again.

A change to a component, a page, or a dependency is a change to `src/` and needs Node: edit `src/`, then from this
folder run `npm ci`, `npm run build`, and the Run line again; `dist/` is what the Run line copies.
