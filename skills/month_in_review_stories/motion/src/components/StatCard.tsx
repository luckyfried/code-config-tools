import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {faceStyle, splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Counter, Kicker, Line, SafeBox} from '../text';
import {LivePhoto, Scrim} from '../photo';
import type {Beat} from '../types';

type Stat = {value: number; label: string; line?: string};

const sizeFor = (text: string, width: number, family: string, weight: number, cap: number) => {
  const m = measureText({text, fontFamily: `'${family}'`, fontWeight: weight, fontSize: 100, letterSpacing: '0em'});
  return Math.min(cap, Math.floor((width / m.width) * 100 * 0.96));
};

/** One stat on screen: the number counts up, the label lands under it. */
const One: React.FC<{stat: Stat; index: number; photo?: string; kicker?: string}> = ({stat, index, photo, kicker}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween} = useMotion();
  const d = system.direction;
  const text = stat.value.toLocaleString('en-US');
  const size = sizeFor(text, s.width, system.display.family, system.display.weight, system.scale.hero * (d === 'kinetic' ? 1.6 : 1.15));
  const label = (
    <div style={{...faceStyle(system.text), fontSize: system.scale.h3, fontWeight: d === 'kinetic' ? 800 : 500, lineHeight: 1.05, marginTop: 18, color: system.colors.ink, opacity: tween(0, 1, 8, 10), transform: `translateY(${tween(30, 0, 8, 16)}px)`}}>
      {stat.label}
    </div>
  );
  if (d === 'kinetic') {
    const fills = [system.colors.accent, system.colors.bg, system.colors.accent2];
    return (
      <AbsoluteFill style={{background: fills[index % 3]}}>
        {photo ? (
          <AbsoluteFill style={{opacity: 0.28, mixBlendMode: 'luminosity'}}>
            <LivePhoto file={photo} treatment="push" intensity={1.6} />
          </AbsoluteFill>
        ) : null}
        <SafeBox name={`stat-${index}`} justify="center">
          {kicker ? <Kicker text={kicker} color={system.colors.ink} /> : null}
          <Counter value={stat.value} size={size} dur={18} />
          {label}
          {stat.line ? <Line text={stat.line} delay={14} /> : null}
        </SafeBox>
      </AbsoluteFill>
    );
  }
  if (d === 'documentary') {
    return (
      <AbsoluteFill style={{background: '#000'}}>
        {photo ? <LivePhoto file={photo} treatment={index % 2 ? 'mask' : 'push'} /> : null}
        <Scrim side="bottom" strength={0.85} />
        <SafeBox name={`stat-${index}`} justify="end">
          <div style={{height: 4, width: `${tween(0, 100, 0, 20)}%`, background: system.colors.accent, marginBottom: 26}} />
          {kicker ? <Kicker text={kicker} /> : null}
          <Counter value={stat.value} size={Math.min(size, system.scale.hero)} dur={22} />
          {label}
          {stat.line ? <Line text={stat.line} delay={16} /> : null}
        </SafeBox>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {photo ? (
        <div style={{position: 'absolute', left: s.left, right: s.right, top: s.top, height: s.height * 0.46, overflow: 'hidden', clipPath: `inset(${(1 - tween(0, 1, 0, 24)) * 100}% 0 0 0)`}}>
          <LivePhoto file={photo} treatment="push" />
        </div>
      ) : null}
      <SafeBox name={`stat-${index}`} justify="end">
        {kicker ? <Kicker text={kicker} /> : null}
        <Counter value={stat.value} size={Math.min(size, system.scale.hero)} dur={26} />
        <div style={{height: 2, width: `${tween(0, 100, 6, 26)}%`, background: system.colors.ink, opacity: 0.4, marginTop: 20}} />
        {label}
        {stat.line ? <Line text={stat.line} delay={16} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};

/** Every stat on one card, number over label, for the carousel's numbers page. */
const Ledger: React.FC<{stats: Stat[]; kicker?: string; photo?: string}> = ({stats, kicker, photo}) => {
  const {system} = useSys();
  const s = useSafe();
  const d = system.direction;
  const rows = stats.slice(0, 6);
  const cols = rows.length > 3 ? 2 : 1;
  const colW = (s.width - (cols - 1) * 48) / cols;
  const widest = rows.reduce((a, r) => (r.value.toLocaleString('en-US').length > a.length ? r.value.toLocaleString('en-US') : a), '0');
  const rowsPer = Math.ceil(rows.length / cols);
  const room = (s.height - 160) / rowsPer;
  const size = Math.min(sizeFor(widest, colW, system.display.family, system.display.weight, system.scale.h1 * 1.4), room * 0.62);
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {photo ? (
        <AbsoluteFill style={{opacity: d === 'editorial' ? 0.14 : 0.22}}>
          <LivePhoto file={photo} treatment="push" />
        </AbsoluteFill>
      ) : null}
      <SafeBox name="stat-ledger" justify="center">
        {kicker ? <Kicker text={kicker} /> : null}
        <div style={{display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, columnGap: 48, rowGap: room * 0.12, width: '100%'}}>
          {rows.map((r, i) => (
            <div key={i} style={{borderTop: `2px solid ${d === 'kinetic' ? system.colors.accent : system.colors.muted}`, paddingTop: 14}}>
              <div style={{...faceStyle(system.display), fontSize: size, lineHeight: 1, color: i % 3 === 1 && d === 'kinetic' ? system.colors.accent : system.colors.ink}}>
                {r.value.toLocaleString('en-US')}
              </div>
              <div style={{...faceStyle(system.text), textTransform: 'none', fontSize: system.scale.label * 1.15, fontWeight: 500, marginTop: 8, color: system.colors.ink, opacity: 0.8}}>
                {r.label}
              </div>
              {r.line ? (
                <div style={{...faceStyle(system.text), textTransform: 'none', fontSize: system.scale.label, fontWeight: 600, marginTop: 4, color: system.colors.accent}}>
                  {r.line}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </SafeBox>
    </AbsoluteFill>
  );
};

export const StatCard: React.FC<{beat: Beat}> = ({beat}) => {
  const stats: Stat[] = beat.data?.stats ?? [];
  const {still} = useSys();
  const photos = beat.photos ?? [];
  if (!stats.length) return null;
  if (still) return stats.length > 2 ? <Ledger stats={stats} kicker={beat.text?.kicker} photo={photos[0]} /> : <One stat={stats[0]} index={0} photo={photos[0]} kicker={beat.text?.kicker} />;
  return (
    <AbsoluteFill>
      {splits(beat, stats.length).map(([from, dur], i) => (
        <Sequence key={i} from={from} durationInFrames={dur} layout="none">
          <SubShot frames={dur}>
            <One stat={stats[i]} index={i} photo={photos[i % Math.max(1, photos.length)]} kicker={i === 0 ? beat.text?.kicker : undefined} />
          </SubShot>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
