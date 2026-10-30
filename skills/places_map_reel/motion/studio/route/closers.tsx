// The places film's three closers, each the map resolving into the style's last frame with the map showing through a
// window the board leaves open on it (scripts/board_drive.py closer_window) and every word set inside the type-safe
// area around the window: a poster on the grid (swiss-grid), a title card between the letterbox bars
// (cinematic-letterbox), and the book's cover closing over the page, the map through its die-cut window (scrapbook).
// Each one is the card's own end card (system/moves/closer) with the map in it: the same ground, ink, faces and order of
// title, line and handle. Every color is a tone or a role of the card and every face the card's.
import React, {createContext, useContext} from 'react';
import {register, type CloserProps} from '../../system/moves';
import {alpha, balance, fill, fitTo, inkOn, land, OUT, SINE, SNAP, span, Words} from '../../system/moves/kit';
import type {Box} from './plan';

/** The window the closer leaves open on the map, [x, y, w, h] frame px, and the top and bottom of the type-safe area
 * inside any letterbox bar. */
export const CloserFrame = createContext<{window: Box; top: number; bottom: number}>({window: [0, 0, 0, 0], top: 0, bottom: 0});

/** Frame px for `v` px of a 1080 px short side: the closers' words scale with the frame's short side, so a 16:9 frame
 * sets them at the size a vertical one does. */
const short = (look: {W: number; H: number}) => (v: number) => (v * Math.min(look.W, look.H)) / 1080;

/** The closing line, the places in the order they were reached, in as few balanced rows as hold it at `size` and
 * `weight` across `width` px, three at most. */
const rowsOf = (text: string, family: string, width: number, size: number, weight = 400) => {
  for (let n = 1; n < 3; n++) {
    const rows = balance(text, n);
    if (fitTo(rows, family, width, {weight}) >= size) return rows;
  }
  return balance(text, 3);
};

/** swiss-grid: the card's ground closes in around the map from above and below on the grid's snap, a heavy rule in the
 * ink snapping across the measure over the map's cell, the title set big, bold and flush left over it in the display
 * face with the closing line under it in the text face, and at the foot the handle on the left and one block of the
 * card's accent filling the grid's last column on the right. */
