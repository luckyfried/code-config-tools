// The best nine's film: the board's beats in the board's order on one held frame. Each beat lays its photographs out as
// the board drew them (a photograph in its layout's box, cropped to the board's crop, the grid's nine tiles), the move
// the board chose for it moving the picture inside that crop, and its words set where the board measured them, on
// their baselines, in the card's faces. Over the picture, each beat's move, the cut into it, the card's closer and the
// beat's words, all inside the stage, so the card's finish lies over them as it lies over the picture (or under the
// words, on a card that keeps its words clean).
import {useLoader, useThree} from '@react-three/fiber';
import React, {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, Img, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {FontGate, framesOf, pulseOf, SystemProvider} from '../system/system';
import {bezier, clamp01, span} from '../system/three/motion';
import {Stage, type Pose} from '../system/three/Stage';
import {STILL} from '../system/three/travel';
import {alpha, land, px} from '../system/moves/kit';
import {fxAt, MoveLayer, nudgeAt, type Timeline} from '../system/moves/layer';
import type {BeatOn, Look} from '../system/moves/types';
import type {Pt} from '../system/three/motion';
import type {Board, Clip, FilmProps, Layer, System} from '../system/types';

/** The board as this film reads it: the shared board, with the closer's moments and the words the closer sets. */
type Nine = Board & {title: string; signoff: string; closer?: {at: number; still: number}};
type Line = {text: string; size: number; face: 'display' | 'text'; x: number; y: number; color: string; anchor?: 'middle' | 'end'};

/** The field of view the frame is held at; the camera stands where the frame fills it exactly. */
const FOV = 30;
/** How far each photograph's crop is drawn in about its focus, so a move that pulls out still finds picture. */
const ROOM = 1.12;

/** The camera that holds the whole frame, W x H px, still. */
const held = (W: number, H: number): Pose => ({position: [0, 0, H / 2 / Math.tan((FOV * Math.PI) / 360)], target: [0, 0, 0], roll: 0, fov: FOV});

/** A role of the card's colors, or a color as given. */
const colorOf = (s: System, c: string) => (c in s.colors ? (s.colors as unknown as Record<string, string>)[c] : c);

/** Where each beat starts, in frames and in musical beats, and the pulse they are counted in. */
const timeOf = (board: Nine) => {
  const fps = board.format.fps;
  const pulse = pulseOf(board.beats[0], board, fps);
  const starts: number[] = [];
  let n = 0;
  for (const b of board.beats) {
    starts.push(n);
    n += framesOf(b, board, fps);
  }
  return {pulse, starts: starts.map((f) => f / pulse), end: n / pulse};
};

/** How long before its cut a beat's words and marks have left: the words fade over the last LEAVE beats, and a mark
 * drawn on the photograph fades with them. */
const LEAVE = 0.35;

/** Where a photo beat's words stand, [x0, y0, x1, y1] px, from their baselines and sizes; none when it has none. */
const typeOf = (b: Board['beats'][number], W: number): [number, number, number, number] | undefined => {
  const lines = b.layers.filter((L) => L.kind === 'Words').flatMap((L) => L.lines as Line[]).filter((ln) => ln.text.trim());
  if (!lines.length) return undefined;
  const ys = lines.flatMap((ln) => [ln.y - ln.size, ln.y + 0.3 * ln.size]);
  const x0 = Math.min(...lines.map((ln) => ln.x));
  return [x0, Math.min(...ys), Math.max(x0 + 1, W - x0), Math.max(...ys)];
};

/** The film's beats and their cuts as the moves read them. A photo beat carries its photograph's box (the picture, inside
 * its print's rim), the box its words stand in, and the beats the frame holds on it, so a move crops, mats and marks the
 * photograph where it lies and its marks leave with the words before the cut. */
const lineOf = (board: Nine, at: number[], end: number): Timeline => ({
  beats: board.beats.map((b, i): BeatOn => {
    const x = b as unknown as {form: string; words?: string; label?: string; peak?: boolean};
    const to = i + 1 < at.length ? at[i + 1] : end;
    const pic = x.form === 'photo' ? b.layers.find((L) => L.kind === 'Photo') : undefined;
    // the grid under a move that marks a print's corner carries the box its tiles fill, so the mark lands on the grid
    const box = pic ? (pic.box as number[]) : (b as unknown as {marks?: number[]}).marks;
    return {id: b.id, form: x.form, at: at[i], end: to, move: b.move, transition: b.transition ?? null,
      words: x.words ?? '', label: x.label ?? '', peak: !!x.peak,
      ...(box ? {box: [box[0], box[1], box[0] + box[2], box[1] + box[3]] as [number, number, number, number], type: typeOf(b, board.format.width),
        held: [at[i], Math.max(at[i], to - LEAVE)] as Pt} : {})};
  }),
  cuts: at,
});

/** A card's color, a role or a hex, as a hex. */
const toneOf = (s: System, v: string) => {
  const hex = (s.colors as unknown as Record<string, string>)[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut and closer: the frame, the card's colors, tones, grid and faces, its print, and the
 * board's own words; the photograph the masked moves fill their letters with is the top of the countdown. */
const lookOf = (board: Nine, pulse: number): Look => {
  const s = board.system;
  const {swatches: _, ...colors} = s.colors;
  const W = board.format.width, H = board.format.height;
  const g = s.photo.grid;
  const pic = s.photo.picture;
  const m = g.margin * W;
  const hook = board.beats.find((b) => (b as unknown as {form: string}).form === 'title');
  const top = hook?.layers.find((L) => L.kind === 'Photo');
  return {W, H, fps: board.format.fps, pulse, colors, display: s.display.family, text: s.text.family,
    italic: !!s.display.italic, title: board.title, handle: board.handle, signoff: board.signoff,
    tone: {
      ground: toneOf(s, s.photo.ground), dip: s.finish.dip === 'none' ? null : toneOf(s, s.finish.dip), matte: toneOf(s, s.finish.matte),
      light: toneOf(s, s.finish.light), pen: toneOf(s, pic.penColor), rim: toneOf(s, pic.rimColor), tape: toneOf(s, pic.tapeColor),
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
    finished: s.finish.words !== 'clean',
    photo: top ? staticFile(top.photo.file as string) : undefined,
  };
};

/** The frame of a generated clip, as one texture whose picture is replaced each frame once it has loaded. */
const useClipFrame = (src: string | null) => {
  const advance = useThree((s) => s.advance);
  const tex = useMemo(() => {
    const t = new THREE.Texture();
    t.colorSpace = THREE.SRGBColorSpace;
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

/**
 * A photograph on the frame: the board's box (frame px) showing the board's crop of the picture, drawn in about the
 * focus by ROOM, the move's push, pull, and slide (`scale`, `dx`, `dy`, shares of the box's height) moving the picture
 * inside the box, never the box. `grow` scales the box about its middle and `alpha` fades it.
 */
const Picture: React.FC<{W: number; H: number; layer: Layer; texture: THREE.Texture; scale?: number; dx?: number; dy?: number; grow?: number; alpha?: number; order: number;
  system: System}> = ({W, H, layer, texture, scale = 1, dx = 0, dy = 0, grow = 1, alpha = 1, order, system}) => {
  const [x, y, w, h] = layer.box as number[];
  const [u0, v0, u1, v1] = layer.uv as number[];
  const [fx, fy] = (layer.focus as number[] | undefined) ?? [0.5, 0.5];
  const geo = useMemo(() => new THREE.PlaneGeometry(1, 1), []);
  const mat = useMemo(() => new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false}), []);
  // the crop in the picture's own [0, 1] coordinates, top-left origin, narrowed about the focus and moved by the move
  const cu = u0 + (u1 - u0) * fx, cv = v0 + (v1 - v0) * fy;
  const k = scale / ROOM;
  let a = cu + (u0 - cu) * k, b = cu + (u1 - cu) * k, c = cv + (v0 - cv) * k, d = cv + (v1 - cv) * k;
  const sx = (dx * h * (b - a)) / w, sy = -dy * (d - c);
  // the slide stays inside the picture
  const mx = Math.min(Math.max(sx, -a), 1 - b), my = Math.min(Math.max(sy, -c), 1 - d);
  a += mx; b += mx; c += my; d += my;
  useLayoutEffect(() => {
    const uv = geo.attributes.uv as THREE.BufferAttribute;
    // PlaneGeometry's corners: top-left, top-right, bottom-left, bottom-right; the texture's v runs bottom to top
    uv.setXY(0, a, 1 - c);
    uv.setXY(1, b, 1 - c);
    uv.setXY(2, a, 1 - d);
    uv.setXY(3, b, 1 - d);
    uv.needsUpdate = true;
  }, [geo, a, b, c, d]);
  useLayoutEffect(() => {
    mat.map = texture;
    mat.opacity = alpha;
    mat.needsUpdate = true;
  }, [mat, texture, alpha]);
  // a print: its rim of paper around it, the whole turned by its tilt, its tape across the top corners; every plane
  // lies at one depth, so each draws in its own order (shadow, rim, picture, tape) and never by the sorter's tie
  const pr = layer.print as {rim: number; rimColor: string; tilt: number; tape: number; tapeColor: string} | undefined;
  const turn = -((pr?.tilt ?? 0) * Math.PI) / 180;
  const tw = Math.min(w, h) * 0.34, th = Math.min(w, h) * 0.085;
  return (
    <group position={[x + w / 2 - W / 2, H / 2 - (y + h / 2), 0]} rotation={[0, 0, turn]} scale={[grow, grow, 1]}>
      {pr && pr.rim > 0 ? (
        <>
          {[18, 9, 3].map((r, i) => (
            <mesh key={i} renderOrder={order * 10 + i} position={[r * 0.35, -r * 0.6, 0]}>
              <planeGeometry args={[w + 2 * pr.rim + r, h + 2 * pr.rim + r]} />
              <meshBasicMaterial color={colorOf(system, 'ink')} transparent opacity={0.07 * alpha} depthWrite={false} toneMapped={false} />
            </mesh>
          ))}
          <mesh renderOrder={order * 10 + 3}>
            <planeGeometry args={[w + 2 * pr.rim, h + 2 * pr.rim]} />
            <meshBasicMaterial color={colorOf(system, pr.rimColor)} transparent opacity={alpha} depthWrite={false} toneMapped={false} />
          </mesh>
        </>
      ) : null}
      <mesh geometry={geo} material={mat} renderOrder={order * 10 + 5} scale={[w, h, 1]} />
      {pr ? [-1, 1].slice(0, pr.tape).map((side) => (
        <mesh key={side} renderOrder={order * 10 + 7} position={[side * (w / 2 - tw * 0.2), h / 2 + (pr.rim || 0) * 0.4, 0]} rotation={[0, 0, side * -0.62]}>
          <planeGeometry args={[tw, th]} />
          <meshBasicMaterial color={colorOf(system, pr.tapeColor)} transparent opacity={0.82 * alpha} depthWrite={false} toneMapped={false} />
        </mesh>
      )) : null}
    </group>
  );
};

const Scene: React.FC<{board: Nine; beat: number; local: number; t: number; line: Timeline; look: Look; frame: number; clips: Clip[]}> = ({
  board, beat, local, t, line, look, frame, clips,
}) => {
  const W = board.format.width, H = board.format.height;
  const files = useMemo(() => [...new Set(board.beats.flatMap((b) => b.layers.flatMap((L) => (L.photo ? [L.photo.file as string] : []))))], [board]);
  const textures = useLoader(THREE.TextureLoader, files.map((f) => staticFile(f))) as THREE.Texture[];
  useMemo(() => textures.forEach((tx) => {
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    tx.needsUpdate = true;
  }), [textures]);
  const clip = clips.find((c) => frame >= c.from && frame < c.from + c.frames);
  const clipTex = useClipFrame(clip ? `${clip.dir}/${String(frame - clip.from + 1).padStart(4, '0')}.jpg` : null);
  const texOf = (file: string) => (clip && clip.image === file ? clipTex : textures[files.indexOf(file)]);
  const b = board.beats[beat];
  const nudge = nudgeAt(line, look, t);
  const ease = board.system.ease;
  const enter = bezier(ease.enter);
  const form = (b as unknown as {form: string}).form;
  const sys = board.system;
  return (
    <group>
      {form === 'photo' ? (
        <mesh renderOrder={-1} position={[0, 0, -1]}>
          <planeGeometry args={[W * 1.2, H * 1.2]} />
          <meshBasicMaterial color={colorOf(sys, sys.photo.ground)} toneMapped={false} />
        </mesh>
      ) : null}
      {b.layers.map((L, i) => {
        if (L.kind === 'Photo') {
          return <Picture key={i} W={W} H={H} layer={L} texture={texOf(L.photo.file)} scale={nudge.scale} dx={nudge.dx} dy={nudge.dy} order={i} system={sys} />;
        }
        if (L.kind === 'Slice') {
          // the grid's tiles land one after another at the times the board gives them, each settling from a little
          // small; a tile that takes no beats to land stands from the cut
          const u = L.beats === 0 ? 1 : span(local, L.at ?? 0, L.beats ?? 0.5, enter);
          return <Picture key={i} W={W} H={H} layer={L} texture={texOf(L.photo.file)} grow={0.92 + 0.08 * u} alpha={u} order={i} system={sys} />;
        }
        return null;
      })}
    </group>
  );
};

/** The shades or the words of the beat (`only`), drawn on their baselines where the board measured them, each line
 * rising into place in the card's easing and the card's stagger after the one before it, and leaving before the cut.
 * The shades lie under the move's overlay, so a window's paper and the letterbox bars cover them as they cover the
 * picture; the words stand over it. */
const Words: React.FC<{board: Nine; beat: number; local: number; length: number; only: 'Shade' | 'Words'}> = ({board, beat, local, length, only}) => {
  const s = board.system;
  const enter = bezier(s.ease.enter);
  const W = board.format.width, H = board.format.height;
  const all = board.beats[beat].layers;
  const layers = all.filter((L) => L.kind === only);
  const leave = 1 - span(local, length - LEAVE, 0.3);
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position: 'absolute', inset: 0}}>
      <defs>
        {layers.map((L, i) => L.kind === 'Shade' ? (
          <linearGradient key={i} id={`shade-${beat}-${i}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={colorOf(s, L.color)} stopOpacity={0} />
            <stop offset="0.35" stopColor={colorOf(s, L.color)} stopOpacity={0.9 * (L.strength ?? 0.6)} />
            <stop offset="1" stopColor={colorOf(s, L.color)} stopOpacity={L.strength ?? 0.6} />
          </linearGradient>
        ) : null)}
      </defs>
      {layers.map((L, i) => {
        if (L.kind === 'Shade') {
          const words = all.find((x) => x.kind === 'Words');
          const u = span(local, (words?.at ?? 0) - 0.15, 0.4) * leave;
          const [x, y, w, h] = L.box as number[];
          return <rect key={i} x={x} y={y} width={w} height={h} fill={`url(#shade-${beat}-${i})`} opacity={u} />;
        }
        if (L.kind !== 'Words') return null;
        const lines = L.lines as Line[];
        const turn = L.rotate ? `rotate(${L.rotate} ${lines[0].x} ${lines[lines.length - 1].y})` : undefined;
        return (
          <g key={i} transform={turn}>
            {lines.map((ln, j) => {
              const face = ln.face === 'display' ? s.display : s.text;
              const from = (L.at ?? 0) + j * s.ease.stagger * 4;
              const len = Math.max(0.3, (L.beats ?? 1) * 0.6);
              const u = span(local, from, len, enter);
              // the card's entrance: rise into place, slam down from large, type letter by letter, fade, or cut on
              const how = (L.enter as string) ?? 'rise';
              const shown = how === 'cut' ? (local >= from ? 1 : 0) : how === 'type' ? (local >= from ? 1 : 0) : u;
              const text = how === 'type' ? ln.text.slice(0, Math.round(ln.text.length * clamp01((local - from) / len))) : ln.text;
              const dy = how === 'rise' ? (1 - u) * 0.35 * ln.size : 0;
              const big = how === 'slam' ? 1 + 0.35 * (1 - span(local, from, len * 0.5, enter)) : 1;
              const at = `translate(${ln.x} ${ln.y + dy}) scale(${big}) translate(${-ln.x} ${-ln.y})`;
              return (
                <text key={j} x={ln.x} y={ln.y} transform={at} textAnchor={ln.anchor ?? 'start'} dominantBaseline="alphabetic"
                  fontFamily={`'${face.family}'`} fontWeight={face.weight} fontSize={ln.size} letterSpacing={`${face.tracking}em`}
                  fill={colorOf(s, ln.color)} opacity={clamp01(shown) * leave}>
                  {text}
                </text>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
};

/** The scrapbook's last element: once the cover has landed, the top of the countdown is pasted onto its foot as a
 * print in the card's rim, taped at its corners in the card's tape, dropping in, turning onto its tilt and settled well
 * before the stop. It stands below the closing line, over the cover's lower edge and the page under it; it carries no
 * type, since its foot lies in the reel's caption band. */
const Keepsake: React.FC<{look: Look; u: number}> = ({look, u}) => {
  if (!look.photo) return null;
  const k = land(clamp01((u - 0.42) / 0.33));
  const side = px(look, 380), rim = px(look, 24), foot = px(look, 84);
  const tape = {position: 'absolute' as const, width: px(look, 130), height: px(look, 38), background: alpha(look.tone.tape, 0.82), top: -px(look, 16)};
  return (
    <div style={{position: 'absolute', left: look.W * 0.5, top: look.H * 0.585, width: side + 2 * rim, height: side + rim + foot,
      background: look.tone.rim, opacity: clamp01(k * 3), boxShadow: `0 ${px(look, 14)}px ${px(look, 36)}px ${alpha(look.tone.matte, 0.32)}`,
      transform: `translateY(${(1 - k) * -px(look, 60)}px) rotate(${6 + (1 - k) * 10}deg) scale(${1 + (1 - k) * 0.12})`}}>
      <Img src={look.photo} style={{position: 'absolute', left: rim, top: rim, width: side, height: side, objectFit: 'cover'}} />
      <div style={{...tape, left: -px(look, 34), transform: 'rotate(-32deg)'}} />
      <div style={{...tape, right: -px(look, 34), transform: 'rotate(32deg)'}} />
    </div>
  );
};

/** The kit's own last element over each card's closer that leaves it room. */
const KEEPSAKES: Partial<Record<string, typeof Keepsake>> = {'book-cover': Keepsake};

const Frame: React.FC<{board: Nine; clips: Clip[]}> = ({board, clips}) => {
  // a card with a cadence steps the picture at that many frames a second, as a camera that shoots fewer frames does
  const now = useCurrentFrame();
  const step = board.system.finish.cadence > 0 ? board.format.fps / board.system.finish.cadence : 1;
  const frame = Math.floor(now / step) * step;
  const {pulse, starts, end} = useMemo(() => timeOf(board), [board]);
  const line = useMemo(() => lineOf(board, starts, end), [board, starts, end]);
  const look = useMemo(() => lookOf(board, pulse), [board, pulse]);
  const W = board.format.width, H = board.format.height;
  const still = board.closer?.still ?? end;
  const t = Math.min(frame / pulse, still);
  let beat = 0;
  while (beat + 1 < starts.length && t >= starts[beat + 1]) beat++;
  const local = t - starts[beat];
  const length = (beat + 1 < starts.length ? starts[beat + 1] : end) - starts[beat];
  const travel = {...STILL, time: t * 0.25, ...fxAt(line, look, t)};
  const pose = useMemo(() => held(W, H), [W, H]);
  const Keep = KEEPSAKES[board.system.closer];
  if (!board.beats.length) return null;
  return (
    <AbsoluteFill style={{background: board.system.colors.bg}}>
      <Stage pose={pose} travel={travel} background={board.system.colors.bg}
        over={
          <>
            <Words board={board} beat={beat} local={local} length={beat + 1 < starts.length ? length : Infinity} only="Shade" />
            <MoveLayer line={line} look={look} t={t} bars={board.system.finish.bars}
              closer={board.closer ? {name: board.system.closer, at: board.closer.at, still: board.closer.still} : undefined}>
              <Words board={board} beat={beat} local={local} length={beat + 1 < starts.length ? length : Infinity} only="Words" />
              {Keep && board.closer && t >= board.closer.at
                ? <Keep look={look} u={Math.min(1, (t - board.closer.at) / Math.max(0.05, still - board.closer.at))} />
                : null}
            </MoveLayer>
          </>
        }>
        <Scene board={board} beat={beat} local={local} t={t} line={line} look={look} frame={Math.round(t * pulse)} clips={clips} />
      </Stage>
    </AbsoluteFill>
  );
};

/** The film: the board's beats on one held frame, each with the move and the cut the board chose for it, under the
 * board's style card: its faces, its finish, its closer. */
export const Film: React.FC<FilmProps> = ({board, clips}) => (
  <SystemProvider value={{system: board.system}}>
    <FontGate system={board.system}>
      <AbsoluteFill data-frame style={{background: board.system.colors.bg}}>
        <Frame board={board as Nine} clips={clips ?? []} />
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);
