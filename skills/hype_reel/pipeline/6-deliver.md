# 6. Render, deliver

Goal: `out/` complete (`film.mp4`, `cover.png`, `feed.png`, `captions.md`, `review.html`, `brief.md`, and for a launch
`story-1.png`, `story-2.png`, `story-3.png` and `countdown.png`) and a green gate. `out/` holds the deliverables and
nothing else: the storyboards, the vote and the strips stay in the run folder.

## Render

```
python3 S/scripts/film.py render
```

It refuses with the reason ("not yet: ...") until movement 5 shipped the current cut. Then it lays the mastered music
and the board's sound effects (a whoosh on each cut, a shutter as each photograph lands, an impact on each slammed word
and on the closer, a riser into the closer, all on the music's grid and in its key) under the cut into `out/film.mp4`
(AAC 192 kbps), and renders the stills as settled frames of the same film, each from the frame `film.json` `cards`
names: the cover (the reveal at rest, the strongest settled frame), the feed post as the closer laid for 1080×1350,
and for a launch the three teaser stories and the countdown card in the story format (1080×1920). None is scaled and
none is a second composition. The cover is also baked into the reel as its frame 0, so the feed shows it before the
reel plays; the length and the sound are untouched. `engine.json` records the engine and the seconds each part took;
`cards.json` names each still, its format and its frame.

Open `out/cover.png` and `out/feed.png` with the Read tool, and for a launch the stories and `out/countdown.png`: the
cover reads as the subject at a glance, the subject holds when the grid crops the feed post to a square, the stories
are three different moments, the date reads at a glance. A still that is wrong is fixed in the storyboard, and the film
is cut, read and rendered again.

## Captions

Write `captions.md` in their voice, with sections headed exactly `## film`, `## feed post` and `## share`, and for a
launch also `## story 1`, `## story 2`, `## story 3` and `## countdown`. Every section names the subject. `## share`
is the share caption: one to three plain sentences someone could post with the reel as it is, true to the subject
(`taste.json` `plan.share` is its draft). When their own captions carry hashtags (`register.hashtags` in
`taste.json`), the film and the feed post carry one to ten, theirs first; when that list is empty, no section carries
one. Use their case, their length, their kind of emoji (or none), and open the film's caption on the film's hook.
When they write in lowercase, every section is lowercase except the subject's name. Read their captions in `taste.md`
first. When you do not write one, deliver.py drafts every section from `taste.json`.

## Deliver

```
python3 S/scripts/deliver.py
python3 S/scripts/deliver.py feed          # they asked for only the feed post
```

Name the pieces they asked for when they asked for only some (film, cover, feed, captions, and for a launch stories
and countdown): the gate runs on the whole set as always, then `out/` keeps those pieces and `brief.md`, and the rest
moves to the run folder. With no piece named, everything is delivered. Asking for stories or a countdown on a reel
that is not a launch is refused with one plain line.

It writes `out/captions.md`, `out/brief.md` (the subject as given and its kind, the plan, where the palettes meet,
every door, every assumption, the vote, the pictures in the film with the words on each and the rule that cast each,
each clip generated or standing in, the music's origin, the engine, the critics' scores) and `out/review.html` (the
reel with the cover as its poster beside the captions, the feed post and any launch stills below), then runs `qa.py
gate`: the picture's checks of movement 4 on `out/film.mp4` (with the audio: AAC near 192 kbps, −14 LUFS within 1 LU),
frame 0 matching the cover, the stills' sizes, `out/film.mp4` being the render of the current cut, the hook entry, the
winner passing the swap test, the critic round passing every read, the captions (the share caption one to three
sentences), the research and the board. On a red gate it names each failing check: fix the cause, then run deliver.py
again.

## Tell the person

The reply opens with the reel's full path from the workspace root, copied from the last line `deliver.py` printed,
in a sentence: "Your reel is at build/20261026-014049/out/film.mp4." Never the bare name `film.mp4`. When they asked
for only some pieces, that line is the first of them, and the reply names those pieces and what the run assumed. Then
two or three plain lines: where everything else is (`build/current/out/review.html` opens it all), the share caption,
and the idea of the film in one sentence.

When the gate has not passed, `deliver.py`'s last line is `the gate failed: ` and the failing checks' names, and it
prints no path. Fix what it names and run deliver.py again; when you stop before a green gate, the reply says
what failed in plain words and names no film and no path, so nothing points at a reel that is not ready.
