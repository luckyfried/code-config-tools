import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {faceStyle, splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Card, CARD_PAD, LivePhoto, Scrim} from '../photo';
import {Leaks} from '../texture';
import type {Beat} from '../types';

/**
 * The product still, lightly veiled, that keeps moving under the type, so no frame of the countdown stands still.
 * The veil stays light so the product's own colors survive (a heavy dark veil turns a lemon glaze olive); the type
 * carries a shadow for its contrast instead.
 */
const Under: React.FC<{beat: Beat; dim: number}> = ({beat, dim}) => {
  const {system} = useSys();
  return (
    <>
      <LivePhoto file={beat.photos?.[0] ?? ''} treatment="push" intensity={1.2} />
      <AbsoluteFill style={{background: system.colors.bg, opacity: dim}} />
      <Leaks strength={0.9} seed={beat.id} />
    </>
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
      <Under beat={beat} dim={0.28} />
      <SafeBox name="tick" justify="center" align="center">
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textShadow: '0 4px 30px rgba(0,0,0,0.55)'}}>
          <div style={{...faceStyle(system.display), fontSize: Math.min(s.width / (String(days).length * 0.62), system.scale.hero * 2.4), lineHeight: 0.85,
            color: system.direction === 'kinetic' ? system.colors.accent : system.colors.ink, transform: `scale(${0.75 + 0.25 * p})`, opacity: tween(0, 1, 0, 5)}}>
            {days}
          </div>
          <Line text={label} delay={4} size={system.scale.label * 1.3} />
        </div>
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
      <Under beat={beat} dim={d === 'editorial' ? 0.15 : 0.35} />
      <Scrim side="bottom" strength={0.8} />
      {day !== undefined ? (
        <SafeBox name="date-day" justify="start" align={d === 'kinetic' ? 'center' : 'end'}>
          <div style={{...faceStyle(system.display), fontSize: system.scale.hero * 2.2, lineHeight: 0.8, color: 'transparent',
            WebkitTextStroke: `3px ${system.colors.ink}`, opacity: 0.9 * p, transform: `translateY(${(1 - p) * 20}%)`}}>
            {day}
          </div>
        </SafeBox>
      ) : null}
      <SafeBox name="date" justify="end" align={d === 'kinetic' ? 'center' : 'start'}>
        {d === 'editorial' ? <Card>{words}</Card> : words}
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
