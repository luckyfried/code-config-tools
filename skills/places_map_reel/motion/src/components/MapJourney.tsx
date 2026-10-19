import React from 'react';
import {AbsoluteFill, Img, useVideoConfig} from 'remotion';
import {faceStyle, hash, src, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {RETRIES, Scrim} from '../photo';
import {MapCanvas, PinLabel, legHead, legPath, lerpCam, project} from '../map';
import type {View} from '../map';
import type {Beat, Cam, MapPin} from '../types';

const alpha = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

/** A photo of theirs pinned to the map at a place it was taken: a round marker on a short stem. */
const PhotoPin: React.FC<{file: string; at: [number, number]; size: number; ring: string; enter: number}> = ({file, at, size, ring, enter}) => (
  <div
    style={{
      position: 'absolute',
      left: at[0] - size / 2,
      top: at[1] - size - 14,
      width: size,
      height: size,
      borderRadius: size,
      overflow: 'hidden',
      border: `4px solid ${ring}`,
      boxShadow: '0 10px 24px rgba(0,0,0,0.35)',
      transform: `scale(${enter})`,
      transformOrigin: '50% 125%',
    }}
  >
    <Img src={src(file)} maxRetries={RETRIES} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
  </div>
);

/**
 * The route on a map in their colors. overview: every place appears as the camera comes down onto the start.
 * leg: the camera moves from the last arrival to frame the next, the leg draws itself, the pin lands and their
 * photo of that place is pinned beside it; the photos of earlier arrivals stay pinned where they were taken.
 */
export const MapJourney: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const {width: W, height: H} = useVideoConfig();
  const s = useSafe();
  const {frame, duration, tween, pop, drift} = useMotion();
  const d = beat.data ?? {};
  const m = system.map;
  const legs = board.map.legs;
  const pins: Record<string, MapPin> = Object.fromEntries(board.map.pins.map((p) => [p.id, p]));
  const move = tween(0, 1, 0, Math.round(duration * (d.mode === 'overview' ? 0.8 : 0.5)), 'move');
  const cam: Cam = lerpCam(d.cam0, d.cam1, move);
  const view: View = {cam, w: W, h: H};
  const active: number[] = d.legs ?? [];
  const drawStart = Math.round(duration * 0.1);
  const drawEnd = Math.round(duration * 0.56);
  const per = (drawEnd - drawStart) / Math.max(1, active.length);
  const progress = (k: number) => tween(0, 1, drawStart + k * per, per, 'move');
  const arrived = active.length ? progress(active.length - 1) >= 1 : true;
  const visited = new Set<string>();
  if (d.mode === 'overview') board.map.pins.forEach((p) => visited.add(p.id));
  legs.slice(0, d.done ?? 0).forEach((l) => {
    visited.add(l.from);
    visited.add(l.to);
  });
  active.forEach((k, i) => {
    visited.add(legs[k].from);
    if (progress(i) >= 1) visited.add(legs[k].to);
  });
  if (!legs.length) board.map.pins.forEach((p) => visited.add(p.id));
  const px = (id: string) => project(view, pins[id].x, pins[id].y);
  const routeW = system.direction === 'kinetic' ? 9 : 8;
  const dash = (far: boolean) => (far ? `${routeW * 0.1} ${routeW * 2.6}` : undefined);
  const arrive: string | undefined = d.arrive;
  const landAt = drawEnd + 2;
  const landed = pop(landAt);
  const card = d.card;
  const target = arrive && pins[arrive] ? project({cam: d.cam1, w: W, h: H}, pins[arrive].x, pins[arrive].y) : [W / 2, H / 2];
  const cardW = 430;
  const side: string = card?.side ?? (target[0] < W / 2 ? 'right' : 'left');
  const cardLeft = side === 'right' ? W - s.right - cardW + 30 : s.left - 10;
  const cardTop = s.top + 20;
  const c = pop(landAt + 4);
  const tilt = (hash(beat.id) - 0.5) * 7;
  return (
    <AbsoluteFill style={{background: m.sea, overflow: 'hidden'}}>
      <MapCanvas view={view} sea={m.sea} land={m.land} coast={m.coast} graticule={alpha(m.coast, 0.18)}>
        {legs.slice(0, d.done ?? 0).map((l, i) => (
          <path key={`d${i}`} d={legPath(view, l.arc, 1)} fill="none" stroke={alpha(m.route, 0.75)} strokeWidth={routeW * 0.75}
            strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash(l.far)} />
        ))}
        {active.map((k, i) => {
          const l = legs[k];
          const t = progress(i);
          if (t <= 0) return null;
          const [hx, hy] = legHead(view, l.arc, t);
          return (
            <g key={`a${k}`}>
              <path d={legPath(view, l.arc, t)} fill="none" stroke={m.route} strokeWidth={routeW} strokeLinecap="round"
                strokeLinejoin="round" strokeDasharray={dash(l.far)} />
              {t < 1 ? <circle cx={hx} cy={hy} r={routeW * 1.6} fill={m.route} stroke={m.halo} strokeWidth={3} /> : null}
            </g>
          );
        })}
        {board.map.pins.map((p, i) => {
          if (!visited.has(p.id)) return null;
          const [x, y] = px(p.id);
          const isNew = p.id === arrive && arrived;
          const e = d.mode === 'overview' ? pop(6 + i * 3) : isNew ? landed : 1;
          const r = (p.home ? 11 : 8) * e;
          return (
            <g key={p.id}>
              {isNew ? <circle cx={x} cy={y} r={14 + 60 * tween(0, 1, landAt, 22)} fill="none" stroke={m.pin}
                strokeWidth={3} opacity={1 - tween(0, 1, landAt, 22)} /> : null}
              <circle cx={x} cy={y} r={r + 4} fill={m.halo} />
              <circle cx={x} cy={y} r={r} fill={p.home ? m.label : m.pin} />
            </g>
          );
        })}
        {d.mode === 'overview'
          ? board.map.pins.map((p, i) => (
              <PinLabel key={`l${p.id}`} pin={p} at={px(p.id)} side={d.labels?.[p.id] ?? 'right'} size={30} color={m.label} halo={m.halo}
                opacity={tween(0, 0.9, 14 + i * 3, 10)} />
            ))
          : null}
      </MapCanvas>
      {(d.pinned ?? []).map((q: {id: string; photo: string}) =>
        pins[q.id] ? <PhotoPin key={q.id} file={q.photo} at={px(q.id)} size={70} ring={system.colors.paper} enter={1} /> : null,
      )}
      {card?.photo && arrive && pins[arrive] ? (
        <>
          <PhotoPin file={card.photo} at={px(arrive)} size={78} ring={m.pin} enter={landed} />
          <div
            style={{
              position: 'absolute',
              left: cardLeft,
              top: cardTop,
              width: cardW,
              padding: '18px 18px 0',
              background: system.colors.paper,
              boxShadow: '0 30px 70px rgba(0,0,0,0.45)',
              transform: `translateY(${(1 - c) * 120}px) rotate(${tilt + (1 - c) * 6}deg) scale(${0.9 + 0.1 * c})`,
              opacity: Math.min(1, c * 1.5),
            }}
          >
            <div style={{width: '100%', aspectRatio: '4 / 5', overflow: 'hidden', background: m.land}}>
              <Img src={src(card.photo)} maxRetries={RETRIES}
                style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${drift(1.04, 1.14)})`}} />
            </div>
            <div style={{...faceStyle(system.text), fontSize: 24, color: system.colors.bg, padding: '14px 2px 16px', whiteSpace: 'nowrap',
              overflow: 'hidden', textOverflow: 'clip', letterSpacing: '0.04em'}}>
              {card.name}{card.country ? `, ${card.country}` : ''}
            </div>
          </div>
        </>
      ) : null}
      <Scrim side="bottom" strength={0.82} />
      <SafeBox name="map" justify="end">
        {beat.text?.kicker ? <Kicker text={beat.text.kicker} delay={4} /> : null}
        {beat.text?.headline ? <Headline text={beat.text.headline} max="h1" lines={2} delay={7} /> : null}
        {beat.text?.line ? <Line text={beat.text.line} delay={16} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
