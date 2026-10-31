// tilted-wall: the film's photographs hang on a wall without end, tipped back and turned, drifting slowly across the
// frame; the beat's photograph among them catches the light while the rest dim into the card's ground tone. The wall
// turns flat and the camera closes on that one photograph until it fills the place the camera holds it, then the frame
// goes back to the picture. Made for a best-nine or a grid beat, where the photographs are a set.
import React from 'react';
import {alpha, clamp01, hash, px, SINE} from '../kit';
import {arrivalOf, Face, landingOf, photosOf} from '../arrival';
import {spring} from '../spring';
import type {Move, MoveProps} from '../types';

/** The tiles drawn either side of the lit one, across and down. */
const ACROSS = 4, DOWN = 5;

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, seed} = p;
  const {s, land, shows} = arrivalOf(p, 1.2);
  const {box: [x, y, w, h], src, place} = landingOf(p);
  const photos = photosOf(p);
  if (shows <= 0) return null;
  // a tile has the picture box's shape, a third of the frame across
  const tw = look.W * 0.34, th = (tw * h) / w;
  const g = tw * 0.07;
  const pxx = tw + g, pyy = th + g;
  // close: tilted (0) to flat on the photograph (1), sprung to settle at the landing
  const close = clamp01(spring(s - (land - 0.6), 120, 19));
  const lit = SINE(clamp01(s / 0.35));
  const side = seed % 2 ? 1 : -1;
  // the wall drifts on a slant and comes to rest with the lit tile at the middle of the landing
  const drift = (1 - close) * (land - Math.min(s, land) + 0.25) * pxx * 1.1;
  const ox = side * drift, oy = -drift * 0.55;
  const big = w / tw;
  const mix = (a: number, b: number) => a + (b - a) * close;
  const cx = mix(look.W / 2, x + w / 2), cy = mix(look.H * 0.42, y + h / 2);
  const scale = mix(0.95, big);
  const rx = mix(40, 0), rz = mix(side * -14, 0);
  const shift = [Math.round(ox / pxx), Math.round(oy / pyy)];
  const tiles: React.ReactNode[] = [];
  for (let j = -DOWN - shift[1]; j <= DOWN - shift[1]; j++) {
    for (let i = -ACROSS - shift[0]; i <= ACROSS - shift[0]; i++) {
      const focus = i === 0 && j === 0;
      const pic = focus ? src : photos[Math.floor(Math.abs(hash(seed * 13 + i * 31 + j * 57)) * photos.length) % Math.max(1, photos.length)];
      const veil = focus ? 0 : Math.min(1, 0.6 * lit + close * 0.6);
      tiles.push(
        <div key={`${i},${j}`} style={{position: 'absolute', left: i * pxx + ox - tw / 2, top: j * pyy + oy - th / 2, width: tw, height: th,
          boxShadow: focus ? `0 0 ${px(look, 70) * lit * (1 - close)}px ${px(look, 10) * lit * (1 - close)}px ${alpha(look.tone.light, 0.7)}` : 'none'}}>
          <Face src={pic} w={tw} h={th} place={focus && place ? [place[0] / big, place[1] / big, place[2] / big, place[3] / big] : undefined}
            style={{filter: focus ? `brightness(${1 + 0.12 * lit * (1 - close)})` : undefined}}>
            {veil > 0 ? <div style={{position: 'absolute', inset: 0, background: alpha(look.tone.ground, veil)}} /> : null}
          </Face>
        </div>,
      );
    }
  }
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', opacity: shows, background: look.tone.ground,
      perspective: look.H * 1.4, perspectiveOrigin: `${cx}px ${cy}px`}}>
      <div style={{position: 'absolute', left: cx, top: cy, width: 0, height: 0, transformStyle: 'preserve-3d',
        transform: `rotateZ(${rz}deg) rotateX(${rx}deg) scale(${scale})`}}>
        {tiles}
      </div>
    </div>
  );
};

export default {Overlay} satisfies Move;
