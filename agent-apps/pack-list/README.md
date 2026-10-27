# pack-list

## What this makes

A packing list built from the person's own kinds of trips: pick a template or compose several, and the items show up grouped, with a bag in the header that fills with liquid as things are packed, the percentage rolling beside it, and a weight bar against the bag's limit. Checks, added items, and the trip name stay in the browser it is opened in, so it works at the suitcase with no agent nearby.

## Run

Run this from the project folder before asking for anything personal, so the person sees the sample right away:

```sh
cd <project> && python3 <agent-apps root>/pack-list/scripts/run.py
```

It reads `pack-list.inputs.json` from the project folder. When the person has none yet, copy `inputs.example.json` from this app folder to `<project>/pack-list.inputs.json` first. The page is written to `out/pack-list/` in the project folder. A missing or wrong key is named in one line and the script exits with 2.

Then ask, in one message: "What kinds of trips do you take most? What always comes with you? Is there a bag weight limit I should track?" Put the answers in `pack-list.inputs.json` and run the same line again.

## Check

Serve the output (see Host) and open `http://localhost:8000/`. The bag fills as the trip's already-packed items check off one by one on the first visit. Check three more items: the bag rises and the count under the percentage reads one more each time, like `14/29`. Reload: the checks stay. With `limitKg` set, the weight bar shows the total of the checked items' weights and warms to amber near the limit. Settings has Export, Import, and "Unpack everything for the next trip", which empties the checks.

## Host

The page is served, never opened as a file:

```sh
cd <project> && python3 -m http.server 8000 --directory out/pack-list
```

and open `http://localhost:8000/`. Any static host takes the `out/pack-list/` folder as it is, at any path. Checks live in each browser's own storage under `pack-list:v1`; Export and Import in Settings move a list between devices.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens this app's page on code-config.com. It sends no data. To remove it, delete its script line from `out/pack-list/index.html` (or from `index.html` in this folder before a rebuild).

## Make it yours

Every key in `pack-list.inputs.json` changes the page with no Node, only a new run:

- `templates`: the trips, each `{ "id", "label", "groups": [{ "label", "items": [{ "name", "weight" }] }] }`. Weight is in kilograms and optional. Composing two trips merges groups by label, and an item already on the list is listed once.
- `always`: items that go on every list, as names or `{ "name", "weight" }`. They sit in the "Every trip" group.
- `limitKg`: the bag's weight limit. Leave it out to hide weights and the weight bar.
- `trip`: the trip the list opens on the first visit: `name`, the template ids in `templates`, and `packed`, items already in the bag.
- `theme`: `canvas` (bone paper, olive checks, a terracotta bag), `night-flight` (navy, mint checks, a bone bag), or `auto` to follow the device's light or dark setting.

A theme is one file of shadcn color variables in `src/themes/`; copy one, change the colors, and name it in `theme`. No Node is needed for that either.

A new field on an item, a new screen, or a new component is a change to `src/`: it needs Node. From this app folder run `npm ci && npm run build`, keep the new `dist/` and `package-lock.json`, and delete `node_modules/` before saving the folder.
