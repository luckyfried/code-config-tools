# Step 1: Brand kit

A brand kit is what makes the posts look like one business, today and next week.

## 1. Reuse if it's theirs

Look for `brand.json` in the workspace root (then `out/brand.json`). Reuse it **only if
its `name` is this business**. A brand kit for a different business is ignored (never
blend two businesses). If you reuse it, copy it to `out/brand.json` and tick the box.

## 2. Otherwise derive one (two minutes, no questions)

Sources, in order: the user's logo or photos in `in/` (sample their real colours), their
website if one is given (`curl -sL --max-time 10 <url>`; take colours, tagline, hours,
address; skip silently if unreachable), the name itself, the business type and place.

**Style direction** (pick one; it is a mood, not a template set: it decides which library examples you study first in step 4, and sets the type/colour/texture feel you then design in your own way):

| family | looks like | default for |
|---|---|---|
| `editorial` | serif display, lots of white, photo-led | cafés, studios, real estate, photographers, wedding |
| `bold_type` | huge condensed sans, high contrast, colour blocks | restaurants, gyms, promos, events, sales |
| `warm_craft` | paper texture, hand-drawn accents, rounded type | bakeries, Etsy/makers, nonprofits, markets |
| `clean_modern` | neutral grid, product-forward | e-commerce, launches, B2B, coaches, apps |
| `playful_pop` | bright duotones, stickers, rotated cards | food trucks, kids, casual brands, coffee carts |
| `quiet_luxury` | muted palette, thin type, air | salons, spas, weddings, premium goods |

Use the playbook's suggestion unless the request clearly says otherwise ("festive",
"fun", "classy", "minimal"). Save it as `style_family` in brand.json. The six names are also the folder
names used by `python3 S/scripts/library.py find <job> --family <name>`.

**Palette (max 4)**: `bg` (background), `fg` (text/ink), `accent`, `accent2`. Build it from something real:
the logo, the photos, the name ("El Sol": sun yellow, chile red, warm cream), the
cuisine/culture done respectfully, the place, the season. Rules:

- `fg` on `bg` contrast at least 7:1; `accent` on `bg` at least 3:1.
- **No purple, violet, lavender, magenta or plum** (hues roughly 260-330 degrees). Not as an accent, not in a gradient.
- Avoid the generic generator look: navy+teal+coral, blue-to-violet gradients, pure #000/#fff pairs with one neon.
- Check it: `python3 S/scripts/qa.py palette brand.json` (prints contrast ratios and flags purple).

**Fonts**: a pairing from the bundled set. Use the **CSS family names exactly as written
here** (render.py injects them as `@font-face`, you write `font-family:'Fraunces'` in your HTML): `Archivo Black`, `Archivo`, `Inter`,
`Fraunces`, `Playfair Display`, `DM Serif Display`, `Bitter`, `Caveat`, `Work Sans`,
`Space Grotesk`, `Manrope`, `JetBrains Mono`. Keys: `display` (headlines) and `body`
(everything else). Always set both keys (two typefaces at most). A direction's usual pairing is a fine start, a more
distinctive one for this business is better. Never system fonts, never a CDN.

**Voice**: 3 adjectives plus concrete do/don't lines, written for THIS business:
`"do": ["say the price in the first line", "talk like the person at the counter"]`,
`"dont": ["exclamation marks on every line", "'mouthwatering', 'delectable'", "emoji bullets"]`.

**Logo**: path to their file if supplied. If none: `null`, and you set the name as a
wordmark in the display font. Never draw an invented logo mark.

## 3. Save it

Write `brand.json` (workspace root, so the next session reuses it) and copy it to `out/brand.json`:

```json
{
  "name": "Taqueria El Sol",
  "business_type": "restaurant",
  "playbook": "restaurant",
  "location": null,
  "handle": null,
  "website": null,
  "style_family": "bold_type",
  "palette": {"bg": "#FFF4E2", "fg": "#22160F", "accent": "#E2452B", "accent2": "#F6B321"},
  "fonts": {"display": "Archivo Black", "body": "Inter"},
  "voice": {"adjectives": ["warm", "quick", "neighbourly"],
            "do": ["price in the first line", "one Spanish word where it's natural, never forced"],
            "dont": ["sombreros, cacti or maracas clip-art", "'fiesta' puns", "exclamation marks everywhere"]},
  "logo": null,
  "derived_from": ["name", "business type"],
  "assumed": true
}
```

Field names matter: `render.py` reads `palette`, `fonts`, `logo` and `name`. Add a line to
`## Assumptions` saying the palette/fonts were chosen for them and live in `brand.json`
(so they can change it once and every future post follows). Tick box 1.
