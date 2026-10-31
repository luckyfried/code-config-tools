// The camera's space a film is shot in: one WebGL canvas the size of the frame, a camera set for each frame from a
// pose and leaned into a sideways move as far as the style's easing says (where the pose holds, the camera holds
// exactly), the frame held until every texture and font is in, drawn again after every effect has run, and a finishing
// pass (bloom on what is brighter than the style's halation threshold, then the travel pass and the film's finish: its
// one grade, its vignette and its grain, on every film and card a kit draws through the stage). Every finish value is
// the style card's (the board's `system.finish`), zero included; a board without a card finishes with its `texture`.
import {useThree} from '@react-three/fiber';
import {Bloom, EffectComposer} from '@react-three/postprocessing';
import {ThreeCanvas} from '@remotion/three';
import {Suspense, useId, useLayoutEffect, useMemo, type CSSProperties, type ReactNode} from 'react';
import {continueRender, delayRender, random, useCurrentFrame, useVideoConfig} from 'remotion';
import * as THREE from 'three';
import {useSys} from '../system';
import type {Vec3} from './motion';
import {IDENTITY, TravelEffect, type Finish, type Grade, type Travel} from './travel';

/** Where the camera stands, what it looks at, its roll in radians, and its vertical field of view in degrees. */
export type Pose = {position: Vec3; target: Vec3; roll: number; fov: number};

/** A style card's finish, as the board's system carries it: each value is used as it is. */
export type CardFinish = {
  grain: number; vignette: number; bloom: number; dust: number; blur: number; halation: number; cadence: number; bars: number;
  burn: string; grade: Grade; words?: 'finished' | 'clean';
};

/** What the stage reads from the board's system: the card's finish and lean when the board has a style, else the
 * older `texture`. */
type Sys = {finish?: CardFinish; texture?: {grain?: number; vignette?: number}; ease?: {lean?: number}};
export const finishOf = (system: unknown): CardFinish | undefined => (system as Sys).finish;

/**
 * Sets the camera for this frame before the frame is drawn: the pose, leaned into the sideways move the travel pass
 * carries (its smear is the picture's own motion over the last half frame). Nothing else moves it, so the pose's own
 * curve is the camera's: an eased arrival arrives eased, and a pose that holds is a camera that holds.
 */
const Rig: React.FC<{pose: Pose; travel: Travel; lean: number; near: number; far: number}> = ({pose, travel, lean: most, near, far}) => {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const gl = useThree((s) => s.gl);
  useLayoutEffect(() => {
    gl.localClippingEnabled = true;
    const [px, py, pz] = pose.position;
    const [tx, ty, tz] = pose.target;
    const fwd = new THREE.Vector3(tx - px, ty - py, tz - pz).normalize();
    const lean = most * Math.tanh(-travel.smear[0] / 0.03);
    const up = new THREE.Vector3(0, 1, 0).applyAxisAngle(fwd, -(pose.roll + lean));
    camera.position.set(px, py, pz);
    camera.up.copy(up);
    camera.lookAt(tx, ty, tz);
    camera.fov = pose.fov;
    camera.near = near;
    camera.far = far;
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
  }, [camera, gl, pose, travel, most, near, far]);
  return null;
};

/** Holds the frame while anything in the scene is still loading. */
const Hold: React.FC = () => {
  useLayoutEffect(() => {
    const handle = delayRender('stage: loading');
    return () => continueRender(handle);
  }, []);
  return null;
};

/**
 * Holds the capture until the frame renderer has drawn this frame at its full size. The scene is drawn once a frame, by
 * the frame renderer after every effect has run; it is drawn here only when no draw has come after three animation
 * frames.
 */
