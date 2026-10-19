import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Scrim} from '../photo';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

const MARK: Record<string, string> = {question: '?', confession: '“', list: '1.'};

/** Their best opener line, set large over a photo or clip: the first thing the film says, in their own words. */
export const Hook: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween, pop} = useMotion();
  const t = beat.text ?? {};
  const d = system.direction;
  const mark = MARK[beat.data?.style as string] ?? '';
  const bg = beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={beat.photos?.[0] ?? ''} treatment="push" intensity={1.3} />;
  const p = pop(0, d === 'kinetic' ? {damping: 11, stiffness: 190} : undefined);
  const glyph = mark ? (
    <div style={{...faceStyle(system.display), fontSize: s.width * 0.42, lineHeight: 0.8, color: 'transparent',
      WebkitTextStroke: `4px ${system.colors.accent}`, opacity: tween(0, 0.85, 0, 10), transform: `scale(${1.3 - 0.3 * p}) rotate(${(1 - p) * -8}deg)`}}>
      {mark}
    </div>
  ) : null;
  const words = (
    <>
      {t.kicker ? <Kicker text={t.kicker} delay={4} color={system.colors.accent} /> : null}
      {t.headline ? <Headline text={t.headline} max="h1" lines={4} delay={4} width={d === 'editorial' ? s.width - 2 * CARD_PAD : undefined} /> : null}
      {t.line ? <Line text={t.line} delay={16} /> : null}
    </>
  );
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <AbsoluteFill style={{opacity: d === 'kinetic' ? 0.55 : 0.8}}>{bg}</AbsoluteFill>
      <Scrim side="both" strength={0.85} />
      {d === 'kinetic' ? <AbsoluteFill style={{background: system.colors.accent, opacity: tween(0.9, 0, 0, 6)}} /> : null}
      {glyph ? (
        <SafeBox name="hook-mark" justify="start" align="end">
          {glyph}
        </SafeBox>
      ) : null}
      <SafeBox name="hook" justify="end" align={d === 'kinetic' ? 'center' : 'start'}>
        {d === 'editorial' ? <Card>{words}</Card> : words}
      </SafeBox>
    </AbsoluteFill>
  );
};
