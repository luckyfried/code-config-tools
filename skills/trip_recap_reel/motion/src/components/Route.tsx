import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {RouteMap} from '../map';
import {LivePhoto} from '../photo';
import {Leaks} from '../texture';
import type {Beat} from '../types';

/** Where the map sits and where the words sit, for a tall frame or a wide one. */
export const routeLayout = (s: ReturnType<typeof useSafe>, textHeight: number) => {
  const wide = s.W > s.H;
  const box = wide
    ? {x: s.left, y: s.top, w: s.width * 0.58, h: s.height}
    : {x: s.left, y: s.top, w: s.width, h: Math.max(320, s.height - textHeight)};
  const textLeft = wide ? s.left + s.width * 0.63 : s.left;
  return {wide, box, textLeft, textWidth: wide ? s.W - s.right - textLeft : s.width};
};

const Words: React.FC<{beat: Beat; textLeft: number; textWidth: number; wide: boolean; name: string}> = ({beat, textLeft, textWidth, wide, name}) => {
  const {system} = useSys();
  const t = beat.text ?? {};
  return (
    <SafeBox name={name} justify="end" style={wide ? {left: textLeft} : undefined}>
      {t.kicker ? <Kicker text={t.kicker} delay={10} color={system.colors.accent} /> : null}
      {t.headline ? <Headline text={t.headline} max="h1" lines={2} delay={14} width={textWidth} /> : null}
      {t.line ? <Line text={t.line} delay={24} /> : null}
    </SafeBox>
  );
};

/** The whole route drawing itself across a map of their own coordinates. */
export const Route: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween, drift, duration} = useMotion();
  const data = beat.data ?? {};
  const {wide, box, textLeft, textWidth} = routeLayout(s, 360);
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <AbsoluteFill style={{transform: `scale(${drift(1.0, 1.05)})`, transformOrigin: `${(box.x + box.w / 2) / s.W * 100}% ${(box.y + box.h / 2) / s.H * 100}%`}}>
        <RouteMap points={data.points ?? []} upto={data.upto} progress={tween(0, 1, 6, duration * 0.72, 'move')} box={box}
          width={s.W} height={s.H} stroke={wide ? 7 : 9} labelSize={system.scale.label * 1.15} />
      </AbsoluteFill>
      <Leaks strength={0.8} seed={beat.id} />
      <Words beat={beat} textLeft={textLeft} textWidth={textWidth} wide={wide} name="route" />
    </AbsoluteFill>
  );
};

/** The last beat: the whole route over the trip's last photo, with their handle and the trip's name. */
export const CloserScene: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween, duration} = useMotion();
  const data = beat.data ?? {};
  const {wide, box, textLeft, textWidth} = routeLayout(s, 380);
  const photo = beat.photos?.[0];
  const paper = system.direction === 'editorial';
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {photo ? <LivePhoto file={photo} treatment="push" intensity={0.6} /> : null}
      <AbsoluteFill style={{background: system.colors.bg, opacity: photo ? (paper ? 0.86 : 0.74) : 1}} />
      <RouteMap points={data.points ?? []} upto={data.upto} progress={tween(0, 1, 4, duration * 0.45, 'move')} box={box}
        width={s.W} height={s.H} stroke={wide ? 7 : 9} labelSize={system.scale.label * 1.1} />
      <Words beat={beat} textLeft={textLeft} textWidth={textWidth} wide={wide} name="closer" />
    </AbsoluteFill>
  );
};
