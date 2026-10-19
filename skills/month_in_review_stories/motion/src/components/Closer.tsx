import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Photo} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat} from '../types';

/**
 * The frame they post: their best photos settle into a stack of prints, the sign-off lands, and the
 * last second holds still enough to screenshot while the prints keep breathing.
 */
export const Closer: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const s = useSafe();
  const {pop, drift, tween} = useMotion();
  const t = beat.text ?? {};
  const photos = (beat.photos ?? []).slice(0, 4);
  const d = system.direction;
  const angles = [-7, 5, -3, 8];
  const offsets = [[-16, -6], [14, -2], [-6, 6], [10, 10]];
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {beat.clip ? (
        <AbsoluteFill style={{opacity: 0.45}}>
          <ClipLayer clip={beat.clip} />
        </AbsoluteFill>
      ) : null}
      <Leaks strength={0.8} seed="closer" />
      <div style={{position: 'absolute', left: 0, right: 0, top: s.top + 20, height: s.H * 0.34, display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
        {photos.map((p, i) => {
          const q = pop(i * 5, d === 'kinetic' ? {damping: 13} : undefined);
          const [ox, oy] = offsets[i % 4];
          return (
            <div key={i} style={{position: 'absolute', width: s.W * 0.36, aspectRatio: '4 / 5', background: system.colors.paper, padding: s.W * 0.018, paddingBottom: s.W * 0.06,
              boxShadow: '0 30px 70px rgba(0,0,0,0.35)', transform: `translate(${ox * q + (1 - q) * 0}%, ${oy * q + (1 - q) * 120}%) rotate(${angles[i] * q + drift(-0.8, 0.8)}deg) scale(${0.8 + 0.2 * q})`,
              opacity: Math.min(1, q * 2)}}>
              <div style={{width: '100%', height: '100%', overflow: 'hidden'}}>
                <div style={{width: '100%', height: '100%', transform: `scale(${drift(1.02, 1.1)})`}}>
                  <Photo file={p} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <SafeBox name="closer" justify="end" align={d === 'kinetic' ? 'center' : 'start'}>
        <Kicker text={t.kicker ?? `@${board.handle}`} delay={10} />
        <Headline text={t.headline ?? 'see you next month'} max="h1" lines={2} delay={14} />
        {t.line ? <Line text={t.line} delay={24} /> : null}
        <div style={{display: 'flex', gap: 8, marginTop: 30, width: '60%'}}>
          {system.colors.swatches.slice(0, 5).map((w, i) => (
            <div key={i} style={{flex: 1, height: 10, background: w.hex, transform: `scaleX(${tween(0, 1, 28 + i * 3, 14)})`, transformOrigin: '0 50%'}} />
          ))}
        </div>
        <div style={{...faceStyle(system.text), fontSize: system.scale.label * 0.85, textTransform: 'none', letterSpacing: '0.04em', color: system.colors.ink, opacity: tween(0, 0.7, 44, 12), marginTop: 18}}>
          {beat.data?.signoff ?? (board.month ? `my ${board.month.name.toLowerCase()} on instagram` : `my ${board.year} on instagram`)}
        </div>
      </SafeBox>
    </AbsoluteFill>
  );
};
