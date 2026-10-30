// The story film in one continuous camera over one wall. It opens on the wall of their posts, every print dim in its
// tile, and dives to day one, which lifts out of its tile with their first line; then the camera walks their story print by
// print, each lifting out of the wall as the camera lands on it, standing off the wall in its light with their line on
// its label, and dropping back into its tile, lit, as the camera moves on, the chapters holding longer and the peak longest;
// until the latest drops into the last tile, the camera pulls back to the whole wall, lit, their words for the span land
// on the course of plain plaster across it, the ask lands, and the style card's closer takes the frame; picture and
// music stop together, and from that moment the picture holds still and silent. Over it the card's moves and cuts play
// on their beats (the opening's words, the flare, the dip between prints) under its letterbox bars, and the whole
// frame takes the card's finish: its grade, grain, vignette, bloom and cadence.
import {useLoader, useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo, useRef, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {Stage} from '../../system/three/Stage';
import {fileOf, useFonts, type Font} from '../../system/three/type';
import {closerOf} from '../../system/moves';
import {fxAt, MoveLayer} from '../../system/moves/layer';
import type {Board, Clip} from '../../system/types';
import {framingAt, shotAt} from './camera';
import {CardView, restZ} from './card';
import {linesOf, planOf, timesOf, type Card, type Plan} from './plan';
import {CardWords, CloserWords} from './words';

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

/**
 * The station-size photographs of the prints the camera is near (lifting out, held, or dropping), loaded as they are
 * needed and released after, so a tab holds a few large textures at once; every other card shows its tile copy.
 */
const useStationTextures = (plan: Plan, t: number) => {
  const advance = useThree((s) => s.advance);
  const cache = useRef(new Map<string, THREE.Texture>());
  const [, bump] = useState(0);
  const near = plan.cards.filter((c) => {
    const tm = timesOf(c);
    return t >= tm.rise[0] - 0.5 && t <= tm.drop[0] + tm.drop[1] + 0.25;
  }).map((c) => c.file);
  const key = near.join('|');
  useLayoutEffect(() => {
    for (const [f, tex] of cache.current) {
      if (!near.includes(f)) {
        tex.dispose();
        cache.current.delete(f);
      }
    }
    const missing = near.filter((f) => !cache.current.has(f));
    if (!missing.length) return;
    const handle = delayRender(`photos ${missing.join(' ')}`);
    let left = missing.length;
    let live = true;
    const one = () => {
      left -= 1;
      if (left > 0 || !live) return;
      bump((v) => v + 1);
      requestAnimationFrame(() => {
        advance(performance.now());
        advance(performance.now());
        continueRender(handle);
      });
    };
    for (const f of missing) {
      const img = new Image();
      img.onload = () => {
        const tex = new THREE.Texture(img);
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.anisotropy = 8;
        tex.needsUpdate = true;
        cache.current.set(f, tex);
        one();
      };
      img.onerror = () => {
        console.log(`IMAGE_ERROR ${f}`);
        one();
      };
      img.src = staticFile(f);
    }
    return () => {
      if (left > 0) continueRender(handle);
      live = false;
    };
  }, [key, advance]);
  return cache.current;
};

/** The wall: a plaster in the ground's color with a fine tooth and a light that falls a little unevenly across it,
 * quiet enough that a flat ground still reads flat, that every print stands in and casts its shadow on. */
const plaster = (ground: string) => {
  const N = 512;
  const cv = document.createElement('canvas');
  cv.width = cv.height = N;
  const g = cv.getContext('2d')!;
  g.fillStyle = ground;
  g.fillRect(0, 0, N, N);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const blot = (count: number, least: number, most: number, lift: number, shade: number) => {
    for (let i = 0; i < count; i++) {
      const x = rnd() * N, y = rnd() * N, r = least + rnd() * (most - least), light = rnd() > 0.5;
      for (const [dx, dy] of [[0, 0], [-N, 0], [N, 0], [0, -N], [0, N]]) {
        const grad = g.createRadialGradient(x + dx, y + dy, 0, x + dx, y + dy, r);
        grad.addColorStop(0, light ? `rgba(255,240,220,${lift})` : `rgba(0,0,0,${shade})`);
        grad.addColorStop(1, 'rgba(0,0,0,0)');
        g.fillStyle = grad;
        g.fillRect(x + dx - r, y + dy - r, 2 * r, 2 * r);
      }
    }
  };
  // the tooth of the plaster, then the light across it
  blot(2600, 1.5, 7, 0.03, 0.035);
  blot(40, 90, 200, 0.012, 0.016);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  return tex;
};
const WALL = 30000;
/** The camera's depth range in wall px: it never comes nearer than a print's station allows, so the layers of a print
 * (paper, photograph, light) a fraction of a px apart keep their order from the whole wall in to the closest hold. */
const NEAR = 100;
const FAR = 20000;
const PLASTER_PX = 700;

const Scene: React.FC<{plan: Plan; t: number; frame: number; fonts: Map<string, Font>; clips: Clip[]}> = ({plan, t, frame, fonts, clips}) => {
  const files = useMemo(() => [...new Set(plan.cards.map((c) => c.tileFile))], [plan]);
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
  const station = useStationTextures(plan, t);
  const texOf = (c: Card) => (clip && clip.image === c.file ? clipTex : station.get(c.file) ?? textures[files.indexOf(c.tileFile)]);
  const ground = plan.colors.ground;
  const wall = useMemo(() => {
    const tex = plaster(ground);
    tex.repeat.set(WALL / PLASTER_PX, WALL / PLASTER_PX);
    return tex;
  }, [ground]);
  const light = useMemo(() => {
    const d = new THREE.DirectionalLight('#fff4e6', 1.6);
    d.position.set(-900, 1500, 2600);
    d.target.position.set(0, 0, 0);
    return d;
  }, []);
  const view = framingAt(plan, t);
  const shadowZ = restZ(plan.cards.length) + 0.05;
  return (
    <group>
      <hemisphereLight args={['#ffffff', '#8a7f74', 1.1]} />
      <primitive object={light} />
      <primitive object={light.target} />
      <mesh position={[0, 0, -0.5]} renderOrder={-10}>
        <planeGeometry args={[WALL, WALL]} />
        <meshBasicMaterial map={wall} toneMapped={false} />
      </mesh>
      {plan.cards.map((c, i) => <CardView key={c.id} plan={plan} card={c} index={i} t={t} texture={texOf(c)} view={view} shadowZ={shadowZ} />)}
      {plan.cards.map((c, i) => <CardWords key={c.id} plan={plan} card={c} fonts={fonts} t={t} index={i} />)}
      <CloserWords plan={plan} fonts={fonts} t={t} />
    </group>
  );
};

export const DriveFilm: React.FC<{board: Board; clips: Clip[]}> = ({board, clips}) => {
  const frame = useCurrentFrame();
  const plan = useMemo(() => planOf(board), [board]);
  const files = useMemo(() => [...new Set(linesOf(plan).map(fileOf))], [plan]);
  const fonts = useFonts(files);
  // the picture steps at the card's cadence, and from the stop on every part of it is held at the stop's instant
  const still = Math.round(plan.closer.still * plan.pulse);
  const step = plan.finish.cadence > 0 ? board.format.fps / plan.finish.cadence : 1;
  const f = Math.min(Math.floor(frame / step) * step, still);
  const t = f / plan.pulse;
  const shot = shotAt(plan, t);
  const travel = {...shot.travel, ...fxAt(plan.line, plan.look, t)};
  const ground = plan.colors.ground;
  return (
    <AbsoluteFill style={{background: ground}}>
      {fonts ? (
        <Stage pose={shot.pose} travel={travel} background={ground} near={NEAR} far={FAR}
          over={<MoveLayer line={plan.line} look={plan.look} t={t} bars={plan.finish.bars}
            closer={closerOf(plan.shape.name) ? {name: plan.shape.name, at: plan.shape.at, still: plan.closer.still} : undefined} />}>
          <Scene plan={plan} t={t} frame={f} fonts={fonts} clips={clips} />
        </Stage>
      ) : null}
    </AbsoluteFill>
  );
};
