// The places film in one continuous camera over the map: it opens wide on the whole route under the film's title, the
// dot on the first place's pin, and comes down onto the first place as its photograph opens out of the pin; then place
// by place the dot runs the real route, each place opening out of its pin into its card, laid out by the style card,
// with its name and the person's line about it, and folding back onto the map as a small print while the camera follows
// the dot on; each beat's move and the cut into it play over the picture; the closer is the map resolving into the
// style's last frame, the map showing through its window with every place named on its pin, where the picture comes to
// rest and the music stops, and the closer keeps the shared layer's slow push to the last frame. The cut into a flown
// stop plays where its flight takes the frame (plan.ts flightCutAt); the shared layer plays every other cut.
import {useLoader, useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {fxAt, MoveLayer, nudgeAt, type Timeline} from '../../system/moves/layer';
import type {Look} from '../../system/moves';
import {Stage, type Pose} from '../../system/three/Stage';
import {fileOf, useFonts} from '../../system/three/type';
import type {Board, Clip} from '../../system/types';
import {framingAt, shotAt} from './camera';
import {CardView} from './card';
import {CloserFrame, KIT, registerClosers} from './closers';
import {Dot, legDrawn} from './dot';
import {MapView} from './map';
import {flightCutAt, lookOf, planOf, sharedOf, timelineOf, wordsGoneBy, type Line, type Plan} from './plan';
import {CardWords, HookTitle, type Fonts} from './words';

registerClosers();

const linesOf = (plan: Plan): Line[] => plan.cards.flatMap((c) => c.lines);

/** The frame of a generated clip the film is on, as one texture whose picture is replaced each frame. */
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

const Scene: React.FC<{plan: Plan; t: number; frame: number; fonts: Fonts; clips: Clip[]; pose: Pose; line: Timeline; look: Look; gone: Record<number, number>}> = ({plan, t, frame, fonts, clips, pose, line, look, gone}) => {
  const files = useMemo(() => [...new Set(plan.cards.map((c) => c.file))], [plan]);
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
  const texOf = (f: string) => (clip && clip.image === f ? clipTex : textures[files.indexOf(f)]);
  const h = useMemo(() => (tt: number) => framingAt(plan, tt).framing.h, [plan]);
  const viewH = h(t);
  // the light and the shadow it throws follow what the camera frames; every surface is drawn in its own color, so the
  // light only casts the shadows
  const light = useMemo(() => {
    const d = new THREE.DirectionalLight();
    d.castShadow = true;
    d.shadow.mapSize.set(4096, 4096);
    d.shadow.bias = -0.0004;
    d.shadow.radius = 6;
    return d;
  }, []);
  const k = viewH / 1920;
  light.position.set(pose.target[0] - 900 * k, pose.target[1] + 1500 * k, 2600 * k);
  light.target.position.set(pose.target[0], pose.target[1], 0);
  const sc = light.shadow.camera as THREE.OrthographicCamera;
  sc.left = -2200 * k; sc.right = 2200 * k; sc.top = 2600 * k; sc.bottom = -2600 * k; sc.near = 10 * k; sc.far = 9000 * k;
  sc.updateProjectionMatrix();
  light.target.updateMatrixWorld();
  const nudge = nudgeAt(line, look, t);
  return (
    <group>
      <primitive object={light} />
      <primitive object={light.target} />
      <MapView plan={plan} t={t} drawn={(i, tt) => legDrawn(plan, i, tt)} h={viewH} />
      {plan.cards.map((c, i) => <CardView key={c.id} plan={plan} card={c} index={i} t={t} texture={texOf(c.file)} pulse={1} nudge={nudge} />)}
      {plan.cards.map((c, i) => <CardWords key={c.id} plan={plan} card={c} fonts={fonts} t={t} index={i} gone={gone[i]} />)}
      <Dot plan={plan} t={t} h={h} still={plan.closer.still} />
    </group>
  );
};

export const RouteFilm: React.FC<{board: Board; clips: Clip[]}> = ({board, clips}) => {
  const frame = useCurrentFrame();
  const plan = useMemo(() => planOf(board), [board]);
  const files = useMemo(() => [...new Set(linesOf(plan).map(fileOf))], [plan]);
  const fonts = useFonts(files);
  const sys = board.system;
  const look: Look = useMemo(() => lookOf(plan), [plan]);
  const full = useMemo(() => timelineOf(board, plan), [board, plan]);
  const line = useMemo(() => sharedOf(full), [full]);
  const gone = useMemo(() => wordsGoneBy(full, look), [full, look]);
  const safe = sys.safe[board.format.name ?? 'reel'] ?? {top: 0, bottom: 0};
  const still = Math.round(plan.closer.still * plan.pulse);
  const t = Math.min(frame, still) / plan.pulse;
  const shot = shotAt(plan, t);
  const flight = flightCutAt(full, look, t);
  const bg = plan.colors.sea;
  const over = (
    <CloserFrame.Provider value={{window: plan.closer.window, top: Math.max(safe.top, sys.finish.bars * plan.H),
      bottom: plan.H - Math.max(safe.bottom, sys.finish.bars * plan.H)}}>
      <MoveLayer line={line} look={look} t={t} now={frame / plan.pulse} closer={{name: KIT + sys.closer, at: plan.closer.at, still: plan.closer.still}} bars={sys.finish.bars}>
        {flight?.cut.Overlay ? <flight.cut.Overlay into={flight.into} look={look} u={flight.u} t={t} /> : null}
        <HookTitle plan={plan} system={sys} t={t} />
      </MoveLayer>
    </CloserFrame.Provider>
  );
  return (
    <AbsoluteFill style={{background: bg}}>
      {fonts ? (
        <Stage pose={shot.pose} travel={{...shot.travel, ...fxAt(line, look, t), ...(flight?.cut.fx ? flight.cut.fx({into: flight.into, look, u: flight.u, t}) : {})}} background={bg}
          near={Math.max(5, shot.distance * 0.02)} far={Math.max(40000, shot.distance * 6)} over={over}>
          <Scene plan={plan} t={t} frame={frame} fonts={fonts} clips={clips} pose={shot.pose} line={line} look={look} gone={gone} />
        </Stage>
      ) : null}
    </AbsoluteFill>
  );
};
