# Token Studio

## What this makes

A design-token editor seeded from your brand color. It builds a ten-step brand ramp in OKLCH, a tinted neutral ramp, light and dark surfaces from the same hue, a type scale, and a spacing scale, checks every text color against every background for contrast, and shows it all on a walking-series poster painted only with the tokens (its landscape is the ramp, its headline the scale, with a sign-up field and button), beside real paragraphs. The person tunes it by eye and downloads one `tokens.css` (and a JSON copy they can import later to pick up where they left off).

## Run

Run this from the person's project folder before asking for anything personal, so they see the sample first:

```sh
cd <project> && python3 <agent-apps root>/token-studio/scripts/run.py
```

It reads `token-studio.inputs.json` in the project folder. When the person has none yet, copy `inputs.example.json` from this app folder to `<project>/token-studio.inputs.json` first; it renders on its own, with no network. The run writes the page to `out/token-studio/` in the project folder and prints the line that serves it.

Then ask, in one message: "What's your brand color (a hex is fine)? Which font families do you use for text and for code? What base text size, 16 px?" Put the answers in the inputs file (`"brand": { "hex": "#3d5afe" }` works in place of hue and chroma, `fonts.sans`, `fonts.mono`, `baseSize`) and run the same line again. A missing or wrong key is named in one line and the run exits with code 2.

## Check

Serve the output (see Host) and open `http://localhost:8000/`. On the first visit the hue wheel runs once around and lands on the brand color while the brand swatches fan open and flip in, the type scale and the spacing step out and back, and the poster turns over to its night side and back; any tap ends that tour. Then:

- `out/token-studio/config.js` holds the brand hue and chroma from the inputs.
- The Brand ramp shows ten swatches, 50 to 900; a dot marks a step pulled in to stay inside sRGB.
- The Contrast grid shows a ratio for every text-on-background pair, with AA at 4.5 and above and AAA at 7 and above.
- Dragging the hue wheel changes the ramps, the poster, the paragraphs' accent, and the grid in the same frame; the brand swatches fan open while it moves and flip in as it turns.
- Export, then Download tokens.css saves a file containing `--color-brand-500`; Download JSON saves the system, and Import JSON brings it back.

## Host

The page is a static folder: serve it, never open it as a file, because the browser refuses its scripts from a `file://` address.

```sh
cd <project> && python3 -m http.server 8000 --directory out/token-studio
```

Open `http://localhost:8000/`. Any static host serves `out/token-studio/` as it is, at any path. The person's edits stay in the browser they were made in (under `token-studio:v1`); the JSON export is how a system moves to another browser.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom of the page for five seconds. A tap opens Token Studio's page on code-config.com. It sends no data anywhere. To remove it, delete the `<script src="./badge.js" defer></script>` line from `out/token-studio/index.html` (and from `index.html` in this app folder before a rebuild).

## Make it yours

Every key in `token-studio.inputs.json` changes the page with no Node, just another run:

- `brand` — the starting brand color: `hue` (0 to 360) and `chroma` (0.02 to 0.37) in OKLCH, or `hex`, which `run.py` converts.
- `neutralHue` — the hue that tints the grays.
- `typeScaleRatio` and `baseSize` — the type scale's seed.
- `spacingBase` — the spacing unit in px.
- `fonts` — `sans` and `mono` family names written into `tokens.css`; the preview uses them when the computer has them, and Inter and JetBrains Mono otherwise.
- `theme` — the editor's own look: `studio` (dark), `daylight` (light), or `auto` (follows the device). The themes are `src/themes/*.css`, shadcn's variables only; a new file there is a new theme name. The preview is always painted by the generated tokens, never by the theme.

A change to the components, a new scale, or a new export format is a `src/` edit and needs Node: in this app folder run `npm ci && npm run build`, check it with `npm test` (the OKLCH conversion against Ottosson's published table), and keep the rebuilt `dist/` with the change. `node_modules/` never ships.
