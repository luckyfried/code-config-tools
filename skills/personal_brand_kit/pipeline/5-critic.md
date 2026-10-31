# 5. Critic: the cut is measured and watched before it renders

Goal: `qa/check.json` passing for the cut, and `critic/verdict.json` shipping it at the bar or spending its one fix.
`film.py render` refuses until both hold for the cut `cut.json` names.

## Measure

```
python3 S/scripts/qa.py check
```

`check` holds `cut.mp4` and the boards to the kit's measured rules (`qa.py --help` lists each with its number): the
board's size, H.264, yuv420p, 30 fps and 12–30 s; no black stretch of 0.4 s; no frozen stretch of 1.0 s before the
picture holds still at the end; no white frame; no failed render job, font or photograph; the hook inside the first
30 frames; the bounds of every board; the hook's subject inside the frame; `brand.json` and `out/plan.md`; and the
cut's sound, which is the delivered reel's: its `audio` row names the film's AAC track and loudness, the master's,
the bed's and the effects' loudness, the gap (8 LU or more), the cues against the beats, where the film goes quiet
against where the picture holds still, and where the bed came from.

Two figures land beside the checks in `qa/check.json` and are never a pass or a fail: the cuts (as planned and as the
picture shows them, and cuts a minute) and the luma line (each second's change; the seconds under 0.5 are where the
picture stands still). A failing check is fixed at its source and the cut made again (`snap`, `music.py master`,
`film.py cut`, `qa.py check`) before the critics watch.

A render on a shared graphics card can lose its context and come back as white frames with the job reported as a
success: `check` fails it on `white` or `safe`. Run `film.py cut` once more, unchanged, before reading it as a defect.

## Watch

```
python3 S/scripts/vote.py cut
```

`cut` writes the round file `critic/cut-N.json` for the cut `cut.json` names and prints the cut's `audio` row. Read
`S/critic/critic.md`, section "The cut". Then, as the motion designer and as the person, score the film (keyed `film`
under each critic) 1–5 on each of the six criteria, `idea`, `picture`, `type`, `motion`, `sound` and `own`, with a
paragraph each: the picture's criteria from `cut.mp4`, its strips and frames, `sound` from the `audio` row. Never
replace the file with one from another run; a round is tied to its cut.

```
python3 S/scripts/vote.py verdict
```

The bar: the mean of every score 4.5 or more, and no score under 4. Never round a score up to reach it.

- `SHIP`: at the bar; go on to movement 6.
- `FIX ONCE`: under the bar in round 1. It names the lowest score: fix that one thing at its source with the levers
  (`S/critic/critic.md`, "Levers"), make the cut again (`storyboard.py draft`, `check`, `sheets` and the pick when the
  boards change, `snap`, `music.py master`, `film.py cut`, `qa.py check`), then `vote.py cut` for round 2 (say in
  `fixed` what changed) and score again.
- Round 2 under the bar: the one fix is spent. `film.py render` makes the cut as it stands, and `brief.md` carries
  its scores and what holds it under; the review page never shows a score. A measured check never ships failing: a
  failing `qa.py check` is fixed before any round.
