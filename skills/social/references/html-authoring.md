# Authoring a post in HTML (the contract with render.py)

You design every post as your own HTML/CSS file, then `render.py --html` turns it into an exact
WxH PNG. The renderer guarantees the boring parts so you can spend your effort on the design.
Start from `references/html-skeleton.html` (copy it to `build/html/pNN-name.html`).

```
python3 S/scripts/render.py --html build/html/p01-taco.html --format ig_feed_portrait \
   --brand brand.json --out out/p01-taco-1080x1350.png
python3 S/scripts/render.py --batch build/plan.json      # [{"html": "...", "format": "...", "brand": "brand.json", "out": "..."}]
```

Use format **keys** from `formats.json` (`ig_feed_portrait` 1080x1350, `ig_feed_square`, `ig_story` 1080x1920,
`tiktok_cover`, `pinterest_pin`, `link_card` ...). The key turns on that platform's safe-zone check.

## What render.py gives you (you write none of this)

| | |
|---|---|
| **Fonts** | Every bundled family is injected as `@font-face` from local files. Use the names `Archivo Black`, `Archivo`, `Inter`, `Fraunces`, `Playfair Display`, `DM Serif Display`, `Bitter`, `Caveat`, `Work Sans`, `Space Grotesk`, `Manrope`, `JetBrains Mono` in `font-family`. No `<link>`, no CDN. (Write `{{fonts_css}}` inside a `<style>` only if you want to control where it lands.) Any `http(s)` request fails the render. |
| **Brand variables** | `:root` gets `--bg --fg --accent --accent2` from `brand.json`'s palette, `--font-display` and `--font-body` from its fonts, `--brand-name`. |
| **Canvas variables** | `--w` and `--h` (px) are the exact output size; `--safe-top --safe-bottom --safe-left --safe-right` are the platform's keep-clear bands (30px on formats with none). |
| **Autofit** | Put `data-fit` on a text element and it shrinks until it fits (never grows). It needs a box with a fixed height (or a `data-fit-box` ancestor with a fixed height) and `overflow:hidden`; `data-fit-min="0.5"` sets the smallest allowed ratio (default 0.4). If it cannot fit at the minimum the render **fails**; under 60% it warns: shorten the words instead. |
| **Safe-zone check** | Every text node's rectangle must sit inside the safe zone and the canvas. A breach **fails the render** (exit 1, no PNG, the old PNG is deleted) and prints the text and its position. Opt out only for deliberate cropped display type with `data-bleed`, or for decoration with `data-safe-ignore`. |
| **Output** | Exactly `W x H` PNG, written atomically. Text under 22px warns (it will not read on a phone). |

## Rules for the file

- Size the page to the canvas: `html,body{width:var(--w);height:var(--h);overflow:hidden}`. Position with px, %, flex or grid; there is no scaling.
- **Images:** use an **absolute path** (`url("/abs/path/build/photos/p01.jpg")`, `<img src="/abs/...">`) or a path relative to the HTML file. Prepare the photo first with `photo.py fit` so the crop is right. Missing image = broken box; open the PNG.
- **Shared CSS:** `<link rel="stylesheet" href="../design-system.css">` (relative to the HTML file). Put the set's type, colour, grid and motif there once.
- **Text:** write the real words. `{{token}}` placeholders fail the render unless you pass `"data": {...}` in the batch entry (used for motion beats that reuse one layout with progressive text).
- **Colours:** use the variables (`var(--accent)`) so brand changes flow through; add tints with `color-mix(in srgb, var(--accent) 20%, var(--bg))`. No purple.
- **No remote anything**, no JS needed (JS runs, but keep layouts static), no animations in stills.
- Fixed pixel sizes are fine and expected (`font-size:180px`); `data-fit` is the safety net, not the design tool.

## Patterns that work

```html
<!-- headline that must never overflow its box -->
<h1 style="height:300px;overflow:hidden" data-fit>The exact words</h1>

<!-- fit inside a flexible parent: give the parent the height, mark it -->
<div class="price-box" data-fit-box style="height:620px"><div class="price" data-fit>$2</div></div>

<!-- photo with a chosen focal point -->
<div style="position:absolute;inset:0 0 38% 0;background:url('/abs/p01.jpg') 40% 30%/cover"></div>

<!-- Story: stay inside the bands -->
<div style="position:absolute;left:80px;right:80px;top:calc(var(--safe-top) + 24px);bottom:calc(var(--safe-bottom) + 24px)">...</div>
```

## When the render fails

`SAFE ZONE BREACH`: the message names the text and the band; move it, shorten it, or make the box smaller.
`TEXT OVERFLOW`: shorten the words or give the box more room. `loads from the network`: remove the URL.
`unfilled tokens`: you left a `{{...}}`. Fix the file, never loosen the check.
