// The year with them in one continuous camera: the occasion photograph falls flat with the age rising out of its
// line, then one card per moment of the year, each flying whole onto the closer's wall as a print standing off it with
// its shadow on the wall, a streak of light running along its own line as the moment's name rises out of that line,
// its words rising under it; the dust in the light floats between the wall and the cards, under the type; at the last
// card the camera pulls back onto the whole wall, a sheet of the ground with the age cut out of it slams shut over the
// year, the age's last figure is punched through it, and the style card's closer takes the frame with the wish; the film
// holds still and silent from there. Every move, cut, and closer is the style card's, drawn over the picture by the
// shared move layer inside the stage, so its words take the film's grain and grade; and a card with a cadence steps the
// picture as a camera that shoots fewer frames does.
import {useLoader, useThree} from '@react-three/fiber';
import {Component, useLayoutEffect, useMemo, type ReactNode} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {Dust, Burst} from '../../system/three/Dust';
import {clamp01, span} from '../../system/three/motion';
import {Stage} from '../../system/three/Stage';
import {fileOf, useFonts, type Font} from '../../system/three/type';
import {MoveLayer} from '../../system/moves/layer';
import type {Board, Clip} from '../../system/types';
import {CardView, liftOf} from './card';
import {shotAt, timelineOf} from './camera';
import {lookOf, onWall, paint, planOf, type Line, type Plan} from './plan';
import {CardWords, Cover, COVER_Z, flightPoint, HeadWords, wallOf} from './words';

const linesOf = (plan: Plan): Line[] => [plan.closer.big, plan.closer.last, ...plan.cards.flatMap((c) => [...c.head, ...c.lines])];

/** Each card's line on the print, in world space, for the burst its streak throws off: the flour rises out of the line
 * and stays under the type standing over it. */
const edgesOf = (plan: Plan) => plan.cards.map((c) => {
  const w = (x: number, y: number) => {
    const p = onWall(c.T, [x, y]);
    return new THREE.Vector3(p[0] - plan.W / 2, plan.H / 2 - p[1], liftOf(c) + c.T.s);
  };
  return {a: w(0, c.line[0]), b: w(plan.W, c.line[1])};
});

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
  const imageOf = useMemo(() => (f: string) => textures[files.indexOf(f)]?.image as HTMLImageElement | undefined, [textures, files]);
  const edges = useMemo(() => edgesOf(plan), [plan]);
  const wall = useMemo(() => wallOf(plan, imageOf, 'smoked'), [plan, imageOf]);
  const ground = paint(plan, plan.photo.ground);
  const C = plan.closer.at;
  // the card the camera is on, for the colour the dust is lit by
  const on = [...plan.cards].reverse().find((c) => t >= c.arrive - 0.3) ?? plan.cards[0];
  const dust = mixHex(plan.colors.paper, plan.colors[on.field] ?? plan.colors.paper, 0.3);
  // the type in flight pushes the dust aside, harder the faster it goes
  const k = flightPoint(plan, t);
  const k0 = flightPoint(plan, t - 0.03);
  const ahead = k && k0 ? k.clone().sub(k0) : new THREE.Vector3();
  const dir: [number, number] = ahead.lengthSq() > 1e-6 ? [ahead.x / ahead.length(), ahead.y / ahead.length()] : [0, 1];
  const sweepAmt = k ? clamp01(ahead.length() / (40 * on.T.s)) * (1 - span(t, C + 2.5, 0.5)) : 0;
  const swept = k ?? new THREE.Vector3();
  const big = plan.closer.big;
  const last = plan.closer.last;
  const punch = [new THREE.Vector3(last.x - 0.45 * last.size - plan.W / 2, plan.H / 2 - last.y + 0.35 * last.size, COVER_Z + 1),
    new THREE.Vector3(last.x - plan.W / 2, plan.H / 2 - last.y + 0.35 * last.size, COVER_Z + 1)];
  const light = useMemo(() => {
    // above and to the left, so a card's shadow falls beside it on the wall, down and to the right
    const d = new THREE.DirectionalLight(plan.colors.paper, 1.6);
    d.position.set(-900, 1500, 2600);
    d.target.position.set(0, 0, 0);
    d.castShadow = true;
    d.shadow.mapSize.set(2048, 2048);
    const sc = d.shadow.camera as THREE.OrthographicCamera;
    sc.left = -1500; sc.right = 1500; sc.top = 1700; sc.bottom = -1700; sc.near = 100; sc.far = 8000;
    d.shadow.bias = -0.0004;
    d.shadow.radius = 6;
    return d;
  }, [plan]);
  return (
    <group>
      <hemisphereLight args={[plan.colors.paper, plan.colors.ink, 1.1]} />
      <primitive object={light} />
      <primitive object={light.target} />
      <mesh position={[0, 0, -2]} renderOrder={-10}>
        <planeGeometry args={[30000, 30000]} />
        <meshBasicMaterial color={ground} toneMapped={false} />
      </mesh>
      {/* the year's wall dimmed, every cell waiting for its photograph, so a travel always crosses pictures */}
      <mesh position={[0, 0, -1.5]} renderOrder={-9.5}>
        <planeGeometry args={[plan.W, plan.H]} />
        <meshBasicMaterial map={wall} toneMapped={false} />
      </mesh>
      {plan.cards.map((c, i) => <CardView key={c.key} plan={plan} card={c} index={i} t={t} texture={texOf(c.file)} />)}
      {/* the wall and the photographs in their cells take the shadow of every card standing off it; gone as the cover
          starts to fall, so the figures cut through it never show the wall in shadow and the age reads one way */}
      {t < C + 0.75 ? (
        <mesh position={[0, 0, 0.8]} receiveShadow renderOrder={-9}>
          <planeGeometry args={[30000, 30000]} />
          <shadowMaterial opacity={0.75 * (1 - span(t, C + 0.3, 0.45))} transparent depthWrite={false} />
        </mesh>
      ) : null}
      <Cover plan={plan} fonts={fonts} t={t} imageOf={imageOf} />
      {plan.cards.map((c, i) => <CardWords key={c.key} plan={plan} card={c} fonts={fonts} t={t} index={i} />)}
      {plan.cards.map((c, i) => <HeadWords key={c.key} plan={plan} card={c} fonts={fonts} t={t} index={i} />)}
      {plan.cards.map((c, i) => {
        const e = edges[i];
        const along = e.b.clone().sub(e.a).normalize();
        return (
          <Burst key={c.key} seed={i} p0={e.a} p1={e.b} up={new THREE.Vector3(-along.y, along.x, 0).multiplyScalar(c.side === 'under' ? -1 : 1)} age={t - c.cut} sweepLen={0.25} reach={100 * c.T.s}
            color={mixHex(plan.colors.paper, plan.colors[c.field] ?? plan.colors.paper, 0.25)} height={plan.H} size={2.6 * c.T.s} />
        );
      })}
      <Burst seed={90} p0={new THREE.Vector3(big.x - plan.W / 2, plan.H / 2 - big.y, COVER_Z + 1)} p1={new THREE.Vector3(last.x - plan.W / 2, plan.H / 2 - big.y, COVER_Z + 1)}
        up={new THREE.Vector3(0, 1, 0)} age={t - (C + 1.25)} sweepLen={0.1} reach={160} color={plan.colors.paper} height={plan.H} size={2.4} />
      <Burst seed={91} p0={punch[0]} p1={punch[1]} up={new THREE.Vector3(0, 1, 0)} age={t - (C + 3.0)} sweepLen={0.08} reach={420} color={plan.colors.paper} height={plan.H} size={3.2} count={1400} />
      <Dust time={Math.min(frame, Math.round(plan.closer.still * plan.pulse))} box={[[-760, -1200, 0], [760, 1200, 12]]} color={dust} height={plan.H}
        sweep={[swept.x, swept.y, 40]} sweepDir={dir} sweepAmt={sweepAmt} />
    </group>
  );
};

