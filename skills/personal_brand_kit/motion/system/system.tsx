import React, {createContext, useContext, useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import {setFaces} from './three/type';
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

/** The files a system's faces load from: each face upright, and its italic when the card names one. */
const filesOf = (system: System) =>
  [system.display, system.text].flatMap((f) => [
    {family: f.family, file: f.file, style: 'normal'},
    ...(f.italic ? [{family: f.family, file: f.italic, style: 'italic'}] : []),
  ]);

/** Loads the faces of the system's card before anything measures or draws text, and names them to `fileOf`. */
export const FontGate: React.FC<{system: System; children: React.ReactNode}> = ({system, children}) => {
  setFaces(system);
  const files = filesOf(system);
  const key = files.map((f) => f.file).join('|');
  const [ready, setReady] = useState(files.every((f) => loaded.has(f.file)));
  const [handle] = useState(() => (ready ? null : delayRender(`fonts ${key}`)));
  useEffect(() => {
    if (ready) return;
    Promise.all(
      files.map(async (f) => {
        if (loaded.has(f.file)) return;
        const face = new FontFace(f.family, `url(${staticFile(f.file)})`, {weight: '100 900', style: f.style});
        await face.load();
        document.fonts.add(face);
        loaded.add(f.file);
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
