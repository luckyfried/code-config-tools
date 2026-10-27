# Cheat Sheet

## What this makes

A one-page reference for the tools the person is learning: shortcuts as keycaps with the real glyphs (⌘ ⌥ ⇧ ⌃ on a Mac, Ctrl, Alt, and Shift elsewhere), commands in mono, grouped in columns with hairline rules. On screen the keys stand up off the sheet and tapping a row presses them in order. It has a search that closes the sheet up around the matches, a Mac, Windows, and Linux toggle, and Learn, which turns every key face down until the row is hovered or tapped. Printed, it is light paper at A4 or Letter in two or three columns with the title up the left margin.

## Run

Write `cheat-sheet.inputs.json` in the project folder (copy `inputs.example.json` from this folder to start), then:

```
cd <project> && python3 <agent-apps root>/cheat-sheet/scripts/run.py
```

It writes `out/cheat-sheet/`. Running it again replaces that folder with the same files. If a key is missing or wrong, it prints one plain line for each problem and writes nothing.

## Check

- `out/cheat-sheet/config.js` carries every section and entry from the inputs file.
- `out/cheat-sheet/theme.css` is the theme the inputs name.
- Served and opened, the title is at the top, every entry shows keycaps (`kbd`) or a command (`code`), and typing an action's name in the search leaves that row alone on the sheet.
- Printing shows the chosen number of columns on light paper, with no keycap split across a column or page.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/cheat-sheet
```

Then open http://localhost:8000/. To keep it online, upload the `out/cheat-sheet/` folder to any static host. Print from the page's Print button; the browser's print dialog can also save it as a PDF.

## Make it yours

Ask the person, in one message: "Which tool or tools is this for? Mac, Windows, or Linux? Which shortcuts or commands do you keep forgetting, so they go at the top?" Then write `cheat-sheet.inputs.json`:

- `title`: the sheet's name, like "Neovim, the parts I use".
- `platform` (optional): `mac`, `windows`, or `linux`, the keys shown first. The page has a toggle for the others. Default `mac`.
- `sections`: the groups, top to bottom, each a `label` and its `entries`. Put the ones the person keeps forgetting in the first section.
- Each entry: `action`, what it does in the person's words, and at least one of
  - `keys`: keys pressed together, like `["mod", "shift", "p"]`, or keys pressed one after another, like `[["ctrl", "b"], ["%"]]`. `mod` is Command on a Mac and Ctrl elsewhere; names include `cmd`, `ctrl`, `alt`, `shift`, `enter`, `esc`, `tab`, `space`, `backspace`, `up`, `down`, `left`, `right`, `f1` to `f12`, and any single character.
  - `command`: a command typed in full, shown in mono.
  - `platforms`: keys for `mac`, `windows`, or `linux` where they differ from `keys`.
  - `note` (optional): one short line under the action.
- `columns` (optional): 2 or 3 columns on the printed page. Default 3.
- `paper` (optional): `A4` or `Letter`. Default `Letter`.
- `theme` (optional): `graphite` (cool: bone keycaps on near-black in dark mode, graphite caps on a pale desk in light) or `paper` (warm: a white sheet with bone caps, deep ink at night). The page follows the device's light or dark setting; print is always light paper. Default `graphite`.

To change the sheet later, edit the inputs file and run the Run line again. The page keeps the person's platform, Learn, and search choices on their device.
