import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {MapCanvas, PinLabel, legPath, project} from '../map';
import type {View} from '../map';
import type {Beat, MapLayout, MapPin} from '../types';

const alpha = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

const mix = (a: string, b: string, t: number) => {
  const p = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, '0')).join('');
};

/** A pin: a dot on the poster, a light with a glow on the night map. */
const Dot: React.FC<{at: [number, number]; r: number; color: string; halo: string; night: boolean; e: number; home: boolean}> = ({at, r, color, halo, night, e, home}) => (
  <g opacity={Math.min(1, e * 1.4)}>
    {night ? <circle cx={at[0]} cy={at[1]} r={r * 4.2 * e} fill={color} opacity={0.22} filter="url(#glow)" /> : null}
    <circle cx={at[0]} cy={at[1]} r={(r + 4) * e} fill={halo} />
    <circle cx={at[0]} cy={at[1]} r={r * e} fill={color} />
    {home ? <circle cx={at[0]} cy={at[1]} r={(r + 10) * e} fill="none" stroke={color} strokeWidth={2.5} /> : null}
  </g>
);

/**
 * The map of the year: every place, the route between them and the count. As the film's closer the route draws
 * in and the places land one by one; as the poster (1080x1350) it is the settled frame. Far places sit in an inset
 * with the distance; the night version lights every place on a dark map.
 */
/** The map rect melts into the background at its top and bottom edges. */
const FADE = 'linear-gradient(to bottom, transparent 0, black 70px, black calc(100% - 70px), transparent 100%)';

