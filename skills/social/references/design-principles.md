# Design principles: what makes a post look like a designer made it

The 66 library examples all obey these. Your design must too; the critic checks each one. They are
rules you can measure, not tastes. Each has a good and a bad. (Sizes are for a 1080x1350 canvas; scale for others.)

## 1. One focal point
One element is 3-6x bigger or heavier than anything else: the price, one phrase, the photo. Everything else supports it.
- Good: "$2" fills 80% of the width; "tacos, every Tuesday, all day" is 1/6 its size.
- Bad: headline, price, badge and photo all at similar weight, each shouting.
- Test: squint, or view at 360px wide. If you cannot say what you saw first, there is no focal point.

## 2. Type: at most 2 typefaces, a real scale
- Two families max (display + body), and a **ratio of at least 2.5:1** between the headline and the body/fact text (180px / 44px, not 80px / 60px). One weight jump is not hierarchy.
- Headline 110-260px for feed, 2-6 words, 2-4 lines; support text 32-48px; micro labels 24-30px uppercase with letter-spacing .08-.16em. Nothing under 24px.
- Line-height .88-1.0 for display type, 1.25-1.4 for body. Display letter-spacing -.01 to -.03em, labels positive.
- No orphan word on its own line (unless it is the whole headline); no line ends on a/the/with/at/for.
- Good: Fraunces 200px headline + Work Sans 36px fact line. Bad: three display fonts, bold-italic-outline-shadow on one headline.

## 3. Whitespace
- Outer margin at least 6.5% of width (70px at 1080), the same on left and right. Text never touches an edge (the renderer enforces 30px; design for 70).
- Empty space is at least 25% of the canvas on a text post. If the layout feels full, remove an element, do not shrink the type.
- Gap between groups at least 2x the gap inside a group (headline to fact line: 32px; between blocks: 80px+).

## 4. Colour discipline
- At most 4 colours: bg, fg, one accent, one secondary. **One accent**, used for the single thing that matters (the number, the date, one word). If the accent is everywhere it is nothing.
- Flat fills, or a real photo. Gradients only as a subtle scrim to hold text on a photo. No gradient blobs, no glows.
- `fg` on `bg` at 7:1; the accent at 3:1 on `bg` for large text. No purple, ever.
- Good: cream page, rust "$2", ink text. Bad: red, yellow, teal and orange each at equal weight.

## 5. Alignment and grid
- Pick **one left edge** (or one centre axis) and hang everything on it. Mixed alignments need a reason (a deliberate flush-right price).
- Use 2-3 spacing values for the whole set (e.g. 72 / 36 / 18) instead of a new gap every time.
- Rules and numbers align to the same baseline grid; photos align to margins or bleed off the edge. Nothing floats at 3px off.

## 6. Photos: crop and focal point
- Crop to the subject, tight: the food fills the frame; a face is never cut at the eyes. Put the subject on a third, not dead centre by default.
- Either full-bleed, or in a clean block with a hard edge; never a small floating photo with a drop shadow.
- Text over a photo only on a calm area, with a scrim or a solid bar behind it. Never on a busy region.
- One grade for the whole set (same warmth, contrast). Use `photo.py fit --focus` / `--grade`.
- Good: croissant cross-section cropped to the lamination. Bad: a whole stock bakery scene with text across the shelves.

## 7. Legibility at 360px feed width
View the render at 360px wide: headline readable, fact line readable or clearly secondary, no tiny grey text carrying a price or a date. Headline x-height at 1080 should be at least 70px, body at least 32px.

## 8. Consistency across a set (one design system)
Same type pair, same palette roles, same margin and grid, one recurring motif (a rule style, a corner mark, a number treatment, a crop shape). Layouts vary by job; the system does not.

## 9. No AI tells (each one is a FIX)
- Gradient blobs, glows, glass cards, neon on dark, mesh gradients.
- Everything centred: centre-aligned headline, centre-aligned paragraph, centre-aligned CTA (a quiet-luxury frame can centre on purpose; a promo cannot).
- Emoji soup, emoji as bullets, sparkles; clip-art (sombreros, chef hats, rockets, light bulbs, handshakes).
- Fake buttons, pills with arrows, play icons, like counts, fake UI chrome.
- Generic stock person as "our team", stock storefront as "our shop".
- Decorative frames, borders and drop shadows on everything; every element in a rounded card.
- Headline plus subhead plus three bullets plus button plus badge on one image.
- Purple, or a default Tailwind palette.

## 10. What separates a designer's post from a generator's
| Generator | Designer |
|---|---|
| Fills a layout with words | Starts from the one idea and sizes everything by its importance |
| Same structure on every post | Layout fits the job (price = type fills frame; story = photo and a line; list = rhythm) |
| Everything medium-sized | One huge thing, the rest small |
| Decoration to fill space | Space left empty on purpose |
| Photo dropped in a box | Photo cropped and placed so it works with the type (type reads over its calm area, or the photo bleeds off) |
| Hedges with 4 colours | One accent, used once or twice |
| Looks like the other 1000 posts for that business type | Has one choice only this brand would make (its name, its place, its product) |

## 11. Stories and tall formats (9:16)
- The platform UI covers the top ~250px and bottom ~320px. Keep **words** out of them, but do not leave them blank: bleed the photo or the colour field through them so the canvas is one composition.
- Focal element between 35% and 65% of the height. Text block no taller than the middle band; it reads best as one group, not scattered.
- A flat empty slab (cream or yellow) under or over the text is the mark of a feed post stretched to 9:16. Re-compose: full-bleed photo with a small type block, or a type/number that fills the middle, or a photo that bleeds off one edge.
- A decorative shape (a circle, a blob) needs a job (it holds the number, it is the brand's sun). Cropped awkwardly against a photo edge it reads as a mistake.

## Checklist before you call a post done
1. One focal point, 3x or more bigger than the rest? 2. At most 2 typefaces, headline/body ratio 2.5:1 or more? 3. Margins at least 70px, 25% empty? 4. One accent, at most 4 colours, no purple? 5. One alignment axis? 6. Photo cropped tight with a chosen focal point, text on calm area? 7. Reads at 360px wide? 8. None of the AI tells? (Stories: no blank bands, focal at mid-height.) 9. Is it the library's layout with new words? (If yes, redesign: change the structure and the proportions, not just the colours.) 10. Would a designer sign it?
