// The hype reel: each beat's picture laid out the way the board says (the card's photo layout, the whole frame, the
// card's ground alone, or the picture above the matte), alive under the card's camera and the beat's move; the beat's
// words in the card's faces and entrance, landing on the beat and leaving before the cut; over them the shared move
// layer: the beat's move, the cut into the next beat, the card's closer from the closer's start to the stop, where the
// picture holds, and the card's letterbox bars, with words set in the matte above them all. The card's
// finish (its one grade, its halation, its vignette, its grain) lies over all of it, or under the words and the moves
// on a card that keeps its words clean.
import React, {useMemo} from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {bezier, clamp01, fill, lumOf, span} from '../../system/moves/kit';
import {MoveLayer, nudgeAt} from '../../system/moves/layer';
import {closerOf} from '../../system/moves/index';
import type {Look} from '../../system/moves/types';
import {faceStyle} from '../../system/system';
import type {Board, Clip, Grade, Line, System} from '../../system/types';
import {beatOfTime, lookOf, placeBeats, timeAt, timelineOf, type Placed} from './time';

const colorOf = (sys: System, role: string) => sys.colors[role] ?? role;

/** How the card's camera holds a beat, `local` beats into it: how far it is pushed in (1 the photograph covering its
 * box) and how far it has moved sideways, in shares of the box's height. slam lands hard on the beat through the card's
 * entrance curve, settles past its mark and back, creeps on, and draws back a little before the next hit; dolly travels
 * slowly across and in along the card's move curve; snap creeps in steadily and cuts in once, cleanly, to the subject at the beat's middle. */
const cameraOf = (sys: System, local: number, len: number, index: number) => {
  const move = bezier(sys.ease.move);
  const enter = bezier(sys.ease.enter);
  if (sys.camera === 'slam') {
    const k = enter(clamp01(local / 0.5));
    return {zoom: 1.04 + 0.14 * (1 - k) + 0.03 * clamp01(local / len) - 0.02 * span(local, len - 0.3, 0.3), dx: 0};
  }
  if (sys.camera === 'dolly') {
    const u = move(clamp01(local / len));
    return {zoom: 1.1 - 0.06 * u, dx: (index % 2 ? -1 : 1) * 0.03 * (u - 0.5)};
  }
  if (sys.camera === 'snap') return {zoom: 1.02 + 0.03 * clamp01(local / len) + 0.16 * move(clamp01((local - len / 2) / 0.3)), dx: 0};
  return {zoom: 1, dx: 0};
};

/** The beat's picture: the card's ground, the photograph (or the clip's frame made from it) in its box, rimmed, tilted
 * and taped as the card says, pushed and moved about its focus by the camera and the move but never off its box, and
 * the card's shade under the words. */
