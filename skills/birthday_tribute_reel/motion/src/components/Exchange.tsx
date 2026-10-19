import React from 'react';
import {AbsoluteFill} from 'remotion';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Kicker, SafeBox} from '../text';
import {LivePhoto, Scrim} from '../photo';
import {Leaks} from '../texture';
import type {Beat} from '../types';

type Said = {by: string; text: string; side: 'mine' | 'theirs'};

/**
 * Their own words to each other as the captions: under the photo the thread was on, each line lands in turn
 * like a subtitle, the handle that wrote it above it, one side set left in ink and the other set right in the
 * accent, so the two voices read as a conversation.
 */
export const Exchange: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, still} = useSys();
  const s = useSafe();
  const {pop, tween, duration, frame} = useMotion();
  const lines: Said[] = (beat.data?.lines ?? []).slice(0, 4);
  const t = beat.text ?? {};
  const photo = beat.photos?.[0];
  const span = Math.max(8, Math.floor((duration * 0.62) / Math.max(1, lines.length)));
  const f = system.display;
  const each = (s.height * 0.78) / Math.max(1, lines.length);
  const size = Math.min(
    system.scale.h2,
    each / 2.9,
    ...lines.map((l) => fitTextOnNLines({text: l.text, maxLines: 2, maxBoxWidth: s.width * 0.86, fontFamily: `'${f.family}'`, fontWeight: f.weight,
      letterSpacing: `${f.tracking}em`, textTransform: f.case === 'none' ? undefined : f.case, maxFontSize: system.scale.h2}).fontSize),
  );
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {photo ? <LivePhoto file={photo} treatment="push" intensity={0.8} /> : null}
      <AbsoluteFill style={{background: `linear-gradient(to bottom, color-mix(in srgb, ${system.colors.bg} 72%, transparent) 0%, color-mix(in srgb, ${system.colors.bg} 55%, transparent) 45%, transparent 80%)`}} />
      <Scrim side="both" strength={0.85} />
      {system.direction === 'documentary' ? <Leaks strength={0.6} seed={beat.id} /> : null}
      <SafeBox name="exchange" justify="center">
        {t.kicker ? <Kicker text={t.kicker} delay={2} /> : null}
        {lines.map((l, i) => {
          const at = 6 + i * span;
          const p = pop(at);
          const mine = l.side === 'mine';
          const active = still || Math.floor(Math.max(0, frame - 6) / span) >= i;
          return (
            <div key={i} style={{alignSelf: mine ? 'flex-start' : 'flex-end', maxWidth: '88%', textAlign: mine ? 'left' : 'right', marginTop: i ? size * 0.55 : 0,
              opacity: active ? Math.min(1, p * 1.5) : 0, transform: `translateY(${(1 - p) * 40}px)`}}>
              <div style={{...faceStyle(system.text), fontSize: system.scale.label, fontWeight: 600, textTransform: 'none', letterSpacing: '0.04em',
                color: mine ? system.colors.ink : system.colors.accent, opacity: tween(0, 0.8, at + 2, 8), marginBottom: '0.35em'}}>
                {l.by}
              </div>
              <div style={{...faceStyle(f), fontSize: size, lineHeight: 1.08, color: mine ? system.colors.ink : system.colors.accent}}>
                {l.text}
              </div>
            </div>
          );
        })}
      </SafeBox>
    </AbsoluteFill>
  );
};
