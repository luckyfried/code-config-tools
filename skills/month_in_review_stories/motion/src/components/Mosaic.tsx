import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {faceStyle, splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Photo, Scrim} from '../photo';
import type {Beat} from '../types';

type Group = {label: string; headline: string; line?: string; photos: string[]};

/** A month as a grid: tiles land one after another on springs, then the whole wall drifts. */
const Wall: React.FC<{group: Group; index: number}> = ({group, index}) => {
  const {system, still} = useSys();
  const s = useSafe();
  const {pop, drift, stagger} = useMotion();
  const n = group.photos.length;
  const cols = n >= 9 ? 3 : n >= 4 ? 2 : 1;
  const rows = Math.ceil(n / cols);
  const gap = system.direction === 'kinetic' ? 8 : 14;
  // A documentary wall is a contact sheet that runs the full frame; the others leave paper or color below for the type.
  const gridH = system.direction === 'documentary' ? s.H : s.H * (still ? 0.6 : 0.7);
  const tileH = (gridH - gap * (rows + 1)) / rows;
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <div style={{position: 'absolute', left: gap, right: gap, top: gap, display: 'grid', gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, gap,
        transform: `scale(${drift(1, 1.05)})`, transformOrigin: '50% 30%'}}>
        {group.photos.map((p, i) => {
          const q = pop(i * Math.max(1, Math.round(stagger * 0.7)));
          return (
            <div key={i} style={{height: tileH, overflow: 'hidden', transform: `scale(${0.6 + 0.4 * q}) translateY(${(1 - q) * 80}px)`, opacity: Math.min(1, q * 1.5),
              borderRadius: system.direction === 'editorial' ? 2 : 0}}>
              <div style={{width: '100%', height: '100%', transform: `scale(${drift(1.04, 1.14)})`}}>
                <Photo file={p} />
              </div>
            </div>
          );
        })}
      </div>
      <Scrim side="bottom" strength={0.95} />
      <SafeBox name={`mosaic-${index}`} justify="end">
        <Kicker text={group.label} delay={Math.min(8, n * 2)} />
        <Headline text={group.headline} max="h1" lines={2} delay={Math.min(12, n * 2 + 4)} />
        {group.line ? <Line text={group.line} delay={Math.min(20, n * 2 + 12)} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};

type Swatch = {hex: string; name: string; photo?: string};

/** Their palette as bars that rise in turn, each named, each holding the photo that shows it best. */
const PaletteBars: React.FC<{swatches: Swatch[]; beat: Beat}> = ({swatches, beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {pop, tween, drift} = useMotion();
  const t = beat.text ?? {};
  const barsH = s.height * 0.46;
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <div style={{position: 'absolute', left: s.left, width: s.width, top: s.top, height: barsH, display: 'flex', gap: 12, alignItems: 'flex-end'}}>
        {swatches.slice(0, 5).map((w, i) => {
          const q = pop(4 + i * 4);
          return (
            <div key={i} style={{flex: 1, height: `${q * 100}%`, background: w.hex, position: 'relative', overflow: 'hidden'}}>
              {w.photo ? (
                <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: '45%', opacity: 0.9, transform: `scale(${drift(1.1, 1.25)})`}}>
                  <Photo file={w.photo} />
                </div>
              ) : null}
              <div style={{position: 'absolute', left: 10, bottom: 14, right: 6, ...faceStyle(system.text), textTransform: 'none', letterSpacing: '0.02em',
                fontSize: system.scale.label * 0.8, fontWeight: 600, color: lum(w.hex) > 0.55 ? '#1a1410' : '#fbf6ee', opacity: tween(0, 1, 16 + i * 4, 10),
                lineHeight: 1.15}}>
                {w.name}
                <br />
                <span style={{fontWeight: 400, opacity: 0.8}}>{w.hex.toUpperCase()}</span>
              </div>
            </div>
          );
        })}
      </div>
      <SafeBox name="palette" justify="end">
        {t.kicker ? <Kicker text={t.kicker} delay={8} /> : null}
        {t.headline ? <Headline text={t.headline} max="h1" lines={2} delay={12} /> : null}
        {t.line ? <Line text={t.line} delay={20} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};

const lum = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
};

export const Mosaic: React.FC<{beat: Beat}> = ({beat}) => {
  const {still} = useSys();
  if (beat.data?.mode === 'palette') return <PaletteBars swatches={beat.data.swatches ?? []} beat={beat} />;
  const groups: Group[] = beat.data?.groups ?? [];
  if (!groups.length) return null;
  if (still) return <Wall group={groups[0]} index={0} />;
  return (
    <AbsoluteFill>
      {splits(beat, groups.length).map(([from, dur], i) => (
        <Sequence key={i} from={from} durationInFrames={dur} layout="none">
          <SubShot frames={dur}>
            <Wall group={groups[i]} index={i} />
          </SubShot>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