/** Beats after the closer starts before the style card's closer may take the frame: once the age's last figure has
 * punched home and settled. */
const CLOSER_SHAPE = 3.75;
/** Beats each style card's closer is given to land its wish and sender, so its last line is still arriving on the
 * stop's frame and the picture and the sound stop together: the book cover's last line fades in over 1.6, and the lone
 * caption is given a beat for its page to cover the wall and its words to rise. */
const CLOSER_LAND: Record<string, number> = {'book-cover': 1.56, 'caption-alone': 1.0};
const LAND = 1.56;
/** How far below full the page's light stands when a closer starts, for the closers whose own ease settles before the
 * stop: the light comes up across the landing, quickest into the stop, and is full on the stop's frame, so the lone
 * caption's page is still brightening as the last note ends and the picture stops with the sound. */
const CLOSER_LIGHT: Record<string, number> = {'caption-alone': 0.08};

/** The scene, reported when it cannot draw: a photograph the page failed to load stops the whole scene, and the line
 * it logs is a finding of the render, so a frame left without its photographs never passes as a finished one. */
class Lost extends Component<{children: ReactNode}, {lost: boolean}> {
  state = {lost: false};
  static getDerivedStateFromError() {
    return {lost: true};
  }
  componentDidCatch(error: Error) {
    console.log(`IMAGE_ERROR ${error.message}`);
  }
  render() {
    return this.state.lost ? null : this.props.children;
  }
}

export const DriveFilm: React.FC<{board: Board; clips: Clip[]}> = ({board, clips}) => {
  const now = useCurrentFrame();
  const plan = useMemo(() => planOf(board), [board]);
  // a card with a cadence steps the picture at that many frames a second
  const step = plan.finish.cadence > 0 ? plan.fps / plan.finish.cadence : 1;
  const still = Math.round(plan.closer.still * plan.pulse);
  // from the stop on, the picture is the still frame
  const frame = Math.min(Math.floor(now / step) * step, still);
  const line = useMemo(() => timelineOf(plan), [plan]);
  const look = useMemo(() => lookOf(plan), [plan]);
  const files = useMemo(() => [...new Set(linesOf(plan).map(fileOf))], [plan]);
  const fonts = useFonts(files);
  const t = frame / plan.pulse;
  const shot = shotAt(plan, t);
  const ground = paint(plan, plan.photo.ground);
  const closerAt = Math.max(plan.closer.at + CLOSER_SHAPE, plan.closer.still - (CLOSER_LAND[plan.closerShape] ?? LAND));
  const landed = Math.min(1, Math.max(0, (t - closerAt) / (plan.closer.still - closerAt)));
  const dim = (CLOSER_LIGHT[plan.closerShape] ?? 0) * (1 - landed ** 3);
  return (
    <AbsoluteFill style={{background: ground}}>
      {fonts ? (
        <Stage pose={shot.pose} travel={shot.travel} background={ground}
          over={<MoveLayer line={line} look={look} t={t} bars={plan.finish.bars}
            closer={{name: plan.closerShape, at: closerAt, still: plan.closer.still}}>
            {t >= closerAt && dim > 0 ? <AbsoluteFill style={{background: paint(plan, 'ink'), opacity: dim}} /> : null}
          </MoveLayer>}>
          <Lost>
            <Scene plan={plan} t={t} frame={frame} fonts={fonts} clips={clips} />
          </Lost>
        </Stage>
      ) : null}
    </AbsoluteFill>
  );
};
