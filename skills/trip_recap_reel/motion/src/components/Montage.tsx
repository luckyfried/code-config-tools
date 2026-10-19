import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {splits, SubShot, useMotion, useSys} from '../system';
import {Headline, SafeBox} from '../text';
import {LivePhoto, Scrim} from '../photo';
import type {Beat} from '../types';

const Flash: React.FC = () => {
  const {system} = useSys();
  const {tween} = useMotion();
  return <AbsoluteFill style={{background: system.colors.accent, opacity: tween(0.55, 0, 0, 5, 'exit'), mixBlendMode: 'screen'}} />;
};

/** A place as a burst of its photos, one per shot on the music's beats, under one heavy word. */
export const Montage: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const {pop} = useMotion();
  const t = beat.text ?? {};
  const photos = beat.photos?.length ? beat.photos : [''];
  const spans = splits(beat, photos.length);
  const treat = ['push', 'mask', 'push'] as const;
  const bar = pop(8);
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {spans.map(([from, frames], i) => (
        <Sequence key={i} from={from} durationInFrames={frames}>
          <SubShot frames={frames}>
            <LivePhoto file={photos[i]} treatment={treat[i % 3]} intensity={1.4} />
            {i > 0 ? <Flash /> : null}
          </SubShot>
        </Sequence>
      ))}
      <Scrim side="both" strength={0.55} />
      {t.headline ? (
        <SafeBox name="montage" justify="center" align="center">
          <Headline text={t.headline} max="hero" lines={2} delay={2} />
          <div style={{width: '38%', height: 12, marginTop: 26, background: system.colors.accent, transform: `scaleX(${bar})`}} />
        </SafeBox>
      ) : null}
    </AbsoluteFill>
  );
};
