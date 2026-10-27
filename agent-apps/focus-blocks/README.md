# Focus Blocks

## What this makes

A focus timer page in `out/focus-blocks/`: a full-screen ring that drains as a block runs, a strip of today's finished
blocks, and a week of seven strips with the hours for each day, all kept in the browser.

## Run

```
cd <project> && python3 <agent-apps folder>/focus-blocks/scripts/run.py
```

It reads `<project>/focus-blocks.inputs.json`, or `inputs.example.json` from this folder when the project has none,
and writes the page to `<project>/out/focus-blocks/`. A missing or wrong key prints one plain line per problem and
exits 2 without writing anything.

## Check

- `out/focus-blocks/index.html`, `out/focus-blocks/config.js`, and `out/focus-blocks/theme.css` exist.
- `out/focus-blocks/config.js` starts with `window.__APP_CONFIG__ =` and holds the person's name and block lengths.
- Served and opened, the page greets the person by name, shows the ring, and the Start button names the first length.

## Host

Serve the output folder on this computer with `python3 -m http.server 8000 --directory out/focus-blocks` and open
http://localhost:8000, or copy `out/focus-blocks/` to any static host the person names. The page needs no server code
and fetches nothing from the network; its blocks live in the browser that opened it.

## Make it yours

Ask for these in one message: "What block lengths do you like (25, 50, 90)? What three or four things do you usually
focus on, a word each? Dusk, dawn, or mono?" Then write `<project>/focus-blocks.inputs.json`:

- `name`: the first name in the greeting.
- `blockLengths`: one to five lengths in minutes; the first is the default.
- `labels`: up to six one-word quick picks for what a block is for.
- `dayStart`, `dayEnd`: the hours the day strip covers; default 6 and 24.
- `chime`: `soft` for a two-note chime at the end of a block, `off` for silence; default `soft`.
- `theme`: `dusk`, `dawn`, `mono`, or `auto` (dawn on a light device, dusk on a dark one).
- `sample`: leave it out (or `false`) for a real start; `true` fills a first visit with a sample week and opens on a
  block's last seconds, which ends and hands the ring to a new block at the first length.

Restyle a theme by editing its file in `site/themes/`; every color the page uses is a token there.
