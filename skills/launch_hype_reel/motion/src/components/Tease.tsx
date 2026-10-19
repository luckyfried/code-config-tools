import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Photo, Scrim} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

/**
 * The product behind a mask that opens from data.from to data.to (0 hidden, 1 whole). Editorial opens a slit,
 * kinetic opens bars, documentary opens an iris; below half open the product stays out of focus, so a tease
 * shows its color and shape and never the thing itself.
 */
export const Tease: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween} = useMotion();
  const t = beat.text ?? {};
  const d = system.direction;
  const from: number = beat.data?.from ?? 0;
  const to: number = beat.data?.to ?? 1;
  const open = tween(from, to, 0, Math.max(8, beat.frames * 0.7), 'move');
  const blur = Math.max(0, 0.6 - open) * 40;
  const photo = beat.photos?.[0] ?? '';
  const inner = beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={photo} treatment="push" />;
  const focus = <AbsoluteFill style={{filter: blur > 0.2 ? `blur(${blur}px) saturate(1.15)` : undefined}}>{inner}</AbsoluteFill>;

  let mask: React.ReactNode;
  if (d === 'kinetic') {
    const bars = 6;
    mask = (
      <AbsoluteFill style={{flexDirection: 'row'}}>
        {Array.from({length: bars}, (_, i) => {
          const k = Math.min(1, Math.max(0, open * 1.25 - (i % 2) * 0.12));
          return (
            <div key={i} style={{flex: 1, position: 'relative', overflow: 'hidden'}}>
              <div style={{position: 'absolute', inset: 0, clipPath: `inset(${(1 - k) * 50}% 0 ${(1 - k) * 50}% 0)`}}>
                <div style={{position: 'absolute', top: 0, height: '100%', width: `${bars * 100}%`, left: `${-i * 100}%`}}>{focus}</div>
              </div>
            </div>
          );
        })}
      </AbsoluteFill>
    );
  } else if (d === 'documentary') {
    const r = 4 + open * 76;
    mask = <AbsoluteFill style={{clipPath: `circle(${r}% at 50% 44%)`}}>{focus}</AbsoluteFill>;
  } else {
    const h = (1 - open) * 50;
    mask = <AbsoluteFill style={{clipPath: `inset(${h}% 0 ${h}% 0)`}}>{focus}</AbsoluteFill>;
  }

  const ghost = open < 1 ? (
    <AbsoluteFill style={{opacity: 0.18, filter: 'blur(60px) saturate(1.3)'}}>
      <Photo file={photo} />
    </AbsoluteFill>
  ) : null;
  const words = (
    <>
      {t.kicker ? <Kicker text={t.kicker} delay={6} color={d === 'kinetic' ? system.colors.accent : d === 'documentary' ? system.colors.ink : undefined} /> : null}
      {t.headline ? <Headline text={t.headline} max={open >= 1 ? 'hero' : 'h1'} lines={2} delay={10} width={d === 'editorial' ? s.width - 2 * CARD_PAD : undefined} /> : null}
      {t.line ? <Line text={t.line} delay={18} /> : null}
    </>
  );
  // Off a card the words sit over the product's lightest part, partly above the scrim's reach, so they carry a shadow.
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {ghost}
      {mask}
      <Leaks strength={0.8} seed={beat.id} />
      {(t.headline || t.kicker) && d !== 'editorial' ? <Scrim side="bottom" strength={0.85} /> : null}
      {t.headline || t.kicker ? (
        <SafeBox name="tease" justify="end" align={d === 'documentary' ? 'start' : d === 'kinetic' ? 'center' : 'start'}>
          {d === 'editorial' ? <Card>{words}</Card> : <div style={{textShadow: '0 2px 18px rgba(0,0,0,0.6)'}}>{words}</div>}
        </SafeBox>
      ) : null}
    </AbsoluteFill>
  );
};
