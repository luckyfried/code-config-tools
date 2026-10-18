# Playbook: Realtor
Realtors, listing agents, brokerages, property managers, rentals, mortgage brokers.

## What actually works
- The listing's best real photo, one room or the front, cropped tight. Kitchen, the view, the light in the main room.
- The facts in one line, exactly as given: "$649,000 · 3 bd · 2 ba · 1,480 sq ft".
- A named series people recognise: Just listed, Open house, Under contract, Just sold. Same design each time, so the feed reads as a track record.
- Distances to named places, given by the agent or measured from a given address: "0.4 mi to Lincoln Elementary", "6 min walk to the Farmers Market".
- The carousel walk-through: front, kitchen, main room, primary bedroom, yard. One room per slide.
- The agent's face on market updates and "Just sold" posts, if they supplied a headshot.

## Post mix
A week is 5 posts. One listing ask is one hero plus its Story, or a carousel if photos were given.

| Post type | Share | Study (library examples, inspiration only) | Image shows |
|---|---|---|---|
| Just listed | 1 | editorial/hero | the listing's own best photo, price and beds/baths in small text |
| Listing walk-through | 1 | editorial/carousel-cover + inner + cta | one real room per slide, a short line each |
| Open house | 1 | editorial/event | listing photo, date with computed weekday, time, street address |
| Under contract / Just sold | 1 | editorial/statement or hero | the listing photo with a plain "Just sold" headline |
| Market note or tip list | 1 | editorial/list | type-only: 4 local facts the agent gave, or 4 buyer tips |
| Client quote | 0-1 | editorial/quote | a review the agent supplied, first name and initial |

## Rhythm
- Just listed: the day it goes live on MLS, 8:00am or 6:00pm local.
- Open house: announce Thu 6pm for a weekend open house, Story Sat/Sun 9am, Story at start time.
- Just sold / under contract: within a day, any weekday 12pm.
- Market notes: Tue or Wed 7:30am. LinkedIn copy of it at 8am if they use LinkedIn.
- Stories: open house countdown sticker, "Swipe for the kitchen", polls on two finishes.
- Series names: "Just listed", "Open house", "Under contract", "Just sold". Use the agent's own label if they have one.

## Hooks that work
- "Just listed: 3 bd, 2 ba, 1,480 sq ft on Alder Street. $649,000."
- "Open house Saturday 1-4. 412 Alder Street."
- "0.4 miles to Lincoln Elementary. 6 minutes to the train."
- "South-facing kitchen, and the light to prove it."
- "Under contract in 9 days."
- "Just sold. Thank you to the Ramirez family for trusting us with it." (only with the client's OK, stated as an assumption)
- "Rates moved again this week. Here's what that did to a $500,000 payment."
- "Four things to check before your first open house this weekend."

## Style family
- Default `editorial`: photo-led, lots of white, serif headline. Pick `quiet_luxury` for high-end listings. Pick `clean_modern` for mortgage brokers, rate updates and property managers.
- Palette from the brokerage brand if given, else warm white, charcoal ink and one accent pulled from the photo (brick, oak, sage, slate blue). Never purple, never navy+teal+coral.
- Imagery: only the actual listing photos. No listing photos given: type-only statement or event designs, or a CC photo of the town or a named landmark, labelled as such. Never a stock house, kitchen or interior presented as the listing.

## Pitfalls
- A stock home shown as if it were the listing. This is misrepresentation, not a style choice.
- Inventing square footage, lot size, year built, HOA, school ratings or "walk score". Use only what was given.
- Rounding or reformatting the price ("$649K" when they wrote "$649,000" is fine only if space forces it; never change the number).
- "Just Listed!" starbursts, sold-sign clip art, house icons, keys-in-hand stock photos, handshakes.
- "Won't last", "rare opportunity", "dream home", "nestled", "boasts", "stunning".
- Missing brokerage name or license info in the caption where the state requires it.
- Putting an open house date on the image without a computed weekday.

## Fair Housing (US)
Describe the property and its distances. Never describe who the home suits.
- Never: "perfect for families", "ideal for young professionals", "great for empty nesters", "singles", "bachelor pad", "mother-in-law suite" for people, "no kids", "adults only", "Christian home", "walking distance to church" (say "0.3 mi to St. Mark's" instead), "safe neighborhood", "exclusive", "private community", "integrated", "able-bodied", "ideal for", "suits".
- Say "primary bedroom", never "master bedroom". Say "in-law unit" only as a room description.
- Distances: name the place and the number. "0.4 mi to Lincoln Elementary", never "great schools" or "family-friendly area".
- Accessibility features are fine as features: "step-free entry", "36-inch doorways", "roll-in shower".
- Rentals: never state preferences on tenants (students, couples, no Section 8). State the rent, deposit, terms as given.
- Run every caption against this list before `qa.py copy`. If a phrase is borderline, rewrite it as a property fact.
- Required in each listing caption: "[Brokerage name]" and, where given, license number and the Equal Housing Opportunity line. Unknown: leave `[Brokerage name] · [DRE/license #]` as a placeholder and list it in Assumptions.

## Defaults when the user gave nothing
- Platforms: Instagram feed + Story, Facebook same image. Add LinkedIn (`li_post` 1200x1200) for market notes.
- Sizes: `ig_feed_portrait` 1080x1350, `ig_story` 1080x1920, story MP4; carousel as `ig_carousel`.
- "A post": 1 feed + 1 Story + 1 Story MP4. "A week": 5 posts, 1 carousel, 2+ Stories.
- Assumptions to state: brokerage and license are placeholders; facts used exactly as given, none added; photos are the listing's own (or none were given, so type-only); MLS status as stated; open house times as given.