const Poster: React.FC<CloserProps> = ({look, local}) => {
  const u = short(look);
  const {window: [x, y, w, h], top} = useContext(CloserFrame);
  const m = look.grid.m;
  const measureW = look.W - 2 * m;
  const k = span(local, 0, 0.45, SNAP);
  const ground = look.tone.ground;
  const ink = inkOn(ground, [look.colors.ink, look.colors.paper]);
  const title = look.title || look.signoff;
  const lines = balance(title, title.length > 12 ? 2 : 1);
  const ruleH = u(18), ruleY = y - u(30) - ruleH;
  const said = look.title ? rowsOf(look.signoff, look.text, measureW, u(30)) : [];
  const saidSize = said.length ? Math.min(u(30), fitTo(said, look.text, measureW)) : 0;
  const saidTall = said.length ? said.length * saidSize * 1.25 : 0;
  const foot = ruleY - u(30) - saidTall - (said.length ? u(18) : 0);
  const size = Math.min(fitTo(lines, look.display, measureW, {weight: 700, tracking: -0.035, most: u(250)}), (foot - top - u(10)) / (lines.length * 0.95));
  const col = (look.grid.cols[look.grid.cols.length - 1] - look.grid.cols[0]) / (look.grid.cols.length - 1);
  const low = y + h + u(40);
  const lowH = Math.min(u(220), look.H - low - m);
  // the ground is one sheet with the window cut out of it, the cut closing from the frame's edges onto the window
  const [l, t, r, b] = [x * k, y * k, look.W - (look.W - x - w) * k, look.H - (look.H - y - h) * k];
  const hole = `${l}px ${t}px, ${l}px ${b}px, ${r}px ${b}px, ${r}px ${t}px, ${l}px ${t}px`;
  return (
    <div style={fill}>
      <div style={{...fill, background: ground, clipPath: `polygon(evenodd, 0 0, ${look.W}px 0, ${look.W}px ${look.H}px, 0 ${look.H}px, 0 0, ${hole})`}} />
      <div style={{position: 'absolute', left: x, top: y, width: w, height: h, boxShadow: `inset 0 0 0 ${u(3)}px ${ink}`, opacity: span(local, 0.3, 0.3)}} />
      <div style={{position: 'absolute', left: m, top: ruleY, width: measureW * span(local, 0.25, 0.4, SNAP), height: ruleH, background: ink}} />
      <Words text={lines.join('\n')} family={look.display} size={size} color={ink}
        style={{position: 'absolute', left: m - size * 0.04, right: m, bottom: look.H - foot, lineHeight: 0.95, fontWeight: 700, letterSpacing: '-0.035em',
          whiteSpace: 'pre', clipPath: `inset(${(1 - span(local, 0.35, 0.35, SNAP)) * 100}% 0 0 0)`}} />
      {said.length ? <Words text={said.join('\n')} family={look.text} size={saidSize} color={ink}
        style={{position: 'absolute', left: m, right: m, top: ruleY - u(30) - saidTall, lineHeight: 1.25, whiteSpace: 'pre', opacity: span(local, 0.6, 0.3)}} /> : null}
      {look.handle && lowH > u(40) ? <Words text={look.handle} family={look.text} size={u(32)} color={ink}
        style={{position: 'absolute', left: m, top: low, opacity: span(local, 0.7, 0.3)}} /> : null}
      {lowH > u(40) ? <div style={{position: 'absolute', left: look.W - m - col, top: low, width: col, height: lowH,
        background: look.colors.accent, transform: `scaleY(${span(local, 0.55, 0.5, OUT)})`, transformOrigin: 'top'}} /> : null}
      {look.handle && lowH <= u(40) ? <Words text={look.handle} family={look.text} size={u(28)} color={ink}
        style={{position: 'absolute', right: m, top: ruleY - u(30) - u(28) * 1.25, opacity: span(local, 0.7, 0.3)}} /> : null}
    </div>
  );
};

// the title card's weights, the ones a phone holds over the dark: the title in the display face's semibold, the places
// and the handle in the text face's medium (the card's own text weight is a light that thins out at phone size)
const TITLE_WEIGHT = 600;
const TEXT_WEIGHT = 500;

/** cinematic-letterbox: the frame dims to the card's matte around the map's band until only the band shows, the
 * title comes up out of the dark above it in the display face's capitals, widely spaced, the places under it in the
 * text face's italic, and the handle as the film's credit centered under the band, or under the places where the frame
 * leaves no room below the band; every word in the tone that reads on the matte. */
