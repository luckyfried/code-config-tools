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

/** Where the wall sits on screen when it is whole: below the type on the reel and the story, edge to edge on the square. */
const useWallBox = () => {
  const {format} = useSys();
  const s = useSafe();
  if (format === 'square') return {size: s.W, top: 0};
  if (format === 'story') return {size: s.W - 2 * 72, top: s.top + 380};
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

/** One tile at its slot: the photo, its own reel playing over it when it has one, and its rank. */
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

/** kickerDelay: when the kicker wipes in; a negative value shows it already in place (it carries over from the shot before). */
const Words: React.FC<{text: BeatText; name: string; delay?: number; numeral?: string; kickerDelay?: number}> = ({text, name, delay = 0, numeral, kickerDelay}) => {
  const {system, format} = useSys();
  const s = useSafe();
  const {tween} = useMotion();
  const box = useWallBox();
  if (format === 'square') {
    const chip = [text.kicker, text.headline].filter(Boolean).join(' · ');
    return (
      <SafeBox name={name} justify="end" align="start">
        <div style={{background: system.colors.bg, padding: '12px 20px', ...faceStyle(system.text), fontSize: 30, fontWeight: 600,
          letterSpacing: '0.06em', textTransform: 'none', color: system.colors.ink, whiteSpace: 'nowrap', borderLeft: `6px solid ${system.colors.accent}`}}>
          {chip}
        </div>
      </SafeBox>
    );
  }
  const p = tween(0, 1, delay, 8);
  return (
    <SafeBox name={name} justify="start" bottom={s.H - box.top + 16}>
      {numeral ? (
        <div style={{...faceStyle(system.display), fontSize: system.scale.hero, lineHeight: 0.82, color: system.colors.accent,
          transform: `translateY(${(1 - p) * 30}%) scale(${0.6 + 0.4 * p})`, transformOrigin: '0% 0%', opacity: Math.min(1, p * 2)}}>
          {numeral}
        </div>
      ) : null}
      {text.kicker ? <Kicker text={text.kicker} delay={kickerDelay ?? delay} /> : null}
      {text.headline && !numeral ? <Headline text={text.headline} max="h2" lines={2} delay={delay + 4} /> : null}
      {text.line && !numeral ? <Line text={text.line} delay={delay + 12} size={format === 'story' ? system.scale.body : system.scale.label} /> : null}
    </SafeBox>
  );
};

/** fly: the nine land one per beat, nine to one, then the wall holds with the words. */
const Fly: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const {pop, drift, frame} = useMotion();
  const s = useSafe();
  const box = useWallBox();
  const data = beat.data;
  const tiles: Tile[] = data.tiles;
  const order: number[] = data.order;
  const spans = splits(beat, 10);
  const by = new Map(tiles.map((t) => [t.rank, t]));
  const k = box.size / V;
  const hold = spans[9][0];
  const shot = spans.findIndex(([a, n]) => frame >= a && frame < a + n);
  const landing = shot >= 0 && shot < 9 ? 9 - shot : null;
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <div style={{position: 'absolute', left: (s.W - box.size) / 2, top: box.top, width: V, height: V,
        transform: `scale(${k * drift(1, 1.025)})`, transformOrigin: '0 0'}}>
        {order.map((rank, slot) => {
          const t = by.get(rank);
          if (!t) return null;
          const a = spans[9 - rank]?.[0] ?? 0;
          const q = pop(a, {damping: 13, stiffness: 170});
          return <TileView key={rank} tile={t} slot={slot} arrive={frame >= a ? 1 : 0} enter={frame >= a ? q : 0} badge />;
        })}
      </div>
      {landing !== null ? (
        <Sequence key={landing} from={spans[9 - landing][0]} durationInFrames={spans[9 - landing][1]} layout="none">
          <SubShot frames={spans[9 - landing][1]}>
            <Words text={{kicker: beat.text?.kicker}} name={`no-${landing}`} numeral={String(landing)} kickerDelay={landing === 9 ? 0 : -20} />
          </SubShot>
        </Sequence>
      ) : (
        <Sequence from={hold} durationInFrames={spans[9][1]} layout="none">
          <SubShot frames={spans[9][1]}>
            <Words text={beat.text ?? {}} name="hold" delay={2} kickerDelay={-20} />
          </SubShot>
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

/** reveal: the whole wall settles in, slot by slot, under the words. */
const Reveal: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, format} = useSys();
  const {pop, tween, drift} = useMotion();
  const s = useSafe();
  const box = useWallBox();
  const data = beat.data;
  const tiles: Tile[] = data.tiles;
  const by = new Map(tiles.map((t) => [t.rank, t]));
  const stagger = data.stagger ?? system.ease.stagger;
  const k = box.size / V;
  const card = format === 'square' || format === 'story';
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {system.texture.leaks && !card ? <Leaks strength={0.6} seed={beat.id} /> : null}
      <div style={{position: 'absolute', left: (s.W - box.size) / 2, top: box.top, width: V, height: V,
        transform: `scale(${k * (card ? 1 : drift(1, 1.02))})`, transformOrigin: '0 0'}}>
        {(data.order as number[]).map((rank, slot) => {
          const t = by.get(rank);
          if (!t) return null;
          const e = system.direction === 'kinetic' ? pop(slot * stagger) : tween(0, 1, slot * stagger, 18);
          return <TileView key={rank} tile={t} slot={slot} arrive={1} enter={e} badge={!card} />;
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
        const line = t.likes != null ? `${t.likes.toLocaleString('en-US')} likes${t.comments ? ` · ${t.comments} comments` : ''}` : undefined;
        return (
          <Sequence key={i} from={a} durationInFrames={n} layout="none">
            <SubShot frames={n}>
              <Words text={{kicker: `${String(t.rank).padStart(2, '0')} · ${t.label ?? ''}`, headline: t.caption, line}} name={`tile-${t.rank}`} delay={4} />
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
  if (still || mode === 'reveal') return <Reveal beat={beat} />;
  if (mode === 'camera') return <Camera beat={beat} />;
  return <Fly beat={beat} />;
};

