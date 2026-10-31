// The person's film, one beat after another as the board lays them out: each beat's photograph where the style card
// stands it (cropped around its subject, the beat's move turning the framing), the card's ground around it, the shade
// under its words, the beat's move and the cut into it drawn over the picture, the beat's words set where the board
// set them in the card's faces and entering the card's way, and the card's closer on the sign-off. A beat that plays a
// recorded clip shows the clip's frame for the film's frame in the photograph's place, under the same crop and move.
// Everything over the picture is the stage's `over` layer, so the words, the moves, the cuts and the closer take the
// card's finish with it.
import {useLoader, useThree} from '@react-three/fiber';
import React, {useEffect, useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {closerOf} from '../system/moves';
import {land, OUT, Window} from '../system/moves/kit';
import {beatAt, fxAt, MoveLayer, nudgeAt, type Timeline} from '../system/moves/layer';
import type {BeatOn, Look} from '../system/moves/types';
import {FontGate, SystemProvider} from '../system/system';
import {clamp01, type Pt} from '../system/three/motion';
import {Stage} from '../system/three/Stage';
import {STILL} from '../system/three/travel';
import type {Beat, Clip, Face, FilmProps, System} from '../system/types';

type Line = {text: string; x: number; y: number};
type Label = {text: string; x: number; y: number; size: number; face: string; tracking: number; color: string};
type Text = {lines: Line[]; size: number; face: string; tracking: number; color: string; italic?: boolean; enter: string;
  at: number; label: Label | null; box: number[]; panel?: {box: number[]; color: string} | null};
type Picture = {file: string; aspect: number; subject?: number[]; box: [number, number, number, number]; zoom: number};
/** A beat as storyboard.py lays it out: times in musical beats from the film's start, places in frame px. */
type KitBeat = Beat & {start: number; beats: number; words: string; label: string; say: string; peak: boolean; picture: Picture | null;
  ground: string; scrim: {from: number; to: number; dark: number} | null; text: Text | null};
type KitBoard = {id: string; title: string; handle: string; signoff: string; bpm: number; format: {width: number; height: number; fps: number; name?: string};
  system: System; closer: {at: number; still: number}; beats: KitBeat[]};

const colorOf = (sys: System, c: string) => (c.startsWith('#') ? c : ((sys.colors as unknown as Record<string, string>)[c] ?? sys.colors.ink));
const faceOf = (sys: System, f: string): Face => (f === 'display' ? sys.display : sys.text);

const pulseOf = (b: KitBoard) => b.beats[0]?.pulse ?? (b.format.fps * 60) / b.bpm;

type Box = [number, number, number, number];

/** Where a beat's label and lines stand, [x0, y0, x1, y1] px, from their baselines and sizes; none when it has no
 * words of the kit's. */
const typeOf = (x: KitBeat): Box | undefined => {
  const tx = x.text;
  if (!tx || !tx.lines.length) return undefined;
  const rows = [...tx.lines.map((ln) => ({y: ln.y, size: tx.size})), ...(tx.label ? [{y: tx.label.y, size: tx.label.size}] : [])];
  const ys = rows.flatMap((r) => [r.y - r.size, r.y + 0.3 * r.size]);
  return [tx.box[0], Math.min(...ys), tx.box[2], Math.max(...ys)];
};

/** Where the photograph lies in the frame while the camera holds on it, [x, y, w, h] px: the whole photograph, of
 * which the box shows the part cropOf frames. */
const placeOf = (p: Picture): [number, number, number, number] => {
  const [x0, y0, x1, y1] = p.box;
  const c = cropOf(p, {});
  const w = (x1 - x0) / (c.u1 - c.u0), h = (y1 - y0) / (c.v1 - c.v0);
  return [x0 - c.u0 * w, y0 - (1 - c.v1) * h, w, h];
};

/** The film's beats and the moments of its cuts. A photo beat's words and label are the card's photo layout's to set,
 * so its move is handed only what the board gave it: the photograph's box and where it lies in the frame, where its
 * words stand, its line, and the beats the camera holds on it (the whole beat: the film never pulls back between
 * beats). A move that takes the frame flies the photograph in onto where it lies and hands the frame back to it; the
 * kit draws every photograph as a bare, level print (Photo), so the move lands it bare and level: no rim, tape or tilt. */
const timelineOf = (b: KitBoard): Timeline => ({
  beats: b.beats.map((x): BeatOn => ({id: x.id, form: x.form ?? 'photo', at: x.start, end: x.start + x.beats, move: x.move,
    transition: x.transition, words: x.words, label: x.label, peak: x.peak, say: x.say,
    ...(x.form === 'photo' && x.picture ? {box: x.picture.box, type: typeOf(x), held: [x.start, x.start + x.beats] as Pt,
      photo: staticFile(x.picture.file), place: placeOf(x.picture), tilt: 0, rim: 0, tape: 0} : {})})),
  cuts: b.beats.map((x) => x.start),
});

/** A card's color, a role or a hex, as a hex. */
const toneOf = (sys: System, v: string) => {
  const hex = colorOf(sys, v);
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut, and closer: the frame and its profile's safe area, the card's colors, tones, grid,
 * print and faces, the board's own words, the photograph a move draws itself (`file`, the beat's own), and every
 * photograph of the film in its order. */
const lookOf = (b: KitBoard, file: string | undefined): Look => {
  const sys = b.system;
  const W = b.format.width, H = b.format.height;
  const g = sys.photo.grid;
  const pic = sys.photo.picture;
  const m = g.margin * W;
  return {
    W, H, fps: b.format.fps, pulse: pulseOf(b), safe: b.format.name ? sys.safe[b.format.name] : undefined,
    colors: Object.fromEntries(Object.entries(sys.colors).filter(([, v]) => typeof v === 'string')) as Record<string, string>,
    display: sys.display.family, text: sys.text.family, italic: !!sys.display.italic,
    title: b.title, handle: b.handle, signoff: b.signoff,
    tone: {
      ground: toneOf(sys, sys.photo.ground), dip: sys.finish.dip === 'none' ? null : toneOf(sys, sys.finish.dip),
      matte: toneOf(sys, sys.finish.matte), light: toneOf(sys, sys.finish.light), pen: toneOf(sys, pic.penColor),
      rim: toneOf(sys, pic.rimColor), tape: toneOf(sys, pic.tapeColor),
    },
    grid: {
      m, rules: g.rules,
      cols: Array.from({length: g.cols + 1}, (_, i) => m + (i * (W - 2 * m)) / g.cols),
      rows: Array.from({length: g.rows + 1}, (_, i) => m + (i * (H - 2 * m)) / g.rows),
    },
    print: {
      box: [Math.max(0, pic.box[0]) * W, Math.max(0, pic.box[1]) * H,
        (Math.min(1, pic.box[0] + pic.box[2]) - Math.max(0, pic.box[0])) * W, (Math.min(1, pic.box[1] + pic.box[3]) - Math.max(0, pic.box[1])) * H],
      rim: pic.rim * W, tilt: pic.tilt, tape: pic.tape,
    },
    finished: sys.finish.words !== 'clean',
    photo: file ? staticFile(file) : undefined,
    photos: [...new Set(b.beats.flatMap((x) => (x.picture ? [x.picture.file] : [])))].map((f) => staticFile(f)),
  };
};

/** The part of the photograph a box shows: the photograph covering the box, `zoom` times closer, around its subject,
 * moved by the move's nudge (its `scale` multiplies the framed height, `dx` and `dy` move the middle by shares of it). */
const cropOf = (p: Picture, nudge: {scale?: number; dx?: number; dy?: number}) => {
  const [x0, y0, x1, y1] = p.box;
  const bw = x1 - x0, bh = y1 - y0;
  const rb = bh / bw;
  const z = p.zoom / (nudge.scale ?? 1);
  let su = 1, sv = 1;
  if (p.aspect > rb) sv = rb / p.aspect;
  else su = p.aspect / rb;
  su /= z;
  sv /= z;
  const [cx0, cy0] = p.subject && p.subject.length >= 2 ? p.subject : [0.5, 0.45];
  const cx = cx0 + ((nudge.dx ?? 0) * bh * su) / bw;
  const cy = cy0 + (nudge.dy ?? 0) * sv;
  const u0 = Math.min(1 - su, Math.max(0, cx - su / 2));
  const t0 = Math.min(1 - sv, Math.max(0, cy - sv / 2));
  return {u0, u1: u0 + su, v0: 1 - (t0 + sv), v1: 1 - t0};
};

const Photo: React.FC<{p: Picture; texture: THREE.Texture; W: number; H: number; nudge: {scale?: number; dx?: number; dy?: number}}> = ({p, texture, W, H, nudge}) => {
  const [x0, y0, x1, y1] = p.box;
  const c = cropOf(p, nudge);
  const geo = useMemo(() => {
    const g = new THREE.PlaneGeometry(x1 - x0, y1 - y0);
    const uv = g.attributes.uv as THREE.BufferAttribute;
    uv.setXY(0, c.u0, c.v1);
    uv.setXY(1, c.u1, c.v1);
    uv.setXY(2, c.u0, c.v0);
    uv.setXY(3, c.u1, c.v0);
    uv.needsUpdate = true;
    return g;
  }, [x0, y0, x1, y1, c.u0, c.u1, c.v0, c.v1]);
  useEffect(() => () => geo.dispose(), [geo]);
  return (
    <mesh geometry={geo} position={[(x0 + x1) / 2 - W / 2, H / 2 - (y0 + y1) / 2, 0]}>
      <meshBasicMaterial map={texture} toneMapped={false} />
    </mesh>
  );
};

/** One frame of a recorded clip as a texture, its file loaded before the film's frame is taken. */
const useClipFrame = (src: string | null) => {
  const advance = useThree((s) => s.advance);
  const tex = useMemo(() => {
    const t = new THREE.Texture();
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    return t;
  }, []);
  useLayoutEffect(() => {
    if (!src) return;
    const handle = delayRender(`clip ${src}`);
    let done = false;
    const finish = () => {
      if (!done) continueRender(handle);
      done = true;
    };
    const img = new Image();
    img.onload = () => {
      tex.image = img;
      tex.needsUpdate = true;
      advance(performance.now());
      advance(performance.now());
      finish();
    };
    img.onerror = () => {
      console.log(`IMAGE_ERROR ${src}`);
      finish();
    };
    img.src = staticFile(src);
    return () => {
      img.onload = null;
      img.onerror = null;
      finish();
    };
  }, [src, tex, advance]);
  return tex;
};

/** The file of a clip's frame for film frame `frame`: its first before the clip starts, its last after it ends. */
const clipFrameOf = (c: Clip, frame: number) =>
  `${c.dir}/${String(Math.min(c.frames - 1, Math.max(0, Math.floor((frame - c.from) * c.step))) + 1).padStart(4, '0')}.jpg`;

const Scene: React.FC<{board: KitBoard; beat: KitBeat | null; clip: string | null; nudge: {scale?: number; dx?: number; dy?: number}}> = ({board, beat, clip, nudge}) => {
  const files = useMemo(() => [...new Set(board.beats.flatMap((b) => (b.picture ? [b.picture.file] : [])))], [board]);
  const textures = useLoader(THREE.TextureLoader, files.map((f) => staticFile(f))) as THREE.Texture[];
  useMemo(() => textures.forEach((tx) => {
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    tx.minFilter = THREE.LinearMipmapLinearFilter;
    tx.needsUpdate = true;
  }), [textures]);
  const clipTex = useClipFrame(clip);
  if (!beat?.picture) return null;
  const tex = clip ? clipTex : textures[files.indexOf(beat.picture.file)];
  return <Photo p={beat.picture} texture={tex} W={board.format.width} H={board.format.height} nudge={nudge} />;
};

/** How far into its entrance line `j` of `n` is, `local` beats after the words begin. */
const entered = (enter: string, local: number, j: number, stagger: number) => {
  const l = local - j * stagger;
  if (enter === 'cut') return {o: l >= 0 ? 1 : 0, s: 1, y: 0, chars: 1};
  if (enter === 'slam') {
    const k = land(l * 1.6);
    return {o: clamp01(l * 8), s: 1.28 - 0.28 * k, y: 0, chars: 1};
  }
  if (enter === 'type') return {o: l >= 0 ? 1 : 0, s: 1, y: 0, chars: clamp01(l / 1.2)};
  const r = OUT(clamp01(l / (enter === 'fade' ? 1.6 : 1.0)));
  return {o: r, s: 1, y: (1 - r) * (enter === 'fade' ? 0.12 : 0.45), chars: 1};
};

const Words: React.FC<{board: KitBoard; beat: KitBeat; t: number}> = ({board, beat, t}) => {
  const tx = beat.text;
  if (!tx) return null;
  const sys = board.system;
  const local = t - beat.start - tx.at;
  if (local < -0.25) return null;
  const face = faceOf(sys, tx.face);
  const stagger = Math.max(0.12, sys.ease.stagger || 0.18);
  const color = colorOf(sys, tx.color);
  const W = board.format.width, H = board.format.height;
  const lab = tx.label;
  const labFace = lab ? faceOf(sys, lab.face) : null;
  const labIn = lab ? entered(tx.enter === 'slam' ? 'cut' : tx.enter, local + 0.1, 0, 0) : null;
  // the panel the lines stand on draws across from its left edge just before the first line lands
  const pan = tx.panel ? OUT(clamp01((local + 0.25) / 0.35)) : 0;
  const pb = tx.panel?.box;
  // with no photograph under it the line itself carries the beat's motion: a slow push toward the viewer about its box
  const push = beat.picture ? 1 : 1 + 0.04 * clamp01(local / Math.max(1, beat.beats - tx.at));
  const [bx0, by0, bx1, by1] = tx.box;
  const cx = (bx0 + bx1) / 2, cy = (by0 + by1) / 2;
  return (
    <>
      {pb && pan > 0 ? (
        <div style={{position: 'absolute', left: pb[0], top: pb[1], width: (pb[2] - pb[0]) * pan, height: pb[3] - pb[1],
          background: colorOf(sys, tx.panel!.color)}} />
      ) : null}
      {local >= 0 ? (
        <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
          <g transform={push !== 1 ? `translate(${cx} ${cy}) scale(${push}) translate(${-cx} ${-cy})` : undefined}>
          {lab && labFace && labIn ? (
            <text x={lab.x} y={lab.y + labIn.y * lab.size} fontFamily={`'${labFace.family}'`} fontWeight={labFace.weight}
              fontSize={lab.size} letterSpacing={lab.tracking * lab.size} fill={colorOf(sys, lab.color)} opacity={labIn.o}>
              {lab.text}
            </text>
          ) : null}
          {tx.lines.map((ln, j) => {
            const e = entered(tx.enter, local, j, stagger);
            const text = e.chars < 1 ? ln.text.slice(0, Math.ceil(ln.text.length * e.chars)) : ln.text;
            return (
              <text key={j} x={ln.x} y={ln.y + e.y * tx.size} fontFamily={`'${face.family}'`} fontWeight={face.weight}
                fontStyle={tx.italic ? 'italic' : 'normal'} fontSize={tx.size} letterSpacing={tx.tracking * tx.size} fill={color}
                opacity={e.o} transform={e.s !== 1 ? `translate(${ln.x} ${ln.y}) scale(${e.s}) translate(${-ln.x} ${-ln.y})` : undefined}
                style={{fontVariationSettings: face.axes ? Object.entries(face.axes).map(([k, v]) => `'${k}' ${v}`).join(', ') : undefined}}>
                {text}
              </text>
            );
          })}
          </g>
        </svg>
      ) : null}
    </>
  );
};

const Shade: React.FC<{beat: KitBeat; H: number}> = ({beat, H}) => {
  const s = beat.scrim;
  if (!s) return null;
  const soft = Math.min(H / 6, Math.max(1, s.to - s.from));
  const k = (soft / Math.max(1, s.to - s.from)) * 100;
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: s.from, height: s.to - s.from,
      background: `linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,${s.dark}) ${k.toFixed(1)}%, rgba(0,0,0,${s.dark}) 100%)`}} />
  );
};

