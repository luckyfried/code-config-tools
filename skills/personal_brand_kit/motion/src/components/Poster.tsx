import React from 'react';
import {AbsoluteFill, Easing, interpolate} from 'remotion';
import {faceStyle, splits, useMotion, useSafe, useSys} from '../system';
import {ClipLayer} from './ClipShot';
import {CH, CW, fit, GuideCard} from './GuideCard';
import type {Beat, GuideCardData} from '../types';

/** The poster is laid out at full card size, three across and four down, and the camera moves over it. */
const G = 40;
const M = 70;
const PW = 3 * CW + 2 * G + 2 * M;
const PH = 4 * CH + 3 * G + 2 * M;
/** The header takes the first two cells; the ten cards fill the rest, left to right, top to bottom. */
const cell = (i: number) => {
  const slot = i + 2;
  return {x: M + (slot % 3) * (CW + G), y: M + Math.floor(slot / 3) * (CH + G), w: CW, h: CH};
};
const HEADER = {x: M, y: M, w: 2 * CW + G, h: CH};

type Cam = {cx: number; cy: number; sx: number; sy: number; k: number};

/** The whole guide as one poster: an establishing view, the header, each panel in turn, then the pull back. */
export const Poster: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const s = useSafe();
  const {frame, tween} = useMotion();
  const ns: number[] = beat.data?.cards ?? [];
  const deck = ns.map((n) => board.cards.find((c) => c.n === n)).filter(Boolean) as GuideCardData[];
  const header = beat.data?.header ?? {};
  const whole: Cam = {cx: PW / 2, cy: PH / 2, sx: s.W / 2, sy: s.H / 2, k: Math.min(s.W / PW, s.H / PH) * 0.94};
  const on = (r: {x: number; y: number; w: number; h: number}): Cam => ({
    cx: r.x + r.w / 2, cy: r.y + r.h / 2, sx: s.left + s.width / 2, sy: s.top + s.height / 2, k: Math.min(s.width / r.w, s.height / r.h),
  });
  const cams: Cam[] = [whole, on(HEADER), ...deck.map((_, i) => on(cell(i))), whole];
  const shots = splits(beat, cams.length);
  const ease = Easing.bezier(...system.ease.move);
  let i = 0;
  while (i < shots.length - 1 && frame >= shots[i + 1][0]) i++;
  const [start, len] = shots[i];
  const from = cams[Math.max(0, i - 1)];
  const to = cams[i];
  const t = i === 0 ? 1 : interpolate(frame, [start, start + Math.min(22, len * 0.55)], [0, 1], {easing: ease, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const lerp = (a: number, b: number) => a + (b - a) * t;
  const k = Math.exp(lerp(Math.log(from.k), Math.log(to.k)));
  const cx = lerp(from.cx, to.cx);
  const cy = lerp(from.cy, to.cy);
  const sx = lerp(from.sx, to.sx);
  const sy = lerp(from.sy, to.sy);
  const breathe = 1 + 0.015 * Math.sin((frame / 30) * 0.8);
  const kk = k * breathe;
  const lead = system.colors.swatches[0]?.hex ?? system.colors.accent;
  const fitted = fit(String(header.statement ?? ''), system.display, HEADER.w - 220, 150, 4);
  return (
    <AbsoluteFill style={{background: system.colors.bg, overflow: 'hidden'}}>
      {beat.clip ? (
        <AbsoluteFill style={{opacity: 0.55}}>
          <ClipLayer clip={beat.clip} />
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={{background: system.colors.bg, opacity: 0.35}} />
      <div style={{position: 'absolute', left: 0, top: 0, width: PW, height: PH, transformOrigin: '0 0',
        transform: `translate(${sx - cx * kk}px, ${sy - cy * kk}px) scale(${kk})`, background: system.colors.cardInk,
        boxShadow: '0 80px 200px rgba(0,0,0,0.45)'}}>
        <div style={{position: 'absolute', left: HEADER.x, top: HEADER.y, width: HEADER.w, height: HEADER.h, background: lead, padding: 110,
          display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxSizing: 'border-box'}}>
          <div style={{...faceStyle(system.text), fontSize: 46, fontWeight: 600, letterSpacing: '0.16em', textTransform: 'uppercase',
            color: system.colors.card}}>{header.handle} · brand kit</div>
          <div style={{...faceStyle(system.display), fontSize: fitted.fontSize, color: system.colors.card}}>
            {fitted.lines.map((l, j) => (
              <div key={j} style={{whiteSpace: 'nowrap'}}>{l}</div>
            ))}
          </div>
          <div style={{display: 'flex', gap: 20}}>
            {system.colors.swatches.map((w, j) => (
              <div key={j} style={{width: 150, height: 60, background: w.hex, border: `4px solid ${system.colors.card}`}} />
            ))}
          </div>
        </div>
        {deck.map((c, j) => {
          const r = cell(j);
          return (
            <div key={c.n} style={{position: 'absolute', left: r.x, top: r.y, width: CW, height: CH, opacity: tween(0, 1, 2 + j * 2, 12)}}>
              <GuideCard card={c} settled />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
