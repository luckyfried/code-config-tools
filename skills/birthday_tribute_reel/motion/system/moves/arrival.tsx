// What the spectacle moves share: when a beat's spectacle plays and where it lands, the photograph it lands, that
// photograph drawn as the print the shot draws once the camera holds on it, so the move hands the frame back to the
// picture without a jump, and the frame a cut opens onto, drawn the way the incoming beat will show it.
import React, {type CSSProperties} from 'react';
import {Img} from 'remotion';
import {alpha, clamp01, pictureOf, SINE} from './kit';
import {secondsOf} from './spring';
import type {BeatOn, Look, MoveProps} from './types';

type Box = [number, number, number, number];

/** A beat's spectacle in seconds since it began: `s` now, `land` when it lands on the photograph, `out` when the move
 * has handed the frame back, `shows` how much of the move is over the picture (1 until it lands, 0 from `out`), `bare`
 * how much of the frame outside the print the move still covers (1 until the last of the flight, 0 from the landing,
 * so the landing frame shows the shot's own ground and words around the print), and `room` the seconds from its start
 * to the pull back to the wall (or the beat's end). A move begins at the cut into its beat, or the beat's `early`
 * seconds before it. The spectacle takes `want` seconds when the beat has room, and lands within the first part of a
 * short beat, so every move has settled and gone before the pull. */
export const arrivalOf = (p: MoveProps, want = 1) => {
  const {beat, look, t, local} = p;
  const lead = Math.max(0, beat.early ?? 0);
  const start = t - local;
  const room = Math.max(0.3, secondsOf(look, (beat.held ? beat.held[1] : beat.end) - start) + lead);
  const s = secondsOf(look, local) + lead;
  const land = Math.min(want, room * 0.55);
  const out = Math.min(land + 0.38, room - 0.12);
  const shows = 1 - SINE(clamp01((s - land) / Math.max(0.05, out - land)));
  const give = Math.min(0.3, land * 0.4);
  const bare = 1 - SINE(clamp01((s - (land - give)) / give));
  return {s, land, out, shows, bare, room};
};

/** The photograph a beat lands: its own, else the film's ground photograph. Its box on the frame, and where the
 * photograph lies relative to that box (absent: it covers the box). */
export const landingOf = (p: MoveProps) => {
  const box = pictureOf(p.look, p.beat) as Box;
  const src = p.beat.photo ?? p.look.photo;
  const place = p.beat.place ? ([p.beat.place[0] - box[0], p.beat.place[1] - box[1], p.beat.place[2], p.beat.place[3]] as Box) : undefined;
  return {box, src, place};
};

/** The beat's print as the shot draws it: `rect` the photograph's rect on the frame [x, y, w, h], where its box and
 * its place meet; `at` where the photograph lies relative to that rect; `mid` the box's middle the print hangs about;
 * `tilt` the degrees clockwise it hangs at; `rim` the rim px around the rect. */
export const printOf = (look: Look, beat: BeatOn) => {
  const [bx, by, bw, bh] = pictureOf(look, beat) as Box;
  const pl = beat.place;
  const x0 = pl ? Math.max(bx, pl[0]) : bx, y0 = pl ? Math.max(by, pl[1]) : by;
  const x1 = pl ? Math.min(bx + bw, pl[0] + pl[2]) : bx + bw, y1 = pl ? Math.min(by + bh, pl[1] + pl[3]) : by + bh;
  const rect: Box = [x0, y0, Math.max(1, x1 - x0), Math.max(1, y1 - y0)];
  const at = pl ? ([pl[0] - x0, pl[1] - y0, pl[2], pl[3]] as Box) : undefined;
  return {rect, at, mid: [bx + bw / 2, by + bh / 2] as [number, number], tilt: beat.tilt ?? look.print.tilt, rim: beat.rim ?? look.print.rim,
    src: beat.photo ?? look.photo};
};

