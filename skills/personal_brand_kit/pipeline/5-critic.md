# 5. Critic: the cut is measured and watched before it renders

Goal: `qa/check.json` passing for the full-size cut, and `critic/verdict.json` shipping it at the bar or spending
its one fix. Every round before that is scored on the half-size proof (`film.py cut --proof`); the last read, of the
type, is on the full-size cut. `film.py render` refuses until both hold for the full-size cut `cut.json` names.

## Measure

```
python3 S/scripts/qa.py check
```

While `proof-cut.mp4` is the newest cut, `check` reads it and its first line says "reading the half-size proof";
every size it reports is in board units, the full-size cut's numbers, so the proof passes or fails exactly where the
cut would. `check` holds the cut and the boards to the kit's measured rules (`qa.py --help` lists each with its number): the
board's size, H.264, yuv420p, 30 fps and 12–30 s; no black stretch of 0.4 s; no frozen stretch of 1.0 s anywhere, the
ending too (the closer keeps a slow push to the last frame); no white frame; no failed render job, font or photograph;
the hook inside the first 30 frames; the bounds of every board; the hook's subject inside the frame; `brand.json` and
`out/plan.md`; and the cut's sound, which is the delivered reel's: its `audio` row names the film's AAC track and
loudness, the master's, the bed's and the effects' loudness, the gap (8 LU or more), the cues against the beats, where
the film goes quiet against where the picture holds still, and where the bed came from.

Two figures land beside the checks in `qa/check.json` and are never a pass or a fail: the cuts (as planned and as the
picture shows them, and cuts a minute) and the luma line (each second's change; the seconds under 0.5 are where the
picture stands still). A failing check is fixed at its source and the proof made again (`snap`, `music.py master`,
`film.py cut --proof`, `qa.py check`) before the critics watch.

A render on a shared graphics card can lose its context and come back as white frames with the job reported as a
success: `check` fails it on `white` or `safe`. Run the same `film.py cut` once more, unchanged, before reading it as
a defect.

## Watch

```
python3 S/scripts/vote.py cut
```

`cut` writes the round file `critic/cut-N.json` for the newest cut (the proof, which its first line says) and prints
the cut's `audio` row. Read
`S/critic/critic.md`, section "The cut". Then, as the motion designer and as the person, score the film (keyed `film`
under each critic) 1–5 on each of the six criteria, `idea`, `picture`, `type`, `motion`, `sound` and `own`, with a
paragraph each: the picture's criteria from the cut it names, its strips and frames, `sound` from the `audio` row. Never
replace the file with one from another run; a round is tied to its cut.

```
python3 S/scripts/vote.py verdict
```

The bar: the mean of every score 4.5 or more, and no score under 4. Never round a score up to reach it.

- `SHIP` on the proof: at the bar; make the full-size cut and read the type on it (below).
- `SHIP` on the full-size cut: at the bar; go on to movement 6.
- `FIX ONCE`: under the bar in round 1. It names the lowest score: fix that one thing at its source with the levers
  (`S/critic/critic.md`, "Levers"), make the proof again (`storyboard.py draft`, `check`, `sheets` and the pick when
  the boards change, `snap`, `music.py master`, `film.py cut --proof`, `qa.py check`), then `vote.py cut` for round 2
  (say in `fixed` what changed) and score again.
- Round 2 under the bar: the one fix is spent. Make the full-size cut and read its type as below; `film.py render`
  then makes the cut as it stands, and `brief.md` carries its scores and what holds it under; the review page never
  shows a score. A measured check never ships failing: a failing `qa.py check` is fixed before any round.

## The full-size cut and its type

```
python3 S/scripts/film.py cut
python3 S/scripts/qa.py check
python3 S/scripts/vote.py cut
python3 S/scripts/vote.py verdict
```

`film.py cut` makes the same cut at full size, `cut.mp4`, and takes the proof away. `vote.py cut` moves the round to
it and empties each critic's `type` score; the other scores stand. As each critic, watch `cut.mp4` and read its strips
again, read every line at the size a phone shows it, and score `type` again. A `type` score that drops the round under
the bar is a `FIX ONCE` (or the spent fix in round 2) like any other.
