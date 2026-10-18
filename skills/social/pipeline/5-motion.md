# Step 5: Motion

If the scope includes Reels, TikTok or Stories, make **at least one MP4** (6-15 s,
1080x1920, H.264, burned-in captions). Stories that are a still image still get one
moving version: motion gets more taps-forward-stopped than a static card.
If nothing in scope is 9:16 or video, write "5 motion: not in scope (feed only)" next to the box and tick it.

## The two routes

**A. Slides (default, always works).** Render 2-4 stills from your own Story HTML that
build the message in beats (the same HTML file rendered with progressive text, or a few small variations of it), then animate them:

```
python3 S/scripts/motion.py slides build/frames/p01-1.png build/frames/p01-2.png out/p01-tacotuesday-story-1080x1920.png \
  --seconds 8 --out out/p01-tacotuesday-story-1080x1920.mp4
```

- Beats are separate renders of the same HTML with progressive content (headline only,
  then + price, then + "all day"/the CTA): give the file `{{beat2}}`-style tokens and pass them with `"data"` in
  a `--batch` entry, or hide later elements with `visibility:hidden` in a copy. Same design, so it looks like kinetic
  type, not a slideshow. Put the in-between frames in `build/frames/`; only the final MP4 goes in `out/`.
- Transitions: `--transition auto` (default) hard-cuts between beats of one design and
  uses a short eased fade between different pictures. Blanking text makes a centred layout
  reflow (the headline moves when the price appears), and a crossfade there shows two ghosted
  headlines; a cut looks deliberate, like kinetic type. Force one style with
  `--transition cut|fade|push`; `--fade 0.25` sets the fade/push length (0.1-0.5 s, `0` = all cuts).
- No push-in by default. `--zoom 1.04` adds one slow push-in across the whole clip (same scale on
  both sides of every transition, so nothing doubles); use it for photo slides, not type.
- Open the filmstrip to confirm no double text.
- Here the last beat is the finished Story PNG, so the video ends on the full message.
- `--captions 'Tuesday.' '$2 tacos.' 'All day.'` takes one line per slide (single quotes keep `$` safe) (or `--captions-file build/captions.json` with
  `[{"start":0,"end":2.5,"text":"..."}]`). Max 2 lines on screen, 3-5 words per line.
  Captions are placed automatically at one height for the whole clip, inside the strictest
  9:16 safe zone (below the top 250px, above the bottom 420px, clear of the right rail), in the
  clearest band of the stills; they use brand colours and are hidden during fades/pushes.
  If it warns that captions overlap artwork, the stills already carry the words: drop them.
  Don't say everything twice.
- Colours come from `brand.json` (./brand.json or out/brand.json; `--brand <path>` to point
  elsewhere). Non-9:16 stills (e.g. a 1080x1350 post) are centred on brand `bg`; with no brand
  the pad continues each still's own edge colour. Transparent cutouts sit on the set's
  background. `--bg "#hex"` overrides; it warns if that is far from the brand.

**B. Animated HTML (when the idea needs real movement).** Write a self-contained HTML
page at 1080x1920 whose animation uses CSS animations/transitions (no JS timers), then:

```
python3 S/scripts/motion.py html build/anim.html --seconds 8 --out out/p02-reel-1080x1920.mp4 --captions-file build/captions.json
```

The script pauses every animation and seeks it frame by frame, so the video is smooth
and deterministic. Use the bundled fonts by absolute path in `@font-face`.

## Rules

- First second = the hook (the offer or the most striking frame). No logo intro, no fade from black.
- 6-15 seconds. A single promo: 6-9 s. A list or tips: up to 15 s.
- No fake UI in the video either (no fake record buttons, fake "like" bursts).
- Silent by design: the file carries a silent audio track so platforms accept it; tell
  the user in the caption notes to add a trending sound in-app if they want one.
- After rendering, `qa.py check` makes a filmstrip of each MP4 in `build/qa/` and a safe-zone
  overlay `build/qa/overlays/<name>-video.png`; open both. It also checks H.264/yuv420p,
  1080x1920, 6-15 s, and that the file decodes; `qa.py gate` refuses a video that fails these.

Tick box 5.
