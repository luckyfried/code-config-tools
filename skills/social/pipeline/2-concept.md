# Step 2: Concept

This is the step that wins or loses. A layout filled with the facts is a flyer. A post
with an idea is something people stop for, screenshot and send to a friend. Do it in
writing, in `out/brief.md`, before any render.

## 1. Write 3-5 genuinely different ideas

Different means a different **angle**, not the same idea in three colours. Draw from at
least three of these angle types:

| angle | the post is about... | e.g. taqueria, "$2 tacos all day" |
|---|---|---|
| The number | the price/offer as the hero, set huge | a giant "$2" that fills the frame; "all day" small underneath |
| The math | what the offer means in real life | "$10 = five tacos and change for the jukebox" |
| The ritual | the day/occasion as a habit people already have | "Tuesday has a plan now." |
| The insider | something only this business knows | the 3pm tortilla press, the salsa they won't share |
| The contrast | old way vs this way, before/after | "Monday lunch: sad desk salad. Tuesday lunch: four tacos." |
| The people | a regular, the cook, the owner, the customer moment | "Ask for Rosa's salsa verde." (only if a name was given) |
| The name | a play on the business name or place | El Sol: the sun rises on Tuesday; a sun made of the "$2" |
| The question | a choice the audience argues about | "Al pastor or carnitas? Wrong answers only." |

Each idea is three lines:

```
### C2: Tuesday math
Hook: "$10 = 5 tacos. Tuesday math."
Visual: the equation set huge in two brand colours, nothing else on the canvas (study: library offer examples; design: original)
Why/risk: shareable, instantly clear at feed size / risk: reads like a coupon if the type is weak
```

Rules for ideas:
- At least one idea must be **only possible for this business** (uses its name, place, product or a given detail).
- At least one must work with **no photography** (type-led), because stock food photos are often weak.
  That is a fallback, not a goal: for food and products, the strongest idea usually shows the thing.
- No clichés the playbook bans (sombreros, coffee-bean borders, "Just Listed!" starbursts, sad-dog eyes, rocket ships, light bulbs, handshake photos).
- If the product changes state (a lamp that lights, a progress bar that fills, dough that rises, a room before/after), that change can carry the whole set: give each image a state value and render it.

## 2. Score and pick

Score each idea 1-5 on five things and total it:

| criterion | question |
|---|---|
| Stop | at phone feed size (about 360px wide) would a stranger stop? |
| Ours | could only this business post it? |
| Fit | does it suit the playbook, the audience and the ask (small ask = simple idea)? |
| Make | can we make it look great with what we actually have (their photos / CC photos / type)? |
| Clear | is the offer or point readable in 2 seconds? |

Write the table, then `## Pick` with 2-4 sentences: which idea, why it beat the runner-up,
and what you'll borrow from the runner-up (often its line goes in the caption). A pick
with no rationale fails the gate.

## 3. Write the brief

```
## Pick
C1 "The number" + C3's line in the caption. Why: ...

## Idea
One sentence the whole set acts out.

## Hook
The line that leads the image and the first caption line.

## Key visual
What the eye hits first, what's second, what's third. Colours from brand.json.

## Subject treatment
How the product/subject appears: their photo (which file) / CC photo (search terms) /
3D render / phone mockup / type-only. Say why. If it's a stand-in, say so in Assumptions.

## Plan
| file | format | job / design idea | headline (exact words) | small text | image shows | source | alt text |
|---|---|---|---|---|---|---|---|
| p01-tacotuesday-1080x1350.png | ig_feed_portrait | offer: the price fills the frame | $2 TACOS | Every Tuesday · All day | big type, no food photo | type-only | "Poster reading $2 tacos, every Tuesday, all day, Taqueria El Sol" |
| p01-tacotuesday-story-1080x1920.png | ig_story | offer: same system, vertical | $2 TACOS | All day Tuesday | same system, text inside the safe band | type-only | ... |
| p01-tacotuesday-story-1080x1920.mp4 | 1080x1920 | motion from the two PNGs | ... | ... | type builds in 3 beats | motion.py | ... |
```

File names: `pNN-<slug>-<WxH>.png`. Every file for the same post starts with the same
`pNN-` (deliver.py groups by it). Carousels: `p03-<slug>-1-1080x1350.png`, `-2-`, `-3-`.

The **headline** and **image shows** columns are a contract: the critic will fail any
image whose picture does not match its words. Write "image shows" as what a person would
see ("three tacos on a blue plate, top-down"), not as intent ("appetizing food").

Tick box 2.
