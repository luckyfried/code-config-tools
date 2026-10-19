import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {faceStyle, splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Photo} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat, BeatText, Tile} from '../types';

/** The wall is laid out at full photo size and scaled down to the frame, so every zoom stays sharp. */
const T = 1080;
const G = 30;
const V = 3 * T + 2 * G;
const at = (slot: number) => ({x: (slot % 3) * (T + G), y: Math.floor(slot / 3) * (T + G)});

type Cam = {cx: number; cy: number; k: number; ay: number};

/** Where the wall sits on screen when it is whole: below the type. */
const useWallBox = () => {
  const s = useSafe();
  return {size: s.W - 2 * 48, top: s.top + 380};
};

const Badge: React.FC<{rank: number; show: number}> = ({rank, show}) => {
  const {system} = useSys();
  const d = system.direction;
  const label = d === 'documentary' ? String(rank).padStart(2, '0') : String(rank);
  const size = d === 'kinetic' ? 230 : d === 'editorial' ? 170 : 120;
  return (
    <div style={{position: 'absolute', left: 44, bottom: d === 'documentary' ? undefined : 30, top: d === 'documentary' ? 40 : undefined,
      ...faceStyle(d === 'documentary' ? system.text : system.display), fontSize: size, lineHeight: 0.9, letterSpacing: d === 'documentary' ? '0.04em' : undefined,
      color: d === 'kinetic' ? system.colors.accent : system.colors.paper, opacity: show,
      textShadow: d === 'editorial' ? '0 6px 40px rgba(0,0,0,0.55)' : 'none',
      background: d === 'editorial' ? undefined : d === 'kinetic' ? system.colors.bg : 'rgba(0,0,0,0.55)',
      padding: d === 'kinetic' ? '18px 30px 6px' : d === 'documentary' ? '10px 22px' : undefined}}>
      {label}
    </div>
  );
};

/** One tile at its slot: the photo, its own reel playing over it when it has one, and its number. */
const TileView: React.FC<{tile: Tile; slot: number; arrive: number; enter: number; badge: boolean; clipFrom?: number}> = ({
  tile, slot, arrive, enter, badge, clipFrom,
}) => {
  const {system} = useSys();
  const {drift} = useMotion();
  const {x, y} = at(slot);
  const d = system.direction;
  const fromX = (slot % 3) - 1;
  const fromY = Math.floor(slot / 3) - 1;
  const move = d === 'kinetic'
    ? `translate(${(1 - enter) * fromX * 900}px, ${(1 - enter) * (fromY * 900 + 500)}px) scale(${1.35 - 0.35 * enter}) rotate(${(1 - enter) * (slot % 2 ? 9 : -9)}deg)`
    : `translateY(${(1 - enter) * 120}px) scale(${0.94 + 0.06 * enter})`;
  return (
    <>
      <div style={{position: 'absolute', left: x, top: y, width: T, height: T, border: `6px solid ${system.colors.muted}`, opacity: 0.35 * (1 - arrive),
        boxSizing: 'border-box'}} />
      <div style={{position: 'absolute', left: x, top: y, width: T, height: T, overflow: 'hidden', transform: move, opacity: Math.min(1, enter * 1.4),
        boxShadow: d === 'kinetic' && enter < 1 ? '0 60px 120px rgba(0,0,0,0.5)' : undefined}}>
        <div style={{width: '100%', height: '100%', transform: `scale(${drift(1.03, 1.1)})`}}>
          <Photo file={tile.photo} />
        </div>
        {tile.clip && clipFrom !== undefined && tile.clip.frames ? (
          <Sequence from={clipFrom} durationInFrames={tile.clip.frames} layout="none">
            <AbsoluteFill>
              <ClipLayer clip={tile.clip} />
            </AbsoluteFill>
          </Sequence>
        ) : null}
        {badge ? <Badge rank={tile.rank} show={enter} /> : null}
      </div>
    </>
  );
};

/** The words above the wall: who is in the photo, when, and her caption. */
const Words: React.FC<{text: BeatText; name: string; delay?: number}> = ({text, name, delay = 0}) => {
  const {system} = useSys();
  const s = useSafe();
  const box = useWallBox();
  return (
    <SafeBox name={name} justify="start" bottom={s.H - box.top + 16}>
      {text.kicker ? <Kicker text={text.kicker} delay={delay} /> : null}
      {text.headline ? <Headline text={text.headline} max="h2" lines={2} delay={delay + 4} /> : null}
      {text.line ? <Line text={text.line} delay={delay + 12} size={system.scale.label} /> : null}
    </SafeBox>
  );
};