const BeatPicture: React.FC<{p: Placed; local: number; sys: System; look: Look; nudge: {scale?: number; dx?: number; dy?: number; roll?: number}; frame: number; clips: Clip[]}> = ({
  p, local, sys, look, nudge, frame, clips,
}) => {
  const b = p.beat;
  const pic = b.picture;
  // a field beat's ground is the field its latest word landed on
  const field = b.layout === 'field' ? b.lines.filter((l) => l.t <= local).pop()?.ground : undefined;
  const ground = <div style={{...fill, background: colorOf(sys, field ?? b.ground)}} />;
  if (!pic || b.layout === 'field') return ground;
  const [bx, by, bw, bh] = pic.box;
  const [px, py, pw, ph] = pic.place;
  const [fx, fy] = pic.focus;
  const cam = cameraOf(sys, local, b.len, p.i);
  const z = Math.max(1, cam.zoom / (nudge.scale ?? 1));
  // the photograph scaled about its focus, then moved, never so far that the box shows past its edge; one narrower or
  // shorter than its box stays in its middle, on the box's fill
  const x0 = fx + (px - fx) * z, y0 = fy + (py - fy) * z;
  const hold = (lo: number, hi: number, v: number) => (lo <= hi ? Math.min(hi, Math.max(lo, v)) : (lo + hi) / 2);
  const tx = hold(bw - x0 - pw * z, -x0, -((nudge.dx ?? 0) + cam.dx) * bh);
  const ty = hold(bh - y0 - ph * z, -y0, -(nudge.dy ?? 0) * bh);
  const clip = clips.find((c) => c.image === pic.file && frame >= c.from && frame < c.from + c.frames);
  const src = clip ? `${clip.dir}/${String(frame - clip.from + 1).padStart(4, '0')}.jpg` : pic.file;
  const card = b.layout === 'card' ? sys.photo.picture : null;
  const rim = card ? card.rim * look.W : 0;
  const k = look.W / 1080;
  // the shade: a band under the words, clear a tenth of the frame above and below them, easing (smoothstep, so no
  // edge shows) to the beat's darkness a little before the words and back after them, so on a light picture it reads
  // as a title band and never as a grey wash; a band whose reach passes the box's edge stays dark to that edge
  const ink = b.lines;
  let scrim: React.ReactNode = null;
  if (b.scrim > 0 && ink.length) {
    const top = Math.min(...ink.map((l) => l.top)) - by;
    const bottom = Math.max(...ink.map((l) => l.top + l.size * 1.2)) - by;
    const reach = look.H / 10;
    const ease = (from: number, to: number) => Array.from({length: 9}, (_, i) => {
      const u = i / 8;
      return `rgba(0,0,0,${(b.scrim * u * u * (3 - 2 * u)).toFixed(3)}) ${(from + (to - from) * u).toFixed(1)}px`;
    });
    const rise = ease(top - reach, top - 0.15 * reach);
    const fall = ease(bottom + reach, bottom + 0.15 * reach).reverse();
    const bg = `linear-gradient(to bottom, ${[...rise, ...fall].join(', ')})`;
    scrim = <div style={{...fill, background: bg}} />;
  }
  return (
    <>
      {ground}
      <div style={{position: 'absolute', left: bx, top: by, width: bw, height: bh, transform: card?.tilt ? `rotate(${card.tilt}deg)` : undefined,
        boxShadow: rim ? `0 0 0 ${rim}px ${colorOf(sys, card!.rimColor)}, ${8 * k}px ${14 * k}px ${30 * k}px rgba(0,0,0,0.28)` : undefined}}>
        <div style={{...fill, overflow: 'hidden', background: pic.fill ? `linear-gradient(to bottom, ${pic.fill[0]}, ${pic.fill[1]})` : undefined}}>
          <Img src={staticFile(src)} style={{position: 'absolute', left: px, top: py, width: pw, height: ph, maxWidth: 'none',
            transformOrigin: `${fx - px}px ${fy - py}px`, transform: `translate(${tx}px, ${ty}px) scale(${z})${nudge.roll ? ` rotate(${-nudge.roll}rad)` : ''}`}} />
          {scrim}
        </div>
        {card && card.tape > 0
          ? Array.from({length: Math.min(2, card.tape)}, (_, i) => (
              <div key={i} style={{position: 'absolute', top: -20 * k, [i ? 'right' : 'left']: -40 * k, width: 150 * k, height: 40 * k,
                background: colorOf(sys, card.tapeColor), opacity: 0.7, transform: `rotate(${i ? 35 : -35}deg)`}} />
            ))
          : null}
      </div>
    </>
  );
};

/** The least luma (0 to 1) an accent needs to read as a line over a shaded photograph, as a warm gold or a pale blue
 * does; a darker accent, such as an olive, gives the line the paper instead. */
const LIGHT_ACCENT = 0.6;

/** One line of the beat's words, landing at its beat in the card's entrance and leaving at its `until`, where the next
 * word lands in its place, or with the card's exit curve before the cut (a line that cuts on cuts off). A line on a
 * photograph carries a soft shadow; on the ground, none. */
