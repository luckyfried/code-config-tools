// The drive film in one continuous camera on their grid: the hook opens on the card's title page, the film's hook
// line set in the card's line box with a window onto their grid, then the page opens out and the frame finds the
// posts that break the first screen; each of the next nine comes into the top of the grid by its own move (held whole
// and closed on, read on the card's page with its caption, slid onto the station, or fallen from the lens), pushing
// every post one place along; the closer is their profile with the nine in place under their handle and their own bio,
// then the card's closing card with the film's ask, and the film holds still and silent from the stop. The card's
// moves, cuts and closer draw over the picture on their beats, and the stage finishes the picture and them together in
// the card's grade, grain and bloom.
import {useLoader, useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {MoveLayer} from '../../system/moves/layer';
import {Burst, Dust} from '../../system/three/Dust';
import {bezier, clamp01, span} from '../../system/three/motion';
import {Stage} from '../../system/three/Stage';
import {fileOf, useFonts, type Font} from '../../system/three/type';
import type {Board, Clip} from '../../system/types';
import {musicAt, shotAt, timelineOf} from './camera';
import {FrameView, frameAt} from './frame';
import {Pages} from './page';
import {cellBox, planOf, toWorld, type Plan} from './plan';
import {PostView} from './post';
import {Wall} from './wall';

// how far the closer pushes in, as a share of the frame, between their header's entrance and the stop
const CLOSER_PUSH = 0.025;
// how far the hook's title page pushes in, as a share of the frame, from the first frame to the paper opening out:
// the page sets the words and then lets them stand, and the push keeps the picture alive under them
const TITLE_PUSH = 0.035;

// how many times a photograph that does not load is asked for again, the wait doubling from the first, ms: a photograph
// a busy machine's server drops once is loaded on a later try, never drawn as a black wall
const TRIES = 5;
const FIRST_WAIT = 250;

/** The texture loader the scene's photographs load through: a photograph that fails to load is asked for again. */
class SteadyTextureLoader extends THREE.TextureLoader {
  load(...[url, onLoad, onProgress, onError]: Parameters<THREE.TextureLoader['load']>) {
    const attempt = (n: number): ReturnType<THREE.TextureLoader['load']> =>
      super.load(url, onLoad, onProgress, (e) => (n + 1 < TRIES ? void setTimeout(() => attempt(n + 1), FIRST_WAIT * 2 ** n) : onError?.(e)));
    return attempt(0);
  }
}

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
  const files = useMemo(() => [...new Set([...plan.cells.map((c) => c.file), ...plan.posts.map((p) => p.file)])], [plan]);
  const textures = useLoader(SteadyTextureLoader, files.map((f) => staticFile(f))) as THREE.Texture[];
  useMemo(() => textures.forEach((tx) => {
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    tx.needsUpdate = true;
  }), [textures]);
  // a generated clip plays on its photograph over its beat; with none, the photograph holds
  const clip = clips.find((c) => frame >= c.from && frame < c.from + c.frames);
  const clipSrc = clip ? `${clip.dir}/${String(frame - clip.from + 1).padStart(4, '0')}.jpg` : null;
  const clipTex = useClipFrame(clipSrc);
  const texOf = (f: string) => (clip && clip.image === f ? clipTex : textures[files.indexOf(f)]);
  const light = useMemo(() => {
    const d = new THREE.DirectionalLight(plan.light, 1.6);
    d.position.set(-900, 1500, 2600);
    d.target.position.set(0, 0, 0);
    d.castShadow = true;
    d.shadow.mapSize.set(2048, 2048);
    const sc = d.shadow.camera as THREE.OrthographicCamera;
    sc.left = -1500; sc.right = 1500; sc.top = 1700; sc.bottom = -1700; sc.near = 100; sc.far = 8000;
    d.shadow.bias = -0.0004;
    d.shadow.radius = 6;
    return d;
  }, [plan.light]);
  // the dust the frame pushes as it travels, lit by the photograph in play
  const {box} = frameAt(plan, t);
  const ahead = frameAt(plan, t + 0.05).box;
  const c = new THREE.Vector3(...toWorld(plan, [box[0] + box[2] / 2, box[1] + box[3] / 2], 120));
  const v = new THREE.Vector2(ahead[0] + ahead[2] / 2 - box[0] - box[2] / 2, -(ahead[1] + ahead[3] / 2 - box[1] - box[3] / 2));
  const speed = v.length();
  const dir: [number, number] = speed > 1e-3 ? [v.x / speed, v.y / speed] : [0, 1];
  const slot0 = cellBox(plan.grid, 0);
  const seatEdge = (b: [number, number, number, number]) => [new THREE.Vector3(...toWorld(plan, [b[0], b[1] + b[3]], 6)), new THREE.Vector3(...toWorld(plan, [b[0] + b[2], b[1] + b[3]], 6))];
  const [s0, s1] = seatEdge(slot0);
  const closerBox = plan.closer.box;
  const [k0, k1] = seatEdge(closerBox);
  const motes = mixHex(plan.light, plan.colors.paper, 0.4);
  return (
    <group>
      <hemisphereLight args={[plan.light, plan.colors.muted, 1.1]} />
      <primitive object={light} />
      <primitive object={light.target} />
      <mesh position={[0, 0, -2]} renderOrder={-10}>
        <planeGeometry args={[30000, 30000]} />
        <meshBasicMaterial color={plan.colors.bg} toneMapped={false} />
      </mesh>
      {/* the shadows on the wall, drawn over its cells (render order 1 to 3) and under every card */}
      <mesh position={[0, 0, 0.5]} receiveShadow renderOrder={5}>
        <planeGeometry args={[30000, 30000]} />
        <shadowMaterial opacity={0.55} transparent depthWrite={false} />
      </mesh>
      <Wall plan={plan} t={t} textureOf={texOf} />
      {plan.posts.map((p, i) => <PostView key={p.beat} plan={plan} post={p} index={i} t={t} texture={texOf(p.file)} />)}
      <FrameView plan={plan} t={t} fonts={fonts} />
      {/* the motes a post knocks off the wall as it seats, and the card's dust, only on a card that has dust */}
      {plan.dust > 0 ? plan.posts.map((p, i) => (
        <Burst key={p.beat} seed={i + 1} p0={s0} p1={s1} up={new THREE.Vector3(0, -1, 0)} age={t - p.times.seat} sweepLen={0.2} reach={120}
          color={motes} height={plan.H} size={2.4} />
      )) : null}
      {plan.dust > 0 ? <Burst seed={40} p0={k0} p1={k1} up={new THREE.Vector3(0, -1, 0)} age={t - plan.closer.lock} sweepLen={0.3} reach={200} color={motes} height={plan.H} size={2.8} /> : null}
      {plan.dust > 0 ? (
        <Dust time={Math.min(frame, Math.round(plan.closer.still * plan.pulse))} box={[[-760, -1200, 15], [760, 1200, 650]]} color={mixHex(plan.light, plan.colors.paper, 0.3)} height={plan.H}
          sweep={[c.x, c.y, 0.45 * box[2]]} sweepDir={dir} sweepAmt={clamp01(speed / 40) * (1 - span(t, plan.closer.lock, 1))} />
      ) : null}
    </group>
  );
};

