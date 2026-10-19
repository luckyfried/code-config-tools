import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Scrim} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

/** The chapters as segments: the ones behind filled, this one filling, the ones ahead empty. */
const Segments: React.FC<{n: number; of: number; delay?: number}> = ({n, of, delay = 6}) => {
  const {system} = useSys();
  const {tween} = useMotion();
  return (
    <div style={{display: 'flex', gap: 10, width: '100%', marginTop: 34}}>
      {Array.from({length: of}, (_, i) => (
        <div key={i} style={{flex: 1, height: 8, background: system.colors.muted, position: 'relative', overflow: 'hidden'}}>
          <div style={{position: 'absolute', inset: 0, background: system.colors.accent, transformOrigin: '0 50%',
            transform: `scaleX(${i < n - 1 ? 1 : i === n - 1 ? tween(0, 1, delay, 24) : 0})`}} />
        </div>
      ))}
    </div>
  );
};

/** The chapter's number, outlined and huge, settling from a slam. */
const ChapterNumber: React.FC<{n: number; size: number}> = ({n, size}) => {
  const {system} = useSys();
  const {pop, tween} = useMotion();
  const p = pop(0, system.direction === 'kinetic' ? {damping: 11, stiffness: 200} : undefined);
  return (
    <div style={{...faceStyle(system.display), fontSize: size, lineHeight: 0.8, color: 'transparent', WebkitTextStroke: `4px ${system.colors.ink}`,
      whiteSpace: 'nowrap', transform: `scale(${1.6 - 0.6 * p})`, transformOrigin: '0% 0%', opacity: tween(0, 1, 0, 5)}}>
      {String(n).padStart(2, '0')}
    </div>
  );
};

/**
 * A chapter card: one milestone of the run (or day one, or now) with the caption they wrote that day on screen
 * as the narration, over that day's photo.
 */
export const Chapter: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween} = useMotion();
  const t = beat.text ?? {};
  const n: number = beat.data?.n ?? 1;
  const of: number = beat.data?.of ?? 1;
  const d = system.direction;
  const photo = beat.photos?.[0] ?? '';
  const bg = beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={photo} treatment={beat.treatment ?? (d === 'editorial' ? 'parallax' : 'push')} />;

  if (d === 'editorial') {
    return (
      <AbsoluteFill style={{background: system.colors.paper}}>
        {bg}
        <SafeBox name="number" justify="start">
          <ChapterNumber n={n} size={system.scale.hero} />
        </SafeBox>
        <SafeBox name="chapter" justify="end">
          <Card>
            {t.kicker ? <Kicker text={t.kicker} delay={6} /> : null}
            {t.headline ? <Headline text={t.headline} max="h2" lines={4} delay={10} width={s.width - 2 * CARD_PAD} /> : null}
            <Segments n={n} of={of} delay={12} />
          </Card>
        </SafeBox>
      </AbsoluteFill>
    );
  }

  const shade = d === 'kinetic' ? 0.55 : 0.35;
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {bg}
      <AbsoluteFill style={{background: system.colors.bg, opacity: tween(0.85, shade, 0, 18)}} />
      {d === 'documentary' ? <Leaks strength={0.8} seed={beat.id} /> : null}
      <Scrim side="bottom" strength={0.85} />
      <SafeBox name="number" justify="start">
        <ChapterNumber n={n} size={system.scale.hero * (d === 'kinetic' ? 1.25 : 1)} />
      </SafeBox>
      <SafeBox name="chapter" justify="end">
        {t.kicker ? <Kicker text={t.kicker} delay={4} color={system.colors.accent} /> : null}
        {t.headline ? <Headline text={t.headline} max="h2" lines={4} delay={6} /> : null}
        <Segments n={n} of={of} delay={8} />
      </SafeBox>
    </AbsoluteFill>
  );
};
