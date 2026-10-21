// The drive film in one continuous camera: the hook's total on the top photograph, a countdown from the ninth
// photograph to the first, each flying onto the closer's wall as a tile, cut along its own line by the blade, its
// count landing on the edge and moving into its place, the ribbon of the nine standing out of the finished wall and
// folding back into it, and the closer, framed exactly as it is posted, where the dot runs the countdown across the
// wall count to count and the film holds still and silent from the moment it lands on the top count.
import {useLoader, useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {Dust, Burst} from '../../system/three/Dust';
import {clamp01, span} from '../../system/three/motion';
import {Stage} from '../../system/three/Stage';
import {fileOf, useFonts, type Font} from '../../system/three/type';
import {Finish} from '../../system/texture';
import type {Board, Clip} from '../../system/types';
import {CardView, liftOf} from './card';
import {shotAt} from './camera';
import {planOf, type Line, type Plan} from './plan';
import {Ribbon} from './ribbon';
import {Route, Spark, sparkAt, edgesOf} from './spark';
import {CardWords, CloserWords, HookWords, routeOf} from './words';

const linesOf = (plan: Plan): Line[] => [
  ...(plan.total ? [plan.total] : []), ...plan.kicker, ...plan.closer.lines,
  ...plan.cards.flatMap((c) => [...(c.count ? [c.count] : []), ...c.rest, ...Object.values(c.slotRest)]),
];

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
  const files = useMemo(() => [...new Set(plan.cards.map((c) => c.file))], [plan]);
  const route = useMemo(() => routeOf(plan, fonts), [plan, fonts]);
  const textures = useLoader(THREE.TextureLoader, files.map((f) => staticFile(f))) as THREE.Texture[];
  useMemo(() => textures.forEach((tx) => {
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    tx.needsUpdate = true;
  }), [textures]);
  // a generated clip plays on its photograph's card over its beat; with none, the card holds the photograph
  const clip = clips.find((c) => frame >= c.from && frame < c.from + c.frames);
  const clipSrc = clip ? `${clip.dir}/${String(frame - clip.from + 1).padStart(4, '0')}.jpg` : null;
  const clipTex = useClipFrame(clipSrc);
  const imageOf = useMemo(() => (f: string) => textures[files.indexOf(f)]?.image as HTMLImageElement | undefined, [textures, files]);
  const texOf = (f: string) => (clip && clip.image === f ? clipTex : textures[files.indexOf(f)]);
  const edges = useMemo(() => edgesOf(plan), [plan]);
  const ground = plan.colors[plan.closer.ground] ?? plan.closer.ground;
  // the card the camera is on, for the colour the dust is lit by
  const on = [...plan.cards].reverse().find((c) => t >= c.arrive - 0.3) ?? plan.cards[0];
  const dust = mixHex('#fffaf0', plan.colors[on.field] ?? plan.colors.paper, 0.3);
  const spark = sparkAt(edges, t);
  const ahead = sparkAt(edges, t + 0.03).p.clone().sub(spark.p);
  const dir: [number, number] = ahead.lengthSq() > 1e-6 ? [ahead.x / ahead.length(), ahead.y / ahead.length()] : [0, 1];
  const light = useMemo(() => {
    const d = new THREE.DirectionalLight('#fff4e6', 1.6);
    d.position.set(-900, 1500, 2600);
    d.target.position.set(0, 0, 0);
    d.castShadow = true;
    d.shadow.mapSize.set(2048, 2048);
    const sc = d.shadow.camera as THREE.OrthographicCamera;
    sc.left = -1500; sc.right = 1500; sc.top = 1700; sc.bottom = -1700; sc.near = 100; sc.far = 8000;
    d.shadow.bias = -0.0004;
    d.shadow.radius = 6;
    return d;
  }, []);
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
      {plan.cards.map((c, i) => <CardView key={c.key} plan={plan} card={c} index={i} t={t} texture={texOf(c.file)} />)}
      <HookWords plan={plan} fonts={fonts} t={t} />
      {plan.cards.map((c, i) => <CardWords key={c.key} plan={plan} card={c} fonts={fonts} t={t} index={i} />)}
      <CloserWords plan={plan} fonts={fonts} t={t} />
      {plan.cards.map((c, i) => {
        const e = edges[i];
        const along = e.b.clone().sub(e.a).normalize();
        return (
          <Burst key={c.key} seed={i} p0={e.a} p1={e.b} up={new THREE.Vector3(-along.y, along.x, 0)} age={t - c.cut} sweepLen={0.25} reach={170 * c.T.s}
            color={mixHex('#ffffff', plan.colors[c.field] ?? plan.colors.paper, 0.25)} height={plan.H} size={2.6 * c.T.s} />
        );
      })}
      <Dust time={Math.min(frame, Math.round(plan.closer.still * plan.pulse))} box={[[-760, -1200, 15], [760, 1200, 650]]} color={dust} height={plan.H}
        sweep={[spark.p.x, spark.p.y, 260 * Math.max(0.3, liftOf(on) / 90)]} sweepDir={dir} sweepAmt={spark.glow * clamp01(ahead.length() / (60 * on.T.s)) * (1 - span(t, plan.ribbon.at, 1))} />
      <Spark plan={plan} t={t} height={plan.H} />
      <Route plan={plan} t={t} nodes={route} />
      <Ribbon plan={plan} t={t} image={imageOf} font={fonts.get(fileOf({face: 'display'}))} />
    </group>
  );
};

export const DriveFilm: React.FC<{board: Board; clips: Clip[]}> = ({board, clips}) => {
  const frame = useCurrentFrame();
  const plan = useMemo(() => planOf(board), [board]);
  const files = useMemo(() => [...new Set(linesOf(plan).map(fileOf))], [plan]);
  const fonts = useFonts(files);
  const t = frame / plan.pulse;
  const shot = shotAt(plan, t);
  const ground = plan.colors[plan.closer.ground] ?? plan.closer.ground;
  return (
    <AbsoluteFill style={{background: ground}}>
      {fonts ? (
        <Stage pose={shot.pose} travel={shot.travel} background={ground} bloom={0.55 + 0.35 * clamp01(1 - t / 4)}>
          <Scene plan={plan} t={t} frame={frame} fonts={fonts} clips={clips} />
        </Stage>
      ) : null}
      <Finish until={Math.round(plan.closer.still * plan.pulse)} />
    </AbsoluteFill>
  );
};

