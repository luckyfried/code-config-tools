// The year film in one camera over one wall: the dot draws the title's underline and the year slams onto it, the line
// opens into a window where the months flash and the camera dives in, then each month in calendar order, where the
// card stands its photograph, splits on its line into two layers that slide against each other under the month's move,
// with its name and their own line from the post where the card sets them; the next month comes in on the card's cut
// as this one closes onto its line and slides into its row. The closer is the year's chapters whole, the dot drawing one
// spine down the rows' ends, then the card's closer takes the frame and lands the sign-off, where the film holds still
// and silent. Every move, cut and closer the card names draws over the picture; one grade, the card's turned by the
// person's palette, covers every frame, and the card's finish (its grain, vignette, bloom and cadence) with it.
import {useLoader, useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {Burst, Dust} from '../../system/three/Dust';
import {clamp01, span} from '../../system/three/motion';
import {Stage} from '../../system/three/Stage';
import {fileOf, useFonts, type Font} from '../../system/three/type';
import {closerOf} from '../../system/moves';
import {MoveLayer} from '../../system/moves/layer';
import type {Board, Clip} from '../../system/types';
import {shotAt} from './camera';
import {CardDot, signoffStop} from './card';
import {DotView, dotAt, endsOf, type Route} from './dot';
import {Ground} from './ground';
import {HookWindow} from './hook';
import {MonthView} from './month';
import {monthAt, planOf, world, type Month, type Plan} from './plan';
import {CloserWords, HookWords, linesOf, MonthWords, stopAfter, WallPlates} from './words';

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

/**
 * The photographs' loader: a picture that fails to load is asked for again, up to four times a quarter second apart,
 * before the failure reaches the scene, because a failed load holds for the page's whole run and every frame after it
 * would draw without the scene.
 */
class PhotoLoader extends THREE.TextureLoader {
  load(...[url, onLoad, onProgress, onError]: Parameters<THREE.TextureLoader['load']>) {
    let tries = 0;
    const attempt = (): ReturnType<THREE.TextureLoader['load']> => super.load(url, onLoad, onProgress, (e) => {
      if (++tries < 5) setTimeout(attempt, 250);
      else onError?.(e);
    });
    return attempt();
  }
}

/** The photographs' mean color, for the dust the light catches. */
const DUST = '#fff4dc';

/** Where the dot rests: the year's full stop, each row's end, and the sign-off's full stop, where the card's closer sets
 * the sign-off when it sets one. */
const routeOf = (plan: Plan, fonts: Map<string, Font>): Route => ({
  title: stopAfter(plan, fonts, plan.title),
  ends: plan.months.map((m) => world(plan, [m.row.x1, m.row.rule], 3)),
  stop: signoffStop(plan) ?? stopAfter(plan, fonts, plan.signoff),
});

const Scene: React.FC<{plan: Plan; t: number; frame: number; fonts: Map<string, Font>; clips: Clip[]; still: number; route: Route}> = ({plan, t, frame, fonts, clips, still, route}) => {
  const files = useMemo(() => [...new Set(plan.months.map((m) => m.file))], [plan]);
  const textures = useLoader(PhotoLoader, files.map((f) => staticFile(f))) as THREE.Texture[];
  useMemo(() => textures.forEach((tx) => {
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    tx.needsUpdate = true;
  }), [textures]);
  // a generated clip plays on its month's photograph over its open hold; with none, the photograph holds
  const clip = clips.find((c) => frame >= c.from && frame < c.from + c.frames);
  const clipSrc = clip ? `${clip.dir}/${String(frame - clip.from + 1).padStart(4, '0')}.jpg` : null;
  const clipTex = useClipFrame(clipSrc);
  const photo = (m: Month) => textures[files.indexOf(m.file)];
  const texOf = (m: Month) => (clip && clip.image === m.file && t < m.at.slide[0] ? clipTex : photo(m));
  const dot = dotAt(plan, t, route);
  const ahead = dotAt(plan, t + 0.03, route).p.clone().sub(dot.p);
  const dir: [number, number] = ahead.lengthSq() > 1e-6 ? [ahead.x / ahead.length(), ahead.y / ahead.length()] : [0, 1];
  const on = monthAt(plan, t);
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
        <meshBasicMaterial color={plan.colors.bg} toneMapped={false} />
      </mesh>
      <mesh position={[0, 0, -1]} receiveShadow renderOrder={-9}>
        <planeGeometry args={[30000, 30000]} />
        <shadowMaterial opacity={0.6} transparent depthWrite={false} />
      </mesh>
      <Ground plan={plan} t={t} textures={photo} />
      <WallPlates plan={plan} t={t} />
      <HookWindow plan={plan} t={t} textures={photo} />
      {plan.months.map((m, i) => <MonthView key={m.id} plan={plan} month={m} index={i} t={t} texture={texOf(m)} />)}
      <HookWords plan={plan} fonts={fonts} t={t} />
      {plan.months.map((m, i) => <MonthWords key={m.id} plan={plan} month={m} fonts={fonts} t={t} index={i} />)}
      {closerOf(plan.closerShape) ? null : <CloserWords plan={plan} fonts={fonts} t={t} />}
      {plan.months.map((m, i) => {
        const [a, b] = endsOf(plan, m);
        const along = b.clone().sub(a).normalize();
        return (
          <Burst key={m.id} seed={i} p0={a} p1={b} up={new THREE.Vector3(-along.y, along.x, 0)} age={t - m.at.part[0]} sweepLen={0.15} reach={150 * m.T.s}
            color={mixHex('#ffffff', plan.colors.accent, 0.35)} height={plan.H} size={2.4 * m.T.s} />
        );
      })}
      <Dust time={Math.min(frame, still)} box={[[-760, -1200, 15], [760, 1200, 650]]} color={DUST} height={plan.H}
        sweep={[dot.p.x, dot.p.y, 200 * Math.max(0.3, on ? on.T.s / 0.3 : 1)]} sweepDir={dir} sweepAmt={clamp01(ahead.length() / 18) * (1 - span(t, plan.closer.at, 1))} />
      <DotView plan={plan} t={t} route={route} upTo={plan.closer.card} />
    </group>
  );
};