/** The card's ground around the photograph, drawn over the stage so it is the same color the moves, the cuts and the
 * closer draw it in. */
const Ground: React.FC<{beat: KitBeat | null; color: string; W: number; H: number}> = ({beat, color, W, H}) => {
  const p = beat?.picture;
  if (!p) return <div style={{position: 'absolute', inset: 0, background: color}} />;
  const [x0, y0, x1, y1] = p.box;
  if (x0 <= 0 && y0 <= 0 && x1 >= W && y1 >= H) return null;
  return <Window box={[x0, y0, x1 - x0, y1 - y0]} color={color} />;
};

const Picture: React.FC<{board: KitBoard; clips: Clip[]}> = ({board, clips}) => {
  const line = useMemo(() => timelineOf(board), [board]);
  // the photograph a move draws itself is the beat's own; a beat with none takes the film's first
  const first = board.beats.find((b) => b.picture)?.picture?.file;
  const sys = board.system;
  const current = useCurrentFrame();
  const step = sys.finish.cadence > 0 ? board.format.fps / sys.finish.cadence : 1;
  const frame = Math.floor(current / step) * step;
  const pulse = pulseOf(board);
  // from the stop on, the moves read the stop's frame, and the closer keeps its slow push on the film's own time
  const now = frame / pulse;
  const t = Math.min(now, board.closer.still);
  const base = useMemo(() => lookOf(board, first), [board, first]);
  const on = beatAt(line, base, t);
  const i = on ? board.beats.findIndex((b) => b.id === on.beat.id) : -1;
  const beat = i >= 0 ? board.beats[i] : null;
  const file = beat?.picture?.file ?? first;
  const look = useMemo(() => (file === first ? base : lookOf(board, file)), [board, base, file, first]);
  const shot = beat ? clips.find((c) => c.beat === beat.id) : undefined;
  const clip = shot ? clipFrameOf(shot, Math.min(frame, Math.round(board.closer.still * pulse))) : null;
  // every photograph pushes in slowly over its beat, under whatever the move does with it, so no beat sits still
  const nudged = nudgeAt(line, look, t);
  const drift = beat ? clamp01((t - beat.start) / Math.max(1, beat.beats)) : 0;
  const nudge = {...nudged, scale: (nudged.scale ?? 1) / (1 + 0.05 * drift)};
  const travel = {...STILL, ...fxAt(line, look, t), smear: [0, 0] as [number, number]};
  const closing = !!closerOf(sys.closer) && t >= board.closer.at;
  const ground = beat ? colorOf(sys, beat.ground) : sys.colors.bg;
  // a words beat's card is held whole by the camera, so what is drawn over it pushes in slowly instead
  const push = beat?.form === 'words' ? 1 + 0.015 * drift : 1;
  const over = (
    <div style={{position: 'absolute', inset: 0, transform: `scale(${push})`}}>
      <Ground beat={beat} color={ground} W={look.W} H={look.H} />
      {beat ? <Shade beat={beat} H={look.H} /> : null}
      {beat && !closing ? <Words board={board} beat={beat} t={t} /> : null}
      <MoveLayer line={line} look={look} t={t} now={now} bars={sys.finish.bars || 0}
        closer={{name: sys.closer, at: board.closer.at, still: board.closer.still}} />
    </div>
  );
  return (
    <AbsoluteFill style={{background: ground, overflow: 'hidden'}}>
      <Stage pose={{position: [0, 0, look.H / 2 / Math.tan(Math.PI / 12)], target: [0, 0, 0], roll: 0, fov: 30}} travel={travel}
        background={ground} over={over}>
        <Scene board={board} beat={beat} clip={clip} nudge={nudge} />
      </Stage>
    </AbsoluteFill>
  );
};

/** The film of one board, under the board's style card: its faces, its colors, its finish, its moves and its closer. */
export const Film: React.FC<FilmProps> = ({board, clips}) => {
  const b = board as unknown as KitBoard;
  if (!b?.system) return <AbsoluteFill style={{background: '#000'}} />;
  return (
    <SystemProvider value={{system: b.system}}>
      <FontGate system={b.system}>
        <Picture board={b} clips={clips ?? []} />
      </FontGate>
    </SystemProvider>
  );
};

