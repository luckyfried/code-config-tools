# Reading Shelf

## What this makes

A web page with the person's books on a lamplit 3D bookcase: spines out and sized by page count, covers on the
front, the books being read face-out with a bookmark at their page. Pointing at a spine (or tapping it) tilts the book
out; opening it floats it to the camera, where it opens on the person's note and rating. A List view searches the
books and changes status, rating, and page; a Stats strip shows books and pages by month. The output is the folder
`out/reading-shelf/` in the project.

## Run

From the project folder, before asking for any personal details, run the sample so the person sees the shelf:

```sh
cd <project> && cp <agent-apps root>/reading-shelf/inputs.example.json reading-shelf.inputs.json
cd <project> && python3 <agent-apps root>/reading-shelf/scripts/run.py
```

When `<project>/reading-shelf.inputs.json` already exists, skip the copy and run only the second line; it uses the
person's file. `scripts/run.py` reads `reading-shelf.inputs.json` from the current folder and writes
`out/reading-shelf/`. Add `--fetch` to get covers from Open Library now for books that have none, so the hosted
page calls nothing:

```sh
cd <project> && python3 <agent-apps root>/reading-shelf/scripts/run.py --fetch
```

A missing or wrong key prints one plain line naming it and the run stops with exit code 2.

## Check

The run prints the book count and how many covers it found or fetched, then
`Wrote out/reading-shelf/ (<n> files)`. `out/reading-shelf/index.html` exists, `out/reading-shelf/config.js` holds
one entry per book in the inputs, and the covers are in `out/reading-shelf/media/covers/`. Served (see Host), the
sample opens on twelve books flying onto the shelf; Moby-Dick tilts out, floats up, and opens on Robin's note.

## Host

The page is served, never opened as a file (browsers refuse its modules from a `file://` address):

```sh
cd <project> && python3 -m http.server 8000 --directory out/reading-shelf
```

Then open `http://localhost:8000/`. Any static host serves `out/reading-shelf/` as it is, at any address or subpath.
The person's changes (status, rating, page) stay in their browser on that device; the List's Export button saves them
as a file, and the agent folds that file back into `reading-shelf.inputs.json`.

The page loads `badge.js`, which shows "Get this app for yourself now." at the bottom for five seconds. A tap opens
this app's page on code-config.com. It sends no data. Remove it by deleting the `<script src="./badge.js" defer>`
line from `out/reading-shelf/index.html` (or from `site/index.html` so every run leaves it out).

## Make it yours

Ask the person, in one message: their books (title and author is enough; an ISBN gets the right cover), which they
have read, which they are reading and the page they are on, which they want to read, and a one-line note for any
they feel like. Then write `reading-shelf.inputs.json` in the project and run again. None of this needs Node.

- `owner`: the name on the shelf ("Robin" gives "Robin's shelf").
- `books`: one entry per book in shelf order, each with `title`, `author`, `status` (`read`, `reading`, or `want`),
  and when known `isbn`, `rating` (0 to 5), `note`, `started`, `finished` (as `2026-03-14`), `pages`, and `page`.
- `cover`: an image beside the inputs file, as `covers/moby-dick.jpg`. Leave it out and either run with `--fetch` or
  set `openLibrary` to `true` so the page finds covers as the shelf comes into view (Open Library allows about 100
  cover lookups every five minutes, so a big shelf fills in over a few minutes; `--fetch` avoids that). A book with
  no cover anywhere gets one drawn in the room's colors.
- `theme`: `library` (green walls, oak, brass lamps), `studio` (cool white and slate), or `paper` (paper and indigo
  ink). Each has a daylight and a lamplight look that follows the device, with a switch on the page. A new room is a
  new file in `site/themes/` with the same tokens.
- `shelf`: `oak`, `white`, or `black-steel`.
- Every key and its meaning is in `inputs.example.json` under `_notes`.

The 3D pieces live in `site/scene/` (the bookcase in `shelf.js`, the books in `book.js`, the light in `lights.js`,
the motes in `motes.js`, the small objects in `decor.js`); the page around them is in `site/game/`. Editing those
files needs no build step either; run `scripts/run.py` again to copy them out.