const TitleCard: React.FC<CloserProps> = ({look, local}) => {
  const {window: [x, y, w, h], top, bottom} = useContext(CloserFrame);
  const dark = span(local, 0, 1.1, SINE);
  const title = (look.title || look.signoff).toUpperCase();
  const u = short(look);
  const side = u(100), room = look.W - 2 * side;
  const ink = inkOn(look.tone.matte, [look.colors.paper, look.tone.light, look.colors.ink]);
  const lines = balance(title, title.length > 16 ? 2 : 1);
  const said = look.title ? rowsOf(look.signoff, look.text, room * 0.9, u(36), TEXT_WEIGHT) : [];
  // the title, the places and the handle stand in one column between the safe top and the band, shrunk together when
  // the frame is short (16:9 and square) so no line reaches the map
  const want = {title: Math.min(u(120), fitTo(lines, look.display, room, {weight: TITLE_WEIGHT, tracking: 0.14})),
    said: said.length ? Math.min(u(40), fitTo(said, look.text, room * 0.9, {weight: TEXT_WEIGHT})) : 0, handle: u(30)};
  const gaps = [u(30), u(26)];
  const credit = Boolean(look.handle) && bottom - (y + h) > want.handle * 1.2 + u(120);
  const tall = lines.length * want.title * 1.05 + (said.length ? said.length * want.said * 1.2 + gaps[0] : 0) + (look.handle && !credit ? want.handle * 1.1 + gaps[1] : 0);
  const space = y - top - u(40);
  const k = Math.min(1, space / tall);
  const size = want.title * k, saidSize = want.said * k, hand = want.handle * k;
  const t0 = top + Math.max(u(12), (space - tall * k) / 2);
  const t1 = t0 + lines.length * size * 1.05 + gaps[0] * k;
  const t2 = (said.length ? t1 + said.length * saidSize * 1.2 : t0 + lines.length * size * 1.05) + gaps[1] * k;
  const field = look.tone.matte;
  const push = 1 + 0.03 * span(local, 0.5, 2, OUT);
  return (
    <div style={fill}>
      <div style={{position: 'absolute', left: x, top: y, width: w, height: h, boxShadow: `0 0 0 6000px ${field}`, opacity: dark}} />
      <div style={{position: 'absolute', left: x, top: y, width: w, height: h, boxShadow: `inset 0 0 ${u(90)}px ${u(30)}px ${alpha(field, 0.9)}`, opacity: dark}} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: y, transform: `scale(${push})`, transformOrigin: '50% 60%'}}>
        <Words text={lines.join('\n')} family={look.display} size={size} color={ink}
          style={{position: 'absolute', left: side - size * 0.07, right: side - size * 0.07, top: t0, lineHeight: 1.05, textAlign: 'center', letterSpacing: '0.14em',
            fontWeight: TITLE_WEIGHT, whiteSpace: 'pre', opacity: span(local, 0.5, 0.9, SINE)}} />
        {said.length ? <Words text={said.join('\n')} family={look.text} size={saidSize} color={ink}
          style={{position: 'absolute', left: side, right: side, top: t1, lineHeight: 1.2, textAlign: 'center', whiteSpace: 'pre', fontWeight: TEXT_WEIGHT,
            fontStyle: look.italic ? 'italic' : 'normal', opacity: 0.88 * span(local, 0.9, 0.8, SINE)}} /> : null}
        {look.handle && !credit ? <Words text={look.handle} family={look.text} size={hand} color={ink}
          style={{position: 'absolute', left: 0, right: 0, top: t2, textAlign: 'center', letterSpacing: '0.2em', fontWeight: TEXT_WEIGHT, opacity: 0.85 * span(local, 1.2, 0.8, SINE)}} /> : null}
      </div>
      {credit ? <Words text={look.handle} family={look.text} size={want.handle} color={ink}
        style={{position: 'absolute', left: 0, right: 0, top: y + h + Math.min(u(110), (bottom - y - h - want.handle) / 2), textAlign: 'center',
          letterSpacing: '0.2em', fontWeight: TEXT_WEIGHT, opacity: 0.85 * span(local, 1.2, 0.8, SINE)}} /> : null}
    </div>
  );
};

/** scrapbook: the page closes in around the map in the card's ground, then the book's cloth cover, in whichever of the
 * card's accents stands furthest from the page, swings shut over it from the right and lands with a little bounce, a
 * ruled inset round its edge and another round the die-cut window the map shows through, the title written large
 * across the cover over the window in the display face under the handle, set at the cover's head the way an author's name
 * is, and the places under the window in the text face. */
