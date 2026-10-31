# 6. Critic, gate, deliver

Goal: the finished film scored by both critics on the seven rules against the bar, a green `qa.py gate`, and the
run's `out/` holding the deliverables and nothing else: `film.mp4`, `film-landscape.mp4` and `film-square.mp4`,
`posts/`, `story.png`, `caption.txt`, `grid-after.png`, `grid-before.png` (when there is a feed), `boards.png` (the
three looks) and `review.html`, the film's cover. The working files stay in the run folder beside `out/`: `brief.md`,
`audit.md` (when there is a feed), `plan.md`, `crops.png`, `storyboards/`, `vote.md`, `critic/` and `frames/`.

## Measure, then look

```
python3 S/scripts/qa.py check
```

`check` measures each film the render made (size, H.264 yuv420p at 30 fps, the length band, the AAC track's loudness, black
stretches, and frozen stretches before the board's stop: the still from the stop to the end is the ending), the
render report, the swap test, the posts (one 1080x1350 picture per post, no two the same), `out/` (the deliverables
and nothing else) and the two grid images. It writes `qa/check.json` with every figure and the reel it measured,
`qa/film.check.json` with the reel's cuts and luma line, and the reel's strips in `qa/`. Run it after every render:
`vote.py cut` opens a round only for the reel `qa/check.json` measured. Fix anything it fails before the critics
look. Then:

```
python3 S/scripts/vote.py cut
```

Read `S/critic/critic.md` section "The cut". As the designer, then as the person, open this render's files with the
Read tool: every `frames/*.png` (full size), `qa/film-strip12.jpg`, `out/story.png`, `out/grid-after.png`, every
`out/posts/NN.png`, `clips/requests.json`, the `out/` listing and `qa/check.json`; then fill in the round file it
names (`critic/cut-1.json`): a score 1-5 on each of the seven rules and a paragraph each. Every score is read from
this render; a score carried from an earlier round or board is not a read.

```
python3 S/scripts/vote.py verdict
```

The bar: a mean of 4.5 or more over the seven rules, and no rule under 4. Each rule's score is the lower of the two
critics' scores. Score what you see; a score is never rounded up to reach the bar.

- `SHIP` (exit 0): the film is at the bar. Go on to deliver.
- `FIX ONCE` (exit 2): it names the lowest rule under the bar that has a lever in the run, the lever, and the steps
  to run after it. Make the fix now, in this run: change what it names (the hook or the ask, a post's shot, the
  grade's palette, the music), then run the steps it names in order, which always end `film.py render`, `qa.py
  check` and `vote.py cut` for round 2 (say in `fixed` what changed); score round 2 on the new render, and run
  `vote.py verdict` again. Delivering without the fix is a refusal: the gate's critic row stays red on a `FIX ONCE`.
- `DELIVER` (exit 0): the film is still under the bar and the one fix is spent, or no rule under the bar has a
  lever in the run. The render is delivered as the best cut, and `brief.md` states every score against the bar.

## Deliver

```
python3 S/scripts/deliver.py
```

It writes `brief.md` beside `out/` (every door, every assumption, which look was picked and why, which of their
photos each post is, how the film was made, the music's origin, and every score against the bar) and
`out/review.html`, the person's page: the reel playing first with the landscape and square films beside it, the posts
with the Story card and the captions, when to post them, their grid before and after with the read of their grid,
the two other looks with "Prefer another look? Say 'make the second one'", and how it was made, in plain words. The
page carries no scores. Then it runs `qa.py gate`. On a red gate the page's last section and deliver.py name each failing check: fix the cause, then
run deliver.py again. On a green gate its last line is the reel's path from the project's root,
`build/<run>/out/film.mp4`.

## Tell the person

Your reply names the reel first: its full path from the project's root, exactly as deliver.py printed it on its last
line, in a sentence ("Your reel is at build/20261026-014049/out/film.mp4"). Never a bare `film.mp4`. Then, in two or
three plain lines: `review.html` in the same `out/` folder opens everything (the three films, the posts, the Story
card, the captions in `caption.txt`, the grid after),
what the film shows in one sentence, and when the first post goes up. Where you may ask, add that two other looks are
on the page and they can say "make the second one".

## Another look

When the person asks for another look ("make the second one", "the bold one"), pick that board
(`storyboard.py pick <letter> --by person --reason "..."`) and run the steps from the music on (pipeline/5-produce.md:
`music.py find`, `analyze` and `master`, `film.py render`), then this page again, in the same run folder.

When the gate failed, deliver.py's last line names the failing checks ("not ready: the gate failed on ...") and no
path: your reply says what failed, in plain words, and names no film, no path to one, and no review page.

