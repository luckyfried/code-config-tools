import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Photo, Scrim} from '../photo';
import {Leaks} from '../texture';
import type {Beat, BeatText} from '../types';

const ORDER: Record<string, ('push' | 'parallax' | 'mask' | 'split')[]> = {
  editorial: ['mask', 'parallax', 'push'],
  kinetic: ['push', 'split', 'mask'],
  documentary: ['push', 'mask', 'parallax'],
};

const Shot: React.FC<{file: string; second?: string; treatment: 'push' | 'parallax' | 'mask' | 'split'; text: BeatText; index: number; rank?: string}> = ({
  file, second, treatment, text, index, rank,
}) => {
  const {system} = useSys();
  const {tween} = useMotion();
  const s = useSafe();
  const kinetic = system.direction === 'kinetic';
  const editorial = system.direction === 'editorial';
  const words = (
    <>
      {text.kicker ? <Kicker text={text.kicker} delay={6} /> : null}
      {text.headline ? <Headline text={text.headline} max="h2" lines={3} delay={10} width={editorial ? s.width - 2 * CARD_PAD : undefined} /> : null}
      {text.line ? <Line text={text.line} delay={18} /> : null}
    </>
  );
  return (
    <AbsoluteFill>
      <LivePhoto file={file} second={second} treatment={treatment} />
      {system.direction === 'documentary' ? <Leaks strength={0.7} seed={file} /> : null}
      {editorial ? null : <Scrim side="bottom" strength={0.8} />}
      {rank ? (
        <SafeBox name={`rank-${index}`} justify="start" align={kinetic ? 'start' : 'end'}>
          <div style={{fontFamily: `'${system.display.family}'`, fontWeight: system.display.weight, fontSize: system.scale.hero,
            lineHeight: 0.8, color: kinetic ? system.colors.accent : system.colors.ink, opacity: tween(0, kinetic ? 1 : 0.85, 4, 10),
            transform: `translateY(${tween(-40, 0, 4, 18)}px)`}}>
            {rank}
          </div>
        </SafeBox>
      ) : null}
      <SafeBox name={`photo-${index}`} justify="end">
        {editorial && (text.kicker || text.headline || text.line) ? <Card>{words}</Card> : words}
      </SafeBox>
    </AbsoluteFill>
  );
};

/** Their photos, alive: one to three shots, each with its own move, cut where storyboard.py snapped the music. */
export const PhotoLive: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, still} = useSys();
  const s = useSafe();
  const photos = beat.photos ?? [];
  const items: (BeatText & {rank?: string})[] = beat.data?.items ?? [beat.text ?? {}];
  const order = beat.treatment ? [beat.treatment] : ORDER[system.direction];
  if (!photos.length) return null;
  if (still && photos.length > 1) {
    const n = Math.min(3, photos.length);
    return (
      <AbsoluteFill style={{background: system.colors.bg}}>
        <div style={{position: 'absolute', left: s.left, right: s.right, top: s.top, height: s.height * 0.62, display: 'grid', gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))`, gap: 14}}>
          {photos.slice(0, n).map((p, i) => (
            <div key={i} style={{position: 'relative', overflow: 'hidden'}}>
              <Photo file={p} />
              {items[i]?.rank ? <div style={{position: 'absolute', left: 14, top: 8, fontFamily: `'${system.display.family}'`, fontWeight: system.display.weight, fontSize: system.scale.h2, color: system.colors.ink, textShadow: '0 4px 24px rgba(0,0,0,0.4)'}}>{items[i].rank}</div> : null}
            </div>
          ))}
        </div>
        <SafeBox name="photo-card" justify="end">
          {beat.text?.kicker ? <Kicker text={beat.text.kicker} /> : null}
          <Headline text={beat.text?.headline ?? items[0]?.headline ?? ''} max="h2" lines={2} />
          {beat.text?.line ? <Line text={beat.text.line} /> : null}
        </SafeBox>
      </AbsoluteFill>
    );
  }
  const parts = splits(beat, Math.min(photos.length, Math.max(1, items.length)));
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {parts.map(([from, dur], i) => {
        const tr = order[i % order.length];
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <SubShot frames={dur}>
              <Shot file={photos[i]} second={tr === 'split' ? photos[(i + 1) % photos.length] : undefined} treatment={tr} text={items[i] ?? {}} index={i} rank={items[i]?.rank} />
            </SubShot>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
