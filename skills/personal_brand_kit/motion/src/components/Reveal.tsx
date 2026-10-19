import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {LivePhoto} from '../photo';
import {CH, CW, PlacedCard} from './GuideCard';
import type {Beat, GuideCardData} from '../types';

/** The scale that seats a card inside the reel's safe area with room for the counter above it. */
export const fitCard = (width: number, height: number) => Math.min(width / CW, (height - 60) / CH);

/** Their photo, slowly alive under the field color: the room every card is shown in. */
export const Field: React.FC<{beat: Beat; strength?: number}> = ({beat, strength = 0.8}) => {
  const {system} = useSys();
  const photo = beat.photos?.[0];
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {photo ? <LivePhoto file={photo} treatment="push" intensity={0.6} /> : null}
      <AbsoluteFill style={{background: system.colors.bg, opacity: photo ? strength : 1}} />
    </AbsoluteFill>
  );
};

/** One card of the guide, revealed on its own beat: it rises into the safe area and its contents arrive in order. */
export const Reveal: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const s = useSafe();
  const {pop, tween} = useMotion();
  const card = board.cards.find((c) => c.n === beat.data?.card) as GuideCardData | undefined;
  if (!card) return null;
  const k = fitCard(s.width, s.height);
  const x = s.left + (s.width - CW * k) / 2;
  const y = s.top + 60;
  const p = pop(0);
  return (
    <AbsoluteFill>
      <Field beat={beat} />
      <div style={{position: 'absolute', left: x, top: s.top, ...faceStyle(system.text), fontSize: system.scale.label, fontWeight: 600,
        letterSpacing: '0.18em', textTransform: 'uppercase', color: system.colors.accent, opacity: tween(0, 1, 2, 10), whiteSpace: 'nowrap'}}>
        {String(card.n).padStart(2, '0')} of {board.cards.length} · {card.kind}
      </div>
      <PlacedCard card={card} x={x} y={y} scale={k} delay={6}
        style={{transform: `translateY(${(1 - p) * 140}px) scale(${k * (0.94 + 0.06 * p)})`, opacity: Math.min(1, p * 1.6)}} />
    </AbsoluteFill>
  );
};