const Words: React.FC<{line: Line; p: Placed; local: number; sys: System; onPhoto: boolean}> = ({line: l, p, local, sys, onPhoto}) => {
  const enter = p.beat.enter;
  const k = local - l.t;
  if (k < 0 || (l.until !== undefined && local >= l.until)) return null;
  const face = l.face === 'display' ? sys.display : sys.text;
  const inCurve = bezier(sys.ease.enter);
  const gone = enter === 'cut' ? 0 : 0.25;
  const out = gone ? 1 - bezier(sys.ease.exit)(clamp01((local - (p.beat.len - gone)) / gone)) : 1;
  let opacity = out;
  let transform = l.align === 'center' ? 'translateX(-50%)' : '';
  let text = l.text;
  let clipPath: string | undefined;
  if (enter === 'slam') {
    // a slam lands in full ink from its first frame, oversize, so the film's first frame already carries the word
    const v = inCurve(clamp01(k / 0.35));
    transform += ` scale(${1.45 - 0.45 * v})`;
  } else if (enter === 'rise') {
    const v = inCurve(clamp01(k / 0.4));
    transform += ` translateY(${(1 - v) * 0.7 * l.size}px)`;
    clipPath = 'inset(-20% -5% 0 -5%)';
  } else if (enter === 'fade') {
    opacity *= inCurve(clamp01(k / 0.75));
  } else if (enter === 'type') {
    text = l.text.slice(0, Math.ceil(l.text.length * clamp01(k / 0.5)));
  }
  const named = colorOf(sys, l.color);
  const color = onPhoto && l.color.startsWith('accent') && lumOf(named) < LIGHT_ACCENT ? colorOf(sys, 'paper') : named;
  return (
    <div style={{position: 'absolute', left: l.x, top: l.top, fontSize: l.size, whiteSpace: 'pre', color, ...faceStyle(face),
      opacity, transform, transformOrigin: l.align === 'center' ? '50% 60%' : '0 60%', clipPath,
      textShadow: onPhoto ? `0 ${l.size * 0.03}px ${l.size * 0.25}px rgba(0,0,0,0.45)` : undefined}}>
      {text}
    </div>
  );
};

/** The card's grade (lift, gamma, gain in display values, then saturation) and its halation: the light brighter than
 * the halation threshold blurred and laid back over the picture at the card's bloom. */
const GradeFilter: React.FC<{id: string; grade: Grade; bloom: number; halation: number; W: number}> = ({id, grade, bloom, halation, W}) => {
  const e = 1 / grade.gamma;
  const fn = (i: number) => ({type: 'gamma', amplitude: grade.gain[i] - grade.lift[i], exponent: e, offset: grade.lift[i]});
  const h = Math.min(0.99, halation);
  const hi = {type: 'linear', slope: 1 / (1 - h), intercept: -h / (1 - h)};
  return (
    <svg width={0} height={0} style={{position: 'absolute'}}>
      <defs>
        <filter id={id} colorInterpolationFilters="sRGB" x="0" y="0" width="1" height="1">
          <feComponentTransfer in="SourceGraphic" result="graded">
            <feFuncR {...fn(0)} />
            <feFuncG {...fn(1)} />
            <feFuncB {...fn(2)} />
          </feComponentTransfer>
          <feColorMatrix in="graded" type="saturate" values={String(grade.saturation)} result="sat" />
          {bloom > 0 && halation < 1 ? (
            <>
              <feComponentTransfer in="sat" result="hot">
                <feFuncR {...hi} />
                <feFuncG {...hi} />
                <feFuncB {...hi} />
              </feComponentTransfer>
              <feGaussianBlur in="hot" stdDeviation={W * 0.018} result="glow" />
              <feComposite in="sat" in2="glow" operator="arithmetic" k1={0} k2={1} k3={bloom} k4={0} />
            </>
          ) : null}
        </filter>
      </defs>
    </svg>
  );
};

