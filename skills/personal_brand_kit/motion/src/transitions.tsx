import React from 'react';
import {AbsoluteFill, Easing, interpolate} from 'remotion';
import type {TransitionPresentation, TransitionPresentationComponentProps} from '@remotion/transitions';
import {linearTiming, springTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import {iris} from '@remotion/transitions/iris';
import type {System, Transition} from './types';

type WhipProps = {direction: string; blur: number};

/** A whip pan: both frames travel fast with motion blur, the incoming one lands on the cut. */
const Whip: React.FC<TransitionPresentationComponentProps<WhipProps>> = ({
  children,
  presentationProgress: p,
  presentationDirection,
  passedProps,
}) => {
  const sign = passedProps.direction === 'from-left' ? -1 : 1;
  const entering = presentationDirection === 'entering';
  const x = entering ? interpolate(p, [0, 1], [sign * 100, 0]) : interpolate(p, [0, 1], [0, -sign * 100]);
  const speed = Math.sin(p * Math.PI);
  return (
    <AbsoluteFill
      style={{
        transform: `translateX(${x}%) scale(${1 + 0.06 * speed})`,
        filter: `blur(${speed * passedProps.blur}px)`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

type BarProps = {color: string; second: string};

/** A wipe carried by two bars in the palette: the first color sweeps in, the next frame is under the second. */
const Bars: React.FC<TransitionPresentationComponentProps<BarProps>> = ({
  children,
  presentationProgress: p,
  presentationDirection,
  passedProps,
}) => {
  if (presentationDirection === 'exiting') return <AbsoluteFill>{children}</AbsoluteFill>;
  const a = interpolate(p, [0, 0.55], [0, 100], {extrapolateRight: 'clamp', easing: Easing.bezier(0.7, 0, 0.3, 1)});
  const b = interpolate(p, [0.2, 0.8], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.7, 0, 0.3, 1)});
  const c = interpolate(p, [0.45, 1], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.7, 0, 0.3, 1)});
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{clipPath: `inset(${100 - a}% 0 0 0)`, background: passedProps.color}} />
      <AbsoluteFill style={{clipPath: `inset(${100 - b}% 0 0 0)`, background: passedProps.second}} />
      <AbsoluteFill style={{clipPath: `inset(${100 - c}% 0 0 0)`}}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

type DipProps = {color: string};

/** A dip through a color (paper for editorial, black for documentary): out, hold a breath, in. The color sits under
 * the outgoing scene only, because the incoming scene is stacked above it and must stay see-through until it fades in. */
const Dip: React.FC<TransitionPresentationComponentProps<DipProps>> = ({
  children,
  presentationProgress: p,
  presentationDirection,
  passedProps,
}) => {
  const entering = presentationDirection === 'entering';
  const o = entering ? interpolate(p, [0.5, 1], [0, 1], {extrapolateLeft: 'clamp'}) : interpolate(p, [0, 0.5], [1, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: entering ? undefined : passedProps.color}}>
      <AbsoluteFill style={{opacity: o, transform: `scale(${entering ? 1.04 - 0.04 * p : 1 + 0.02 * p})`}}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

type MatchProps = Record<string, never>;

/** A match cut on scale: the outgoing frame pushes into the center, the incoming frame lands from the same point. */
const Match: React.FC<TransitionPresentationComponentProps<MatchProps>> = ({children, presentationProgress: p, presentationDirection}) => {
  const entering = presentationDirection === 'entering';
  const s = entering ? interpolate(p, [0, 1], [1.35, 1], {easing: Easing.bezier(0.16, 1, 0.3, 1)}) : interpolate(p, [0, 1], [1, 1.6], {easing: Easing.bezier(0.7, 0, 0.84, 0)});
  const o = entering ? interpolate(p, [0.35, 0.6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  return <AbsoluteFill style={{transform: `scale(${s})`, opacity: o}}>{children}</AbsoluteFill>;
};

const pres = <T extends Record<string, unknown>>(component: React.FC<TransitionPresentationComponentProps<T>>, props: T) =>
  ({component, props}) as TransitionPresentation<T>;

/** The presets a storyboard names: a presentation and its timing, both from the system. */
export const transitionFor = (t: Transition, system: System, width: number, height: number) => {
  const ease = Easing.bezier(...system.ease.move);
  const timing = linearTiming({durationInFrames: t.frames, easing: ease});
  const dir = (t.direction ?? 'from-right') as 'from-left' | 'from-right' | 'from-top' | 'from-bottom';
  switch (t.preset) {
    case 'whip':
      return {presentation: pres(Whip, {direction: dir, blur: 38}), timing};
    case 'slide':
      return {presentation: slide({direction: dir}), timing: springTiming({config: {damping: 200}, durationInFrames: t.frames})};
    case 'wipe':
      return {presentation: wipe({direction: dir}), timing};
    case 'iris':
      return {presentation: iris({width, height}), timing};
    case 'bars':
      return {presentation: pres(Bars, {color: system.colors.accent, second: system.colors.accent2}), timing};
    case 'dip':
      return {
        presentation: pres(Dip, {color: system.colors.bg}),
        timing,
      };
    case 'match':
      return {presentation: pres(Match, {}), timing};
    case 'fade':
    default:
      return {presentation: fade(), timing};
  }
};
