// The reel in one continuous camera: the month's peak moment first, then every other moment in date order, each
// flying in with its photograph on a band, the line climbing across it from the foot of its post's cell to the cell's
// top with their words on the ground under it, the photograph setting into its cell as the camera leaves,
// and the closer: the wall of the month's posts, each its photograph with its day beneath it, the other posts rising
// out of the wall and every moment standing out furthest, lit, with the month's line and the ask landing under it, held
// still and silent from the board's stop. The style card's move for each beat and its cut into it play over the
// picture and turn the camera, and its closing page comes over the wall to end the film.
import {useLoader, useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {Dust} from '../../system/three/Dust';
import {Stage} from '../../system/three/Stage';
import {fileOf, useFonts, type Font} from '../../system/three/type';
import {MoveLayer} from '../../system/moves/layer';
import {useSys} from '../../system/system';
import type {Clip} from '../../system/types';
import {shotAt} from './camera';
import {Sheet} from './card';
import {lookOf, pulseOf, type Reel} from './plan';
import {brightest} from '../story/plan';
import {Wall} from './wall';
import {CloserWords, linesOf, PostWords} from './words';

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

const Scene: React.FC<{reel: Reel; t: number; frame: number; fonts: Map<string, Font>; clips: Clip[]}> = ({reel: r, t, frame, fonts, clips}) => {
  const files = useMemo(() => [...new Set([...r.cards.map((c) => c.file), ...r.closer.tiles.map((x) => x.file)].filter((f): f is string => !!f))], [r]);
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
  const texOf = (f: string | null) => (!f ? null : clip && clip.image === f ? clipTex : textures[files.indexOf(f)] ?? null);
  const tileTex = useMemo(() => r.closer.tiles.map((x) => (x.file ? textures[files.indexOf(x.file)] ?? null : null)), [r, textures, files]);
  // the light is the palette's own: the key in its brightest color, the fill from below in its muted one
  const key = useMemo(() => brightest(r.colors), [r.colors]);
  const light = useMemo(() => {
    const d = new THREE.DirectionalLight(key, 1.6);
    d.position.set(-900, 1500, 2600);
    d.target.position.set(0, 0, 0);
    d.castShadow = true;
    d.shadow.mapSize.set(2048, 2048);
    const sc = d.shadow.camera as THREE.OrthographicCamera;
    sc.left = -1500; sc.right = 1500; sc.top = 1700; sc.bottom = -1700; sc.near = 100; sc.far = 8000;
    d.shadow.bias = -0.0004;
    d.shadow.radius = 6;
    return d;
  }, [key]);
  return (
    <group>
      <hemisphereLight args={[key, r.colors.muted, 1.1]} />
      <primitive object={light} />
      <primitive object={light.target} />
      <mesh position={[0, 0, -2]} renderOrder={-10}>
        <planeGeometry args={[30000, 30000]} />
        <meshBasicMaterial color={r.colors.bg} toneMapped={false} />
      </mesh>
      <mesh position={[0, 0, -1]} receiveShadow renderOrder={-9}>
        <planeGeometry args={[30000, 30000]} />
        <shadowMaterial opacity={0.35} transparent depthWrite={false} />
      </mesh>
      {r.cards.map((c, i) => <Sheet key={c.key} reel={r} card={c} index={i} t={t} texture={texOf(c.file)} />)}
      <Wall reel={r} t={t} tileTex={tileTex} />
      <PostWords reel={r} fonts={fonts} t={t} />
      <CloserWords reel={r} fonts={fonts} t={t} />
      {/* the dust drifts just over the wall, behind every card and word, so it moves past the cards as the camera travels */}
      <Dust time={Math.min(frame, Math.round(r.closer.still * pulseOf(r)))} box={[[-760, -1200, 3], [760, 1200, 14]]} color={r.colors.accent2} height={r.H}
        sweep={[0, 0, 1]} sweepDir={[0, 1]} sweepAmt={0} />
    </group>
  );
};

export const ClimbFilm: React.FC<{reel: Reel; clips: Clip[]}> = ({reel: r, clips}) => {
  const frame = useCurrentFrame();
  const files = useMemo(() => [...new Set(linesOf(r).map(fileOf))], [r]);
  const fonts = useFonts(files);
  const pulse = pulseOf(r);
  const t = frame / pulse;
  const sys = useSys().system;
  const look = useMemo(() => lookOf(r, sys), [r, sys]);
  const shot = shotAt(r, t, pulse, r.timeline, look);
  const page = r.closer.page;
  return (
    <AbsoluteFill style={{background: r.colors.bg}}>
      {fonts ? (
        <Stage pose={shot.pose} travel={shot.travel} background={r.colors.bg}
          over={<MoveLayer line={r.timeline} look={look} t={Math.min(t, page.still)} bars={sys.finish.bars} closer={page} />}>
          <Scene reel={r} t={t} frame={frame} fonts={fonts} clips={clips} />
        </Stage>
      ) : null}
    </AbsoluteFill>
  );
};
