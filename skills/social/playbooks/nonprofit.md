# Playbook: Nonprofit
Nonprofits, animal rescues, food banks, schools and PTAs, churches, community groups, fundraisers.

## What actually works
- One clear ask per post: donate, volunteer Saturday, adopt Biscuit, bring canned goods. Never three at once.
- A number the org gave, made concrete: "$25 feeds a family of four for a week" (only if they said it).
- One named animal, person or project, with permission: "Biscuit, 4, likes car rides." A single story beats a crowd.
- Progress the audience can watch: "$3,240 of $10,000", updated each post. The bar filling is the series.
- Thank-you posts that name volunteers and donors (with permission) and show the thing that happened.
- Giving-day countdowns with a matching gift, if one exists: "Every dollar matched until midnight."

## Post mix
A week is 5 posts. A campaign with a goal and deadline follows the countdown below.

| Post type | Share | Study (library examples, inspiration only) | Image shows |
|---|---|---|---|
| The ask (donate / adopt / sign up) | 1-2 | warm_craft/hero | their photo of the animal, place or project |
| Progress / impact number | 1 | warm_craft/offer | type-only: raised vs goal, or the given number large |
| Volunteer call | 1 | warm_craft/event | date, time, place, what to bring |
| Story of one | 1 | warm_craft/carousel-cover + inner + cta | 3-5 slides: before, the help, now, the ask |
| Thank-you / recap | 1 | warm_craft/quote or hero | their photo of volunteers or the result, names if given |

## Giving day countdown
Giving Tuesday is the Tuesday after US Thanksgiving (4th Thursday of November). Compute it:
```
python3 -c "import datetime as d;y=2026;n=d.date(y,11,1);t=n+d.timedelta((3-n.weekday())%7+21);g=t+d.timedelta(5);print(g.strftime('%A %B %-d, %Y'));print([(g-d.timedelta(k)).strftime('%a %b %-d') for k in (14,7,1,0)])"
```
Beats: -14 announce the goal and why; -7 the story of one; -1 "tomorrow" + match news; day-of 8am launch, 12pm progress, 6pm "last 6 hours", 9pm final push; +1 thank-you with the total.

## Rhythm
- Feed: Tue to Thu 12:00pm or 7:00pm local. Sunday 4pm for church and school audiences.
- Progress updates: same time each day of a campaign, so people look for them.
- Volunteer calls: 10 days and 2 days before the shift, Story the morning of.
- Stories: progress bar, donation link sticker, countdown sticker, a quick "thank you, Sam" reshare.
- Series ideas: "Adoptable of the week", "Monday numbers", "Volunteer spotlight".

## Hooks that work
- "Biscuit has been waiting 112 days. He's 4 and loves car rides."
- "$3,240 raised. $6,760 to go by Friday."
- "Every dollar is matched until midnight, up to $5,000."
- "We need 12 people Saturday 8-11 to sort 4,000 pounds of food."
- "Thank you. 186 of you gave $14,200 yesterday."
- "$25 stocks one pantry shelf for a week."
- "Bring a can, take a coffee. Saturday at the library steps."
- "Giving Tuesday is December 1. Here's what $10,000 does this winter."

## Style family
- Default `warm_craft`. Pick `editorial` for arts, museums, schools with strong photography. Pick `bold_type` for urgent campaigns and giving days.
- Palette from the org's logo and its real world: shelter kennel red, pantry kraft brown, school colours, forest green for a trail group. Never purple, even for awareness causes that use it: use the cause's ribbon only as a small mark if the org asks, never as the palette.
- Imagery: the org's own photos, used with dignity. A CC stand-in may show a place, an object (a full pantry shelf, a leash on a hook) or hands at work, labelled as illustrative. Type-only for progress and numbers.

## Pitfalls
- Inventing impact stats, people served, "% goes to programs" or dollar-per-meal figures. Only numbers they gave.
- Poverty imagery: sad faces, dirty hands, crying children, dogs behind bars shot for pity. Show people and animals as capable and named.
- A stock photo of a child or animal presented as someone the org helped.
- Two asks in one post ("donate, share and volunteer"). Pick one.
- Guilt copy: "Can you really scroll past?", "Every second you wait...". Say what the money does.
- A "Donate" button drawn on the image. Use "link in bio" or "give at [url]".
- A goal or deadline with no computed weekday; a progress number that was not given (use [amount raised]).

## Defaults when the user gave nothing
- Platforms: Instagram feed + Story, Facebook same image (Facebook matters most for donors 45+).
- Sizes: `ig_feed_portrait` 1080x1350, `ig_story` 1080x1920, story MP4; `li_post` only for corporate-match asks.
- "A post": 1 feed + 1 Story + 1 Story MP4. "A week": 5 posts. Fundraiser with deadline: the countdown above.
- Assumptions to state: donation link is [link in bio]; no stats given so none used; photos are theirs or type-only; names used only with permission; Giving Tuesday date computed.
