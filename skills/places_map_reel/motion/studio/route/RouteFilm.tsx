// The places film in one continuous camera over the map: it opens wide on the whole route under the film's title, the
// dot on the first place's pin, and comes down onto the first place as its photograph opens out of the pin; then place
// by place the dot runs the real route, each place opening out of its pin into its card, laid out by the style card,
// with its name and the person's line about it, and folding back onto the map as a small print while the camera follows
// the dot on; each beat's move and the cut into it play over the picture; the closer is the map resolving into the
// style's last frame, the map showing through its window with every place named on its pin, where the film holds
// still and silent.
import {useLoader, useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {fxAt, MoveLayer, nudgeAt, type Timeline} from '../../system/moves/layer';
import type {BeatOn, Look} from '../../system/moves';
import {Stage, type Pose} from '../../system/three/Stage';
import {fileOf, useFonts} from '../../system/three/type';
import type {Board, Clip} from '../../system/types';
import {framingAt, shotAt} from './camera';
import {CardView} from './card';
import {CloserFrame, KIT, registerClosers} from './closers';
import {Dot, legDrawn} from './dot';
import {MapView} from './map';
import {lookOf, planOf, type Box, type Line, type Plan} from './plan';
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

/** Where a stop's label and line stand on its frame, [x0, y0, x1, y1] px: the bounds of its lines, each as wide as its
 * letters run at an average advance. */
const typeOf = (lines: Line[]): Box | undefined => {
  if (!lines.length) return undefined;
  const xs: number[] = [], ys: number[] = [];
  for (const ln of lines) {
    const w = ln.text.length * ln.size * 0.55;
    const x0 = ln.anchor === 'middle' ? ln.x - w / 2 : ln.anchor === 'end' ? ln.x - w : ln.x;
    xs.push(x0, x0 + w);
    ys.push(ln.y - ln.size, ln.y + 0.25 * ln.size);
  }
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
};

/** Beats before the camera leaves a stop that its marks begin to go: a mark drawn on the photograph is gone before the
 * card folds onto the map. */
const MARKS_GO = 0.35;

/** The film's beats as the moves see them: each stop from its arrival to the next, the closer to the film's end. A
 * photo beat carries where its photograph and its words stand on the frame and the beats the camera holds on it; its
 * words and label are the card layout's, so a move sets none of its own. */
const timelineOf = (board: Board, plan: Plan): Timeline => {
  const at = [...plan.cards.map((c) => c.arrive), plan.closer.at];
  const beats: BeatOn[] = board.beats.map((b, i) => {
    const c = plan.cards[i];
    const photo = b.form === 'photo' && c;
    return {
      id: b.id, form: b.form ?? 'photo', at: at[i] ?? plan.closer.at, end: at[i + 1] ?? plan.end, move: b.move, transition: b.transition ?? null,
      words: photo ? '' : b.words ?? '', label: b.label ?? '', peak: Boolean(b.peak),
      ...(photo ? {box: c.box, type: typeOf(c.lines), held: [c.arrive, c.goAt - MARKS_GO] as [number, number]} : {}),
    };
  });
  return {beats, cuts: beats.map((b) => b.at)};
};

const Scene: React.FC<{plan: Plan; t: number; frame: number; fonts: Fonts; clips: Clip[]; pose: Pose; line: Timeline; look: Look}> = ({plan, t, frame, fonts, clips, pose, line, look}) => {
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
      {plan.cards.map((c, i) => <CardWords key={c.id} plan={plan} card={c} fonts={fonts} t={t} index={i} />)}
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
  const line = useMemo(() => timelineOf(board, plan), [board, plan]);
  const safe = sys.safe[board.format.name ?? 'reel'] ?? {top: 0, bottom: 0};
  const still = Math.round(plan.closer.still * plan.pulse);
  const t = Math.min(frame, still) / plan.pulse;
  const shot = shotAt(plan, t);
  const bg = plan.colors.sea;
  const over = (
    <CloserFrame.Provider value={{window: plan.closer.window, top: Math.max(safe.top, sys.finish.bars * plan.H),
      bottom: plan.H - Math.max(safe.bottom, sys.finish.bars * plan.H)}}>
      <MoveLayer line={line} look={look} t={t} closer={{name: KIT + sys.closer, at: plan.closer.at, still: plan.closer.still}} bars={sys.finish.bars}>
        <HookTitle plan={plan} system={sys} t={t} />
      </MoveLayer>
    </CloserFrame.Provider>
  );
  return (
    <AbsoluteFill style={{background: bg}}>
      {fonts ? (
        <Stage pose={shot.pose} travel={{...shot.travel, ...fxAt(line, look, t)}} background={bg}
          near={Math.max(5, shot.distance * 0.02)} far={Math.max(40000, shot.distance * 6)} over={over}>
          <Scene plan={plan} t={t} frame={frame} fonts={fonts} clips={clips} pose={shot.pose} line={line} look={look} />
        </Stage>
      ) : null}
    </AbsoluteFill>
  );
};
