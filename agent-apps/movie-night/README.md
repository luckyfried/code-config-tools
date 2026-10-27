# Movie Night

## What this makes

A movie night page, `out/movie-night/`, that opens in any browser. The household's watch list stands as a wall of posters in a small 3D room: a polished floor with soft reflections, a rim of light on each frame, and the neighbors of the front poster blurred back. Swipe, drag, scroll, or use the arrow keys and the wall glides with inertia; the poster in front squares up with a little spring. The film with the most hearts (or tonight's film, once there is one) stands under a spotlight that drops from above with dust drifting in it, strikes with a flicker, and dims the rest of the room. Its title opens up from thin to heavy as the light lands.

Tonight is a brass wheel with a slice for every film on the list, one heart wider for each heart. Spin it and every tooth ticks past the flapper, the wheel runs a little past its slice and settles back, confetti flies, and the wall glides to the winner. On a laptop the wheel sits beside the wall, and the first visit spins once to show it; on a phone it is a sheet over the room. Tapping the poster in front, or "Pick for tonight", picks a film by hand.

Everyone in the house hearts films on one device: the turn chip names whose turn it is and passes to the next person, and the chips under the title show who has hearted the film. Watched is a shelf of what you have seen, with the date and your stars; "Back on the list" returns a film to the wall. Hearts, the shelf, and the nights stay in the browser under one key, and Export and Import carry them to another browser.

Without WebGL the same wall is drawn in CSS 3D, and with reduced motion it is a still grid with a stepping wheel.

It needs one file in your project, `movie-night.inputs.json`. `inputs.example.json` in this folder shows every key with a note on each:

- `people`: one to eight names, everyone who hearts films on this device.
- `films`: the watch list in wall order. Each film has `title` and `year`, and can have `note` (one line under the title), `poster` (a `.jpg`, `.jpeg`, `.png`, or `.webp` path in your project), and `hearts` (names from `people`). A film with no `poster` key still finds `posters/<title>-<year>.jpg` in your project, for example `posters/knives-out-2019.jpg`; a film with no poster file gets a drawn poster card.
- `theme`: `cinema` (red velvet, a warm spotlight), `drive-in` (a night sky, neon), or `arthouse` (gallery paper, a cool lamp). Each has a light and a dark room, following the device's setting.
- `title`: the page's name (Movie Night when left out).
- `watched`: films already seen, `{ "title", "year", "date": "2026-10-17", "stars": 0 to 5 }`; they start the shelf.
- `lookupPosters`: true lets the page find a missing poster on Wikipedia when it is online; false keeps every request on your own server. True when left out.

The optional key `TMDB_READ_TOKEN`, set with `csc key set`, makes `run.py` fetch a poster from TMDB for each film with no poster file and save it into the page. The token is only sent to TMDB and is never written to any file.

Ask the person: "Which films are on your watch list, and who picks with you? Which room do you want: cinema, drive-in, or arthouse? Do you have poster images for any of them, and films you have already watched?" A person with no preference gets the example: eight films, three people, the cinema room, and four sample posters from this folder.

## Run

```sh
cd <project> && python3 <this folder>/scripts/run.py
```

It reads `movie-night.inputs.json`, checks every key, and writes `out/movie-night/`: the page, `config.js` with every film and its poster path (or null), `theme.css` with the chosen room, and the posters in `media/posters/`. It prints how many films there are and how many have a poster file. A missing or wrong key, an unknown name in `hearts`, or a poster path that is not there is named in one line and nothing is written. Running it again on the same inputs writes the same files.

## Check

1. `out/movie-night/config.js` lists every film with its poster path or null, and `run.py` printed the film count and the posters found.
2. Serve the page (see Host) and open it. The wall glides in, the spotlight drops onto the film with the most hearts, and its title opens up.
3. Drag or swipe the wall, or press the arrow keys: it glides and lands squarely on one poster. Tap a poster to bring it to the front.
4. Tap "Spin the wheel" beside the wall (on a phone, open the Tonight tab first), or press Space. The wheel ticks, settles, names the film under the pointer, and the wall glides to that film under the spotlight. The card says "Tonight's film".
5. Tap "Heart it": the chip for the person whose turn it is fills, and that film's slice on the wheel grows. Tap the turn chip to pass to the next person.
6. Tap "Watched": the film leaves the wall and appears on the Watched shelf with today's date; tap the stars to rate it, and "Back on the list" to return it.
7. Export saves `movie-night.json`; Import of that file in another browser brings the hearts, the shelf, and the nights.
8. Set `theme` to another room and run again: the room, the light, and the page all change color.
9. The browser console shows no errors.

## Host

```sh
cd <project> && python3 -m http.server 8000 --directory out/movie-night
```

Then open http://localhost:8000/. The folder is plain files, Three.js, the font, and the posters included, so any static host serves it as it is. With `lookupPosters` false nothing is fetched from anywhere else.

## Make it yours

Every change here needs only a new run of `run.py`; nothing is built.

- Every key in `movie-night.inputs.json`: the films, their notes and posters, the people, the room, the shelf, and the poster lookup.
- A room: copy `site/themes/cinema.css` to a new file in `site/themes/`, change its values, and set `theme` to the file's name. The backdrop, the floor, the spotlight, the dust, the wheel's brass, the confetti, and the page all take their colors from it.
- The wall and the room: `site/scene/wall.js` (the posters, their reflections and rim light), `site/scene/materials.js` (the shaders for the posters, floor, backdrop, cone, and dust), `site/scene/room.js`, `site/scene/spotlight.js`, and `site/scene/camera.js` (how the front poster is framed).
- The glide and the springs: `site/game/motion.js`; the spotlight's drop and flicker: `site/game/spot.js`.
- The wheel: `site/ui/wheel.js` (the brass, the teeth, the flapper, the spin and settle) and `site/ui/audio.js` (the tick and the chime).
- The drawn poster cards for films with no poster: `site/game/art.js`.
- The buttons, the panel, and the shelf: `site/index.html` and `site/styles/`.
