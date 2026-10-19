import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Photo, Scrim} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

/** The wall in miniature, filling in as the countdown goes: the tiles already counted, this one landing, the rest still empty. */
const MiniWall: React.FC<{beat: Beat; side: 'left' | 'right'}> = ({beat, side}) => {
  const {system} = useSys();
  const s = useSafe();
  const {pop} = useMotion();
  const wall: (string | null)[] = beat.data?.wall ?? [];
  const shown: number[] = beat.data?.shown ?? [];
  const me: number = beat.data?.slot ?? -1;
  const cell = 66;
  const gap = 6;
  const q = pop(10);
  return (
    <div style={{position: 'absolute', top: s.top, [side]: side === 'left' ? s.left : s.right, width: cell * 3 + gap * 2,
      display: 'grid', gridTemplateColumns: `repeat(3, ${cell}px)`, gap}}>
      {wall.map((p, i) => {
        const on = shown.includes(i);
        const now = i === me;
        return (
          <div key={i} style={{width: cell, height: cell, overflow: 'hidden', boxSizing: 'border-box',
            border: on ? (now ? `3px solid ${system.colors.accent}` : 'none') : `2px solid ${system.colors.paper}`,
            opacity: on ? (now ? q : 1) : 0.45, transform: now ? `scale(${1.5 - 0.5 * q})` : undefined, boxShadow: '0 8px 24px rgba(0,0,0,0.35)'}}>
            {on && p ? <Photo file={p} /> : null}
          </div>
        );
      })}
    </div>
  );
};

const Numeral: React.FC<{rank: number; size: number; color: string; stroke?: string; delay?: number; prefix?: string}> = ({rank, size, color, stroke, delay = 2, prefix}) => {
  const {system} = useSys();
  const {pop, tween} = useMotion();
  const p = pop(delay, system.direction === 'kinetic' ? {damping: 12, stiffness: 180} : undefined);
  return (
    <div style={{...faceStyle(system.display), fontSize: size, lineHeight: 0.8, color, WebkitTextStroke: stroke, whiteSpace: 'nowrap',
      textShadow: system.direction === 'editorial' ? '0 6px 36px rgba(0,0,0,0.5)' : undefined,
      transform: `translateY(${(1 - p) * -30}%) scale(${0.7 + 0.3 * p})`, transformOrigin: '0% 0%', opacity: tween(0, 1, delay, 6)}}>
      {prefix ? <span style={{fontSize: '0.32em', marginRight: '0.12em', verticalAlign: 'top'}}>{prefix}</span> : null}
      {rank}
    </div>
  );
};

/** One of the nine at full frame: its rank, its date, its own words and its numbers, over the photo or its clip. */
export const Countdown: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween} = useMotion();
  const t = beat.text ?? {};
  const rank: number = beat.data?.rank ?? 0;
  const d = system.direction;
  const photo = beat.photos?.[0] ?? '';
  const bg = beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={photo} treatment={d === 'editorial' ? 'parallax' : 'push'} />;

  if (d === 'editorial') {
    return (
      <AbsoluteFill style={{background: system.colors.paper}}>
        {beat.clip ? <AbsoluteFill style={{clipPath: `inset(${tween(100, 0, 0, 20)}% 0 0 0)`}}>{bg}</AbsoluteFill> : bg}
        <MiniWall beat={beat} side="left" />
        <SafeBox name="rank" justify="start" align="end">
          <Numeral rank={rank} size={system.scale.hero} color={system.colors.paper} prefix="no." />
        </SafeBox>
        <SafeBox name="countdown" justify="end">
          <Card>
            {t.kicker ? <Kicker text={t.kicker} delay={6} color={system.colors.accent} /> : null}
            {t.headline ? <Headline text={t.headline} max="h2" lines={3} delay={8} width={s.width - 2 * CARD_PAD} /> : null}
            {t.line ? <Line text={t.line} delay={16} size={system.scale.label} /> : null}
          </Card>
        </SafeBox>
      </AbsoluteFill>
    );
  }

  if (d === 'kinetic') {
    const flash = tween(1, 0, 0, 7);
    return (
      <AbsoluteFill style={{background: system.colors.bg}}>
        {bg}
        <Scrim side="both" strength={0.85} />
        <AbsoluteFill style={{background: system.colors.accent, opacity: flash}} />
        <MiniWall beat={beat} side="right" />
        <SafeBox name="rank" justify="start">
          <Numeral rank={rank} size={system.scale.hero * 1.5} color={system.colors.accent} delay={0} />
        </SafeBox>
        <SafeBox name="countdown" justify="end">
          {t.kicker ? <Kicker text={t.kicker} delay={4} color={system.colors.ink} /> : null}
          {t.headline ? <Headline text={t.headline} max="h2" lines={3} delay={5} /> : null}
          {t.line ? <Line text={t.line} delay={10} color={system.colors.accent} size={system.scale.label * 1.2} /> : null}
        </SafeBox>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{background: '#000'}}>
      {bg}
      <Leaks strength={0.9} seed={beat.id} />
      <Scrim side="both" strength={0.8} />
      <MiniWall beat={beat} side="right" />
      <SafeBox name="rank" justify="start">
        <Numeral rank={rank} size={system.scale.hero} color={system.colors.accent} prefix="#" />
      </SafeBox>
      <SafeBox name="countdown" justify="end">
        {t.kicker ? <Kicker text={t.kicker} delay={6} /> : null}
        {t.headline ? <Headline text={t.headline} max="h2" lines={3} delay={8} /> : null}
        {t.line ? <Line text={t.line} delay={16} size={system.scale.label} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
