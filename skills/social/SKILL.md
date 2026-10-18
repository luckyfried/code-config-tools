---
name: social
description: "Makes finished social media posts: designed image files (PNG), Story/Reel MP4s, captions and a review page, saved to out/. Use for ANY request for social media posts or content, however vague: 'make a post', 'make my taco tuesday post look good', 'a week's worth of instagram posts', 'a week of posts', 'posts for my bakery/shop/business', 'instagram stuff', 'promote my event/listing/fundraiser', 'something for facebook', 'help me post on linkedin', 'make it look good', 'holiday promo', 'new product post'. The person wants posts they can publish, not advice: never answer these with a text-only plan, caption list or content calendar in chat; invoke this skill and make the actual images. Covers Instagram feed, carousels, Stories, Reels, Facebook, TikTok covers and clips, LinkedIn, X, Pinterest and link cards. Runs a fixed pipeline (scope, brand kit, concept, copy, original designed visuals, motion, critic, review page) without asking questions. Use it FIRST, before any other design, image, banner or ad skill."
---

# Social: the pipeline

Someone typed a short, vague request. They want posts they can publish today. You will run
**every step below, in order, every time**. Each step tells you which file to read and
which script to run. Reading the step file is not optional: the rules that win live there.

**Never ask the user a question.** Not about platforms, colours, dates, photos or anything
else. Make the sensible assumption, write it under `## Assumptions` in `out/brief.md`, and
keep going. A finished set with stated assumptions beats a perfect question.

## Paths

`S` below means this skill's folder (the directory holding this SKILL.md, usually
`.claude/skills/social`). Shell variables do not survive between commands, so **write the
path out in full in every command**, e.g. `python3 .claude/skills/social/scripts/qa.py gate`.
Run every command from the workspace root. Deliverables go in `out/`. Scratch work (data
JSON, downloads, crops, QA overlays) goes in `build/`. Never put HTML, scripts or overlays in `out/`.

## Step 0: start

```
python3 S/scripts/setup.py          # installs/locates venv, Chromium, ffmpeg (idempotent; first run takes a minute; SOCIAL_CHROMIUM=playwright or =/path/to/chrome overrides the browser)
mkdir -p out build && date "+%A %Y-%m-%d %H:%M %Z"
ls -la in/ 2>/dev/null; ls brand.json out/brand.json 2>/dev/null
```

Then create `out/brief.md` with the checklist below and tick each box (`[x]`) the moment
that step is done. `qa.py gate` and `deliver.py` read this checklist; unticked boxes fail them.

```
# Brief: <business>

## Pipeline
- [ ] 0 scope: read pipeline/0-scope.md, sized the job, picked playbook
- [ ] 1 brand: read pipeline/1-brand.md, brand.json saved
- [ ] 2 concept: read pipeline/2-concept.md, 3-5 ideas, one picked with rationale, image plan written
- [ ] 3 copy: read pipeline/3-copy.md, out/copy.md written, qa.py copy passes
- [ ] 4 visuals: read pipeline/4-visuals.md, every planned image rendered and opened
- [ ] 5 motion: read pipeline/5-motion.md, MP4 rendered (or "not in scope" with reason)
- [ ] 6 critic: read pipeline/6-critic.md, critic sub-agent ran, FIXes applied, qa.py gate passes
- [ ] 7 deliver: read pipeline/7-deliver.md, deliver.py wrote out/index.html
```

## The steps

| # | Read this first | Do | Output |
|---|---|---|---|
| 0 | `S/pipeline/0-scope.md` and the one matching `S/playbooks/<type>.md` | size the job (one post + story, a week, a campaign), pick platforms, compute real dates | `## Scope` + `## Assumptions` in `out/brief.md` |
| 1 | `S/pipeline/1-brand.md` | reuse `brand.json` if it is for this business, else derive one | `brand.json` + `out/brand.json` |
| 2 | `S/pipeline/2-concept.md` | 3-5 genuinely different ideas, score, pick one, write the image-by-image plan | `## Concepts`, `## Pick`, `## Plan` in `out/brief.md` |
| 3 | `S/pipeline/3-copy.md` | captions per platform, alt text, posting plan; then `python3 S/scripts/qa.py copy` | `out/copy.md` |
| 4 | `S/pipeline/4-visuals.md` | per post: `library.py find` + LOOK at the examples, write an original HTML design, source imagery (`photo.py`, `mockup.py`, `assets.py`), `render.py --html`, look at it full-size and feed-size, iterate | `build/html/*.html`, `build/design-notes.md`, `out/*.png`, `out/credits.md` |
| 5 | `S/pipeline/5-motion.md` | `motion.py` for Reels/Stories/TikTok | `out/*.mp4` |
| 6 | `S/pipeline/6-critic.md` | `qa.py check`, spawn the critic sub-agent with `S/critic/critic.md`, fix every FIX, max 2 rounds, `qa.py gate` | `out/qa.json` all PASS |
| 7 | `S/pipeline/7-deliver.md` | `python3 S/scripts/deliver.py` | `out/index.html` |

`python3 S/scripts/qa.py status` tells you at any point which steps are done and what is missing.

## Non-negotiables (the reasons earlier versions lost)

1. **Idea before layout, design before render.** No rendering until `out/brief.md` has 3-5 concepts, a pick with a
   written reason, and a plan table saying what each image shows and says.
2. **Every post is an original design.** The 66-example library (`S/library/`, found with `library.py find`) is
   a reference to study for taste, never a set of templates to fill. You write each post's HTML yourself, for
   this brand, idea and photo; the critic fails a post that is a library layout with new words.
   Rules of craft: `S/references/design-principles.md`; renderer contract: `S/references/html-authoring.md`.
3. **The picture matches the words.** If a headline says "tacos", the image shows tacos or
   no food at all, never a burrito. If it says "dim", it is dim.
4. **No fake buttons** on organic posts: no "Shop now" pills, play icons, fake like counts or
   UI chrome. CTAs are plain words ("Tuesdays, all day", "link in bio").
5. **Offer terms once.** Price/date/limits stated plainly once per caption; no terms block
   pasted into every post.
6. **Dates are computed, never guessed.** Every weekday next to a date comes from a command.
7. **Every image is seen.** You open every PNG after its last render; the critic opens every
   one too; `qa.py gate` fails until each current file has a PASS that names what it shows.
8. **Scope fits the ask.** "Make my post look good" is one great post plus a Story, not a
   17-asset campaign. "A week of posts" is 5-7 posts with a rhythm, not 7 product shots.
9. **Sound like a person**: the No-AI-tells list in `pipeline/3-copy.md`. Keep the jokes.
10. **No invented facts.** No made-up addresses, hours, reviews, awards, years or stats.
   Missing facts become a stated assumption or a clearly marked `[placeholder]` in the caption.
11. **No purple**, anywhere, ever.

## Final chat reply (short)

What was made (counts and formats), the posting plan (day, time, platform, post), the 3-6
assumptions that matter, and the path `out/index.html`. No essay, no design lecture.
