import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Scrim} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

/** The open quote in the accent color, set large in the display face above the line it opens. */
const Mark: React.FC<{size: number; delay?: number}> = ({size, delay = 4}) => {
  const {system} = useSys();
  const {pop, tween} = useMotion();
  const p = pop(delay);
  return (
    <div style={{...faceStyle(system.display), fontSize: size, lineHeight: 1, height: size * 0.5, marginTop: -size * 0.1, color: system.colors.accent,
      textTransform: 'none', opacity: tween(0, 1, delay, 6), transform: `translateY(${(1 - p) * 20}px)`, transformOrigin: '0% 0%'}}>
      {'“'}
    </div>
  );
};

/**
 * One person at full frame: their best photo (or its clip), who they are and when in the year they were there,
 * and a line of theirs set as type. The same beat rendered still is that person's story card.
 */
export const Portrait: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween} = useMotion();
  const t = beat.text ?? {};
  const d = system.direction;
  const photo = beat.photos?.[0] ?? '';
  const bg = beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={photo} treatment={beat.treatment ?? (d === 'editorial' ? 'parallax' : 'push')} />;

  if (d === 'editorial') {
    return (
      <AbsoluteFill style={{background: system.colors.paper}}>
        {beat.clip ? <AbsoluteFill style={{clipPath: `inset(${tween(100, 0, 0, 20)}% 0 0 0)`}}>{bg}</AbsoluteFill> : bg}
        <SafeBox name="portrait" justify="end">
          <Card>
            {t.kicker ? <Kicker text={t.kicker} delay={6} color={system.colors.accent} /> : null}
            <Mark size={system.scale.h2 * 2.2} delay={7} />
            {t.headline ? <Headline text={t.headline} max="h2" lines={4} delay={8} width={s.width - 2 * CARD_PAD} /> : null}
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
        <SafeBox name="portrait" justify="end">
          {t.kicker ? <Kicker text={t.kicker} delay={4} color={system.colors.ink} /> : null}
          <Mark size={system.scale.h2 * 2.2} delay={4} />
          {t.headline ? <Headline text={t.headline} max="h2" lines={4} delay={5} /> : null}
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
      <SafeBox name="portrait" justify="end">
        {t.kicker ? <Kicker text={t.kicker} delay={6} /> : null}
        <Mark size={system.scale.h2 * 2} delay={7} />
        {t.headline ? <Headline text={t.headline} max="h3" lines={4} delay={8} /> : null}
        {t.line ? <Line text={t.line} delay={16} size={system.scale.label} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
