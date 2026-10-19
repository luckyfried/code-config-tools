import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Scrim} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

const Swatches: React.FC<{delay: number; height?: number}> = ({delay, height = 14}) => {
  const {system} = useSys();
  const {tween} = useMotion();
  return (
    <div style={{display: 'flex', gap: 10, width: '100%', marginTop: 36}}>
      {system.colors.swatches.slice(0, 5).map((s, i) => (
        <div key={i} style={{flex: 1, height, background: s.hex, transformOrigin: '0 50%', transform: `scaleX(${tween(0, 1, delay + i * 4, 18)})`}} />
      ))}
    </div>
  );
};

const Background: React.FC<{beat: Beat}> = ({beat}) =>
  beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={beat.photos?.[0] ?? ''} treatment={beat.treatment ?? 'push'} />;

export const Opener: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const s = useSafe();
  const {tween, pop, frame} = useMotion();
  const t = beat.text ?? {};
  const mark = (board.handle.match(/[a-z0-9]/gi) ?? ['A']).slice(0, 2).join('').toUpperCase();
  const title = t.headline ?? 'brand kit';
  const d = system.direction;

  if (d === 'kinetic') {
    const grow = pop(4, {damping: 14});
    return (
      <AbsoluteFill style={{background: system.colors.accent}}>
        <AbsoluteFill
          style={{
            clipPath: `inset(${(1 - grow) * 38}% ${(1 - grow) * 30}% ${(1 - grow) * 38}% ${(1 - grow) * 30}% round ${(1 - grow) * 60}px)`,
          }}
        >
          <Background beat={beat} />
          <AbsoluteFill style={{background: system.colors.bg, opacity: 0.35}} />
        </AbsoluteFill>
        <AbsoluteFill style={{justifyContent: 'flex-start', alignItems: 'center', paddingTop: s.top + s.height * 0.08}}>
          <div style={{display: 'flex', ...faceStyle(system.display), fontSize: s.width / 2.6, color: system.colors.ink, lineHeight: 0.85}}>
            {mark.split('').map((ch, i) => {
              const p = pop(10 + i * 3);
              return (
                <span key={i} style={{display: 'inline-block', transform: `translateY(${(1 - p) * 60}%) scale(${0.4 + 0.6 * p})`, opacity: Math.min(1, p * 2)}}>
                  {ch}
                </span>
              );
            })}
          </div>
        </AbsoluteFill>
        <SafeBox name="opener" justify="end" align="center">
          <Kicker text={t.kicker ?? `@${board.handle}`} delay={20} color={system.colors.ink} />
          {t.headline ? <Headline text={t.headline} max="h2" lines={2} delay={24} /> : null}
          <Swatches delay={30} height={18} />
        </SafeBox>
      </AbsoluteFill>
    );
  }

  if (d === 'documentary') {
    const rec = Math.floor(frame / 15) % 2 === 0;
    return (
      <AbsoluteFill style={{background: '#000'}}>
        <Background beat={beat} />
        <Leaks strength={1.2} seed="opener" />
        <Scrim side="both" strength={0.9} />
        <SafeBox name="opener-top" justify="start">
          <div style={{...faceStyle(system.text), fontSize: system.scale.label, color: system.colors.ink, display: 'flex', gap: 18, alignItems: 'center', opacity: tween(0, 1, 6, 10)}}>
            <span style={{width: 20, height: 20, borderRadius: 10, background: system.colors.accent, opacity: rec ? 1 : 0.25}} />
            {t.kicker ?? `@${board.handle}`}
          </div>
        </SafeBox>
        <SafeBox name="opener" justify="end">
          <Kicker text={`@${board.handle}`} delay={6} color={system.colors.accent} />
          <Headline text={title} max="hero" lines={2} delay={8} />
          {t.line ? <Line text={t.line} delay={18} /> : null}
          <Swatches delay={22} />
        </SafeBox>
      </AbsoluteFill>
    );
  }

  const r = tween(0, 1, 0, 24);
  return (
    <AbsoluteFill style={{background: system.colors.paper}}>
      <AbsoluteFill style={{clipPath: `inset(0 0 ${(1 - r) * 100}% 0)`}}>
        <Background beat={beat} />
      </AbsoluteFill>
      <SafeBox name="opener" justify="end">
        <Card>
          <Kicker text={t.kicker ?? `@${board.handle}`} delay={6} color={system.colors.ink} />
          <Headline text={title} max="hero" lines={2} delay={8} width={s.width - 2 * CARD_PAD} />
          {t.line ? <Line text={t.line} delay={18} /> : null}
          <Swatches delay={24} height={10} />
        </Card>
      </SafeBox>
    </AbsoluteFill>
  );
};
