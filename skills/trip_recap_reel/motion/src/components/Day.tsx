import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {LivePhoto, Scrim} from '../photo';
import {RouteMap} from '../map';
import type {Beat} from '../types';

const tint = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

/** One day of the trip: its photos in turn, the map thread inset (the route so far, today's leg drawing), its line. */
export const Day: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween, duration, pop} = useMotion();
  const t = beat.text ?? {};
  const data = beat.data ?? {};
  const photos = beat.photos?.length ? beat.photos : [''];
  const spans = splits(beat, photos.length);
  const wide = s.W > s.H;
  const iw = wide ? s.width * 0.34 : s.width * 0.62;
  const ih = iw * 0.78;
  const ix = wide ? s.left + s.width - iw : s.left;
  const iy = s.top;
  const p = pop(4);
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {spans.map(([from, frames], i) => (
        <Sequence key={i} from={from} durationInFrames={frames}>
          <SubShot frames={frames}>
            <LivePhoto file={photos[i]} treatment={i % 2 ? 'mask' : 'push'} />
          </SubShot>
        </Sequence>
      ))}
      <Scrim side="both" strength={0.82} />
      <div style={{position: 'absolute', left: ix, top: iy, width: iw, height: ih, borderRadius: 18, overflow: 'hidden',
        background: tint(system.colors.bg, 0.84), boxShadow: '0 20px 50px rgba(0,0,0,0.3)',
        transform: `translateY(${(1 - p) * -30}px)`, opacity: Math.min(1, p * 1.4)}}>
        <RouteMap points={data.points ?? []} upto={data.upto} progress={tween(0, 1, 10, duration * 0.6, 'move')}
          box={{x: 0, y: 0, w: iw, h: ih}} width={iw} height={ih} stroke={5} labelSize={system.scale.label * 0.8} pad={0.2} />
      </div>
      <SafeBox name="day" justify="end" top={wide ? s.top : s.top + ih + 30} style={wide ? {right: s.right + s.width * 0.36} : undefined}>
        {t.kicker ? <Kicker text={t.kicker} delay={6} /> : null}
        {t.headline ? <Headline text={t.headline} max="h1" lines={2} delay={10} width={wide ? s.width * 0.64 : undefined} /> : null}
        {t.line ? <Line text={t.line} delay={20} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
