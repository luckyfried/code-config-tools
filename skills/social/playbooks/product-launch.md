# Playbook: Product launch
A new product, app, feature, collection, service or menu item going live. Read alongside the business's own playbook.

## What actually works
- One product, drawn the same way in every image: the same photo, cutout or render, so the set reads as one launch.
- A teaser that shows a real part of the thing (a corner, a colour, the box, the silhouette) with the launch date.
- The reveal states what it is and what it costs in one line: "The Ridge Pack. 22 litres. $148."
- "How it works" in 3-5 steps, each with a picture of the step. Apps: real screens in a phone mockup.
- Social proof only if it exists: beta users' words they gave you, waitlist count they gave you.
- A last call with a real deadline: launch price ends Friday at midnight PT.

## Launch sequence
Compute every date from launch day.
```
python3 -c "import datetime as d;x=d.date(2026,11,10);print([(x+d.timedelta(k)).strftime('%a %b %-d') for k in (-5,-2,0,1,3,6)])"
```

| Beat | When | Study (library examples, inspiration only) | Image shows |
|---|---|---|---|
| Teaser | -5 and -2 | family/statement or hero | a crop or silhouette of the real product + the date |
| Reveal (launch hero) | day 0, morning | family/hero | the full product, name, price |
| How it works | day 0 or +1 | family/carousel-cover + inner + cta | one step per slide, same render each time |
| Social proof | +3 | family/quote | a real quote they supplied; else a "first orders" photo or skip |
| Detail / use case | +3 to +5 | family/hero or list | the product in use; 4 specs as a list |
| Last call | final day | family/offer | price, deadline with weekday and time zone |

## Rhythm
- Launch day: feed at 8:00am local (consumer) or 8:30am (B2B/LinkedIn), Stories at 9am, 12pm, 6pm.
- Teasers in the evening, 6:00-7:00pm. Stories carry the countdown sticker from the first teaser.
- Apps and SaaS: LinkedIn + X on launch morning; link card for the landing page.
- Restaurant menu item: the reveal goes out the morning it is first served.

## Subject treatment
1. Their product photo: `photo.py fit`, or `photo.py cutout` then `mockup.py scene` for context shots.
2. No photo, physical product: `mockup.py product3d --init`, edit PARTS to the real silhouette, render one `state` per beat (boxed, open, lit). Say it's a render in Assumptions.
3. App or site: their screenshots in `mockup.py phone`. No screenshots: type-only. Never invent a UI.
4. Reuse the same file or render function in every image. A different-looking product in post 3 breaks the launch.

## Hooks that work
- "Tuesday, November 10. You'll see the rest then."
- "The Ridge Pack. 22 litres, one zip, $148."
- "It took 14 prototypes to get the strap right."
- "Three steps: scan the receipt, pick the category, done."
- "Launch price is $39 until Friday at midnight PT."
- "Our first 40 orders shipped this morning."
- "New on the menu Thursday: green chile mac."
- "Last day at $39."

## Style family
- Default `clean_modern` for products, apps and B2B. Use the business's own family for menu items and handmade (`bold_type`, `warm_craft`). `quiet_luxury` for premium goods and fragrance.
- Palette from the product and its packaging; the background stays quiet so the product colour leads. Never purple, never the blue-to-purple "AI app" gradient, never navy+teal+coral.
- Imagery: the real product or its faithful render. A CC photo may be a backdrop (desk, trail, kitchen). Type-only for teasers works well.

## Pitfalls
- Fake reviews, star ratings, "loved by 10,000", press logos or waitlist numbers not given.
- A different product drawing in different posts, or a generic gradient blob standing in for the product.
- Rockets, confetti cannons, "launching soon" countdown clocks, fake notification badges.
- "Shop now" / "Download" pills or app-store badges drawn on organic images. Words only ("link in bio"). A link card may carry a label.
- "Introducing", "X, reimagined", "Say goodbye to", "game-changer", "We're so excited to announce".
- Inventing specs, price, launch date or materials. Missing ones are [placeholders].
- Terms in every caption. Full price/deadline terms in the reveal and last call only.

## Defaults when the user gave nothing
- Platforms: the business's playbook platforms; apps/B2B add LinkedIn + X.
- Sizes: `ig_feed_portrait` 1080x1350, `ig_story` 1080x1920, story MP4, `link_card` 1200x630; `li_post` 1200x1200 and `x_post` 1600x900 when in scope.
- "A post about my new X": reveal feed + Story + MP4. "Launch" or "campaign": the full sequence above.
- Assumptions to state: launch date and price as given or [placeholder]; product image is their photo / a render / a mockup; no reviews used because none given; time zone assumed local.