const Settle: React.FC = () => {
  const frame = useCurrentFrame();
  const advance = useThree((s) => s.advance);
  const size = useThree((s) => s.size);
  const gl = useThree((s) => s.gl);
  useLayoutEffect(() => {
    const handle = delayRender('stage: settle');
    let id = 0;
    let passes = 0;
    let done = false;
    const drawnFrom = gl.info.render.frame;
    const finish = () => {
      if (!done) continueRender(handle);
      done = true;
    };
    const wait = () => {
      if (passes >= 3) advance(performance.now());
      passes += 1;
      if ((size.width === 0 || gl.info.render.frame === drawnFrom) && passes < 120) id = requestAnimationFrame(wait);
      else finish();
    };
    wait();
    return () => {
      cancelAnimationFrame(id);
      finish();
    };
  }, [frame, advance, size, gl]);
  return null;
};

const Post: React.FC<{travel: Travel; bloom: number; threshold: number; grade: Grade; finish: Finish; burn?: string}> = ({travel, bloom, threshold, grade, finish, burn}) => {
  const effect = useMemo(() => new TravelEffect(), []);
  effect.set(travel);
  effect.grade(grade);
  effect.finish(finish);
  if (burn) effect.burnColor(burn);
  return (
    <EffectComposer multisampling={4} frameBufferType={THREE.HalfFloatType}>
      <Bloom intensity={bloom} luminanceThreshold={threshold} luminanceSmoothing={0.15} mipmapBlur radius={0.7} />
      <primitive object={effect} />
    </EffectComposer>
  );
};

const LAYER: CSSProperties = {position: 'absolute', inset: 0, pointerEvents: 'none'};

/** The grain tile: one gray value a pixel around mid gray, the mean of three draws spread to the deviation the travel
 * pass's grain has, drawn once and laid from a new place on every frame. */
