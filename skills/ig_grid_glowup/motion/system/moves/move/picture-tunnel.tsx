// picture-tunnel: the camera flies down a corridor walled with the film's photographs toward the beat's own, which
// waits square at the far end in the card's ground tone, the corridor fogging into that tone with depth. The flight
// slows as it nears, the corridor's slight roll comes out, and it arrives on the photograph centred and square,
// exactly where the camera holds it; then the frame goes back to the picture.
import React from 'react';
import {alpha, bezier, clamp01, hash, px} from '../kit';
import {arrivalOf, Face, landingOf, photosOf} from '../arrival';
import type {Move, MoveProps} from '../types';

/** The flight: it gathers speed out of the cut and slows into the arrival. */
const FLY = bezier([0.4, 0, 0.18, 1]);

/** Lengths of the corridor, in tiles along each wall. */
const TILES = 7;

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, seed} = p;
  const {s, land, shows} = arrivalOf(p, 1.1);
  const {box: [x, y, w, h], src, place} = landingOf(p);
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
  // each wall: where its tiles stand and how a tile turns to line the corridor; the ceiling's photographs are seen from
  // below, so they are turned the right way up
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
          <Face src={pic} w={wl.tw} h={wl.th} style={{border: `${px(look, 6)}px solid ${look.tone.rim}`, boxSizing: 'border-box', transform: k === 2 ? 'scaleY(-1)' : undefined}}>
            <div style={{position: 'absolute', inset: 0, background: alpha(ground, 0.25 + 0.75 * fog(z0 - cam + len / 2))}} />
          </Face>
        </div>,
      );
    }
  });
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', opacity: shows, background: ground,
      perspective: d, perspectiveOrigin: `${x + w / 2}px ${y + h / 2}px`}}>
      <div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d', transformOrigin: `${x + w / 2}px ${y + h / 2}px`,
        transform: `translateZ(${cam}px) rotateZ(${roll}deg)`}}>
        {tiles}
        <div style={{position: 'absolute', left: x, top: y, width: w, height: h, transform: `translateZ(${-far}px)`}}>
          <Face src={src} w={w} h={h} place={place}>
            <div style={{position: 'absolute', inset: 0, background: alpha(ground, 0.85 * fog(far - cam) * (1 - go))}} />
          </Face>
        </div>
      </div>
    </div>
  );
};

export default {Overlay} satisfies Move;