export const YearFilm: React.FC<{board: Board; clips: Clip[]}> = ({board, clips}) => {
  const plan = useMemo(() => planOf(board), [board]);
  // a card with a cadence steps the picture at that many frames a second, as a camera that shoots fewer frames does
  const now = useCurrentFrame();
  const step = plan.finish.cadence > 0 ? plan.fps / plan.finish.cadence : 1;
  const frame = Math.floor(now / step) * step;
  const files = useMemo(() => [...new Set(linesOf(plan).map(fileOf))], [plan]);
  const fonts = useFonts(files);
  const still = Math.round(plan.closer.still * plan.pulse);
  // from the full stop on, the picture is the still frame
  const t = Math.min(frame, still) / plan.pulse;
  const shot = shotAt(plan, t);
  const route = useMemo(() => (fonts ? routeOf(plan, fonts) : null), [plan, fonts]);
  return (
    <AbsoluteFill style={{background: plan.colors.bg}}>
      {fonts && route ? (
        <Stage pose={shot.pose} travel={shot.travel} background={plan.colors.bg} grade={plan.grade}
          over={<MoveLayer line={plan.line} look={plan.look} t={t} bars={plan.finish.bars}
            closer={{name: plan.closerShape, at: plan.closer.card, still: plan.closer.still}}>
            <CardDot plan={plan} t={t} route={route} />
          </MoveLayer>}>
          <Scene plan={plan} t={t} frame={Math.min(frame, still)} fonts={fonts} clips={clips} still={still} route={route} />
        </Stage>
      ) : null}
    </AbsoluteFill>
  );
};
