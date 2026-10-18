# Playbook: Etsy and e-commerce
Etsy and handmade shops, small online stores, DTC product brands, print-on-demand, makers at markets.

## What actually works
- The real product photo as the hero, nothing else competing. Detail crops: the glaze pooling, the stitch, the grain.
- Process and maker shots: hands at the wheel, the cutting mat, the stack of orders being packed. People buy the person.
- The product in use, in a plausible scene: the mug on a desk, the earrings on an ear. Built from their cutout if needed.
- Pinterest pins (1000x1500) with a keyword title. Pins keep sending traffic for months; Instagram posts do not.
- Hard dates with computed weekdays: "Order by Mon Dec 14 for delivery before Dec 25", "Restock Friday 10am".
- Small-batch facts the owner gave: "12 made this round", "back in stock: 3 left".

## Post mix
A week is 6 posts. A single "make my post" ask is one hero plus its Story.

| Post type | Share | Study (library examples, inspiration only) | Image shows |
|---|---|---|---|
| Product hero | 2 | warm_craft/hero | their product photo, tight crop, or cutout on a plain ground |
| Product in a scene | 1 | warm_craft/hero | `mockup.py scene` of their cutout on a table/desk/shelf photo |
| Process / maker | 1 | warm_craft/carousel-cover + inner + cta | 3-5 steps from raw material to packed order |
| Restock / sale / shipping cutoff | 1 | warm_craft/offer or event | type-only date and terms, or offer over a product crop |
| Pinterest pin | 1-2 | warm_craft/hero or list (pinterest_pin) | product photo with a keyword headline; "4 ways to style" lists |
| Review | 0-1 | warm_craft/quote | a real review the owner pasted, buyer first name |

## Rhythm
- Instagram: Tue, Thu, Sun 7:00-8:00pm local (evening browsing).
- Pinterest: 1-2 pins a day if they want, any time; seasonal pins 45-60 days before the holiday.
- Restock or drop: announce 2 days before (Story countdown sticker), feed post at drop time, Story "half gone" when true.
- Holiday shipping: post the cutoff at -14, -7 and -2 days before the order-by date.
- Stories: packing orders, polls between two colourways, "what's on the bench today".
- Series ideas: "Bench notes" (process), "Restock Friday", "Made this week".

## Dates for shipping cutoffs
Never guess a carrier deadline. Use the shop's processing + shipping days if given; otherwise write [order-by date] and state it.
```
python3 -c "import datetime as d;x=d.date(2026,12,25);p,s=3,5;o=x-d.timedelta(p+s);print('order by',o.strftime('%A %B %-d'))"
```

## Hooks that work
- "Twelve mugs this round. Glaze is called Lake Ice."
- "Order by Monday, December 14 to have it by the 25th."
- "Restock Friday at 10am. Last batch went in a day."
- "Every pair starts as a sheet of brass."
- "Three left in the moss colourway."
- "Wheel to box in five photos."
- "Fits a 13-inch laptop and one very good sandwich."
- Pinterest title: "Handmade stoneware mug, speckled blue glaze, 12 oz"

## Style family
- Default `warm_craft` for handmade. Pick `clean_modern` for product brands with studio photos, tech accessories, skincare with a clean label. Pick `quiet_luxury` for fine jewellery and premium goods.
- Palette from the product and its photos: the glaze, the fabric, the packaging, the logo. Neutral ground (oat, stone, warm white) so the product colour carries. Never purple, even if a product is purple: let the photo show it and keep the palette neutral.
- Imagery: their product photo, always. No clean photo: `photo.py cutout` it, then `mockup.py scene` onto a CC table or shelf. A CC photo may be a surface or a room, never a substitute product. If no product photo exists at all, type-only and say so.

## Pitfalls
- A stock or AI product shown as theirs. The buyer receives the real thing.
- Fake reviews, star ratings, "bestseller" badges, "As seen in" logos, "1,000+ sold" not given.
- "Shop now" buttons, Etsy UI chrome or a fake price tag sticker on the image. Say "link in bio".
- Inventing materials ("sterling silver", "organic cotton"), sizes or shipping times.
- Countdown dates without computed weekdays, or a cutoff the shop never stated.
- Pins with tiny text or the headline in the bottom 180px (save button covers it).
- Seven product heroes in a row for "a week". Mix process, scene, offer and pin.

## Defaults when the user gave nothing
- Platforms: Instagram feed + Story, Pinterest. Facebook same image if mentioned.
- Sizes: `ig_feed_portrait` 1080x1350, `ig_story` 1080x1920, `pinterest_pin` 1000x1500, story MP4.
- "A post": 1 feed + 1 Story + 1 Story MP4 (add 1 pin only if Pinterest was named). "A week": 6 posts incl. 1 carousel, 2 pins, 2+ Stories, 1 Reel.
- Assumptions to state: shop link is [link in bio]; prices and materials as given; scene is a mockup of their cutout; shipping cutoff is [placeholder] until they confirm processing time.
