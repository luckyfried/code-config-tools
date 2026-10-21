import React from 'react';
import {AbsoluteFill, random, staticFile, useCurrentFrame} from 'remotion';
import {useSys} from './system';

/** Film grain: a noise tile shifted every frame up to `until` (where a film holds still), overlaid at the strength the taste sets. */
export const Grain: React.FC<{until?: number}> = ({until = Infinity}) => {
  const {system} = useSys();
  const frame = Math.min(useCurrentFrame(), until);
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

/** The texture pass every frame of a film or card gets, on top of everything else; its grain stops at `until`. */
export const Finish: React.FC<{until?: number}> = ({until}) => (
  <>
    <Vignette />
    <Grain until={until} />
  </>
);
