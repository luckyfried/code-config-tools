import React, {createContext, useContext, useEffect, useState} from 'react';
import {continueRender, delayRender, Easing, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Beat, Board, Safe, System} from './types';

type Ctx = {system: System; board: Board; format: string; beat?: Beat; still: boolean};
const SystemContext = createContext<Ctx | null>(null);

export const SystemProvider: React.FC<{value: Ctx; children: React.ReactNode}> = ({value, children}) => (
  <SystemContext.Provider value={value}>{children}</SystemContext.Provider>
);

export const useSys = (): Ctx => {
  const c = useContext(SystemContext);
  if (!c) throw new Error('SystemProvider is missing');
  return c;
};

export const BeatProvider: React.FC<{beat: Beat; children: React.ReactNode}> = ({beat, children}) => {
  const parent = useSys();
  return <SystemContext.Provider value={{...parent, beat}}>{children}</SystemContext.Provider>;
};

const loaded = new Set<string>();

/** The face the profile's own interface is drawn in, whatever the board's type system. */
const UI_FACE = {family: 'Inter', file: 'fonts/Inter/Inter[opsz,wght].ttf'};

/** Loads both faces of the system and the interface face before anything measures or draws text. */
export const FontGate: React.FC<{system: System; children: React.ReactNode}> = ({system, children}) => {
  const faces = [system.display, system.text, UI_FACE].filter((f, i, all) => all.findIndex((g) => g.family === f.family) === i);
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

/** Eased value between two numbers over [start, start + dur] frames, clamped. */
export const useMotion = () => {
  const {system, still, beat} = useSys();
  const frame = useCurrentFrame();
  const {fps, durationInFrames: whole} = useVideoConfig();
  const durationInFrames = beat?.frames ?? whole;
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
  /** Continuous drift across the whole sequence, for photos that never stand still. */
  const drift = (from: number, to: number) =>
    interpolate(still ? durationInFrames * 0.6 : frame, [0, durationInFrames], [from, to], {easing: curves.move});
  return {frame: f, fps, duration: durationInFrames, tween, pop, drift, stagger: e.stagger, curves};
};

export const faceStyle = (f: System['display']): React.CSSProperties => ({
  fontFamily: `'${f.family}'`,
  fontWeight: f.weight,
  letterSpacing: `${f.tracking}em`,
  textTransform: f.case === 'none' ? undefined : f.case,
  lineHeight: f.lineHeight,
  fontKerning: 'normal',
  fontFeatureSettings: '"kern" 1, "liga" 1, "tnum" 1',
});

export const src = (p: string) => (p.startsWith('http') ? p : staticFile(p));

export const hash = (s: string) => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return ((h >>> 0) % 10000) / 10000;
};

/** Gives a sub-shot its own duration so drift and settle are measured against the sub-shot. */
export const SubShot: React.FC<{frames: number; children: React.ReactNode}> = ({frames, children}) => {
  const ctx = useSys();
  const beat = ctx.beat ? {...ctx.beat, frames, settle: Math.max(Math.floor(frames * 0.5), Math.min(frames - 2, 30))} : undefined;
  return <SystemContext.Provider value={{...ctx, beat}}>{children}</SystemContext.Provider>;
};

/** Sub-shot spans of a beat: the cut points storyboard.py snapped to the music, else equal parts. */
export const splits = (beat: Beat, n: number): [number, number][] => {
  const cuts: number[] = Array.isArray(beat.data?.cuts) && beat.data.cuts.length === n - 1
    ? beat.data.cuts
    : Array.from({length: n - 1}, (_, i) => Math.round(((i + 1) * beat.frames) / n));
  const edges = [0, ...cuts, beat.frames];
  return edges.slice(0, -1).map((e, i) => [e, edges[i + 1] - e]);
};
