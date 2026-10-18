# Step 6: Critic

You have looked at your own work for an hour; you can no longer see it. A fresh pair of
eyes that has never seen the brief's good intentions now reviews every file. You fix
what it finds. Max **2 critic rounds**; then you fix and verify the rest yourself.

## Round 1

```
python3 S/scripts/qa.py check        # refreshes auto-checks, safe-zone overlays, contact sheet, video filmstrips
python3 S/scripts/qa.py round        # starts critic round 1
```

Fix anything `check` marks **BAD** before spawning the critic (blank/flat image, wrong size).

**Spawn the critic as a sub-agent** with the Agent tool (also called Task;
`subagent_type: "general-purpose"`). Do not review the files yourself in its place. Prompt,
filled in (write the skill path out in full):

```
You are the critic for a social media set. Read S/critic/critic.md and follow it exactly.
Workspace root: <absolute path of the workspace root>. Skill folder: <absolute path of S>.
This is critic round <N>. The user's original request was: "<their exact words>".
Review every file in out/ (images and videos), compare each image with its closest library examples, record a verdict for each with
`python3 S/scripts/qa.py verdict ... --by critic`, and write build/critic-round-<N>.md.
Finish with a one-line summary: how many PASS, how many FIX.
```

When it returns, read `build/critic-round-<N>.md` in full.

## Apply every FIX

- Treat each FIX as an instruction, not a suggestion. If the critic says the word is
  orphaned, the photo shows the wrong thing, the date is off, the CTA reads like a
  button: change the data/copy/image and **re-render** that file.
- **Set-level** FIXes (scope, repetition, caption tells, consistency) go into `copy.md` /
  `brief.md` / every affected image.
- If you genuinely disagree with a FIX (it contradicts the brief or a fact the user gave),
  leave the file, and write one line under `## Assumptions` saying which call you made
  and why. Don't argue with taste calls: change it.
- After fixing: open each re-rendered file yourself, then `python3 S/scripts/qa.py check`
  and `python3 S/scripts/qa.py copy`.

A re-rendered file has a new fingerprint, so its old verdict no longer counts: it needs a
new one. Files you didn't touch keep their PASS.

## Round 2 (only if round 1 had any FIX)

`python3 S/scripts/qa.py round`, then spawn the critic again (a **new** sub-agent, same
prompt, round 2). It reviews the whole set again, not just the changes, because fixes can
break neighbours (a new headline length, a different photo crop).

## After round 2

If anything is still FIX, apply the fix, open the file, and record your own verdict
(self verdicts count only after two critic rounds):

```
python3 S/scripts/qa.py verdict out/<file> PASS --by self --seen "<what is visibly in it now: words + picture>"
```

`--seen` must describe the actual pixels you just looked at, not the plan. The gate rejects two
files with identical `--seen` text. For an MP4, also open `build/qa/overlays/<name>-video.png`
(captions inside the safe zones).

## Gate

```
python3 S/scripts/qa.py gate
```

It fails until: steps 0-5 are ticked, the brief has concepts/pick/plan/assumptions,
`out/brand.json` exists with no purple, `copy.md` lints clean (including a CC BY creator credited in a caption), every render job is an `html` job (no `template` jobs, images present, no `{{tokens}}`), `build/design-system.css` exists for a set of 2+, `build/library-log.json` and `build/design-notes.md` show the reference examples were studied, every MP4 is H.264/yuv420p 1080x1920 6-15 s and decodes, the critic ran, and every file in `out/` has a current PASS and belongs to
a post. Fix whatever it lists and re-run until it says `GATE PASSED`. Then tick box 6.

## If no Agent/Task tool exists in this environment

Run the critic inline: read `S/critic/critic.md`, take that role for the duration (be as
strict as it says, look at every file again from scratch), write `build/critic-round-N.md`,
and record verdicts with `--by critic`. Add to `## Assumptions`: "Critic review ran inline
(no sub-agent tool available)." Still max 2 rounds.
