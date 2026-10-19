import React from 'react';
import {AbsoluteFill, Easing, interpolate} from 'remotion';
import {splits, useMotion, useSafe, useSys} from '../system';
import {CH, CW, PlacedCard} from './GuideCard';
import {Field, fitCard} from './Reveal';
import type {Beat, GuideCardData} from '../types';

/**
 * A run of cards on one grid, swiped in one after another: the next card peeks from the right edge until its turn,
 * and its contents arrive as it lands, so every shot moves.
 */
export const Swipe: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const s = useSafe();
  const {frame} = useMotion();
  const ns: number[] = beat.data?.cards ?? [];
  const deck = ns.map((n) => board.cards.find((c) => c.n === n)).filter(Boolean) as GuideCardData[];
  const shots = splits(beat, Math.max(1, deck.length));
  const k = fitCard(s.width, s.height);
  const w = CW * k;
  const gap = 40;
  const x0 = s.left + (s.width - w) / 2;
  const y = s.top + 60;
  const ease = Easing.bezier(...system.ease.move);
  let pos = 0;
  shots.forEach(([start], i) => {
    if (i === 0) return;
    pos += interpolate(frame, [start - 7, start + 7], [0, 1], {easing: ease, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  });
  const active = Math.min(deck.length - 1, Math.round(pos));
  return (
    <AbsoluteFill>
      <Field beat={beat} strength={0.9} />
      {deck.map((c, i) => {
        const x = x0 + (i - pos) * (w + gap);
        if (x > s.W + 40 || x + w < -40) return null;
        const near = 1 - Math.min(1, Math.abs(i - pos));
        return (
          <PlacedCard key={c.n} card={c} x={x} y={y} scale={k} delay={i === 0 ? 4 : shots[i][0] - 2}
            style={{opacity: 0.55 + 0.45 * near, transform: `scale(${k * (0.92 + 0.08 * near)})`, transformOrigin: '50% 50%',
              left: x - (CW - w) / 2, top: y - (CH - CH * k) / 2}} />
        );
      })}
      <div style={{position: 'absolute', left: 0, right: 0, top: y + CH * k + 30, display: 'flex', justifyContent: 'center', gap: 16}}>
        {deck.map((c, i) => (
          <div key={c.n} style={{width: i === active ? 44 : 14, height: 14, borderRadius: 7,
            background: i === active ? system.colors.accent : system.colors.muted}} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
