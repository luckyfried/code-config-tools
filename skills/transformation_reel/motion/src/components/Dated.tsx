import {fitTextOnNLines} from '@remotion/layout-utils';
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Scrim} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

/**
 * The run from the first post to the latest as a line: filled up to this post's date, the milestones as marks
 * on it, this post as the dot that lands. The dot's center runs inside the line's ends, so nothing leaves the box. It fills from the previous post's place so the film reads as moving
 * forward in time.
 */
export const Rail: React.FC<{beat: Beat; color?: string; track?: string; delay?: number}> = ({beat, color, track, delay = 4}) => {
  const {system} = useSys();
  const {tween, pop} = useMotion();
  const at: number = beat.data?.progress ?? 0;
  const from: number = Math.max(0, at - 0.08);
  const ticks: number[] = beat.data?.ticks ?? [];
  const fill = tween(from, at, delay, 22, 'move');
  const dot = pop(delay + 16);
  const c = color ?? system.colors.accent;
  return (
    <div style={{position: 'relative', width: '100%', height: 26, marginTop: 30}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 11, height: 4, background: track ?? system.colors.muted, opacity: 0.55}} />
      <div style={{position: 'absolute', left: 0, top: 11, height: 4, width: `calc(13px + (100% - 26px) * ${fill})`, background: c}} />
      {ticks.map((t, i) => (
        <div key={i} style={{position: 'absolute', left: `calc((100% - 26px) * ${t} + 8px)`, top: 8, width: 10, height: 10, transform: 'rotate(45deg)',
          background: t <= fill + 0.001 ? c : system.colors.muted}} />
      ))}
      <div style={{position: 'absolute', left: `calc((100% - 26px) * ${at})`, top: 0, width: 26, height: 26, borderRadius: 13,
        background: system.colors.ink, border: `5px solid ${c}`, boxSizing: 'border-box', transform: `scale(${dot})`}} />
    </div>
  );
};

/** The count since the first post, in the display face: "day 71", "month 6". */
const Count: React.FC<{text: string; size: number; color: string; delay?: number}> = ({text, size, color, delay = 0}) => {
  const {system} = useSys();
  const s = useSafe();
  const {pop, tween} = useMotion();
  const p = pop(delay, system.direction === 'kinetic' ? {damping: 12, stiffness: 180} : undefined);
  const f = system.display;
  const fit = fitTextOnNLines({text, maxLines: 1, maxBoxWidth: s.width * 0.96, fontFamily: `'${f.family}'`, fontWeight: f.weight,
    letterSpacing: `${f.tracking}em`, textTransform: f.case === 'none' ? undefined : f.case, maxFontSize: size});
  return (
    <div style={{...faceStyle(f), fontSize: fit.fontSize, lineHeight: 0.86, color, whiteSpace: 'nowrap',
      transform: `translateY(${(1 - p) * -24}%) scale(${0.8 + 0.2 * p})`, transformOrigin: '0% 0%', opacity: tween(0, 1, delay, 6)}}>
      {text}
    </div>
  );
};

/** One post of the subject at full frame: its photo (or its clip), its date, its own words, and where it sits in the run. */
export const Dated: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween} = useMotion();
  const t = beat.text ?? {};
  const d = system.direction;
  const photo = beat.photos?.[0] ?? '';
  const milestone = Boolean(beat.data?.milestone);
  const bg = beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={photo} treatment={d === 'editorial' ? 'parallax' : beat.treatment ?? 'push'} />;

  if (d === 'editorial') {
    return (
      <AbsoluteFill style={{background: system.colors.paper}}>
        {beat.clip ? <AbsoluteFill style={{clipPath: `inset(${tween(100, 0, 0, 20)}% 0 0 0)`}}>{bg}</AbsoluteFill> : bg}
        <SafeBox name="dated" justify="end">
          <Card>
            {t.kicker ? <Kicker text={t.kicker} delay={6} color={milestone ? system.colors.accent : system.colors.ink} /> : null}
            {t.headline ? <Headline text={t.headline} max="h2" lines={3} delay={8} width={s.width - 2 * CARD_PAD} /> : null}
            {t.line ? <Line text={t.line} delay={16} size={system.scale.label} /> : null}
            <Rail beat={beat} delay={10} />
          </Card>
        </SafeBox>
      </AbsoluteFill>
    );
  }

  if (d === 'kinetic') {
    const flash = tween(milestone ? 1 : 0.6, 0, 0, 7);
    return (
      <AbsoluteFill style={{background: system.colors.bg}}>
        {bg}
        <Scrim side="both" strength={0.85} />
        <AbsoluteFill style={{background: system.colors.accent, opacity: flash}} />
        <SafeBox name="count" justify="start">
          {t.line ? <Count text={t.line} size={system.scale.h1} color={system.colors.accent} /> : null}
        </SafeBox>
        <SafeBox name="dated" justify="end">
          {t.kicker ? <Kicker text={t.kicker} delay={3} color={system.colors.ink} /> : null}
          {t.headline ? <Headline text={t.headline} max="h2" lines={3} delay={4} /> : null}
          <Rail beat={beat} delay={6} />
        </SafeBox>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{background: '#000'}}>
      {bg}
      <Leaks strength={0.8} seed={beat.id} />
      <Scrim side="both" strength={0.82} />
      <SafeBox name="stamp" justify="start">
        <div style={{...faceStyle(system.text), fontSize: system.scale.h3, color: system.colors.ink, opacity: tween(0, 1, 2, 8), whiteSpace: 'nowrap'}}>
          {t.line ?? ''}
        </div>
      </SafeBox>
      <SafeBox name="dated" justify="end">
        {t.kicker ? <Kicker text={t.kicker} delay={6} color={milestone ? system.colors.accent : system.colors.ink} /> : null}
        {t.headline ? <Headline text={t.headline} max="h2" lines={3} delay={8} /> : null}
        <Rail beat={beat} delay={8} />
      </SafeBox>
    </AbsoluteFill>
  );
};
