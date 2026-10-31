// The drive film: the hook's photograph of them together with a tag on every head, then the people one by one, each
// arriving on the closer's wall the way the style draws the beat's move, found by the tag, cut along their own edge by
// the blade, the stamp of where and when landing on the edge, the style's cut into every beat; then the closer, where
// the tag runs the wall in the film's order, and the style's own last frame, holding still and silent at the stop.
// The picture steps at the card's cadence and takes the card's finish.
import {useLoader, useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {Burst} from '../../system/three/Dust';
import {Stage} from '../../system/three/Stage';
import {fileOf, useFonts, type Font} from '../../system/three/type';
import {closerOf} from '../../system/moves';
import {MoveLayer} from '../../system/moves/layer';
import type {Board, Clip} from '../../system/types';
import {CardView, liftOf} from './card';
import {heldAt, shotAt, stationOf} from './camera';
import {onWall, planOf, type Plan} from './plan';
import {TagTrack, tagsOf} from './tag';
import {CardWords, CloserWords, HookWords} from './words';

const filesOf = (plan: Plan) => [
  ...plan.kicker, ...plan.title, ...plan.closer.lines,
  ...plan.cards.flatMap((c) => [...(c.stamp ? [c.stamp] : []), ...c.rest, ...Object.values(c.slotRest), ...c.tags, ...(c.wallTag ? [c.wallTag] : [])]),
].map((x) => fileOf(x as {face?: string}));

/** A point of card `c`'s edge at piece-frame x, in world space at the depth the card holds at. */
const edgeAt = (plan: Plan, c: Plan['cards'][number], x: number) => {
  const q = onWall(c.T, [x, c.line[0] + ((c.line[1] - c.line[0]) * x) / plan.W]);
  return new THREE.Vector3(q[0] - plan.W / 2, plan.H / 2 - q[1], liftOf(c) + 13 * c.T.s);
};

const mixHex = (a: string, b: string, u: number) => '#' + new THREE.Color(a).lerp(new THREE.Color(b), u).getHexString();

/**
 * The frame of a generated clip the film is on, as one texture whose picture is replaced each frame: the frame is
 * captured once the picture has loaded and the scene has been drawn with it.
 */
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

const Scene: React.FC<{plan: Plan; t: number; frame: number; fonts: Map<string, Font>; clips: Clip[]}> = ({plan, t, frame, fonts, clips}) => {
  const files = useMemo(() => [...new Set(plan.cards.flatMap((c) => [c.file, ...(c.keepsake ? [c.keepsake.file] : [])]))], [plan]);
  const tags = useMemo(() => tagsOf(plan), [plan]);
  const textures = useLoader(THREE.TextureLoader, files.map((f) => staticFile(f))) as THREE.Texture[];
  useMemo(() => textures.forEach((tx) => {
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    tx.needsUpdate = true;
  }), [textures]);
  // a generated clip plays on its photograph's card over its beat; with none, the card holds the photograph
  const print = clips.find((c) => frame >= c.from && frame < c.from + c.frames);
  const srcOf = (c: Clip | undefined) => (c ? `${c.dir}/${String(frame - c.from + 1).padStart(4, '0')}.jpg` : null);
  const printTex = useClipFrame(srcOf(print));
  const texOf = (f: string) => (print?.image === f ? printTex : textures[files.indexOf(f)]);
  const ground = plan.colors[plan.closer.ground] ?? plan.closer.ground;
  // a wall taller than the frame runs this far further down, and its light with it
  const below = plan.closer.height - plan.H;
  const light = useMemo(() => {
    const d = new THREE.DirectionalLight('#fff4e6', 1.6);
    d.position.set(-900, 1500, 2600);
    d.target.position.set(0, 0, 0);
    d.castShadow = true;
    d.shadow.mapSize.set(2048, 2048);
    const sc = d.shadow.camera as THREE.OrthographicCamera;
    sc.left = -1500; sc.right = 1500; sc.top = 1700; sc.bottom = -1700 - below; sc.near = 100; sc.far = 8000;
    d.shadow.bias = -0.0004;
    d.shadow.radius = 6;
    return d;
  }, [below]);
  return (
    <group>
      <hemisphereLight args={['#ffffff', '#8a7f74', 1.1]} />
      <primitive object={light} />
      <primitive object={light.target} />
      <mesh position={[0, 0, -2]} renderOrder={-10}>
        <planeGeometry args={[30000, 30000]} />
        <meshBasicMaterial color={ground} toneMapped={false} />
      </mesh>
      <mesh position={[0, 0, -1]} receiveShadow renderOrder={-9}>
        <planeGeometry args={[30000, 30000]} />
        <shadowMaterial opacity={0.3} transparent depthWrite={false} />
      </mesh>
      {plan.cards.map((c, i) => (
        <CardView key={c.key} plan={plan} card={c} index={i} t={t} texture={texOf(c.file)}
          keepTexture={c.keepsake ? textures[files.indexOf(c.keepsake.file)] : undefined}
          view={{held: heldAt(plan, i, t), station: stationOf(plan, c)}} />
      ))}
      <HookWords plan={plan} fonts={fonts} t={t} />
      {plan.cards.map((c, i) => <CardWords key={c.key} plan={plan} card={c} fonts={fonts} t={t} index={i} />)}
      {plan.closer.shape && closerOf(plan.closer.shape.name) ? null : <CloserWords plan={plan} fonts={fonts} t={t} />}
      {plan.cards.map((c, i) => {
        const a = edgeAt(plan, c, 0), b = edgeAt(plan, c, plan.W);
        const along = b.clone().sub(a).normalize();
        return (
          <Burst key={c.key} seed={i} p0={a} p1={b} up={new THREE.Vector3(-along.y, along.x, 0)} age={t - c.cut} sweepLen={0.25} reach={170 * c.T.s}
            color={mixHex('#ffffff', plan.colors[c.field] ?? plan.colors.paper, 0.25)} height={plan.H} size={2.6 * c.T.s} />
        );
      })}
      <TagTrack plan={plan} tags={tags} fonts={fonts} t={t} />
    </group>
  );
};

export const DriveFilm: React.FC<{board: Board; clips: Clip[]}> = ({board, clips}) => {
  const frame = useCurrentFrame();
  const plan = useMemo(() => planOf(board), [board]);
  const files = useMemo(() => [...new Set(filesOf(plan))], [plan]);
  const fonts = useFonts(files);
  // the picture steps at the card's cadence (a film's 18 frames a second holds each drawing that long), and from the
  // stop on it holds
  const step = plan.finish.cadence > 0 ? board.format.fps / plan.finish.cadence : 1;
  const t = Math.min((Math.floor(frame / step) * step) / plan.pulse, plan.closer.still);
  const shot = shotAt(plan, t);
  const ground = plan.colors[plan.closer.ground] ?? plan.closer.ground;
  const shape = plan.closer.shape;
  return (
    <AbsoluteFill style={{background: ground}}>
      {fonts ? (
        <Stage pose={shot.pose} travel={shot.travel} background={ground}
          over={<MoveLayer line={plan.over} look={plan.look} t={t} bars={plan.finish.bars}
            closer={shape ? {name: shape.name, at: shape.at, still: plan.closer.still} : undefined} />}>
          <Scene plan={plan} t={t} frame={frame} fonts={fonts} clips={clips} />
        </Stage>
      ) : null}
    </AbsoluteFill>
  );
};

