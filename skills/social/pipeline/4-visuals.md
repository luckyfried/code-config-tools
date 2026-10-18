# Step 4: Visuals

You are a designer, not a form-filler. Every post is an **original HTML/CSS design** made for this brand,
this idea and this picture. The library of 66 reference posts exists to teach you taste; you never fill
one in, and a post that is a library layout with new words fails the critic.

Read first: `S/references/design-principles.md` (the measurable rules) and `S/references/html-authoring.md`
(the renderer contract). Both are short.

## 0. The set's design system (once, before any post, when the set has 2+ posts)

Write `build/design-system.css`: the type pair and scale (headline px, body px, label px), margins and the
2-3 spacing values, how the accent is used, one recurring motif (a rule style, a corner mark, a number
treatment, a crop shape, a photo edge), and the grade you will apply to photos. Every post's HTML links it
(`<link rel="stylesheet" href="../design-system.css">`). Layouts vary by job; the system does not.
The brand's `style_family` is a *direction* (mood, type, texture), not a template set: it picks which
library examples you study first, nothing more.

## 1. Per post: study, then design

**(a) State the job and the family.** In `build/design-notes.md`, one line per post: `p01: job = offer (one price,
$2 tacos), direction = bold_type, picture = taco photo`.

**(b) Pull 3-5 examples and LOOK at them.**
```
python3 S/scripts/library.py find offer --family bold_type
```
It prints the closest examples (your direction plus contrast picks from other families) with the image path and
why each works. Run it without `| head`/`| tail`, then **Read every image file it lists, all of them** (3-5 Read
calls); looking at one example is not studying. Then write 2-3 lines in `build/design-notes.md`
for the post: what **principle** you will borrow ("the price is 5x the headline and gets a third of the canvas";
"the photo bleeds off one edge and type sits on the calm side"), and what you will deliberately do differently.
Borrow principles, never the layout: if your sketch has the same blocks in the same proportions as an example,
change the structure. You may open an example's `templates/.../index.html` to learn a technique (a CSS trick
for condensed type, a torn edge), not to copy it.

**(c) Write the original HTML.** `build/html/pNN-name.html`, from `S/references/html-skeleton.html`. Design for
the post's one idea: decide the focal point first, then size everything else by importance. Use the design
system, brand variables and the photo you prepared. Ask what only this brand would do (its name, place, product,
the day, the number) and make one bold choice from it. Different jobs get different structures: a price post
is not laid out like a quote post. In a set, no two posts share a skeleton: at most two posts may use the same photo/text split, so
vary it (full-bleed photo with a small type block; photo inset on one side; type-only; two photos; a
number or word that fills the frame; a crop that bleeds off one edge).
**Stories (9:16):** the top 250px and bottom 320px are where the app draws its UI, not places to leave
empty. Run the photo or the colour through them (full-bleed), and keep the *words* in the middle
band, with the focal element at 35-65% of the height. A Story with a flat blank slab under the text,
or a cream strip above a photo, looks unfinished. See `design-principles.md` section 11.
Layout vs the words: headline = the exact words from the plan, 2-6 words for feed; a CTA is a plain fact line
(`Tuesdays · 11am-9pm`, `link in bio`), never a button verb; prices as the user wrote them (`$2`); dates carry
the computed weekday; the terms appear once, small.

**(d) Render, look, iterate.**
```
python3 S/scripts/render.py --html build/html/p01-taco.html --format ig_feed_portrait --brand brand.json --out out/p01-taco-1080x1350.png
```
Read the PNG at full size. Then make a feed-size view and Read that too:
`python3 S/scripts/qa.py check` writes `build/qa/sheet.png` (the set at phone size); or
`python3 -c "from PIL import Image; im=Image.open('out/p01-taco-1080x1350.png'); im.resize((360, round(360*im.height/im.width))).save('build/feed-p01.png')"`.
Ask: one focal point? readable at 360px? whitespace? alignment? does it read as this brand? is it my
example with new words? Fix the HTML and re-render until the answer is yes. At least one real iteration per
post (render, look, change something specific, render again). A `SAFE ZONE BREACH` or `TEXT OVERFLOW`
failure means shorten the words or move the element; never loosen the check.

## 2. Imagery, in this order of preference

1. **The user's photos** (`in/`). Always first if they exist and show the right thing.
   ```
   python3 S/scripts/photo.py info in/*                       # size, sharpness, brightness, orientation
   python3 S/scripts/photo.py fit in/IMG_1.jpg --format 1080x1350 --focus auto --grade warm --out build/photos/p01.jpg
   python3 S/scripts/photo.py cutout in/mug.jpg --out build/photos/mug-cut.png   # product on transparent bg (rembg if installable, else plain-background key)
   ```
   Grade lightly (`--grade warm|neutral|cool|none`) and use the same grade on every photo in the set.
