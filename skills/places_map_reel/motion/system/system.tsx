import React, {createContext, useContext, useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import type {Beat, Board, System} from './types';

type Ctx = {system: System};
const SystemContext = createContext<Ctx | null>(null);

export const SystemProvider: React.FC<{value: Ctx; children: React.ReactNode}> = ({value, children}) => (
  <SystemContext.Provider value={value}>{children}</SystemContext.Provider>
);

export const useSys = (): Ctx => {
  const c = useContext(SystemContext);
  if (!c) throw new Error('SystemProvider is missing');
  return c;
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

/** Frames per musical beat when snap has not set one: the board's tempo at 30 fps. */
export const pulseOf = (beat: Beat | undefined, board: Board | undefined, fps = 30) =>
  beat?.pulse ?? (fps * 60) / (board?.bpm || 100);

/** Frames a beat runs: what snap set, else its bars at the board's tempo. */
export const framesOf = (beat: Beat, board: Board | undefined, fps = 30) =>
  beat.frames ?? Math.round(beat.bars * 4 * pulseOf(beat, board, fps));
