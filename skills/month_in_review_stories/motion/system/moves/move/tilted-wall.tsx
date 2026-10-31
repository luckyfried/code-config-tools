// tilted-wall: the film's photographs hang on a wall without end, tipped back and turned, drifting slowly across the
// frame; the beat's photograph among them catches the light while the rest dim. The wall turns flat and the camera
// closes on that one photograph until it is the print exactly as the shot draws it; when the beat's photograph is one
// cell of a grid, every other cell's photograph lands in its own cell with it, and the tiles beyond the grid fade to
// the shot's own frame. Then the frame goes back to the picture. Made for a best-nine or a grid beat, where the
// photographs are a set.
import React from 'react';
import {alpha, clamp01, hash, px, SINE} from '../kit';
import {arrivalOf, Face, landingOf, photosOf, Print} from '../arrival';
import {spring} from '../spring';
import type {Move, MoveProps} from '../types';

/** The tiles drawn either side of the lit one, across and down. */
const ACROSS = 4, DOWN = 5;

/** The distance between neighbouring cells' middles across and down, from the cells of a grid around a box `w` x `h`
 * about (`cx`, `cy`); absent along an axis with no neighbour. */
export const pitchOf = (cells: {box: [number, number, number, number]}[], cx: number, cy: number, w: number, h: number) => {
  const mids = cells.map((c) => [c.box[0] + c.box[2] / 2 - cx, c.box[1] + c.box[3] / 2 - cy]);
  const across = mids.filter(([dx, dy]) => Math.abs(dy) < h / 2 && Math.abs(dx) > w / 2).map(([dx]) => Math.abs(dx));
  const down = mids.filter(([dx, dy]) => Math.abs(dx) < w / 2 && Math.abs(dy) > h / 2).map(([, dy]) => Math.abs(dy));
  return {across: across.length ? Math.min(...across) : undefined, down: down.length ? Math.min(...down) : undefined};
};

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, seed} = p;
  const {s, land, shows, bare} = arrivalOf(p, 1.2);
  const {box: [x, y, w, h]} = landingOf(p);
  const photos = photosOf(p);
  if (shows <= 0) return null;
  // a tile has the picture box's shape, a third of the frame across; at the landing the wall is `big` times its size,
  // so a wall point at (lx, ly) from the lit tile's middle lands at the box's middle plus big times that
  const tw = look.W * 0.34, th = (tw * h) / w;
  const big = w / tw;
  const bx = x + w / 2, by = y + h / 2;
  const cells = beat.cells ?? [];
  // the wall's spacing is the grid's when the beat gives its cells, so the tiles land on them
  const pitch = pitchOf(cells, bx, by, w, h);
  const pxx = (pitch.across ?? (w + tw * 0.07 * big)) / big, pyy = (pitch.down ?? (h + tw * 0.07 * big)) / big;
  // close: tilted (0) to flat on the photograph (1), sprung to settle at the landing
  const close = clamp01(spring(s - (land - 0.6), 120, 19));
  const lit = SINE(clamp01(s / 0.35));
  const side = seed % 2 ? 1 : -1;
  // the wall drifts on a slant and comes to rest with the lit tile at the middle of the landing
  const drift = (1 - close) * (land - Math.min(s, land) + 0.25) * pxx * 1.1;
  const ox = side * drift, oy = -drift * 0.55;
  const mix = (a: number, b: number) => a + (b - a) * close;
  const cx = mix(look.W / 2, bx), cy = mix(look.H * 0.42, by);
  const scale = mix(0.95, big);
  const rx = mix(40, 0), rz = mix(side * -14, 0);
  const shift = [Math.round(ox / pxx), Math.round(oy / pyy)];
  // the rest dim while the lit one shines, and come back up as they land
  const dim = 0.6 * lit * (1 - close);
  // each cell of the grid as a tile on the wall, at the place on the wall that lands on it
  const homes = cells.map((c) => ({c, lx: (c.box[0] - bx) / big, ly: (c.box[1] - by) / big, lw: c.box[2] / big, lh: c.box[3] / big}));
  const taken = (lx: number, ly: number) => homes.some((m) => lx > m.lx && lx < m.lx + m.lw && ly > m.ly && ly < m.ly + m.lh);
  const tiles: React.ReactNode[] = [];
  for (let j = -DOWN - shift[1]; j <= DOWN - shift[1]; j++) {
    for (let i = -ACROSS - shift[0]; i <= ACROSS - shift[0]; i++) {
      if (i === 0 && j === 0) continue;
      const lx = i * pxx + ox, ly = j * pyy + oy;
      if (taken(lx - ox, ly - oy)) continue;
      const pic = photos[Math.floor(Math.abs(hash(seed * 13 + i * 31 + j * 57)) * photos.length) % Math.max(1, photos.length)];
      tiles.push(
        <div key={`${i},${j}`} style={{position: 'absolute', left: lx - tw / 2, top: ly - th / 2, width: tw, height: th, opacity: 1 - close}}>
          <Face src={pic} w={tw} h={th}>
            <div style={{position: 'absolute', inset: 0, background: alpha(look.tone.ground, dim)}} />
          </Face>
        </div>,
      );
    }
  }
  homes.forEach((m, k) => {
    const place = m.c.place && ([(m.c.place[0] - m.c.box[0]) / big, (m.c.place[1] - m.c.box[1]) / big, m.c.place[2] / big, m.c.place[3] / big] as [number, number, number, number]);
    tiles.push(
      <div key={`c${k}`} style={{position: 'absolute', left: m.lx + ox, top: m.ly + oy, width: m.lw, height: m.lh}}>
        <Face src={m.c.photo} w={m.lw} h={m.lh} place={place}>
          {dim > 0 ? <div style={{position: 'absolute', inset: 0, background: alpha(look.tone.ground, dim)}} /> : null}
        </Face>
      </div>,
    );
  });
  // the lit tile is the print itself, drawn in frame px a `big`th of its size about the box's middle
  const glow = lit * (1 - close);
  tiles.push(
    <div key="lit" style={{position: 'absolute', left: ox - bx / big, top: oy - by / big, width: look.W, height: look.H,
      transformOrigin: '0 0', transform: `scale(${1 / big})`, filter: glow > 0 ? `brightness(${1 + 0.12 * glow})` : undefined}}>
      {glow > 0 ? <div style={{position: 'absolute', left: x, top: y, width: w, height: h,
        boxShadow: `0 0 ${px(look, 70) * glow * big}px ${px(look, 10) * glow * big}px ${alpha(look.tone.light, 0.7)}`}} /> : null}
      <Print look={look} beat={beat} />
    </div>,
  );
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', opacity: shows,
      perspective: look.H * 1.4, perspectiveOrigin: `${cx}px ${cy}px`}}>
      <div style={{position: 'absolute', inset: 0, background: look.tone.ground, opacity: bare}} />
      <div style={{position: 'absolute', left: cx, top: cy, width: 0, height: 0, transformStyle: 'preserve-3d',
        transform: `rotateZ(${rz}deg) rotateX(${rx}deg) scale(${scale})`}}>
        {tiles}
      </div>
    </div>
  );
};

export default {early: true, Overlay} satisfies Move;
