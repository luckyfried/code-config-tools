import React from 'react';
import {AbsoluteFill, Img, random, useCurrentFrame} from 'remotion';
import {src, useMotion, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {LivePhoto, Photo, RETRIES, Scrim} from '../photo';
import {Leaks} from '../texture';
import type {Beat, Clip} from '../types';

/**
 * A still brought to life: the photo split into a far plane and a near plane that move at
 * different speeds, a breathing light leak and drifting dust. It stands in for any clip that did not arrive.
 */
export const StillToLife: React.FC<{file: string; seed: string}> = ({file, seed}) => {
  const {system} = useSys();
  const {drift, frame} = useMotion();
  const dust = Array.from({length: 26}, (_, i) => {
    const x = random(`${seed}dx${i}`) * 100;
    const y0 = random(`${seed}dy${i}`) * 100;
    const sp = 0.02 + random(`${seed}ds${i}`) * 0.05;
    const y = (y0 - frame * sp + 100) % 100;
    const size = 2 + random(`${seed}dz${i}`) * 5;
    return <div key={i} style={{position: 'absolute', left: `${x}%`, top: `${y}%`, width: size, height: size, borderRadius: size, background: system.colors.paper, opacity: 0.25 + 0.35 * random(`${seed}do${i}`)}} />;
  });
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: system.colors.bg}}>
      <AbsoluteFill style={{transform: `scale(${drift(1.18, 1.1)}) translate(${drift(1.5, -1.5)}%, 0)`, filter: 'blur(3px)'}}>
        <Photo file={file} />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          transform: `scale(${drift(1.08, 1.22)}) translate(${drift(-1.5, 2)}%, ${drift(1, -1.5)}%) rotate(${drift(-0.6, 0.6)}deg)`,
          WebkitMaskImage: 'radial-gradient(ellipse 58% 48% at 50% 48%, #000 55%, rgba(0,0,0,0) 100%)',
          maskImage: 'radial-gradient(ellipse 58% 48% at 50% 48%, #000 55%, rgba(0,0,0,0) 100%)',
        }}
      >
        <Photo file={file} />
      </AbsoluteFill>
      <Leaks strength={1.4} seed={seed} />
      <AbsoluteFill>{dust}</AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * The clip itself, conformed and graded by clips.py and read as its frame sequence, or its substitute when it
 * did not arrive.
 */
export const ClipLayer: React.FC<{clip: Clip}> = ({clip}) => {
  const {drift} = useMotion();
  const frame = useCurrentFrame();
  if (clip.file && clip.frames) {
    const n = String(Math.min(Math.max(frame, 0), clip.frames - 1) + 1).padStart(4, '0');
    return (
      <AbsoluteFill style={{overflow: 'hidden', transform: `scale(${drift(1.0, 1.05)})`}}>
        <Img src={src(`${clip.file.replace(/\.mp4$/, '')}/${n}.jpg`)} maxRetries={RETRIES}
          style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </AbsoluteFill>
    );
  }
  return <StillToLife file={clip.image ?? ''} seed={clip.id} />;
};

export const ClipShot: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const t = beat.text ?? {};
  const chapter = beat.data?.chapter as string | undefined;
  const {tween} = useMotion();
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={beat.photos?.[0] ?? ''} treatment="push" intensity={1.4} />}
      {t.headline || t.kicker ? <Scrim side="bottom" strength={0.7} /> : null}
      {chapter ? (
        <SafeBox name="chapter" justify="center" align="center">
          <div style={{fontFamily: `'${system.display.family}'`, fontWeight: system.display.weight, fontSize: system.scale.hero * 1.2, lineHeight: 0.85,
            color: 'transparent', WebkitTextStroke: `3px ${system.colors.ink}`, opacity: tween(0, 0.9, 0, 12), transform: `scale(${tween(1.25, 1, 0, 30)})`}}>
            {chapter}
          </div>
        </SafeBox>
      ) : null}
      {t.headline || t.kicker ? (
        <SafeBox name="clip" justify="end">
          {t.kicker ? <Kicker text={t.kicker} delay={6} /> : null}
          {t.headline ? <Headline text={t.headline} max="h1" lines={2} delay={10} /> : null}
          {t.line ? <Line text={t.line} delay={20} /> : null}
        </SafeBox>
      ) : null}
    </AbsoluteFill>
  );
};
