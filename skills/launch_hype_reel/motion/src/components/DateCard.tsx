import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {faceStyle, splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, tint} from '../photo';
import {Leaks} from '../texture';
import type {Beat} from '../types';

/**
 * The product still, unveiled, that keeps moving under the type, so no frame of the countdown stands still. The photo
 * keeps its own colors everywhere except the band behind the words.
 */
const Under: React.FC<{beat: Beat}> = ({beat}) => (
  <>
    <LivePhoto file={beat.photos?.[0] ?? ''} treatment="push" intensity={1.2} />
    <Leaks strength={0.9} seed={beat.id} />
  </>
);

/**
 * The type's seat on a photo of any lightness: a feathered band of the background behind the words only. The feather is
 * a box shadow, so the band never adds to the size the safe box measures; a safe box holding a band lets it show past
 * its edge (FEATHER).
 */
const BAND = 0.7;
/** A count's numeral is display size and needs less of a seat than the date's small lines. */
const TICK_BAND = 0.5;
const FEATHER: React.CSSProperties = {overflow: 'visible'};
const Band: React.FC<{children: React.ReactNode; strength?: number}> = ({children, strength = BAND}) => {
  const {system} = useSys();
  const fill = tint(system.colors.bg, strength);
  return (
    <div style={{position: 'relative'}}>
      <div style={{position: 'absolute', inset: 0, background: fill, boxShadow: `0 0 90px 80px ${fill}`, borderRadius: 60, pointerEvents: 'none'}} />
      <div style={{position: 'relative'}}>{children}</div>
    </div>
  );
};

/** One count: the number of days left, large, and the words under it. */
const Tick: React.FC<{beat: Beat; days: number; label: string}> = ({beat, days, label}) => {
  const {system} = useSys();
  const s = useSafe();
  const {pop, tween} = useMotion();
  const p = pop(0, system.direction === 'kinetic' ? {damping: 12, stiffness: 200} : undefined);
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <Under beat={beat} />
      <SafeBox name="tick" justify="center" align="center" style={FEATHER}>
        <Band strength={TICK_BAND}>
          <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textShadow: '0 4px 30px rgba(0,0,0,0.55)'}}>
            <div style={{...faceStyle(system.display), fontSize: Math.min(s.width / (String(days).length * 0.62), system.scale.hero * 2.4), lineHeight: 0.85,
              color: system.direction === 'kinetic' ? system.colors.accent : system.colors.ink, transform: `scale(${0.75 + 0.25 * p})`, opacity: tween(0, 1, 0, 5)}}>
              {days}
            </div>
            <Line text={label} delay={4} size={system.scale.label * 1.3} />
          </div>
        </Band>
      </SafeBox>
    </AbsoluteFill>
  );
};

/** The date itself: the product's name, the date the person gave, the days left. */
const Day: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {pop} = useMotion();
  const t = beat.text ?? {};
  const d = system.direction;
  const day = beat.data?.day as number | undefined;
  const weekday = beat.data?.weekday as string | undefined;
  const p = pop(2);
  const words = (
    <>
      {t.kicker ? <Kicker text={t.kicker} delay={2} color={system.colors.accent} /> : null}
      {t.headline ? <Headline text={t.headline} max="hero" lines={2} delay={6} width={d === 'editorial' ? s.width - 2 * CARD_PAD : undefined} /> : null}
      {t.line ? <Line text={weekday ? `${weekday} · ${t.line}` : t.line} delay={14} /> : null}
    </>
  );
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <Under beat={beat} />
      {/* The outlined day carries a thin halo of the background, so its line reads on a white plate and on a dark field alike. */}
      {day !== undefined ? (
        <SafeBox name="date-day" justify="start" align={d === 'kinetic' ? 'center' : 'end'}>
          <div style={{...faceStyle(system.display), fontSize: system.scale.hero * 2.2, lineHeight: 0.8, color: 'transparent',
            WebkitTextStroke: `3px ${system.colors.ink}`, opacity: 0.9 * p, transform: `translateY(${(1 - p) * 20}%)`,
            filter: `drop-shadow(0 0 1.5px ${system.colors.bg}) drop-shadow(0 0 1.5px ${system.colors.bg}) drop-shadow(0 6px 22px rgba(0,0,0,0.45))`}}>
            {day}
          </div>
        </SafeBox>
      ) : null}
      <SafeBox name="date" justify="end" align={d === 'kinetic' ? 'center' : 'start'} style={d === 'editorial' ? undefined : FEATHER}>
        {d === 'editorial' ? <Card>{words}</Card> : <Band>{words}</Band>}
      </SafeBox>
    </AbsoluteFill>
  );
};

/** The countdown beat: with data.ticks, each count is its own sub-shot and the date lands last; as a card, the date alone. */
export const DateCard: React.FC<{beat: Beat}> = ({beat}) => {
  const {still, system} = useSys();
  const ticks: number[] = Array.isArray(beat.data?.ticks) ? beat.data.ticks : [];
  if (still || !ticks.length) return <Day beat={beat} />;
  const parts = splits(beat, ticks.length + 1);
  const label = (n: number) => (n === 1 ? 'day to go' : 'days to go');
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {parts.map(([from, n], i) => (
        <Sequence key={i} from={from} durationInFrames={n} layout="none">
          <SubShot frames={n} settle={i < ticks.length ? undefined : Math.max(Math.floor(n * 0.5), n - 3)}>
            {i < ticks.length ? <Tick beat={beat} days={ticks[i]} label={label(ticks[i])} /> : <Day beat={beat} />}
          </SubShot>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
