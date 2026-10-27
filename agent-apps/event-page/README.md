# Event Page

## What this makes

The page you send to every guest of a wedding, birthday, party, or reunion. The names arrive in large type while scattered digits fly in and settle into the date, a wind layer that fits the event drifts behind them (petals for a wedding, confetti for a birthday, embers for a party, lanterns for a reunion), and flip tiles count down to the start. The opening holds while you scroll, then the story's photos open with a wipe and drift as they pass, the schedule's line draws itself and lights each stop, and the map tilts in as a pin drops onto the venue and the route glows. Below that: places to stay, the registry, an Add to calendar file, and a reply form whose buttons open a filled text or email to the hosts. On a first visit the page glides once through the story, the schedule, and the map, and any touch, click, or key hands it back. On phones a Details sheet holds the schedule and the places to stay. Each of the four themes has a light and a dark look that follows the guest's setting, and the page is a folder of plain files that any static host serves.

## Run

Put `event-page.inputs.json` and the photos folder in the project folder, then:

```
cd <project> && python3 <agent-apps root>/event-page/scripts/run.py
```

It writes `out/event-page/`. Running it again replaces that folder with the same files. If a key is missing or wrong, it prints one plain line for each problem and writes nothing.

## Check

- `out/event-page/index.html` has every name inside `<h1>`, the date, and the address.
- `out/event-page/event.ics` exists and its `DTSTART` is the event's date.
- The Send by text link starts with `sms:` and the phone number, and the Send by email link starts with `mailto:` and the email.
- Every photo from the photos folder is in `out/event-page/media/`.

## Host

```
cd <project> && python3 -m http.server 8000 --directory out/event-page
```

Then open http://localhost:8000/. To put it online, upload the `out/event-page/` folder to any static host and send guests its address.

## Make it yours

Ask the person for all of this in one message:

- `names`: one to four names, shown big at the top, such as `["Iris", "Theo"]`.
- `kind`: wedding, birthday, party, or reunion. It picks the wind layer and the words.
- `line` (optional): the words under the names, such as "are getting married". The kind picks them otherwise.
- `date`: the start, such as `2027-06-12T16:30`, or `2027-06-12` for a day with no start time. The countdown and the calendar file use it.
- `place`: the venue's `name` and street `address`. With `lat` and `lon` the page draws a map with the route; without them it shows an address card with links to Apple Maps, Google Maps, and the phone's maps app.
- `schedule` (optional): the stops of the day in order, each a `time` and a `what`.
- `story` (optional): a few short paragraphs; a blank line starts a new one.
- `photos` (optional): a folder of pictures beside the inputs file (.jpg, .png, .webp, .avif, or .gif). File names become the captions, with any leading numbers dropped, so `01-the-orchard-at-dusk.jpg` reads "The orchard at dusk" and comes first.
- `stay` (optional): places for guests to stay, each with a `name` and an optional `url` and `note`.
- `registryUrl` (optional): the registry or gift list address.
- `rsvp`: a `phone`, an `email`, or both, for replies, and an optional `deadline` such as `2027-05-01`.
- `theme` (optional): ivory (bone paper and claret), midnight (indigo linen, navy and old gold at night), garden (sage and leaf green), or neon (bright pink, aqua, and gold). The default is ivory.

`inputs.example.json` in this folder shows every key filled in, and `sample/photos/` holds five photos to start from.
