# Step 0: Scope

Goal: decide what to make, for which platforms, on which real dates, before anything else.
Write the result into `out/brief.md` under `## Scope` and `## Assumptions`. Never ask.

## 1. Read the request like a busy owner wrote it

Pull out, in one list: business name, business type, city/area, the offer or news
(price, product, event), every date/time, platforms named, attachments (`in/`, pasted
text, URLs), and the *feeling* words ("look good", "festive", "get people to donate").
Anything not given is an assumption, not a question.

If there is an `in/` folder, list it. Photos: run
`python3 S/scripts/photo.py info in/*` and then `python3 S/scripts/photo.py sheet in/ --out build/in-sheet.jpg`
and **Read the sheet** so you know what the photos actually show. Text files: read them fully.

## 2. Pick the playbook

| If the business is... | Playbook |
|---|---|
| bakery, café, coffee cart, ice cream, juice bar | `playbooks/bakery-cafe.md` |
| restaurant, taqueria, food truck, bar, pizza | `playbooks/restaurant.md` |
| realtor, property manager, mortgage, rentals | `playbooks/realtor.md` |
| salon, barber, nails, spa, yoga, pilates, gym, trainer, dance | `playbooks/salon-studio-fitness.md` |
| Etsy/handmade, online shop, small product brand | `playbooks/etsy-ecommerce.md` |
| nonprofit, rescue, school, church, fundraiser | `playbooks/nonprofit.md` |
| coach, consultant, freelancer, agency, B2B, podcast | `playbooks/coach-freelancer-b2b.md` |
| a one-off event (workshop, market, concert, wedding, class) | `playbooks/events.md` (+ the business's own playbook) |
| a new product/app/feature/menu item launch | `playbooks/product-launch.md` (+ the business's own playbook) |
| nothing fits / unknown business | `playbooks/generic.md` |

Read the chosen playbook(s) now. Note its recommended style family and post mix.

## 3. Size the job (match the ask; do not inflate it)

| The ask sounds like | Make | Formats |
|---|---|---|
| "my X post", "make this look good", "a post about Y", one line | **1 hero post + its Story version + a short MP4 Story** | feed 1080x1350, story 1080x1920, story MP4 |
| "a few posts", "some posts", "posts for this" | 3 posts with different jobs + 1-2 Stories | 1080x1350, 1080x1920 |
| "a week of posts", "content for the week" | 5-7 posts on a real rhythm (see playbook), at least 1 carousel, 2+ Stories, 1 Reel | mix |
| event with a date / "fill it" / deadline | countdown: announce, reminder, scarcity/last call, day-of; Stories for each beat | 1080x1350, 1080x1920, MP4 |
| "launch", "campaign", "kit" | full kit: teaser, launch hero, carousel, Stories, Reel, link card, X/LinkedIn image | per playbook |
| fundraiser with goal + deadline | launch post, updatable progress post, story beats, matching-gift/last-days posts | 1080x1350, 1080x1920 |
| photos supplied ("here are my photos", gallery) | posts built FROM their photos; carousel where the photos tell a story | per platform |
| transcript/article supplied ("turn this into posts") | 3-5 best moments: quote cards, a carousel, a clip script with timestamps, a thread | 1080x1350, 1080x1920 |
| "my posts get no likes", "redo these" | specific diagnosis of THEIR posts, redone versions, one-line change notes | same sizes as theirs |

Platforms: use the ones named. If none are named, default by playbook (local businesses:
Instagram + Facebook; B2B/freelance: LinkedIn; Etsy/handmade: Instagram + Pinterest).
Add a format only when a platform in scope needs it. A 1080x1350 image serves both
Instagram and Facebook feeds; do not make a separate Facebook image unless the layout differs.

Hard cap for a single-post ask: **3 deliverable files** (feed PNG, Story PNG, Story MP4).

## 4. Dates: compute, never guess

Run `date` first. Then compute every date you will print, with its weekday:

```
python3 -c "import datetime as d;t=d.date.today();n=(1-t.weekday())%7;print(t+d.timedelta(n))"   # next Tuesday (0=Mon..6=Sun; 1=Tue). Use n or 7 if today is too late in the day
python3 -c "import datetime as d;x=d.date(2026,11,22);print(x.strftime('%A %B %-d, %Y'))"         # weekday for a given date
python3 -c "import datetime as d;x=d.date(2026,11,22);print([(x-d.timedelta(k)).strftime('%a %b %-d') for k in (14,7,3,1,0)])"  # countdown beats
```

A date the user gave without a year is the next occurrence of it. A recurring promo
("taco tuesday") is evergreen: the image says "Tuesdays" (no date) and the posting plan
names the next real Tuesday with its date.

## 5. Write it down

In `out/brief.md`:

```
## Scope
Business: Taqueria El Sol (restaurant) · Playbook: restaurant · Style family: bold_type
Ask, in their words: "make my taco tuesday post look good. $2 tacos all day."
Deliverables: p01 feed 1080x1350, p01 story 1080x1920, p01 story MP4 (8s)
Platforms: Instagram (feed + Story), Facebook (same image)
Key dates: next Tuesday = Tue Oct 20, 2026 (computed)

## Assumptions
- No address, hours or photos given: no address on the image; caption leaves [address] for them to fill. ...
```

Keep assumptions specific and few (3-8). Each one should be something the owner can
check in two seconds. Then tick box 0.
