import React from 'react';
import {AbsoluteFill, Img} from 'remotion';
import {hash, src, useMotion, useSys} from './system';

/** Image requests retry with backoff (1 s, 2 s, 4 s ...), so a dropped request costs a pause, never the render. */
export const RETRIES = 6;

export const Photo: React.FC<{file: string; style?: React.CSSProperties; position?: string}> = ({file, style, position}) => (
  <Img
    src={src(file)}
    maxRetries={RETRIES}
    style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: position ?? '50% 45%', display: 'block', ...style}}
  />
);

/**
 * One photo kept alive for the whole shot:
 * push   a slow eased push-in with drift
 * parallax  a blurred, darkened copy behind a framed print that moves at its own speed
 * mask   the frame revealed through an expanding mask, then pushed
 * split  two photos sharing the frame, sliding against each other
 */
export const LivePhoto: React.FC<{
  file: string;
  second?: string;
  treatment?: 'push' | 'parallax' | 'mask' | 'split';
  delay?: number;
  intensity?: number;
}> = ({file, second, treatment = 'push', delay = 0, intensity = 1}) => {
  const {system} = useSys();
  const {drift, tween, pop} = useMotion();
  const h = hash(file);
  const dirX = h > 0.5 ? 1 : -1;
  const push = drift(1.06, 1.06 + 0.12 * intensity);
  const dx = drift(-1.5 * dirX, 1.5 * dirX) * intensity;
  const dy = drift(1, -1.2) * intensity;
  if (treatment === 'parallax') {
    const p = pop(delay);
    const editorial = system.direction === 'editorial';
    return (
      <AbsoluteFill style={{background: system.colors.bg, overflow: 'hidden'}}>
        <AbsoluteFill style={{transform: `scale(${1.25 + drift(0, 0.08)}) translate(${dx * 2}%, ${dy * 2}%)`, filter: 'blur(28px) brightness(0.62) saturate(1.1)'}}>
          <Photo file={file} />
        </AbsoluteFill>
        <AbsoluteFill style={{justifyContent: editorial ? 'flex-start' : 'center', alignItems: 'center', paddingTop: editorial ? '7%' : 0}}>
          <div
            style={{
              width: editorial ? '88%' : '78%',
              aspectRatio: '4 / 5',
              overflow: 'hidden',
              boxShadow: '0 40px 90px rgba(0,0,0,0.45)',
              transform: `translateY(${(1 - p) * 140 + dy * -10}px) rotate(${(1 - p) * 3 * dirX + drift(-0.6, 0.6) * dirX}deg) scale(${0.94 + 0.06 * p})`,
              opacity: Math.min(1, p * 1.6),
            }}
          >
            <div style={{width: '100%', height: '100%', transform: `scale(${drift(1.02, 1.12)}) translate(${-dx}%, 0)`}}>
              <Photo file={file} />
            </div>
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }
  if (treatment === 'mask') {
    const r = tween(0, 1, delay, 26, 'enter');
    const shape = system.direction === 'documentary'
      ? `circle(${12 + r * 110}% at 50% 48%)`
      : `inset(${(1 - r) * 100}% 0 0 0)`;
    return (
      <AbsoluteFill style={{background: system.colors.bg, overflow: 'hidden'}}>
        <AbsoluteFill style={{clipPath: shape, transform: `scale(${push + (1 - r) * 0.1}) translate(${dx}%, ${dy}%)`}}>
          <Photo file={file} />
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }
  if (treatment === 'split' && second) {
    const p = pop(delay);
    const q = pop(delay + 5);
    return (
      <AbsoluteFill style={{background: system.colors.bg, overflow: 'hidden'}}>
        <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: '50.2%', overflow: 'hidden', transform: `translateX(${(1 - p) * -100}%)`}}>
          <div style={{width: '100%', height: '100%', transform: `scale(${drift(1.05, 1.15)}) translateX(${drift(2, -2)}%)`}}>
            <Photo file={file} />
          </div>
        </div>
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: '50%', overflow: 'hidden', transform: `translateX(${(1 - q) * 100}%)`}}>
          <div style={{width: '100%', height: '100%', transform: `scale(${drift(1.15, 1.05)}) translateX(${drift(-2, 2)}%)`}}>
            <Photo file={second} />
          </div>
        </div>
        <div style={{position: 'absolute', left: 0, right: 0, top: '50%', height: 6, marginTop: -3, background: system.colors.accent, transform: `scaleX(${q})`}} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: system.colors.bg}}>
      <AbsoluteFill style={{transform: `scale(${push}) translate(${dx}%, ${dy}%)`}}>
        <Photo file={file} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const tint = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

/** A gradient that seats type over a photo without a box. */
export const Scrim: React.FC<{side?: 'bottom' | 'top' | 'both'; strength?: number}> = ({side = 'bottom', strength = 0.7}) => {
  const {system} = useSys();
  const alpha = (a: number) => tint(system.colors.bg, a);
  const bottom = `linear-gradient(to top, ${alpha(strength)} 0%, ${alpha(strength * 0.92)} 36%, ${alpha(strength * 0.55)} 54%, ${alpha(strength * 0.18)} 66%, ${alpha(0)} 76%)`;
  const top = `linear-gradient(to bottom, ${alpha(strength * 0.8)} 0%, ${alpha(0)} 30%)`;
  return (
    <AbsoluteFill style={{background: side === 'both' ? `${bottom}, ${top}` : side === 'top' ? top : bottom, pointerEvents: 'none'}} />
  );
};

/** The card's side padding; a headline inside it fits to the safe width less twice this. */
export const CARD_PAD = 40;

/** A paper card behind the text block only, so the photo around it stays whole: the editorial way to seat type. */
export const Card: React.FC<{children: React.ReactNode}> = ({children}) => {
  const {system} = useSys();
  const {tween} = useMotion();
  return (
    <div style={{background: tint(system.colors.bg, 0.9 * tween(0, 1, 2, 12)), padding: `34px ${CARD_PAD}px 38px`, borderTop: `3px solid ${tint(system.colors.ink, 0.85)}`, boxShadow: '0 24px 60px rgba(0,0,0,0.18)'}}>
      {children}
    </div>
  );
};
