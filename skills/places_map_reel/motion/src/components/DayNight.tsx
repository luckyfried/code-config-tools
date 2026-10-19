import React from 'react';
import {AbsoluteFill, interpolate, random, useVideoConfig} from 'remotion';
import {useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {LivePhoto, Scrim} from '../photo';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

/** The sky across one day, 0 (before dawn) to 1 (night): its color, how strong it lies over the photo, how dark. */
const STOPS = [0, 0.1, 0.22, 0.4, 0.58, 0.7, 0.8, 0.9, 1];
const SKY = ['#1d2a5c', '#e98a6b', '#f6c48f', '#fff6e0', '#ffe2a8', '#f09a3e', '#8a4f86', '#24305e', '#070b1c'];
const TINT = [0.55, 0.42, 0.22, 0.04, 0.1, 0.34, 0.46, 0.5, 0.58];
const DARK = [0.42, 0.16, 0.04, 0, 0, 0.06, 0.2, 0.42, 0.58];

const lerpHex = (a: string, b: string, t: number) => {
  const p = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, '0')).join('');
};

const skyAt = (p: number) => {
  const i = Math.max(0, Math.min(STOPS.length - 2, STOPS.findIndex((s, k) => p >= s && p <= STOPS[k + 1])));
  const t = (p - STOPS[i]) / (STOPS[i + 1] - STOPS[i]);
  return {
    color: lerpHex(SKY[i], SKY[i + 1], t),
    tint: TINT[i] + (TINT[i + 1] - TINT[i]) * t,
    dark: DARK[i] + (DARK[i + 1] - DARK[i]) * t,
  };
};

/**
 * One place at one hour of the year's long day: their reel or their photo, the sky's color laid over it, the sun
 * (or the moon) crossing the top of the frame, the stars once it is night, and a bar across the top that shows
 * where in the day this place falls.
 */
export const DayNight: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const {width: W, height: H} = useVideoConfig();
  const s = useSafe();
  const {frame, duration} = useMotion();
  const d = beat.data ?? {};
  const [p0, p1] = (d.phase ?? [0.5, 0.55]) as [number, number];
  const p = interpolate(Math.min(frame, duration), [0, duration], [p0, p1], {extrapolateRight: 'clamp'});
  const sky = skyAt(p);
  const t = beat.text ?? {};
  const sunT = interpolate(p, [0.04, 0.82], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const moonT = interpolate(p, [0.74, 1.05], [0, 0.7], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const arcY = (u: number) => s.top + 330 - Math.sin(u * Math.PI) * 260;
  const sunX = 80 + sunT * (W - 160);
  const showSun = p < 0.86;
  const moonX = 80 + moonT * (W - 160);
  const night = interpolate(p, [0.76, 0.9], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const stars = Array.from({length: 60}, (_, i) => {
    const x = random(`sx${i}`) * W;
    const y = random(`sy${i}`) * H * 0.42;
    const r = 1 + random(`sr${i}`) * 2.4;
    const tw = 0.55 + 0.45 * Math.sin(frame * 0.25 + i);
    return <circle key={i} cx={x} cy={y} r={r} fill="#fff8e8" opacity={night * tw * 0.9} />;
  });
  const sunColor = lerpHex('#ffd27a', '#ff7a3c', interpolate(p, [0.4, 0.8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  return (
    <AbsoluteFill style={{background: system.colors.bg, overflow: 'hidden'}}>
      {beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={beat.photos?.[0] ?? ''} treatment="push" />}
      <AbsoluteFill style={{background: `linear-gradient(to bottom, ${sky.color} 0%, ${sky.color} 30%, rgba(0,0,0,0) 85%)`, mixBlendMode: 'soft-light', opacity: Math.min(1, sky.tint * 2)}} />
      <AbsoluteFill style={{background: sky.color, mixBlendMode: 'multiply', opacity: sky.tint * 0.7}} />
      <AbsoluteFill style={{background: '#050818', opacity: sky.dark}} />
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
        <defs>
          <radialGradient id={`sun-${beat.id}`}>
            <stop offset="0%" stopColor={sunColor} stopOpacity={0.95} />
            <stop offset="35%" stopColor={sunColor} stopOpacity={0.5} />
            <stop offset="100%" stopColor={sunColor} stopOpacity={0} />
          </radialGradient>
        </defs>
        {stars}
        {showSun ? (
          <g opacity={interpolate(p, [0.78, 0.86], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
            <circle cx={sunX} cy={arcY(sunT)} r={190} fill={`url(#sun-${beat.id})`} />
            <circle cx={sunX} cy={arcY(sunT)} r={46} fill={sunColor} />
          </g>
        ) : null}
        {p > 0.74 ? (
          <g opacity={night}>
            <circle cx={moonX} cy={arcY(moonT)} r={40} fill="#f4ecd8" />
            <circle cx={moonX + 16} cy={arcY(moonT) - 10} r={36} fill={lerpHex(sky.color, '#050818', 0.6)} />
          </g>
        ) : null}
        <line x1={s.left} x2={W - s.left} y1={s.top - 40} y2={s.top - 40} stroke="#ffffff" strokeOpacity={0.35} strokeWidth={3} />
        <line x1={s.left} x2={s.left + (W - 2 * s.left) * p} y1={s.top - 40} y2={s.top - 40} stroke={system.colors.accent} strokeWidth={5} strokeLinecap="round" />
        <circle cx={s.left + (W - 2 * s.left) * p} cy={s.top - 40} r={10} fill={p > 0.8 ? '#f4ecd8' : sunColor} />
      </svg>
      <Scrim side="bottom" strength={0.78} />
      <SafeBox name="day" justify="end">
        {t.kicker ? <Kicker text={t.kicker} delay={4} /> : null}
        {t.headline ? <Headline text={t.headline} max="h1" lines={1} delay={6} /> : null}
        {t.line ? <Line text={t.line} delay={14} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
