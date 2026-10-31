// picture-tunnel: the camera flies down a corridor walled with the film's photographs toward the beat's own, which
// waits at the far end in the card's ground tone, the corridor fogging into that tone with depth. The corridor's mouth
// fills the frame on the first frame and comes down onto the print's rim as the flight slows, the corridor's slight roll
// comes out, and it arrives on the print exactly as the shot draws it; then the frame goes back to the picture.
import React from 'react';
import {alpha, bezier, clamp01, hash, px, SINE} from '../kit';
import {arrivalOf, cornersOf, Face, landingOf, photosOf, Print} from '../arrival';
import type {Move, MoveProps} from '../types';

/** The flight: it gathers speed out of the cut and slows into the arrival. */
const FLY = bezier([0.4, 0, 0.18, 1]);

/** Lengths of the corridor, in tiles along each wall. */
const TILES = 7;

/** How much a `w` x `h` box about (`cx`, `cy`), turned `roll` degrees, must grow to cover the whole frame. */
export const coverOf = (W: number, H: number, cx: number, cy: number, w: number, h: number, roll: number) => {
  const a = (-roll * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return Math.max(1, ...[[0, 0], [W, 0], [W, H], [0, H]].map(([x, y]) => {
    const dx = x - cx, dy = y - cy;
    return Math.max((2 * Math.abs(dx * c - dy * s)) / w, (2 * Math.abs(dx * s + dy * c)) / h);
  }));
};

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, seed} = p;
  const {s, land, shows, bare} = arrivalOf(p, 1.1);
  const {box: [x, y, w, h]} = landingOf(p);
  const photos = photosOf(p);
  if (shows <= 0) return null;
  // the viewer stands `d` px before the frame; a tile's length along the corridor is `len`, `step` with its gap
  const d = look.H * 1.1;
  const len = Math.max(w, h) * 0.42, step = len * 1.12;
  const far = TILES * step + len * 0.4;
  const go = FLY(clamp01(s / Math.max(0.1, land)));
  const cam = far * go;
  const roll = (seed % 2 ? 1 : -1) * 7 * (1 - go);
  const fog = (depth: number) => clamp01((depth - len * 0.3) / (far * 0.75));
  const ground = look.tone.ground;
  const inset = Math.min(w, h) * 0.06;
  const cx = x + w / 2, cy = y + h / 2;
  // the corridor's mouth covers the frame at the cut and comes down to its own size by the arrival
  const grow = 1 + (coverOf(look.W, look.H, cx, cy, w, h, roll) - 1) * (1 - go) ** 1.5;
  // the print waiting down the corridor is drawn flat over it, at the size its depth alone gives it (the mouth's growth
  // never reaches it), so it starts small in the fog and grows only as the flight nears it, and the 3D compositing
  // never leaves part of it uncovered
  const size = d / (d + far - cam);
  // the corridor is seen through its mouth: the print's rim as it will land, grown and rolled with the corridor. The
  // window holds the whole frame at the cut and is the mouth from 30% of the way in, so the corridor fills the frame
  // around the flying print all the way and closes onto the print's rim exactly as it lands; it fades with the move's
  // ground over the last of the flight
  const ra = (roll * Math.PI) / 180, rc = Math.cos(ra), rs = Math.sin(ra);
  const edge = cornersOf(look, beat).map(([ex, ey]) => {
    const dx = ex - cx, dy = ey - cy;
    return [cx + grow * (dx * rc - dy * rs), cy + grow * (dx * rs + dy * rc)];
  });
  const frame = [[0, 0], [look.W, 0], [look.W, look.H], [0, look.H]];
  const shut = SINE(clamp01(go / 0.3));
  const window = frame.map(([fx, fy], i) => `${fx + (edge[i][0] - fx) * shut}px ${fy + (edge[i][1] - fy) * shut}px`).join(', ');
  // each wall: where its tiles stand and how a tile turns to line the corridor; every tile's top edge is its near edge
  // on the ceiling and its far edge on the floor, so each photograph reads the right way up from inside the corridor
  const walls = [
    {left: x, top: y + inset, tw: len, th: h - 2 * inset, origin: 'left center', turn: 'rotateY(90deg)'},
    {left: x + w - len, top: y + inset, tw: len, th: h - 2 * inset, origin: 'right center', turn: 'rotateY(-90deg)'},
    {left: x + inset, top: y, tw: w - 2 * inset, th: len, origin: 'center top', turn: 'rotateX(-90deg)'},
    {left: x + inset, top: y + h - len, tw: w - 2 * inset, th: len, origin: 'center bottom', turn: 'rotateX(90deg)'},
  ];
  const tiles: React.ReactNode[] = [];
  walls.forEach((wl, k) => {
    for (let i = 0; i < TILES; i++) {
      const z0 = i * step + (k % 2) * step * 0.5;
      const near = cam - z0;
      // a tile the viewer has flown past is gone; one about to pass fades so it never fills the frame
      if (near > d * 0.6) continue;
      const pass = 1 - clamp01((near - d * 0.25) / (d * 0.35));
      const pic = photos[Math.floor(Math.abs(hash(seed * 31 + k * 7 + i)) * photos.length) % Math.max(1, photos.length)];
      tiles.push(
        <div key={`${k}-${i}`} style={{position: 'absolute', left: wl.left, top: wl.top, width: wl.tw, height: wl.th,
          transformOrigin: wl.origin, transform: `translateZ(${-z0}px) ${wl.turn}`, opacity: pass}}>
          <Face src={pic} w={wl.tw} h={wl.th} style={{border: `${px(look, 6)}px solid ${look.tone.rim}`, boxSizing: 'border-box'}}>
            <div style={{position: 'absolute', inset: 0, background: alpha(ground, 0.25 + 0.75 * fog(z0 - cam + len / 2))}} />
          </Face>
        </div>,
      );
    }
  });
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', opacity: shows}}>
      <div style={{position: 'absolute', inset: 0, background: ground, opacity: bare}} />
      <div style={{position: 'absolute', inset: 0, background: ground, clipPath: `polygon(${window})`, opacity: bare}}>
        <div style={{position: 'absolute', inset: 0, transformOrigin: `${cx}px ${cy}px`, transform: `scale(${grow})`,
          perspective: d, perspectiveOrigin: `${cx}px ${cy}px`}}>
          <div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d', transformOrigin: `${cx}px ${cy}px`,
            transform: `translateZ(${cam}px) rotateZ(${roll}deg)`}}>
            {tiles}
          </div>
        </div>
      </div>
      <div style={{position: 'absolute', inset: 0, transformOrigin: `${cx}px ${cy}px`, transform: `scale(${size}) rotate(${roll}deg)`}}>
        <Print look={look} beat={beat} veil={0.85 * fog(far - cam) * (1 - go)} />
      </div>
    </div>
  );
};

export default {early: true, Overlay} satisfies Move;
