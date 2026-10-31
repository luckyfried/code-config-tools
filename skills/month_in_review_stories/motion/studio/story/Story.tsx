// The story cards on the reel's system: one camera a card over one moment's photograph. The photograph fills the frame
// as a band; the line climbs it to above its subject; their words stand on a plate sized to them.
// `Series` plays the cards end to end, each card 15 s on its own clock; any frame renders alone.
import {useLoader} from '@react-three/fiber';
import {useMemo} from 'react';
import {AbsoluteFill, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {Burst as Spark, Dust} from '../../system/three/Dust';
import {bezier, clamp01, lerp, span} from '../../system/three/motion';
import {Stage} from '../../system/three/Stage';
import {Type3D} from '../../system/three/Type3D';
import {fileOf, shownAt, useFonts, type Font} from '../../system/three/type';
import {bandMaterial, quad, setQuad} from '../climb/card';
import {fill, useStrokes} from '../climb/wall';
import {frameOf} from '../climb/words';
import {H, shotAt, W} from './camera';
import {at, brightest, colorOf, pulseOf, type Band, type Card, type Colors, type Line, type Rule, type Series, type Strip} from './plan';

type Fonts = Map<string, Font>;
const WH = {W, H};
const enter = bezier([0.22, 1.2, 0.36, 1]);
const SLIDE_IN = bezier([0.12, 0.8, 0.25, 1]);
const toWorld = (x: number, y: number, z: number) => new THREE.Vector3(x - W / 2, H / 2 - y, z);

/** A photograph as a band: laid over its rect, sliding in, its cut edges lit by its own light. */
const BandQuad: React.FC<{band: Band; index: number; count: number; t: number; texture: THREE.Texture | null; colors: Colors}> = ({band: b, index, count, t, texture, colors}) => {
  const mat = useMemo(() => bandMaterial(texture, colors.bg), [texture, colors.bg]);
  const q = useMemo(() => quad(mat.m), [mat]);
  if (b.enter && t < b.enter.at) return null;
  const e = b.enter ? span(t, b.enter.at, b.enter.len, SLIDE_IN) : 1;
  const dx = (1 - e) * (b.enter?.from === 'right' ? 1 : -1) * W * 1.05;
  const {rect, place} = b;
  // flat bands step forward in their order, apart by more than the depth buffer resolves at the stage's near plane,
  // and all behind the shadow plane at z -1
  const z = -3 + index * Math.min(0.1, 1.9 / count);
  const corners: [number, number][] = [[rect[0], rect[1]], [rect[2], rect[1]], [rect[2], rect[3]], [rect[0], rect[3]]];
  const uvOf = ([x, y]: [number, number]): [number, number] => [(x - place[0]) / place[2], 1 - (y - place[1]) / place[3]];
  const uvs = corners.map(uvOf);
  setQuad(q, corners.map(([x, y]) => toWorld(x + dx, y, z)), uvs);
  mat.u.edge.value.set(uvs[0][0], uvs[2][1], uvs[2][0], uvs[0][1]);
  mat.u.wrap.value.set(16 / place[2], 16 / place[3]);
  q.mesh.renderOrder = 10 + index;
  return <primitive object={q.mesh} />;
};

/** A level line, drawn out from its left end and standing at its track's height. */
const RuleLine: React.FC<{rule: Rule; t: number; colors: Colors}> = ({rule: r, t, colors}) => {
  const color = useMemo(() => new THREE.Color(colorOf(colors, r.color)).multiplyScalar(2.4), [colors, r.color]);
  const st = useStrokes(color, 2000);
  const grow = span(t, r.at, 0.35, bezier([0.3, 0, 0.2, 1]));
  const y = at(r.y, t);
  fill(st, WH, grow > 0 ? [[r.x0, y - 4.5, lerp(r.x0, r.x1, grow), y + 4.5]] : [], 58);
  return <primitive object={st.mesh} />;
};

/** The plate under a line of words, sized to the words, solid ground, drawn out from the left. */
const PaperStrip: React.FC<{strip: Strip; t: number; colors: Colors}> = ({strip: s, t, colors}) => {
  const color = useMemo(() => new THREE.Color(colors.bg), [colors.bg]);
  const st = useStrokes(color, s.z && s.z > 50 ? 1500 : 700);
  const run = span(t, s.at, s.len, bezier([0.3, 0, 0.2, 1]));
  st.mat.opacity = (s.out === undefined ? 1 : 1 - span(t, s.out, 0.3));
  const [x0, y0, x1, y1] = s.rect;
  fill(st, WH, run > 0 ? [[x0, y0, lerp(x0, x1, run), y1]] : [], s.z ?? 0.4);
  return <primitive object={st.mesh} />;
};

const fontOf = (fonts: Fonts, ln: Line) => fonts.get(fileOf(ln))!;

const SetLine: React.FC<{ln: Line; fonts: Fonts; t: number; colors: Colors; order: number}> = ({ln, fonts, t, colors, order}) => {
  if (t < ln.at) return null;
  const rise = enter(clamp01((t - ln.at) / 0.45));
  const fade = ln.out === undefined ? 1 : 1 - span(t, ln.out, 0.3);
  if (fade <= 0.002) return null;
  return (
    <Type3D font={fontOf(fonts, ln)} text={shownAt(ln, t)} tracking={ln.tracking ?? 0} color={colorOf(colors, ln.color)} anchor={ln.anchor} matrix={frameOf(WH, ln.x, ln.y, ln.size, ln.z ?? 60)}
      rise={Math.min(1, rise)} opacity={fade} shadow={ln.shadow ?? 0} shade={colors.ink} renderOrder={order} />
  );
};

export const filesOf = (cards: Card[]) => [...new Set(cards.flatMap((c) => c.bands.map((b) => b.file)).filter((f): f is string => !!f))];
export const fontFilesOf = (cards: Card[]) => [...new Set(cards.flatMap((c) => c.lines).map(fileOf))];

const Scene: React.FC<{card: Card; t: number; frame: number; fonts: Fonts; files: string[]; colors: Colors}> = ({card: c, t, frame, fonts, files, colors}) => {
  const textures = useLoader(THREE.TextureLoader, files.map((f) => staticFile(f))) as THREE.Texture[];
  useMemo(() => textures.forEach((tx) => {
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    tx.needsUpdate = true;
  }), [textures]);
  // the light is the palette's own: the key in its brightest color, the fill from below in its muted one
  const key = useMemo(() => brightest(colors), [colors]);
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
  // the dust is pushed up ahead of whichever level line is climbing fastest
  const speeds = c.rules.map((r) => ({r, v: at(r.y, t - 0.08) - at(r.y, t)}));
  const fast = speeds.reduce((a, b) => (b.v > a.v ? b : a), {r: null as Rule | null, v: 0});
  const tip = fast.r ? toWorld(fast.r.x1, at(fast.r.y, t), 58) : toWorld(W / 2, H / 2, 0);
  return (
    <group>
      <hemisphereLight args={[key, colors.muted, 1.1]} />
      <primitive object={light} />
      <primitive object={light.target} />
      <mesh position={[0, 0, -6]} renderOrder={-10}>
        <planeGeometry args={[30000, 30000]} />
        <meshBasicMaterial color={colors.bg} toneMapped={false} />
      </mesh>
      {c.bands.map((b, i) => <BandQuad key={`${c.id}-b${i}`} band={b} index={i} count={c.bands.length} t={t} texture={b.file ? textures[files.indexOf(b.file)] ?? null : null} colors={colors} />)}
      <mesh position={[0, 0, -1]} receiveShadow renderOrder={600}>
        <planeGeometry args={[30000, 30000]} />
        <shadowMaterial opacity={0.35} transparent depthWrite={false} />
      </mesh>
      {c.strips.map((s, i) => <PaperStrip key={`${c.id}-s${i}`} strip={s} t={t} colors={colors} />)}
      {c.rules.map((r, i) => <RuleLine key={`${c.id}-r${i}`} rule={r} t={t} colors={colors} />)}
      {c.lines.map((ln, i) => <SetLine key={`${c.id}-l${i}`} ln={ln} fonts={fonts} t={t} colors={colors} order={2000 + i} />)}
      {c.bursts.map((b, i) => (
        <Spark key={`${c.id}-p${i}`} seed={i} p0={toWorld(b.x0, b.y, 64)} p1={toWorld(b.x1, b.y, 64)} up={new THREE.Vector3(0, 1, 0)} age={t - b.at} sweepLen={0.25}
          reach={b.big ? 260 : 120} color={b.big ? colors.high : colors.paper} height={H} size={b.big ? 3.2 : 2.2} />
      ))}
      <Dust time={frame} box={[[-760, -1200, 15], [760, 1200, 650]]} color={colors.accent2} height={H} sweep={[tip.x, tip.y, 220]} sweepDir={[0, 1]}
        sweepAmt={clamp01(fast.v / 60)} />
    </group>
  );
};

/** Which card frame `frame` of the series is on, and that card's first frame. */
export const cardAt = (cards: Card[], frame: number) => {
  let from = 0;
  for (let i = 0; i < cards.length; i++) {
    if (frame < from + cards[i].frames || i === cards.length - 1) return {i, from};
    from += cards[i].frames;
  }
  return {i: 0, from: 0};
};

export const seriesFrames = (cards: Card[]) => cards.reduce((n, c) => n + c.frames, 0);

export const SeriesFilm: React.FC<{board: Series}> = ({board}) => {
  const frame = useCurrentFrame();
  const cards = board.beats;
  const files = useMemo(() => filesOf(cards), [cards]);
  const fonts = useFonts(useMemo(() => fontFilesOf(cards), [cards]));
  const pulse = pulseOf(board.bpm, board.format.fps);
  const {i, from} = cardAt(cards, frame);
  const c = cards[i];
  const local = frame - from;
  const t = local / pulse;
  const shot = shotAt(c, t);
  const colors = board.system.colors;
  return (
    <AbsoluteFill style={{background: colors.bg}}>
      {fonts ? (
        <Stage pose={shot.pose} travel={shot.travel} background={colors.bg} near={100}>
          <Scene key={c.id} card={c} t={t} frame={frame} fonts={fonts} files={files} colors={colors} />
        </Stage>
      ) : null}
    </AbsoluteFill>
  );
};
