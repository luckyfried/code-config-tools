# The critics

Three critics score the three looks as boards (movement 3); two of them score the timed cut (movement 5). Each one is
a voice you take on in turn, with its own eye. Score what a viewer would notice, against the rules of
`S/motion/system/standards.md`, each look against its own style card (`S/styles/<id>.json`), and say why in plain
words.

## The panel

**The motion designer.** Has shipped title sequences and brand films. Looks at craft: is the type a system (the
card's two faces, a scale, lines that enter and settle); is every move eased, anticipating and settling, or does it
slide; are the cuts the card's own and on the beat; does the card's finish hold the film together; does anything
collide, crop badly or sit outside the safe area.

**The editor.** Cuts documentaries and social films. Looks at story: does every beat show something they did, made or
went to, in their own line, and would their friends say "that is so you"; does the film build to its last moment; does
each shot earn its time; does the ending, their question and their sign-off, make you want to answer and share it.
The editor scores the boards only.

**The person.** Speaks in the first person, from `taste.md` and their captions: "is this me?" Their photos, their
colors, their voice, their pacing, nothing on the avoid list. Would I post this today, without changing a thing?

## The criteria (1–5 each)

| key | what it reads | a 5 | a 3 or lower |
|---|---|---|---|
| `idea` | R1: the hook states one idea in their own words over their own photograph; every move and cut is the look's own; the closer pays it off | the first second says who they are; each moment is theirs, in their line; the ask and the sign-off land as the ending | a hook that could open anyone's film, a beat that shows no moment of theirs, an ending that just stops |
| `picture` | R2: one finish, the look's; every color a photograph's own or the look's palette's; the closer holds still | their photographs fill the frames the card gives them, in one finish, the colors their feed's | a photograph lost under a field, colors from nowhere, a closer that keeps moving |
| `type` | R3: the card's two faces at a clear scale; lines that enter and settle; every line reads on its ground; nothing colliding | every line readable at a glance on a phone, settled within a second, inside the safe area | a line too small to read, a line touching another or the edge, type lost on a busy picture |
| `motion` | R4: every move anticipates and settles, no two beats in a row alike, the last moment held longest, cuts on the beat | a rhythm you can feel, beats of different lengths, the peak held | the same move twice, uniform beats, linear slides |
| `sound` | R5, the cut only, from `qa/check.json`'s audio row: the bed belongs to the look, a cue only where a line lands, effects 8 LU or more under the music, quiet from the stop | the bed fits the look and their words, each cue on a line | a bed at odds with the look, more cues than lines, effects too loud, sound running on past the stop |
| `own` | its own film: the hook and the closer read as this look and no other | the three looks are three different films | two looks that read as one |

## The looks (movement 3)

Look at `out/boards.png`, then each look's `storyboards/<letter>/sheet.png` (the hook, a middle beat and the closer
at rest) and its `storyboard.md`, and score every look as each critic in turn in `vote/scores.json` on `idea`,
`picture`, `type`, `motion` and `own`. A storyboard is a promise: score the film it will become, from the frames you
can see. Write one paragraph per look and critic, at least 25 words: what works, what fails, the one change you
would make. The scores are the critics'; the person picks the look.

## The cut (movement 5)

The motion designer and the person score the timed cut before the film renders. Look, actually look:

- `cut.mp4` with its sound (the master `music.json` names; the reel delivered is this file), and its strips with the
  Read tool: `cut-strip.png` (a frame a second) and `cut-strip12.jpg` (every frame at 12 a second, a row a second),
  read row by row, and any frame you cut from `cut.mp4` to look closer;
- `qa/check.json`: the measured checks and the figures, and its `audio` row, the film's sound measured.

`idea`, `picture`, `type`, `motion` and `own` are scored from the frames and strips alone; `sound` from the `audio`
row alone. A read that cites a storyboard or a move name instead of a frame is not a read. Fill in
`critic/cut-N.json` as `vote.py cut` wrote it and run `vote.py verdict`:

- a mean of 4.5 or more and no score under 4: SHIP, and the film renders;
- round 1, anything less: the verdict names the lowest score; make the one change that fixes it with the levers
  below, cut again and score round 2;
- round 2, anything less: the budget is spent; the film renders as it stands and `brief.md` carries its scores and
  what holds it under.

Score what you see. Never round a score up to reach the bar: a spent budget with honest scores is the right outcome.

## The levers

- The words on screen: `taste.json` `hook`, `question` and `signoff`, and each moment's `line` and `pillar`, then
  `storyboard.py draft`, `check`, `sheets`, the pick, `snap`, `music.py master`, `film.py cut`.
- Which moments play, and in what order: `taste.json` `moments` (the last is held longest), then the same steps.
- Which photograph plays which part, with a folder of photographs: `cast.json`, then the same steps.
- The music: another track at `music/source.<ext>`, or `taste.json` `music` (`words`, `avoid`), then `music.py find`,
  `storyboard.py snap`, `music.py master`, `film.py cut`.
- The look itself is the style card's; a board is never edited by hand. A look that cannot reach the bar is a reason
  to offer another one, never to edit the card.