const isIdentity = (g: Grade) => g.gamma === 1 && g.saturation === 1 && g.lift.every((v) => v === 0) && g.gain.every((v) => v === 1);

/** Grain drawn from a new place on every frame. */
const Grain: React.FC<{amount: number; frame: number; W: number; H: number}> = ({amount, frame, W, H}) => (
  <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, opacity: amount, mixBlendMode: 'overlay', pointerEvents: 'none'}}>
    <filter id={`grain-${frame}`}>
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={frame % 997} stitchTiles="stitch" />
      <feColorMatrix type="saturate" values="0" />
    </filter>
    <rect width={W} height={H} filter={`url(#grain-${frame})`} />
  </svg>
);

export const HypeFilm: React.FC<{board: Board; clips: Clip[]}> = ({board, clips}) => {
  const raw = useCurrentFrame();
  const sys = board.system;
  const fin = sys.finish;
  // a card with a cadence steps the picture that many frames at a time
  const frame = fin.cadence > 0 ? Math.floor(raw / fin.cadence) * fin.cadence : raw;
  const placed = useMemo(() => placeBeats(board), [board]);
  const line = useMemo(() => timelineOf(placed), [placed]);
  const look = useMemo(() => lookOf(board), [board]);
  if (!placed.length) return null;
  const last = placed[placed.length - 1];
  const still = last.at + (last.beat.stop ?? last.beat.len);
  // from the stop the picture holds: everything reads the stop's time
  const t = Math.min(timeAt(placed, frame), still);
  const p = beatOfTime(placed, t);
  const local = t - p.at;
  const nudge = nudgeAt(line, look, t);
  const closing = t >= last.at;
  const graded = !isIdentity(fin.grade) || (fin.bloom > 0 && fin.halation < 1);
  const pic = p.beat.layout === 'field' ? null : p.beat.picture;
  const onPhoto = (l: Line) => !!pic && l.top >= pic.box[1] && l.top <= pic.box[1] + pic.box[3] && l.x >= pic.box[0] && l.x <= pic.box[0] + pic.box[2];
  // the closer's shape draws the end card, so the kit sets no words of its own once it begins
  const words = closing && closerOf(sys.closer) ? null : p.beat.lines.map((l, i) => <Words key={`${p.beat.id}-${i}`} line={l} p={p} local={local} sys={sys} onPhoto={onPhoto(l)} />);
  // the moves, the cuts, the closer and the card's letterbox bars over the picture and its words; words set in the
  // matte stand above them, so the bars and what the moves draw never cover the name
  const matte = p.beat.layout === 'matte';
  const over = (
    <>
      {matte ? null : words}
      <MoveLayer line={line} look={look} t={t} bars={fin.bars} closer={{name: sys.closer, at: last.at, still}} />
      {matte ? words : null}
    </>
  );
  // a finished card lays its grade, vignette and grain over the words and what the moves draw; a clean one keeps them
  // above the finish
  return (
    <AbsoluteFill style={{background: colorOf(sys, 'bg'), overflow: 'hidden'}}>
      {graded ? <GradeFilter id="grade" grade={fin.grade} bloom={fin.bloom} halation={fin.halation} W={look.W} /> : null}
      <div style={{...fill, filter: graded ? 'url(#grade)' : undefined}}>
        <BeatPicture p={p} local={local} sys={sys} look={look} nudge={nudge} frame={frame} clips={clips} />
        {look.finished ? over : null}
      </div>
      {fin.vignette > 0 ? <div style={{...fill, background: `radial-gradient(ellipse at 50% 50%, transparent 52%, rgba(0,0,0,${fin.vignette}) 100%)`}} /> : null}
      {fin.grain > 0 ? <Grain amount={fin.grain} frame={raw} W={look.W} H={look.H} /> : null}
      {look.finished ? null : over}
    </AbsoluteFill>
  );
};
