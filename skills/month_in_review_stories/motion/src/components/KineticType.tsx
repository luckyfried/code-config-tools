import React from 'react';
import {AbsoluteFill} from 'remotion';
import {fitText, measureText} from '@remotion/layout-utils';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Kicker, Line, SafeBox} from '../text';
import {LivePhoto} from '../photo';
import type {Beat} from '../types';

type Row = {text: string; meta?: string};

/**
 * Type that carries the beat on its own: rows (their people, the accounts they loved) land one after
 * another, each fitted to the width, the newest row in the accent; a photo of theirs moves behind it.
 */
export const KineticType: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, still} = useSys();
  const s = useSafe();
  const {pop, tween, duration, frame} = useMotion();
  const rows: Row[] = beat.data?.rows ?? [];
  const t = beat.text ?? {};
  const d = system.direction;
  const f = system.display;
  const span = Math.max(1, Math.floor((duration * 0.55) / Math.max(1, rows.length)));
  const metaW = Math.max(0, ...rows.map((r) => (r.meta ? measureText({text: r.meta, fontFamily: `'${system.text.family}'`, fontWeight: 600, fontSize: system.scale.label, letterSpacing: '0.02em'}).width + 28 : 0)));
  const size = Math.min(
    system.scale.h1,
    ...rows.map((r) => fitText({text: r.text, withinWidth: (s.width - metaW) * 0.97, fontFamily: `'${f.family}'`, fontWeight: f.weight, letterSpacing: `${f.tracking}em`, textTransform: f.case === 'none' ? undefined : f.case}).fontSize),
  );
  const photo = beat.photos?.[0];
  return (
    <AbsoluteFill style={{background: d === 'kinetic' ? system.colors.accent2 : system.colors.bg}}>
      {photo ? (
        <AbsoluteFill style={{opacity: d === 'editorial' ? 0.18 : d === 'kinetic' ? 0.2 : 0.32}}>
          <LivePhoto file={photo} treatment="push" intensity={1.4} />
        </AbsoluteFill>
      ) : null}
      <SafeBox name="kinetic" justify="center">
        {t.kicker ? <Kicker text={t.kicker} color={d === 'kinetic' ? system.colors.ink : system.colors.accent} /> : null}
        {rows.map((r, i) => {
          const at = 6 + i * span;
          const p = pop(at, d === 'kinetic' ? {damping: 12} : undefined);
          const active = still ? 0 : Math.min(rows.length - 1, Math.floor(Math.max(0, frame - 6) / span));
          const lit = i === active;
          return (
            <div key={i} style={{display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 24, overflow: 'hidden', width: '100%'}}>
              <div style={{...faceStyle(f), fontSize: size, lineHeight: 1.0, whiteSpace: 'nowrap', color: lit ? system.colors.accent : system.colors.ink,
                transform: d === 'kinetic' ? `translateX(${(1 - p) * -110}%) skewX(${(1 - p) * -12}deg)` : `translateY(${(1 - p) * 105}%)`, opacity: d === 'kinetic' ? 1 : Math.min(1, p * 1.4)}}>
                {r.text}
              </div>
              {r.meta ? (
                <div style={{...faceStyle(system.text), fontSize: system.scale.label, fontWeight: 600, textTransform: 'none', letterSpacing: '0.02em', whiteSpace: 'nowrap', flexShrink: 0, color: system.colors.ink, opacity: tween(0, 0.85, at + 6, 10)}}>
                  {r.meta}
                </div>
              ) : null}
            </div>
          );
        })}
        {t.line ? <Line text={t.line} delay={6 + rows.length * span} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