2. **A product render or mockup** when there's a physical product or an app/site and no photo.
   ```
   python3 S/scripts/mockup.py phone --screen build/screen.png --out build/mock/phone.png        # phone frame, transparent PNG
   python3 S/scripts/mockup.py scene --product build/photos/mug-cut.png --bg build/photos/table.jpg --format 1080x1350 --out build/mock/scene.jpg
   python3 S/scripts/mockup.py product3d --init build/product3d.html     # three.js template: edit PARTS to the product's silhouette
   python3 S/scripts/mockup.py product3d --html build/product3d.html --state lit --size 1080x1080 --out build/mock/product-lit.png
   ```
   One product, one drawing: the same render (or render function with a `state`) in every image.
3. **Free CC images** (Openverse + Wikimedia Commons, no key). Food and product people
   scroll past type and stop for a picture of the thing, so with no user photos a good CC
   photo of **the exact thing the words name** (tacos for a taco post, a croissant cross-section
   for a croissant post, sourdough for sourdough) is a legitimate **stand-in**: use it, and say
   in Assumptions and the review page which files carry stand-ins to swap for their own photos.
   Never a stock *person* as "our team/baker/staff", never a stock storefront as "our shop", and
   never claim in a caption that the photo is theirs ("our croissants, fresh this morning" over
   a stock croissant is fine only because the caption is about their croissants; don't write
   "photo from our kitchen").
   ```
   python3 S/scripts/assets.py search "street tacos plate" --orientation portrait --n 12
   # Read the contact sheet it prints (build/assets/<slug>-sheet.jpg). Pick by number only after looking.
   python3 S/scripts/assets.py get <slug>:<number> --out build/assets/
   ```
   Search like a stock site, not a sentence: 1-3 words naming the thing ("croissant",
   "sourdough bread", "street tacos", "layer cake"). Long queries ("sourdough bread sliced crumb")
   and `--orientation` return a handful of small images; leave orientation off (`photo.py fit` does the crop) and run 2-3 queries per subject before judging the supply.
   `get` records the licence and attribution in `out/credits.md`. Prefer CC0/public domain;
   a CC BY photo needs the credit line from `credits.md` at the end of the caption
   (`qa.py copy` errors if the creator's name appears in no caption).
   Reject anything blurry, watermarked, oddly lit, cluttered, obviously dated, or that
   shows the wrong thing. If nothing on the sheet is genuinely good, **don't use a photo**.
4. **Type-only design.** A strong statement/offer layout in brand colours beats a weak
   photo every time. Right for a price card, a list, a quote or a one-line statement.

**Mix, don't default.** Search for photos for every image whose words name a food, product,
place or object, and look at the sheets before deciding. A single deal post may be
type-only if the price is the hero, but its Story/clip should then show the food if a good
photo exists. **In a multi-post set (3+ posts) at least half the posts carry a picture**, and
never more than two type-only posts in a row; a week of text cards on one background reads as
one post seven times. If every search really comes back weak, use `photo.py`/`mockup.py`
ideas (ingredients, hands, a counter, the case) before giving up.

State any stand-in in Assumptions ("the taco photo is a CC stand-in; swap in your own").

## 3. Never

- **No fake buttons** in organic posts: no pills saying "Shop now"/"Order"/"Learn more", no
  arrows-in-circles, play icons, fake like/comment counts, fake notifications, fake
  browser or app chrome. Put the CTA in words ("Tuesdays · all day", "link in bio").
  A link card (1200x630) for a website may have a button-like label; nothing else.
- No placeholder text on images ("Your text here", "[address]", an unfilled `{{token}}`) unless the brief has no
  facts at all (one-liner asks): then mark it obviously and say so in Assumptions.
- No clip-art clichés (sombreros, chef hats, rockets, light bulbs, handshakes), no
  generic gradient blobs standing in for a product, no purple.
- No text on top of a busy part of a photo; give it a calm area, a solid bar or a scrim.

## 4. Render a set

Every post's render job goes into `build/plan.json` so the gate can check it; render in one go:

```json
[
  {"html": "build/html/p01-tacotuesday.html", "format": "ig_feed_portrait", "brand": "brand.json",
   "out": "out/p01-tacotuesday-1080x1350.png"},
  {"html": "build/html/p01-tacotuesday-story.html", "format": "ig_story", "brand": "brand.json",
   "out": "out/p01-tacotuesday-story-1080x1920.png"}
]
```

```
python3 S/scripts/render.py --batch build/plan.json
```

Use format **keys** from `formats.json` (`ig_feed_portrait`, `ig_story`, `tiktok_cover`, `pinterest_pin`,
`link_card` ...), not bare `WxH`: the key turns on the safe-zone check. Never use `--template`/`"template"`
jobs: `qa.py gate` rejects them.

## 5. Look at every image, now

**Read every PNG you rendered**, one by one, at full size, plus the set at feed size. For each, check against its
plan row and `design-principles.md`: words right, picture shows what the words say, nothing cut off, no lonely
word, price/date right, one focal point, readable at thumbnail size, does the set read as one campaign with
varied layouts. Fix and re-render anything off before step 5. Update the plan's alt text to what you see.

Tick box 4 only when every planned file exists in `out/`, `build/design-notes.md` records the examples you
studied for each post, and you have opened each image.