const BookCover: React.FC<CloserProps> = ({look, local}) => {
  const u = short(look);
  const {window: [x, y, w, h], top} = useContext(CloserFrame);
  const page = look.tone.ground;
  const cover = inkOn(page, [look.colors.accent, look.colors.accent2]);
  const ink = inkOn(cover, [look.colors.paper, look.colors.ink, page]);
  const pageIn = span(local, 0, 0.3);
  const k = land(Math.max(0, local - 0.25) * 0.9);
  const m = u(48), inset = u(30);
  const panel: Box = [m, Math.max(u(24), top - u(70)), look.W - 2 * m, 0];
  // on a wide or square frame the cover runs as far below as it stands from the top, so it sits in the middle; on a
  // tall frame it ends under the places, above the caption's band
  const foot = look.H > look.W ? y + h + u(190) : Math.max(y + h + u(190), look.H - panel[1]);
  panel[3] = Math.min(look.H - u(24), foot) - panel[1];
  const title = look.title || look.signoff;
  const lines = balance(title, title.length > 14 ? 2 : 1);
  const inner = panel[2] - 4 * inset;
  const hand = u(32), handTop = inset + u(34);
  const roomUp = y - panel[1] - inset - u(40) - (look.handle ? hand * 1.2 + u(34) : 0);
  const size = Math.min(fitTo(lines, look.display, inner, {most: u(200)}), roomUp / (lines.length * 1.02));
  const said = look.title ? rowsOf(look.signoff, look.text, inner, u(36)) : [];
  const saidSize = said.length ? Math.min(u(36), fitTo(said, look.text, inner)) : 0;
  // the places stand in the middle of the cover between the window's rule and the inset's
  const below = panel[3] - inset - (y + h - panel[1] + u(20));
  const saidTop = y + h - panel[1] + u(20) + (below - said.length * saidSize * 1.25) / 2;
  const r = u(26);
  return (
    <div style={fill}>
      <div style={{position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: r, boxShadow: `0 0 0 6000px ${page}`, opacity: pageIn}} />
      <div style={{position: 'absolute', left: panel[0], top: panel[1], width: panel[2], height: panel[3], borderRadius: u(18), overflow: 'hidden',
        boxShadow: `0 ${u(20)}px ${u(50)}px ${alpha(look.tone.matte, 0.3)}`, transformOrigin: 'left center',
        transform: `translateX(${(1 - k) * look.W * 0.9}px) rotate(${(1 - k) * 7}deg)`, opacity: local > 0.25 ? 1 : 0}}>
        <div style={{position: 'absolute', left: x - panel[0], top: y - panel[1], width: w, height: h, borderRadius: r, boxShadow: `0 0 0 6000px ${cover}`}} />
        <div style={{position: 'absolute', left: inset, right: inset, top: inset, bottom: inset, border: `${u(5)}px solid ${ink}`, borderRadius: u(8), opacity: 0.8}} />
        <div style={{position: 'absolute', left: x - panel[0] - u(16), top: y - panel[1] - u(16), width: w + u(32), height: h + u(32),
          borderRadius: r + u(12), border: `${u(4)}px solid ${ink}`, opacity: 0.8}} />
        <Words text={lines.join('\n')} family={look.display} size={size} color={ink}
          style={{position: 'absolute', left: 2 * inset, right: 2 * inset, bottom: panel[3] - (y - panel[1]) + u(36), lineHeight: 1.02, textAlign: 'center',
            whiteSpace: 'pre', transform: 'rotate(-2deg)'}} />
        {said.length && below > said.length * saidSize * 1.25 + u(16) ? <Words text={said.join('\n')} family={look.text} size={saidSize} color={ink}
          style={{position: 'absolute', left: 2 * inset, right: 2 * inset, top: saidTop, lineHeight: 1.25, textAlign: 'center', whiteSpace: 'pre',
            opacity: 0.92 * span(local, 1, 0.5)}} /> : null}
        {look.handle ? <Words text={look.handle} family={look.text} size={hand} color={ink}
          style={{position: 'absolute', left: 0, right: 0, top: handTop, textAlign: 'center', letterSpacing: '0.12em', opacity: span(local, 1.1, 0.5)}} /> : null}
      </div>
    </div>
  );
};

/** The kit's closers under its own names: a board names `places_map_reel/<the card's closer>`. */
export const KIT = 'places_map_reel/';
const CLOSERS = {poster: Poster, 'title-card': TitleCard, 'book-cover': BookCover};
let registered = false;
export const registerClosers = () => {
  if (registered) return;
  registered = true;
  for (const [name, shape] of Object.entries(CLOSERS)) register('closer', KIT + name, shape);
};