/**
 * The closer's header, set as type a browser sets over the band's paper as the frame locks on it: their
 * handle in the card's display face, their bio in its text face as they wrote it, emoji and all, never recased; each
 * line rises out of its baseline on the card's entrance as it appears, and sinks as the card's closing card takes the
 * frame.
 */
const Header: React.FC<{plan: Plan; t: number}> = ({plan, t}) => {
  const {header, look} = plan;
  const enter = bezier(plan.ease.enter);
  const until = (plan.closerShape.at * plan.look.pulse) / plan.pulse;
  if (!header.lines.length || t < header.at || t >= until + 0.4) return null;
  const out = clamp01((t - until) / 0.4);
  return (
    <svg width={plan.W} height={plan.H} style={{position: 'absolute', inset: 0}}>
      {header.lines.map((ln) => {
        const u = enter(clamp01((t - ln.at) / 0.45));
        const shown = Math.min(clamp01((t - ln.at) / 0.2), 1 - out);
        return (
          <text key={ln.name} x={ln.x} y={ln.y + (1 - u) * ln.size * 0.35} fontSize={ln.size} opacity={shown}
            fontFamily={`'${ln.face === 'display' ? look.display : look.text}', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif`}
            fontWeight={ln.bold ? 700 : 500} fill={plan.colors.ink}>
            {ln.text}
          </text>
        );
      })}
    </svg>
  );
};

export const DriveFilm: React.FC<{board: Board; clips: Clip[]}> = ({board, clips}) => {
  // a card with a cadence steps the picture at that many frames a second, as a camera that shoots fewer frames does
  const now = useCurrentFrame();
  const step = board.system.finish.cadence > 0 ? board.format.fps / board.system.finish.cadence : 1;
  const frame = Math.floor(now / step) * step;
  // the camera reads the board's timeline; the card's moves read the one whose photo beats start as the frame locks
  const plan = useMemo(() => planOf(board), [board]);
  const line = useMemo(() => timelineOf(plan), [plan]);
  // the frame's type loads the display face whether or not a band carries words, so the scene waits on a face it has
  const files = useMemo(() => [...new Set([fileOf({face: 'display'}), ...Object.values(plan.bands).flatMap((b) => b.lines.map(fileOf))])], [plan]);
  const fonts = useFonts(files);
  const t = frame / plan.pulse;
  const shot = shotAt(plan, t);
  const tm = musicAt(plan, Math.min(t, plan.closer.still));
  // the closer is never a still frame under the music: from the moment their header starts to appear, the whole
  // picture (the profile, its header, then the closing card) pushes in slowly, gathering to an even speed, and stops
  // dead with the music on the stop
  const from = Math.min(plan.header.at, (plan.closerShape.at * plan.look.pulse) / plan.pulse);
  const u = clamp01((t - from) / Math.max(0.05, plan.closer.still - from));
  const title = plan.timeline.beats[0]?.form === 'words' ? plan.timeline.beats[0] : undefined;
  const lead = title ? 1 + TITLE_PUSH * clamp01(tm / Math.max(0.05, title.end)) : 1;
  const push = (tm < (title?.end ?? 0) ? lead : 1) * (1 + CLOSER_PUSH * u * u * (2 - u));
  // over the picture, inside the stage so they take the card's finish: their header, the card's pages, then every
  // move, cut and the card's closer, and the card's bars over all
  const over = (
    <>
      <Header plan={plan} t={t} />
      <Pages plan={plan} t={t} />
      <MoveLayer line={line} look={plan.look} t={tm} closer={plan.closerShape} bars={plan.finish.bars} />
    </>
  );
  return (
    <AbsoluteFill style={{background: plan.colors.bg}}>
      <AbsoluteFill style={{transform: `scale(${push})`}}>
        {fonts ? (
          <Stage pose={shot.pose} travel={shot.travel} background={plan.colors.bg} over={over}>
            <Scene plan={plan} t={t} frame={frame} fonts={fonts} clips={clips} />
          </Stage>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
