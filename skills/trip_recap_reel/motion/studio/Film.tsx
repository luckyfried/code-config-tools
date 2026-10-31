// The trip film: one stop at a time, each photograph (or the person's own clip) where the card stands it, over the
// whole frame or pasted on the page with its rim, its tilt and its tape, the camera settling in from where they stood
// toward what the photograph looks at and turned by the beat's move; the trip's name and dates on the hook and each
// stop's place and line in the card's line box, in the card's faces; over it all, each beat's move, the cut into it and
// the card's closer, and the card's one finish on the picture.
import {useLoader, useThree} from '@react-three/fiber';
import React, {useLayoutEffect, useMemo, useRef, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {SINE} from '../system/moves/kit';
import {cutAt, fxAt, MoveLayer, nudgeAt} from '../system/moves/layer';
import {Dust} from '../system/three/Dust';
import {clamp01} from '../system/three/motion';
import {Stage} from '../system/three/Stage';
import {FontGate, SystemProvider} from '../system/system';
import type {Clip, FilmProps} from '../system/types';
import {cropAt, planOf, shotAt, type Plan, type Shot} from './plan';
import {Words} from './words';

const FOV = 30;

/** A damped landing at 1: the print overshoots a little and settles. */
const land = (v: number) => {
  const x = clamp01(v);
  return 1 - Math.exp(-6 * x) * Math.cos(x * Math.PI * 2.5);
};

/** The frame of a clip the film is on: one texture whose picture is replaced each frame. Until a frame's picture has
 * loaded the texture is not ready and the shot shows its photograph, and the render waits until the loaded picture has
 * been drawn twice, so no frame is ever captured on an empty texture. */
const useClipFrame = (src: string | null) => {
  const advance = useThree((s) => s.advance);
  const [loaded, setLoaded] = useState<string | null>(null);
  const wait = useRef<number | null>(null);
  const tex = useMemo(() => {
    const t = new THREE.Texture();
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    t.matrixAutoUpdate = false;
    return t;
  }, []);
  useLayoutEffect(() => {
    if (!src) return;
    const handle = delayRender(`clip ${src}`);
    wait.current = handle;
    const img = new Image();
    img.onload = () => {
      tex.image = img;
      tex.needsUpdate = true;
      setLoaded(src);
    };
    img.onerror = () => {
      console.log(`IMAGE_ERROR ${src}`);
      setLoaded(src);
    };
    img.src = staticFile(src);
    return () => {
      img.onload = null;
      img.onerror = null;
      if (wait.current === handle) {
        wait.current = null;
        continueRender(handle);
      }
    };
  }, [src, tex]);
  useLayoutEffect(() => {
    if (!src || loaded !== src || wait.current === null) return;
    advance(performance.now());
    advance(performance.now());
    const handle = wait.current;
    wait.current = null;
    continueRender(handle);
  }, [loaded, src, advance]);
  return {tex, ready: Boolean(src) && loaded === src && Boolean(tex.image)};
};

/** The texture transform that shows the crop in the picture's box: box uv to photograph uv. */
const cropMatrix = (c: {x: number; y: number; cw: number; ch: number; roll: number; A: number}) => {
  const m = new THREE.Matrix3().makeScale(1, 1 / c.A);
  m.multiply(new THREE.Matrix3().makeTranslation(c.x, c.A - c.y));
  m.multiply(new THREE.Matrix3().makeRotation(c.roll));
  m.multiply(new THREE.Matrix3().makeScale(c.cw, c.ch));
  m.multiply(new THREE.Matrix3().makeTranslation(-0.5, -0.5));
  return m;
};

const colorOf = (plan: Plan, role: string) => (plan.system.colors as Record<string, any>)[role] ?? role;

/** A flat rectangle in frame px, turned `deg` about (cx, cy). */
const Rect: React.FC<{plan: Plan; box: [number, number, number, number]; z: number; color: string; opacity?: number; turn?: [number, number, number]; order: number; clip?: THREE.Plane[]}> = ({plan, box, z, color, opacity = 1, turn, order, clip}) => {
  const [x0, y0, x1, y1] = box;
  const [cx, cy, deg] = turn ?? [(x0 + x1) / 2, (y0 + y1) / 2, 0];
  const a = (-deg * Math.PI) / 180;
  const mx = (x0 + x1) / 2 - cx, my = (y0 + y1) / 2 - cy;
  const px = cx + mx * Math.cos(-a) - my * Math.sin(-a), py = cy + mx * Math.sin(-a) + my * Math.cos(-a);
  return (
    <mesh position={[px - plan.W / 2, plan.H / 2 - py, z]} rotation={[0, 0, a]} scale={[x1 - x0, y1 - y0, 1]} renderOrder={order}>
      <planeGeometry args={[1, 1]} />
      <meshBasicMaterial color={color} transparent={opacity < 1} opacity={opacity} toneMapped={false} depthWrite={opacity >= 1} clippingPlanes={clip ?? null} />
    </mesh>
  );
};

/** Where a boxed print stands at `t`: it drops onto the page turned a little more than the card's tilt and settles. */
const settleOf = (plan: Plan, shot: Shot, t: number) => {
  if (shot.full) return {dy: 0, deg: 0, s: 1};
  const k = land((t - (shot.beat.at ?? 0)) / 1.4);
  return {dy: -plan.H * 0.05 * (1 - k), deg: shot.tilt + 5 * (1 - k), s: 1 + 0.06 * (1 - k)};
};

/** One stop's picture where it stands at `t`: a pasted print's shadow, rim and tape with it, at `opacity` (a picture
 * leaving under a dissolve fades with everything that dresses it), kept to the side of `clip` its cut leaves it. */
const Print: React.FC<{plan: Plan; shot: Shot; t: number; tex: THREE.Texture; opacity: number; order: number; clip?: THREE.Plane[]}> = ({plan, shot, t, tex, opacity, order, clip}) => {
  const crop = cropAt(plan, shot, t, nudgeAt(plan.line, plan.look, t));
  tex.matrix.copy(cropMatrix(crop));
  const pic = plan.system.photo.picture;
  const [x0, y0, x1, y1] = shot.box;
  const {dy, deg, s} = settleOf(plan, shot, t);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2 + dy;
  const hw = ((x1 - x0) / 2) * s, hh = ((y1 - y0) / 2) * s;
  const box: [number, number, number, number] = [cx - hw, cy - hh, cx + hw, cy + hh];
  const turn: [number, number, number] = [cx, cy, deg];
  const e = shot.rim * s;
  const k = Math.min(plan.W, plan.H) / 1080;
  const tapeOn = clamp01((t - (shot.beat.at ?? 0) - 0.5) / 0.4);
  const z = order * 12;
  return (
    <group>
      {!shot.full ? [0, 1, 2].map((i) => {
        const g = (6 + 10 * i) * k;
        return <Rect key={`s${i}`} plan={plan} box={[box[0] - e - g + 10 * k, box[1] - e - g + 18 * k, box[2] + e + g + 10 * k, box[3] + e + g + 18 * k]}
          z={z - 12 + i} color="#000000" opacity={0.07 * opacity} turn={turn} order={z - 12 + i} clip={clip} />;
      }) : null}
      {e > 0 ? <Rect plan={plan} box={[box[0] - e, box[1] - e, box[2] + e, box[3] + e]} z={z - 6} color={colorOf(plan, pic.rimColor)} opacity={opacity} turn={turn} order={z - 6} clip={clip} /> : null}
      <mesh position={[cx - plan.W / 2, plan.H / 2 - cy, z]} rotation={[0, 0, (-deg * Math.PI) / 180]} scale={[2 * hw, 2 * hh, 1]} renderOrder={z}>
        <planeGeometry args={[1, 1]} />
        <meshBasicMaterial map={tex} toneMapped={false} transparent={opacity < 1} opacity={opacity} depthWrite={opacity >= 1} clippingPlanes={clip ?? null} />
      </mesh>
      {Array.from({length: shot.tape}, (_, i) => {
        const len = 190 * k, wide = 52 * k;
        const [ax, ay] = i === 0 ? [box[0] - e, box[1] - e] : [box[2] + e, box[1] - e];
        const a = (i === 0 ? -1 : 1) * 38;
        return <Rect key={`t${i}`} plan={plan} box={[ax - len / 2, ay - wide / 2, ax + len / 2, ay + wide / 2]} z={z + 4 + i}
          color={colorOf(plan, pic.tapeColor)} opacity={0.78 * opacity * clamp01(tapeOn * 2 - i * 0.6)} turn={[ax, ay, a + deg]} order={z + 4 + i} clip={clip} />;
      })}
    </group>
  );
};

/** Where a cut that sweeps across the frame stands at `u`: the line under its strip or leaf, as the planes that keep the
 * stop it leaves on the side not yet swept and the stop it enters on the side swept, so the change happens under the
 * paper. The line follows the cut's own path: paper-slide's strip rising across the frame, page-turn's leaf crossing
 * it on its slant. */
const sweepOf = (plan: Plan, name: string | null | undefined, u: number): {from: THREE.Plane[]; to: THREE.Plane[]} | null => {
  const {W, H} = plan;
  let n: THREE.Vector3, c: THREE.Vector3;
  if (name === 'paper-slide') {
    const h = H * 0.42, y = H * 1.05 - SINE(u) * (H * 1.1 + h) + h / 2;
    n = new THREE.Vector3(0, -1, 0);
    c = new THREE.Vector3(0, H / 2 - y, 0);
  } else if (name === 'page-turn') {
    const k = SINE(u), w = W * 0.62, leaf = w * (1 - 0.45 * Math.sin(Math.PI * k));
    const x = W * 1.1 - k * (W * 1.2 + w) + leaf / 2, a = (8 * Math.PI) / 180;
    n = new THREE.Vector3(Math.cos(a), -Math.sin(a), 0);
    c = new THREE.Vector3(x - W / 2, 0, 0);
  } else return null;
  return {to: [new THREE.Plane(n.clone(), -n.dot(c))], from: [new THREE.Plane(n.clone().negate(), n.dot(c))]};
};

/** The two stops of a cut that does not jump while it plays, and how they share the frame: between two photographs over
 * the whole frame a dissolve carries the last picture over the next one, fading as the cut plays, so the frame goes
 * picture to picture; between pasted prints the cut's paper sweeps the one off and the other on. */
const changeAt = (plan: Plan, shot: Shot, t: number) => {
  const c = cutAt(plan.line, t);
  if (!c || c.cut.jump || c.u >= 1 || c.into.form === 'closer') return null;
  const i = plan.shots.indexOf(shot);
  // before the cut's moment the film is still on the stop the cut leaves; from it on, on the stop it enters
  const [from, to] = c.into.id === shot.beat.id ? [plan.shots[i - 1], shot] : [shot, plan.shots[i + 1]];
  if (!from || !to || to.beat.id !== c.into.id) return null;
  if (from.full && to.full) return {from, to, show: 1 - SINE(c.u), sweep: null};
  const sweep = sweepOf(plan, c.into.transition, c.u);
  return sweep ? {from, to, show: 1, sweep} : null;
};

const Scene: React.FC<{plan: Plan; t: number; frame: number; still: number; clips: Clip[]}> = ({plan, t, frame, still, clips}) => {
  const files = useMemo(() => [...new Set(plan.shots.map((s) => s.stop.photo))], [plan]);
  const textures = useLoader(THREE.TextureLoader, files.map((f) => staticFile(f))) as THREE.Texture[];
  useMemo(() => textures.forEach((tx) => {
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    tx.matrixAutoUpdate = false;
    tx.needsUpdate = true;
  }), [textures]);
  const shot = shotAt(plan, t)!;
  const clip = clips.find((c) => c.image === shot.stop.photo && frame >= c.from && frame < c.from + c.frames);
  const clipSrc = clip ? `${clip.dir}/${String(Math.floor((frame - clip.from) * (clip.step ?? 1)) + 1).padStart(4, '0')}.jpg` : null;
  const clipTex = useClipFrame(clipSrc);
  const tex = clip && clipTex.ready ? clipTex.tex : textures[files.indexOf(shot.stop.photo)];
  const gl = useThree((s) => s.gl);
  gl.localClippingEnabled = true;
  const change = changeAt(plan, shot, t);
  const other = change ? {shot: change.from === shot ? change.to : change.from} : null;
  // the other stop of a dissolve shows its photograph; two stops on one photograph share its texture, so the one in
  // front takes a copy that keeps its own crop
  const otherTex = useMemo(() => {
    if (!other) return null;
    const base = textures[files.indexOf(other.shot.stop.photo)];
    if (other.shot.stop.photo !== shot.stop.photo || tex !== base) return base;
    const copy = base.clone();
    copy.matrixAutoUpdate = false;
    copy.needsUpdate = true;
    return copy;
  }, [other?.shot, shot, tex, textures, files]);
  const ground = colorOf(plan, plan.system.photo.ground);
  const texOf = (s: Shot) => (s === shot ? tex : otherTex!);
  return (
    <group>
      <Rect plan={plan} box={[-plan.W, -plan.H, 2 * plan.W, 2 * plan.H]} z={-20} color={shot.full ? plan.system.colors.bg : ground} order={-20} />
      {change ? (
        <>
          {/* the stop arriving lies under, the one leaving over it */}
          <Print plan={plan} shot={change.to} t={t} tex={texOf(change.to)} opacity={1} order={0} clip={change.sweep?.to} />
          {change.show > 0.002 ? <Print plan={plan} shot={change.from} t={t} tex={texOf(change.from)} opacity={change.show} order={1} clip={change.sweep?.from} /> : null}
        </>
      ) : <Print plan={plan} shot={shot} t={t} tex={tex} opacity={1} order={0} />}
      <Dust time={Math.min(frame, still)} box={[[-plan.W / 2, -plan.H / 2, 15], [plan.W / 2, plan.H / 2, 650]]} color={plan.system.colors.paper}
        height={plan.H} sweep={[0, 0, 0]} sweepDir={[0, 1]} sweepAmt={0} />
    </group>
  );
};

/** The smear the picture's own motion over the last half frame leaves: none across a cut. */
const smearAt = (plan: Plan, t: number): [number, number] => {
  const half = 0.5 / plan.pulse;
  const a = shotAt(plan, t - half), b = shotAt(plan, t);
  if (!a || !b || a !== b || t - half < (b.beat.at ?? 0)) return [0, 0];
  const c0 = cropAt(plan, a, t - half, nudgeAt(plan.line, plan.look, t - half));
  const c1 = cropAt(plan, b, t, nudgeAt(plan.line, plan.look, t));
  const bw = b.box[2] - b.box[0], bh = b.box[3] - b.box[1];
  const sm: [number, number] = [(-(c1.x - c0.x) / c1.cw) * bw / plan.W, ((c1.y - c0.y) / c1.ch) * bh / plan.H];
  return Math.hypot(...sm) < 0.0008 ? [0, 0] : sm;
};

const Picture: React.FC<{plan: Plan; clips: Clip[]}> = ({plan, clips}) => {
  const now = useCurrentFrame();
  const f = plan.system.finish;
  // a card with a cadence steps the picture at that many frames a second, as a camera that shoots fewer frames does
  const step = f.cadence > 0 ? plan.fps / f.cadence : 1;
  const frame = Math.floor(now / step) * step;
  const still = Math.round(plan.closer.still * plan.pulse);
  const t = Math.min(frame, still) / plan.pulse;
  const D = plan.H / 2 / Math.tan((FOV * Math.PI) / 360);
  const travel = {zoom: 0, center: [0.5, 0.5] as [number, number], smear: smearAt(plan, t), warp: 0, burn: 0, vignette: 0, time: t * 0.25,
    ...fxAt(plan.line, plan.look, t)};
  return (
    <AbsoluteFill style={{background: plan.system.colors.bg}}>
      <Stage pose={{position: [0, 0, D], target: [0, 0, 0], roll: 0, fov: FOV}} travel={travel} background={plan.system.colors.bg}
        over={<><Words plan={plan} t={t} /><MoveLayer line={plan.line} look={plan.look} t={t} bars={f.bars} closer={plan.closer} /></>}>
        {/* the last stop stays under the closer, which dims it, covers it or lays the page over it as the card's closer does */}
        <Scene plan={plan} t={t} frame={Math.min(frame, still)} still={still} clips={clips} />
      </Stage>
    </AbsoluteFill>
  );
};

/** The film: the board's stops in the board's look, each with the move and the cut the board chose for it. */
export const Film: React.FC<FilmProps> = ({board, clips}) => {
  const plan = useMemo(() => planOf(board), [board]);
  return (
    <SystemProvider value={{system: board.system}}>
      <FontGate system={board.system}>
        <AbsoluteFill data-frame style={{background: board.system.colors.bg}}>
          <Picture plan={plan} clips={clips ?? []} />
        </AbsoluteFill>
      </FontGate>
    </SystemProvider>
  );
};