const TILE = 1024;
let tile: string | null = null;
const grainTile = () => {
  if (tile) return tile;
  const c = document.createElement('canvas');
  c.width = c.height = TILE;
  const ctx = c.getContext('2d')!;
  const img = ctx.createImageData(TILE, TILE);
  let s = 0x9e3779b9;
  const rnd = () => {
    s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
    return (s >>> 0) / 4294967296;
  };
  for (let i = 0; i < TILE * TILE; i++) {
    const n = Math.max(0, Math.min(1, 0.5 + 1.08 * ((rnd() + rnd() + rnd()) / 3 - 0.5)));
    const v = Math.round(n * 255);
    img.data[4 * i] = img.data[4 * i + 1] = img.data[4 * i + 2] = v;
    img.data[4 * i + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  tile = c.toDataURL('image/png');
  return tile;
};

/** The vignette the travel pass draws, as a layer: clear inside 0.45 of the way from the middle to a corner, then a
 * smoothstep to `strength` black at the corners. */
const vignetteOf = (strength: number) => {
  const stops = Array.from({length: 12}, (_, i) => {
    const r = 0.45 + (0.55 * i) / 11;
    const k = (r - 0.45) / 0.55;
    return `rgba(0,0,0,${(strength * k * k * (3 - 2 * k)).toFixed(4)}) ${(r * 100).toFixed(1)}%`;
  });
  return `radial-gradient(ellipse farthest-corner at 50% 50%, transparent 45%, ${stops.join(', ')})`;
};

/** The card's grade as a filter on the layers over the picture, in the travel pass's order: lift and gain, gamma, then
 * the saturation about Rec. 709 luma, in display values. */
const GradeFilter: React.FC<{id: string; grade: Grade}> = ({id, grade: g}) => (
  <svg width={0} height={0} style={{position: 'absolute'}}>
    <filter id={id} colorInterpolationFilters="sRGB" x="0" y="0" width="100%" height="100%">
      <feComponentTransfer>
        {(['R', 'G', 'B'] as const).map((ch, i) => {
          const F = ch === 'R' ? 'feFuncR' : ch === 'G' ? 'feFuncG' : 'feFuncB';
          return <F key={ch} type="linear" slope={g.gain[i] - g.lift[i]} intercept={g.lift[i]} />;
        })}
      </feComponentTransfer>
      <feComponentTransfer>
        <feFuncR type="gamma" amplitude={1} exponent={1 / g.gamma} offset={0} />
        <feFuncG type="gamma" amplitude={1} exponent={1 / g.gamma} offset={0} />
        <feFuncB type="gamma" amplitude={1} exponent={1 / g.gamma} offset={0} />
      </feComponentTransfer>
      <feColorMatrix type="saturate" values={String(g.saturation)} />
    </filter>
  </svg>
);

/**
 * The stage: `pose` for this frame, `travel` the finishing pass's values for it, `bloom` the glow on light brighter
 * than the halation threshold, `background` the color behind everything, `grade` the film's one grade over the whole
 * frame. Each one the kit leaves out is the style card's: its bloom, its grade, its grain, its vignette (or the kit's
 * travel `vignette` on a frame that asks for more), its blur (the share of a move's smear the shutter keeps), its
 * halation and its burn color; a board without a card takes its `texture`'s grain and vignette and draws the rest as
 * given. The grain is drawn from a new place on every frame, the held frames included. Colors are drawn as given: no
 * tone mapping.
 *
 * `over` is what is drawn over the picture (the moves, the cuts, the closer, the bars, and their words). The finish is
 * the top layer: the picture and the over layer take the grade together, and the vignette and the grain lie over both,
 * so a word takes the film's finish. A card whose words are `clean` sets the over layer above the finish instead.
 */
export const Stage: React.FC<{pose: Pose; travel: Travel; bloom?: number; background: string; grade?: Grade; near?: number; far?: number; over?: ReactNode; children: ReactNode}> = ({
  pose, travel, bloom, background, grade, near = 5, far = 40000, over, children,
}) => {
  const {width, height} = useVideoConfig();
  const sys = useSys().system as unknown as Sys;
  const card = sys.finish;
  const frame = useCurrentFrame();
  const id = useId().replace(/:/g, '');
  const blur = card ? card.blur : 1;
  const moved: Travel = {...travel, smear: [travel.smear[0] * blur, travel.smear[1] * blur]};
  const finish: Finish = {
    vignette: Math.max(card ? card.vignette : sys.texture?.vignette ?? 0, travel.vignette || 0),
    grain: card ? card.grain : sys.texture?.grain ?? 0,
    shift: [Math.floor(random(`gx${frame}`) * 1024), Math.floor(random(`gy${frame}`) * 1024)],
  };
  const look = grade ?? card?.grade ?? IDENTITY;
  // the finish lies over the words when there are words over the picture and the card does not keep them clean
  const top = over !== undefined && card?.words !== 'clean';
  const canvas = (
    <ThreeCanvas
      width={width}
      height={height}
      dpr={1}
      flat
      shadows
      gl={{antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance'}}
      camera={{fov: pose.fov, position: pose.position, near, far}}
      style={{position: 'absolute', inset: 0}}
    >
      <color attach="background" args={[background]} />
      <Suspense fallback={<Hold />}>
        <Rig pose={pose} travel={moved} lean={sys.ease?.lean ?? 0} near={near} far={far} />
        {children}
        <Post travel={moved} bloom={bloom ?? card?.bloom ?? 0.7} threshold={card ? card.halation : 1} grade={top ? IDENTITY : look}
          finish={top ? {...finish, vignette: 0, grain: 0} : finish} burn={card?.burn} />
        <Settle />
      </Suspense>
    </ThreeCanvas>
  );
  if (!top) return <>{canvas}{over}</>;
  // the picture and what is drawn over it take the grade together, so a light that screens over the picture still
  // screens over it; then the vignette and the grain over both
  return (
    <>
      <GradeFilter id={`grade-${id}`} grade={look} />
      <div style={{...LAYER, filter: `url(#grade-${id})`}}>
        {canvas}
        {over}
      </div>
      {finish.vignette > 0 ? <div style={{...LAYER, background: vignetteOf(finish.vignette)}} /> : null}
      {finish.grain > 0 ? (
        <div style={{...LAYER, mixBlendMode: 'overlay', opacity: finish.grain, backgroundImage: `url(${grainTile()})`,
          backgroundSize: `${TILE}px ${TILE}px`, backgroundPosition: `${-finish.shift[0]}px ${-finish.shift[1]}px`, imageRendering: 'pixelated'}} />
      ) : null}
    </>
  );
};