/** reveal: the whole wall settles in, slot by slot, under the words. */
const Reveal: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const {pop, tween, drift} = useMotion();
  const s = useSafe();
  const box = useWallBox();
  const data = beat.data;
  const tiles: Tile[] = data.tiles;
  const by = new Map(tiles.map((t) => [t.rank, t]));
  const stagger = data.stagger ?? system.ease.stagger;
  const k = box.size / V;
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {system.texture.leaks ? <Leaks strength={0.6} seed={beat.id} /> : null}
      <div style={{position: 'absolute', left: (s.W - box.size) / 2, top: box.top, width: V, height: V,
        transform: `scale(${k * drift(1, 1.02)})`, transformOrigin: '0 0'}}>
        {(data.order as number[]).map((rank, slot) => {
          const t = by.get(rank);
          if (!t) return null;
          const e = system.direction === 'kinetic' ? pop(slot * stagger) : tween(0, 1, slot * stagger, 18);
          return <TileView key={rank} tile={t} slot={slot} arrive={1} enter={e} badge />;
        })}
      </div>
      <Words text={beat.text ?? {}} name="wall" delay={Math.min(24, 9 * stagger * 0.5)} />
    </AbsoluteFill>
  );
};

/** camera: one unbroken move across the wall along data.path, tile to tile, then the pull back to the whole wall. */
const Camera: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const {frame, curves} = useMotion();
  const s = useSafe();
  const box = useWallBox();
  const data = beat.data;
  const tiles: Tile[] = data.tiles;
  const order: number[] = data.order;
  const path: number[] = data.path ?? [0, 1, 2, 5, 4, 3, 6, 7, 8];
  const by = new Map(tiles.map((t) => [t.rank, t]));
  const spans = splits(beat, 10);
  const near = (slot: number): Cam => ({cx: at(slot).x + T / 2, cy: at(slot).y + T / 2, k: (s.W * 0.86) / T, ay: s.H * 0.585});
  const whole: Cam = {cx: V / 2, cy: V / 2, k: box.size / V, ay: box.top + box.size / 2};
  const lerp = (a: Cam, b: Cam, t: number): Cam => ({cx: a.cx + (b.cx - a.cx) * t, cy: a.cy + (b.cy - a.cy) * t,
    k: Math.exp(Math.log(a.k) + (Math.log(b.k) - Math.log(a.k)) * t), ay: a.ay + (b.ay - a.ay) * t});
  let shot = spans.findIndex(([a, n]) => frame >= a && frame < a + n);
  if (shot < 0) shot = frame < 0 ? 0 : 9;
  const [start, len] = spans[shot];
  const into = Math.min(1, Math.max(0, (frame - start) / Math.max(1, len)));
  let cam: Cam;
  if (shot < 9) {
    const to = near(path[shot]);
    const from = shot === 0 ? {...to, k: to.k * 1.12} : near(path[shot - 1]);
    const m = Math.min(1, (frame - start) / Math.max(1, Math.min(20, len * 0.45)));
    cam = lerp(from, to, curves.move(Math.max(0, m)));
    cam = {...cam, k: cam.k * (1 + 0.035 * into)};
  } else {
    cam = lerp(near(path[8]), whole, curves.move(Math.min(1, into / 0.55)));
  }
  const x = s.W / 2 - cam.cx * cam.k;
  const y = cam.ay - cam.cy * cam.k;
  const shotOf = (rank: number) => path.indexOf(order.indexOf(rank));
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: V, height: V, transform: `translate(${x}px, ${y}px) scale(${cam.k})`, transformOrigin: '0 0'}}>
        {order.map((rank, slot) => {
          const t = by.get(rank);
          if (!t) return null;
          const k = shotOf(rank);
          return <TileView key={rank} tile={t} slot={slot} arrive={1} enter={1} badge clipFrom={Math.max(0, (spans[k]?.[0] ?? 0) - 12)} />;
        })}
      </div>
      <Leaks strength={0.7} seed={beat.id} />
      <AbsoluteFill style={{background: `linear-gradient(to bottom, ${system.colors.bg} 0%, ${system.colors.bg} ${((box.top - 40) / s.H) * 100}%, transparent ${((box.top + 50) / s.H) * 100}%)`,
        opacity: shot < 9 ? 0.94 : 0.94 * (1 - curves.move(Math.min(1, into / 0.55)))}} />
      {spans.slice(0, 9).map(([a, n], i) => {
        const t = by.get(order[path[i]]);
        if (!t) return null;
        return (
          <Sequence key={i} from={a} durationInFrames={n} layout="none">
            <SubShot frames={n}>
              <Words text={{kicker: `${String(t.rank).padStart(2, '0')} · ${t.label ?? ''}`, headline: t.caption, line: t.line}} name={`tile-${t.rank}`} delay={4} />
            </SubShot>
          </Sequence>
        );
      })}
      <Sequence from={spans[9][0]} durationInFrames={spans[9][1]} layout="none">
        <SubShot frames={spans[9][1]}>
          <Words text={beat.text ?? {}} name="wall" delay={Math.round(spans[9][1] * 0.35)} />
        </SubShot>
      </Sequence>
    </AbsoluteFill>
  );
};

export const Grid: React.FC<{beat: Beat}> = ({beat}) => {
  const {still} = useSys();
  const mode = beat.data?.mode ?? 'reveal';
  if (!beat.data?.tiles?.length) return null;
  if (!still && mode === 'camera') return <Camera beat={beat} />;
  return <Reveal beat={beat} />;
};