/** The four corners of the print's rim, turned with the print, clockwise from its top left, in frame px. */
export const cornersOf = (look: Look, beat: BeatOn): [number, number][] => {
  const {rect: [x, y, w, h], mid: [cx, cy], tilt, rim: e} = printOf(look, beat);
  const a = (tilt * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return ([[x - e, y - e], [x + w + e, y - e], [x + w + e, y + h + e], [x - e, y + h + e]] as [number, number][]).map(([px, py]) =>
    [cx + (px - cx) * c - (py - cy) * s, cy + (px - cx) * s + (py - cy) * c]);
};

/** The beat's print, drawn in frame px exactly as the shot draws it once the camera holds on it: the soft shadow of
 * three widening layers, the rim in the card's rim tone, the photograph, and the tape over the rim's top corners, all
 * hung at the print's tilt about its box's middle. `veil` lays the card's ground over the print, 0 to 1. */
export const Print: React.FC<{look: Look; beat: BeatOn; veil?: number}> = ({look, beat, veil = 0}) => {
  const {rect: [x, y, w, h], at, mid, tilt, rim: e, src} = printOf(look, beat);
  const k = Math.min(look.W, look.H) / 1080;
  const dressed = e > 0;
  const len = 150 * k, wide = 40 * k;
  const box = (l: number, t: number, ww: number, hh: number, extra: CSSProperties = {}): CSSProperties =>
    ({position: 'absolute', left: l, top: t, width: ww, height: hh, ...extra});
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: look.W, height: look.H, transformOrigin: `${mid[0]}px ${mid[1]}px`,
      transform: tilt ? `rotate(${tilt}deg)` : undefined}}>
      {dressed ? [0, 1, 2].map((i) => {
        const g = (4 + 6 * i) * k;
        return <div key={`s${i}`} style={box(x - e - g + 8 * k, y - e - g + 14 * k, w + 2 * (e + g), h + 2 * (e + g), {background: 'rgba(0,0,0,0.09)'})} />;
      }) : null}
      {dressed ? <div style={box(x - e, y - e, w + 2 * e, h + 2 * e, {background: look.tone.rim})} /> : null}
      <div style={box(x, y, w, h)}><Face src={src} w={w} h={h} place={at} /></div>
      {veil > 0 ? <div style={box(x - e, y - e, w + 2 * e, h + 2 * e, {background: alpha(look.tone.ground, veil)})} /> : null}
      {dressed ? Array.from({length: Math.min(2, beat.tape ?? look.print.tape)}, (_, i) => (
        <div key={`t${i}`} style={box((i ? x + w + e : x - e) - len / 2, y - e - wide / 2, len, wide,
          {background: alpha(look.tone.tape, 0.7), transform: `rotate(${i ? 35 : -35}deg)`})} />
      )) : null}
    </div>
  );
};

/** Every photograph the film has, the beat's own first; just the beat's own when the film lists none. */
export const photosOf = (p: MoveProps) => {
  const own = p.beat.photo ?? p.look.photo;
  const all = p.look.photos?.length ? p.look.photos : own ? [own] : [];
  return own ? [own, ...all.filter((s) => s !== own)] : all;
};

/** Whether `Incoming` draws the frame `into` opens onto: a beat with a photograph or cells. A beat with neither (a wall
 * that gives no posts, a closer) is drawn by the scene itself, so a cut into it shows the scene and never a stand-in. */
export const opensOnto = (look: Look, into: BeatOn) => Boolean(into.photo || into.cells?.length);

/** How much of a cut into the wall shows the wall's posts, at `u` through the cut's window: they come up from `from`
 * and are gone again by the window's end, so the frame the cut leaves is the shot's own. */
export const standOf = (u: number, from = 0) => SINE(clamp01((u - from) / 0.3)) * (1 - SINE(clamp01((u - 0.75) / 0.25)));

/** The frame a cut opens onto, drawn the way the incoming beat shows it, in frame px over the card's ground: a beat
 * with a photograph shows its print and every other cell of its grid; a wall that gives its posts shows them, each
 * risen `rise` of the way up into its box (0 below it, 1 home), in reading order. Null for a beat with neither (the cut
 * keeps the scene itself). */
export const Incoming: React.FC<{look: Look; into: BeatOn; rise?: number}> = ({look, into, rise = 1}) => {
  const cells = into.cells ?? [];
  if (!into.photo && !cells.length) return null;
  const wall = !into.photo;
  return (
    <>
      <div style={{position: 'absolute', inset: 0, background: look.tone.ground}} />
      {cells.map((c, i) => {
        const up = wall ? SINE(clamp01(rise * 1.6 - (i / Math.max(1, cells.length)) * 0.6)) : 1;
        return (
          <div key={i} style={{position: 'absolute', left: c.box[0], top: c.box[1] + (1 - up) * c.box[3] * 0.6, opacity: up}}>
            <Face src={c.photo} w={c.box[2]} h={c.box[3]} place={c.place && [c.place[0] - c.box[0], c.place[1] - c.box[1], c.place[2], c.place[3]]} />
          </div>
        );
      })}
      {into.photo ? <Print look={look} beat={into} /> : null}
    </>
  );
};

/** A photograph filling a `w` x `h` face: laid at `place` (px from the face's corner) when given, else covering it.
 * The frame waits for the photograph to decode, so no frame shows the face without it. */
export const Face: React.FC<{src?: string; w: number; h: number; place?: Box; style?: CSSProperties; children?: React.ReactNode}> = ({src, w, h, place, style, children}) => (
  <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, overflow: 'hidden', ...style}}>
    {src ? (place
      ? <Img src={src} style={{position: 'absolute', left: place[0], top: place[1], width: place[2], height: place[3]}} />
      : <Img src={src} style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', objectFit: 'cover'}} />) : null}
    {children}
  </div>
);
