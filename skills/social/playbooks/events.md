# Playbook: Events
One-off events: workshops, markets, pop-ups, concerts, open mics, classes, fundraising galas, grand openings, weddings. Read alongside the business's own playbook.

## What actually works
- Date, time and place readable in two seconds on every image. People screenshot event posts as their reminder.
- A countdown people can feel: "3 days", "Tomorrow", "Doors at 7 tonight". Each beat is a different post, not the same post again.
- The one thing that makes it worth going: the headliner, the free tasting, the 40 vendors, the limited seats. Lead with it.
- Scarcity only when true and given: "18 seats", "Last 6 tickets".
- The recap: their photos from the event within 24 hours, which sells the next one.

## Countdown cadence
Compute every beat from the event date. Never type a weekday.
```
python3 -c "import datetime as d;x=d.date(2026,11,14);print(x.strftime('%A %B %-d, %Y'));print([(x-d.timedelta(k)).strftime('%a %b %-d') for k in (14,7,3,1,0)]);print('recap',(x+d.timedelta(1)).strftime('%a %b %-d'))"
```

| Beat | When | Study (library examples, inspiration only) | Image shows |
|---|---|---|---|
| Announce | -14 to -21 days | family/event | the hook, full date with weekday, time, place |
| Reason to go | -7 | family/hero or carousel | the headliner, the menu, the vendors, a past photo |
| Reminder | -3 | family/event | "This Saturday", date, time, place |
| Last call | -1 | family/statement or offer | "Tomorrow" + seats/tickets left if given |
| Day-of | 0, morning | family/story (Story only) | "Today", doors time, place |
| Thank-you recap | +1 | family/carousel-cover + inner | their event photos, one line each |

Fewer than 14 days out: keep announce, -3, -1, day-of, recap. Under 3 days: announce, day-of, recap.

## Rhythm
- Announce and reminders: 6:00-7:00pm local on weekdays (when people check their weekend).
- Day-of: Story at 9:00am and one an hour before doors.
- Ticketed: link sticker on every Story; the countdown sticker on the announce Story.
- Recurring events (monthly market): same design each month, only the date changes.

## Hooks that work
- "Saturday, November 14. 10 to 3. Forty makers, one parking lot."
- "18 seats. Sourdough basics, Sunday 9am."
- "This Saturday. Doors at 7."
- "Tomorrow. Bring cash for the raffle."
- "Today, 10 to 3, at the Grange Hall."
- "Thank you to the 300 of you who came out."
- "Free to get in. Tickets for the tasting are $15."
- "RSVP at the link in bio. We'll save you a chair."

## Style family
- Use the business's own family. No business family: `bold_type` for concerts, markets, sales and openings; `editorial` for workshops, talks and galleries; `quiet_luxury` for weddings and galas; `playful_pop` for kids and family days.
- Palette from the venue, the season or the poster the organiser already has. Never purple, never navy+teal+coral.
- Imagery: the venue, the performer or past events (their photos). A CC stand-in may show the venue type or a named public place. Type-only is the strongest default for announce and last-call beats.

## Pitfalls
- Any image missing the date, time or place. All three, on every image, every beat.
- A weekday typed from memory. Every "Saturday, November 14" comes from the command above.
- "Buy tickets" or "RSVP" pills on the image. Write "Tickets at the link in bio" or "RSVP: [link]".
- The same graphic posted at every beat. Change the headline and, ideally, the layout per beat.
- Inventing a lineup, vendor count, ticket price, "sold out last year" or "limited seats".
- Address errors: use the venue exactly as given, or [venue address] as a placeholder.
- Time zone and AM/PM missing for online events. Write "7pm ET".
- Paid ticket terms repeated in every caption. Full terms in announce and last call only.

## Defaults when the user gave nothing
- Platforms: Instagram feed + Story, Facebook same image (and a Facebook Event is worth suggesting in the caption notes). LinkedIn `li_post` for professional events.
- Sizes: `ig_feed_portrait` 1080x1350, `ig_story` 1080x1920, story MP4; `link_card` 1200x630 for a ticket page; `fb_cover` 1640x924 if they want the page header.
- "A post" for an event: announce feed + Story + MP4. "Promote my event": the full countdown table.
- Assumptions to state: weekday computed; venue/address as given or [placeholder]; ticket or RSVP link is [link in bio]; times in local time; recap photos to come from them.