export const Poster: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board, format} = useSys();
  const {width: W, height: H} = useVideoConfig();
  const s = useSafe();
  const {tween, pop, duration} = useMotion();
  const d = beat.data ?? {};
  const L: MapLayout = d.layout?.[format] ?? d.layout?.reel ?? d.layout?.poster;
  const night = Boolean(d.night);
  const m = system.map;
  const sea = night ? mix(m.sea, '#000000', 0.45) : m.sea;
  const land = night ? mix(m.land, '#000000', 0.25) : m.land;
  const light = night ? mix(system.colors.accent, '#ffe9b0', 0.45) : m.pin;
  const [rx, ry, rw, rh] = L.rect;
  const view: View = {cam: [L.cam[0], L.cam[1], L.cam[2] * tween(1.08, 1, 0, Math.round(duration * 0.6), 'move')], w: rw, h: rh};
  const pins: Record<string, MapPin> = Object.fromEntries(board.map.pins.map((p) => [p.id, p]));
  const inset = L.inset;
  const farSet = new Set(inset?.ids ?? []);
  const order = board.map.route.filter((id, i, a) => a.indexOf(id) === i);
  const legs = board.map.legs;
  const drawFrames = Math.round(duration * 0.42);
  const per = drawFrames / Math.max(1, legs.length);
  const routeW = format === 'poster' ? 5 : 6;
  const at = (id: string) => project(view, pins[id].x, pins[id].y);
  const iview: View | null = inset ? {cam: inset.cam, w: inset.rect[2], h: inset.rect[3]} : null;
  const iat = (id: string): [number, number] => (iview ? project(iview, pins[id].x, pins[id].y) : [0, 0]);
  const toInset = (from: string): string => {
    if (!inset) return '';
    const [x, y] = at(from);
    const tx = inset.rect[0] + inset.rect[2] / 2;
    const ty = inset.rect[1] + inset.rect[3] / 2;
    const ex = tx + (x > tx ? inset.rect[2] / 2 : -inset.rect[2] / 2);
    const ey = ty;
    const cx = (x + ex) / 2;
    const cy = Math.min(y, ey) - Math.abs(x - ex) * 0.25;
    return `M${x.toFixed(1)} ${y.toFixed(1)}Q${cx.toFixed(1)} ${cy.toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`;
  };
  const t = beat.text ?? {};
  const poster = format === 'poster';
  const farKm = (id: string) => pins[id]?.km_from_home ?? null;
  const glow = (
    <defs>
      <filter id="glow" x="-200%" y="-200%" width="500%" height="500%">
        <feGaussianBlur stdDeviation="6" />
      </filter>
    </defs>
  );
  const drawn = new Set<string>();
  return (
    <AbsoluteFill style={{background: night ? sea : system.colors.bg}}>
      <div style={{position: 'absolute', left: rx, top: ry, width: rw, height: rh, overflow: 'hidden', maskImage: FADE, WebkitMaskImage: FADE}}>
        <MapCanvas view={view} sea={sea} land={land} coast={night ? alpha(light, 0.18) : m.coast} graticule={alpha(night ? light : m.coast, night ? 0.07 : 0.16)}>
          {glow}
          {legs.map((l, i) => {
            const p = tween(0, 1, 4 + i * per, per, 'move');
            if (p <= 0) return null;
            const out = farSet.has(l.to) && !farSet.has(l.from);
            const back = farSet.has(l.from) && !farSet.has(l.to);
            if (farSet.has(l.from) && farSet.has(l.to)) return null;
            const dpath = out ? toInset(l.from) : back ? toInset(l.to) : legPath(view, l.arc, p);
            return (
              <path key={i} d={dpath} fill="none" stroke={night ? alpha(light, 0.45) : m.route} strokeWidth={routeW}
                strokeLinecap="round" strokeLinejoin="round" strokeDasharray={out || back || l.far ? `1 ${routeW * 3}` : undefined}
                opacity={out || back ? p : 1} />
            );
          })}
          {order.filter((id) => !farSet.has(id) && pins[id]).map((id, i) => {
            const e = pop(6 + Math.round((order.indexOf(id) * drawFrames) / Math.max(1, order.length)));
            drawn.add(id);
            return <Dot key={id} at={at(id)} r={poster ? 8 : 9} color={pins[id].home && !night ? m.label : light} halo={night ? sea : m.halo} night={night} e={e} home={pins[id].home} />;
          })}
          {order.filter((id) => !farSet.has(id) && pins[id]).map((id) => (
            <PinLabel key={`l${id}`} pin={pins[id]} at={at(id)} side={L.labels[id] ?? 'right'} size={L.size} color={night ? mix(light, '#ffffff', 0.4) : m.label}
              halo={night ? sea : m.halo} opacity={tween(0, 1, Math.round(duration * 0.35), 14)} />
          ))}
        </MapCanvas>
        {inset && iview ? (
          <div
            style={{
              position: 'absolute',
              left: inset.rect[0],
              top: inset.rect[1],
              width: inset.rect[2],
              height: inset.rect[3],
              overflow: 'hidden',
              border: `3px solid ${night ? alpha(light, 0.7) : m.label}`,
              boxShadow: '0 18px 40px rgba(0,0,0,0.3)',
              opacity: tween(0, 1, Math.round(duration * 0.3), 12),
              transform: `scale(${0.92 + 0.08 * tween(0, 1, Math.round(duration * 0.3), 16)})`,
            }}
          >
            <MapCanvas view={iview} sea={sea} land={land} coast={night ? alpha(light, 0.18) : m.coast}>
              {glow}
              {inset.ids.map((id) => (
                <g key={id}>
                  <Dot at={iat(id)} r={8} color={light} halo={night ? sea : m.halo} night={night} e={1} home={false} />
                  <PinLabel pin={pins[id]} at={iat(id)} side={L.labels[id] ?? 'right'} size={Math.round(L.size * 0.85)}
                    color={night ? mix(light, '#ffffff', 0.4) : m.label} halo={night ? sea : m.halo} />
                </g>
              ))}
            </MapCanvas>
            {inset.ids.length === 1 && farKm(inset.ids[0]) ? (
              <div style={{position: 'absolute', left: 14, bottom: 10, ...faceStyle(system.text), fontSize: Math.round(L.size * 0.6),
                fontWeight: 600, color: night ? light : m.label, textShadow: `0 0 6px ${night ? sea : m.halo}`, letterSpacing: '0.04em'}}>
                {`${farKm(inset.ids[0])!.toLocaleString('en-US')} km from home`}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
      {poster ? (
        <>
          <SafeBox name="poster-title" justify="start" bottom={H - ry + 8}>
            {t.kicker ? <Kicker text={t.kicker} delay={4} /> : null}
            {t.headline ? <Headline text={t.headline} max="h1" lines={1} delay={8} /> : null}
          </SafeBox>
          <SafeBox name="poster-foot" justify="start" top={ry + rh + 18}>
            {t.line ? <Line text={t.line} delay={14} style={{marginTop: 0}} /> : null}
            <div style={{display: 'flex', gap: 10, width: '100%', marginTop: 18}}>
              {system.colors.swatches.slice(0, 5).map((w, i) => (
                <div key={i} style={{flex: 1, height: 16, background: w.hex}} />
              ))}
            </div>
          </SafeBox>
        </>
      ) : (
        <>
          <SafeBox name="map-kicker" justify="start" bottom={H - s.top - 80}>
            {t.kicker ? <Kicker text={t.kicker} delay={4} color={night ? light : system.colors.accent} /> : null}
          </SafeBox>
          <SafeBox name="map-title" justify="start" top={ry + rh + 6}>
            {t.headline ? <Headline text={t.headline} max="h2" lines={1} delay={Math.round(duration * 0.4)} color={night ? mix(light, '#ffffff', 0.5) : undefined} /> : null}
            {t.line ? <Line text={t.line} delay={Math.round(duration * 0.4) + 8} style={{marginTop: '0.3em'}} /> : null}
          </SafeBox>
        </>
      )}
    </AbsoluteFill>
  );
};
