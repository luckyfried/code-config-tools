import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ClipShot, MaskReveal, MultiFrame, Parallax, Picture, Polaroid, Push, Sheet, Slam, Split, Strip} from './pictures';
import {Ground, Leak, Shape, Stamp, Sticker, VignetteLayer} from './shapes';
import {useMotion} from './system';
import {Closer, Type} from './text';
import {Move} from './transitions';
import type {Beat, Layer} from './types';

/** Every layer kind a beat's stack may hold, in the order of the composition model: ground, picture, shape, type, foreground. */
const KINDS: Record<string, React.FC<{layer: Layer}>> = {
  Ground,
  Slam,
  MultiFrame,
  MaskReveal,
  Split,
  Parallax,
  Strip,
  Polaroid,
  Push,
  ClipShot,
  Picture,
  Sheet,
  Shape,
  Type,
  Closer,
  Leak,
  Stamp,
  Sticker,
  Vignette: VignetteLayer,
};

/** Layers the camera leaves still: the type reads where it was set, and its safe-area check holds. A layer with
 * `fixed` (words laid over the frame) is left still the same way. */
const UNMOVED = new Set(['Type', 'Closer']);

/** Scale gained per bar by the push camera and the breathe camera, and frame width travelled per bar by the drift camera. */
const PUSH = 0.07;
const BREATHE = 0.025;
const DRIFT = 9;

/**
 * The beat's camera over its ground, picture and shape layers: a push (default), a drift across the frame, a
 * breathe, or none. A push or a drift moves far enough to read at one frame a second: PUSH of scale or DRIFT percent
 * of the width per bar. A breathe gains BREATHE of scale per bar: a composition placed at the most a photograph can
 * be enlarged, with marks on its points, keeps moving without leaving the photograph's resolution or its safe area.
 */
const useCamera = (mode: Beat['camera'] = 'push') => {
  const {travel, duration, pulse} = useMotion();
  const bars = duration / Math.max(1, pulse * 4);
  if (mode === 'none') return undefined;
  if (mode === 'breathe') return `scale(${travel(1, 1 + BREATHE * bars)})`;
  if (mode === 'drift') return `scale(${1.06 + (DRIFT / 100) * bars}) translateX(${travel((-DRIFT / 2) * bars, (DRIFT / 2) * bars)}%)`;
  return `scale(${travel(1, 1 + PUSH * bars)})`;
};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const camera = useCamera(beat.camera);
  return (
    <Move>
      {beat.layers.map((l, i) => {
        const C = KINDS[l.kind];
        if (!C) {
          console.log(`UNKNOWN_KIND ${l.kind}`);
          return null;
        }
        return (
          <AbsoluteFill key={i} style={{transform: UNMOVED.has(l.kind) || l.fixed ? undefined : camera}}>
            <C layer={{id: `${beat.id}-${i}`, ...l}} />
          </AbsoluteFill>
        );
      })}
    </Move>
  );
};
