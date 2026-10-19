import React from 'react';
import {AbsoluteFill, random, staticFile, useCurrentFrame} from 'remotion';
import {useMotion, useSys} from './system';

/** Film grain: a noise tile shifted every frame, overlaid at the strength the taste sets. */
export const Grain: React.FC = () => {
  const {system} = useSys();
  const frame = useCurrentFrame();
  if (!system.texture.grain) return null;
  const x = Math.floor(random(`gx${frame}`) * 512);
  const y = Math.floor(random(`gy${frame}`) * 512);
  return (
    <AbsoluteFill
      style={{
        backgroundImage: `url(${staticFile('fx/grain.png')})`,
        backgroundPosition: `${x}px ${y}px`,
        backgroundSize: '512px 512px',
        mixBlendMode: 'overlay',
        opacity: system.texture.grain,
        pointerEvents: 'none',
      }}
    />
  );
};

export const Vignette: React.FC = () => {
  const {system} = useSys();
  const v = system.texture.vignette;
  if (!v) return null;
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse 75% 62% at 50% 46%, rgba(0,0,0,0) 55%, rgba(0,0,0,${v}) 100%)`,
        pointerEvents: 'none',
      }}
    />
  );
};

/** Warm light leaks drifting across the frame in the palette's accents, only when the taste asks for them. */
export const Leaks: React.FC<{strength?: number; seed?: string}> = ({strength = 1, seed = 'leak'}) => {
  const {system} = useSys();
  const {frame, duration} = useMotion();
  if (!system.texture.leaks) return null;
  const t = frame / Math.max(1, duration);
  const a = 0.32 * strength;
  const x1 = 10 + 70 * random(`${seed}x`) + 25 * Math.sin(t * Math.PI * 1.3);
  const y1 = 15 + 30 * random(`${seed}y`) + 18 * t;
  const x2 = 90 - 60 * random(`${seed}x2`) - 20 * t;
  return (
    <AbsoluteFill style={{mixBlendMode: 'screen', pointerEvents: 'none', opacity: a}}>
      <AbsoluteFill
        style={{background: `radial-gradient(circle at ${x1}% ${y1}%, ${system.colors.accent} 0%, rgba(0,0,0,0) 42%)`}}
      />
      <AbsoluteFill
        style={{background: `radial-gradient(ellipse 60% 40% at ${x2}% 88%, ${system.colors.accent2} 0%, rgba(0,0,0,0) 60%)`}}
      />
    </AbsoluteFill>
  );
};

/** The texture pass every frame of a film or card gets, on top of everything else. */
export const Finish: React.FC = () => (
  <>
    <Vignette />
    <Grain />
  </>
);
