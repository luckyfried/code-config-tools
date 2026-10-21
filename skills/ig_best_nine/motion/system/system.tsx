import React, {createContext, useContext, useEffect, useState} from 'react';
import {continueRender, delayRender, Easing, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Beat, Board, Safe, System, Transition} from './types';

/** `enter` is the move the beat cuts in on, `exit` the move it cuts out on (the next beat's transition). */
type Ctx = {system: System; board: Board; format: string; beat?: Beat; still: boolean; enter?: Transition | null; exit?: Transition | null};
const SystemContext = createContext<Ctx | null>(null);

export const SystemProvider: React.FC<{value: Ctx; children: React.ReactNode}> = ({value, children}) => (
  <SystemContext.Provider value={value}>{children}</SystemContext.Provider>
);

export const useSys = (): Ctx => {
  const c = useContext(SystemContext);
  if (!c) throw new Error('SystemProvider is missing');
  return c;
};

export const BeatProvider: React.FC<{beat: Beat; enter?: Transition | null; exit?: Transition | null; children: React.ReactNode}> = ({
  beat,
  enter = null,
  exit = null,
  children,
}) => {
  const parent = useSys();
  return <SystemContext.Provider value={{...parent, beat, enter, exit}}>{children}</SystemContext.Provider>;
};

const loaded = new Set<string>();

/** Loads both faces of the system before anything measures or draws text. */
export const FontGate: React.FC<{system: System; children: React.ReactNode}> = ({system, children}) => {
  const faces = [system.display, system.text];
  const key = faces.map((f) => f.family).join('|');
  const [ready, setReady] = useState(faces.every((f) => loaded.has(f.family)));
  const [handle] = useState(() => (ready ? null : delayRender(`fonts ${key}`)));
  useEffect(() => {
    if (ready) return;
    Promise.all(
      faces.map(async (f) => {
        if (loaded.has(f.family)) return;
        const face = new FontFace(f.family, `url(${staticFile(f.file)})`, {weight: '100 900'});
        await face.load();
        document.fonts.add(face);
        loaded.add(f.family);
      }),
    )
      .then(() => {
        setReady(true);
        if (handle !== null) continueRender(handle);
      })
      .catch((e) => {
        console.log(`FONT_ERROR ${String(e)}`);
        setReady(true);
        if (handle !== null) continueRender(handle);
      });
  }, []);
  return ready ? <>{children}</> : null;
};

export const useSafe = (): Safe & {width: number; height: number; W: number; H: number} => {
  const {system, format} = useSys();
  const {width, height} = useVideoConfig();
  const s = system.safe[format] ?? system.safe.reel;
  return {...s, W: width, H: height, width: width - s.left - s.right, height: height - s.top - s.bottom};
};

/** Frames per musical beat when snap has not set one: the board's tempo at 30 fps. */
export const pulseOf = (beat: Beat | undefined, board: Board | undefined, fps = 30) =>
  beat?.pulse ?? (fps * 60) / (board?.bpm || 100);

/** Frames a beat runs: what snap set, else its bars at the board's tempo. */
export const framesOf = (beat: Beat, board: Board | undefined, fps = 30) =>
  beat.frames ?? Math.round(beat.bars * 4 * pulseOf(beat, board, fps));

/**
 * The beat's clock and the system's easing. `frame` is the frame inside the beat; `at(b)` turns a musical beat
 * into frames; `tween` and `pop` are clamped and eased; a still (a card) sees every motion settled.
 */
export const useMotion = () => {
  const {system, still, beat, board} = useSys();
  const frame = useCurrentFrame();
  const {fps, durationInFrames: whole} = useVideoConfig();
  const duration = beat ? framesOf(beat, board, fps) : whole;
  const pulse = pulseOf(beat, board, fps);
  const e = system.ease;
  const curves = {
    enter: Easing.bezier(...e.enter),
    exit: Easing.bezier(...e.exit),
    move: Easing.bezier(...e.move),
  };
  const f = still ? 100000 : frame;
  const tween = (from: number, to: number, start: number, dur: number, curve: keyof typeof curves = 'enter') =>
    interpolate(f, [start, start + Math.max(1, dur)], [from, to], {
      easing: curves[curve],
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
  const pop = (delay = 0, cfg?: Partial<System['ease']['spring']>) =>
    still ? 1 : spring({frame: frame - delay, fps, config: {...e.spring, ...cfg}});
  /** The overshooting spring of a thing that lands on a beat. */
  const hit = (delay = 0) => (still ? 1 : spring({frame: frame - delay, fps, config: e.hit ?? {damping: 12, stiffness: 200, mass: 0.7}}));
  /** Continuous eased travel across the whole beat, for things that never stand still. */
  const drift = (from: number, to: number) =>
    interpolate(still ? duration * 0.6 : frame, [0, duration], [from, to], {easing: curves.move, extrapolateRight: 'clamp'});
  /** Linear travel across the beat (and past it while a dissolve holds the beat on screen). */
  const travel = (from: number, to: number) => from + (to - from) * ((still ? duration * 0.6 : frame) / Math.max(1, duration));
  const at = (b: number | undefined) => Math.round((b ?? 0) * pulse);
  return {frame: f, fps, duration, pulse, at, tween, pop, hit, drift, travel, stagger: e.stagger, curves, still};
};

/** A palette key resolved to its color; anything else is taken as a CSS color. */
export const useColor = () => {
  const {system} = useSys();
  return (c: string | undefined, fallback: keyof System['colors'] = 'accent') => {
    const k = (c ?? fallback) as keyof System['colors'];
    const v = system.colors[k];
    return typeof v === 'string' ? v : (c as string);
  };
};

/** A color with alpha, from a #rrggbb hex. */
export const tint = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1, 7), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

/** A face's variable axes as a CSS font-variation-settings value. */
export const axesOf = (f: System['display']) =>
  f.axes ? Object.entries(f.axes).map(([k, v]) => `'${k}' ${v}`).join(', ') : undefined;

export const faceStyle = (f: System['display']): React.CSSProperties => ({
  fontFamily: `'${f.family}'`,
  fontWeight: f.weight,
  letterSpacing: `${f.tracking}em`,
  textTransform: f.case === 'none' ? undefined : f.case,
  lineHeight: f.lineHeight,
  fontKerning: 'normal',
  fontFeatureSettings: '"kern" 1, "liga" 1, "tnum" 1',
  fontVariationSettings: axesOf(f),
});

export const src = (p: string) => (p.startsWith('http') ? p : staticFile(p));

export const hash = (s: string) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return ((h >>> 0) % 10000) / 10000;
};
