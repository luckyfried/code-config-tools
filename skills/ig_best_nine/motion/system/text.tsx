import React, {useEffect, useRef} from 'react';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {useLayer} from './layer';
import {AbsoluteFill} from 'remotion';
import {axesOf, faceStyle, tint, useColor, useMotion, useSafe, useSys} from './system';
import type {Face, Layer} from './types';

const reported = new Set<string>();

/**
 * A box inside the format's safe area. A line box that leaves it, or text cut off by a clipping element inside it,
 * is reported to the renderer as SAFE_BREACH while its type is settled: from `from` (default the beat's `settle`,
 * else its half) until `until`.
 */
export const SafeBox: React.FC<{
  children: React.ReactNode;
  align?: 'start' | 'center' | 'end';
  justify?: 'start' | 'center' | 'end';
  top?: number;
  bottom?: number;
  from?: number;
  until?: number | null;
  name: string;
  style?: React.CSSProperties;
}> = ({children, align = 'start', justify = 'end', top, bottom, from, until = null, name, style}) => {
  const s = useSafe();
  const {beat, format} = useSys();
  const {frame, duration} = useMotion();
  const ref = useRef<HTMLDivElement>(null);
  const t = top ?? s.top;
  const b = bottom ?? s.bottom;
  useEffect(() => {
    const el = ref.current;
    if (!el || frame < (from ?? beat?.settle ?? duration * 0.5) || (until !== null && frame >= until) || frame >= duration) return;
    const box = el.getBoundingClientRect();
    const scale = box.width / Math.max(1, el.offsetWidth);
    const parts = Array.from(el.querySelectorAll<HTMLElement>('*'));
    const tall = Array.from(el.children).some((c) => {
      const r = c.getBoundingClientRect();
      return r.height > 0 && (r.top < box.top - 2 * scale || r.bottom > box.bottom + 2 * scale);
    });
    const wide = el.scrollWidth > el.clientWidth + 2 || parts.some((c) => c.scrollWidth > c.clientWidth + 2 && getComputedStyle(c).overflow !== 'visible');
    const over = tall || wide;
    const outside = t < s.top - 0.5 || b < s.bottom - 0.5;
    const key = `${format}:${beat?.id}:${name}`;
    if ((over || outside) && !reported.has(key)) {
      reported.add(key);
      console.log(
        `SAFE_BREACH ${JSON.stringify({format, beat: beat?.id, box: name, frame, overflow: over, outside,
          content: [el.scrollWidth, el.scrollHeight], box_size: [el.clientWidth, el.clientHeight]})}`,
      );
    }
  });
  const flex = {start: 'flex-start', center: 'center', end: 'flex-end'} as const;
  return (
    <div
      ref={ref}
      style={{
        position: 'absolute',
        left: s.left,
        right: s.right,
        top: t,
        bottom: b,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: flex[justify],
        alignItems: flex[align],
        textAlign: align === 'center' ? 'center' : align === 'end' ? 'right' : 'left',
        overflow: 'hidden',
        ...style,
      }}
    >
      {children}
    </div>
  );
};

const fit = (text: string, f: Face, width: number, max: number, lines: number) =>
  fitTextOnNLines({
    text,
    maxLines: lines,
    maxBoxWidth: width,
    fontFamily: `'${f.family}'`,
    fontWeight: f.weight,
    letterSpacing: `${f.tracking}em`,
    textTransform: f.case === 'none' ? undefined : f.case,
    additionalStyles: f.axes ? {fontVariationSettings: axesOf(f) as string} : undefined,
    maxFontSize: max,
  });

/** The headline's lines: fitted on balanced lines, or forced into two for `split`. */
const linesOf = (text: string, f: Face, width: number, max: number, lines: number, two: boolean) => {
  const r = fit(text, f, width, max, lines);
  if (!two || r.lines.length >= 2) return r;
  const words = text.split(' ');
  if (words.length < 2) return r;
  const h = Math.ceil(words.length / 2);
  const a = words.slice(0, h).join(' ');
  const b = words.slice(h).join(' ');
  const longer = a.length >= b.length ? a : b;
  return {fontSize: Math.min(fit(longer, f, width, max, 1).fontSize, max), lines: [a, b]};
};

const mask: React.CSSProperties = {overflow: 'hidden', paddingBottom: '0.1em', marginBottom: '-0.1em', whiteSpace: 'nowrap'};

/**
 * Type: the beat's kicker, headline and line moving by one of seven moves. The kicker enters first and leaves
 * last; the headline follows; the line comes in last with a shorter stagger.
 * rise     words rise one by one through a mask
 * track    letters tighten from wide tracking, and keep breathing
 * typeOn   characters typed on one by one
 * slam     the headline drops from 2.4x and lands on its beat on the hit spring
 * wipe     a palette bar sweeps across each line carrying its letters from the bar's first frame, then slides off
 *          and leaves them behind
 * split    two lines open from a rule at the centre
 * counter  a number counts up from 0 in tabular figures and lands on its beat; a rule fills under it
 * Every headline and counter is set in the system's display face, so a tone has one type system. Before an
 * outgoing zoomThrough the type leaves, and it is gone by the frame the push starts, so the push never carries a
 * cut word.
 * `plate` lays a scrim of that palette color from the frame's edge behind the type (a band across the middle
 * for centred type), so the words read on any photo.
 */
export const Type: React.FC<{layer: Layer}> = ({layer}) => {
  const L = useLayer(layer);
  const {system, exit} = useSys();
  const s = useSafe();
  const color = useColor();
  const move: string = layer.move ?? 'rise';
  const st = Math.max(2, L.stagger);
  const lands = move === 'slam' || move === 'counter';
  const hAt = L.start + (layer.kicker ? (lands ? Math.round(L.pulse) : Math.round(L.pulse * 0.5)) : 0);
  const land = layer.land !== undefined ? L.at(layer.land) : move === 'counter' ? hAt + Math.round(L.pulse * 2) : hAt;
  const lineAt = Math.max(hAt, land) + Math.round(L.pulse * (lands ? 0.5 : 1));
  const push = exit?.preset === 'zoomThrough' && !L.still ? L.duration - (exit.frames ?? 8) : null;
  const clear = push === null ? null : push - Math.round(L.pulse * 1.5) - 6;
  const end = clear === null ? L.end : Math.min(L.end ?? clear, clear);
  const out = (lead: number, dur = Math.round(L.pulse * 0.6)) => (end === null ? 0 : L.tween(0, 1, end + lead, dur, 'exit'));
  const lineOut = out(0);
  const headOut = out(3);
  const kickOut = out(6);
  const face: Face = system.display;
  const width = s.width * (layer.width ?? 1) * (move === 'track' ? 0.88 : move === 'slam' ? 0.9 : 0.94);
  const ink = color(layer.color ?? 'ink', 'ink');
  const shadow = layer.shadow ? '0 4px 36px rgba(0,0,0,0.45)' : undefined;
  const justify = ({top: 'start', center: 'center', bottom: 'end'} as const)[(layer.place ?? 'bottom') as 'top' | 'center' | 'bottom'];
  const align = (layer.align ?? 'start') as 'start' | 'center' | 'end';
  const origin = align === 'center' ? '50%' : align === 'end' ? '100%' : '0%';
  const settled = Math.max(lineAt, land) + Math.round(L.pulse * 1.5);

  const headline = (() => {
    if (move === 'counter') {
      const value = Number(layer.value ?? 0);
      const k = Math.min(1, L.tween(0, 1, hAt, Math.max(1, land - hAt), 'enter'));
      const p = L.hit(land);
      const n = Math.round(value * k);
      const txt = `${layer.prefix ?? ''}${n.toLocaleString('en-US')}${layer.suffix ?? ''}`;
      const full = `${layer.prefix ?? ''}${value.toLocaleString('en-US')}${layer.suffix ?? ''}`;
      const size = fit(full, face, width, system.scale[(layer.size ?? 'hero') as 'hero'], 1).fontSize;
      const sc = L.frame < land ? 0.9 + 0.1 * k : 1 + 0.14 * (1 - p);
      return (
        <div style={{transform: `scale(${sc * (1 - headOut * 0.2)})`, transformOrigin: `${origin} 100%`, opacity: Math.min(1, (L.frame - hAt + 2) / 3) * (1 - headOut)}}>
          <div style={{...faceStyle(face), fontSize: size, lineHeight: 0.9, color: ink, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', textShadow: shadow}}>{txt}</div>
          <div style={{height: Math.max(6, size * 0.05), marginTop: size * 0.08, background: color(layer.rule ?? 'accent'), transformOrigin: `${origin} 50%`,
            transform: `scaleX(${k})`, width: '100%'}} />
          {layer.label ? (
            <div style={{...mask, marginTop: '0.3em'}}>
              <div style={{...faceStyle(system.display), fontSize: system.scale.h3, color: ink, transform: `translateY(${(1 - L.pop(land)) * 110 + lineOut * -110}%)`, textShadow: shadow}}>
                {layer.label}
              </div>
            </div>
          ) : null}
        </div>
      );
    }
    const text = String(layer.headline ?? '');
    if (!text) return null;
    const r = linesOf(text, face, width, system.scale[(layer.size ?? 'h1') as 'h1'], layer.lines ?? 2, move === 'split');
    const base: React.CSSProperties = {...faceStyle(face), fontSize: r.fontSize, color: ink, textShadow: shadow};
    if (move === 'slam') {
      const p = L.hit(land - 4);
      const shown = L.frame >= land - 4 ? 1 : 0;
      return (
        <div style={{...base, transform: `scale(${(1 + 1.4 * (1 - p)) * L.travel(1, 1.04) * (1 - headOut * 0.2)})`, transformOrigin: `${origin} 60%`,
          opacity: shown * (1 - headOut), filter: p < 0.6 ? `blur(${(0.6 - p) * 10}px)` : undefined}}>
          {r.lines.map((ln, i) => <div key={i} style={{whiteSpace: 'nowrap'}}>{ln}</div>)}
        </div>
      );
    }
    if (move === 'typeOn') {
      const total = r.lines.reduce((n, ln) => n + ln.length, 0);
      const speed = layer.speed ?? 1.2;
      const typed = Math.floor(Math.max(0, L.frame - hAt) / speed);
      const left = end === null ? total : Math.max(0, total - Math.floor(Math.max(0, L.frame - end - 3) / 0.6));
      const n = Math.min(typed, left, total);
      let used = 0;
      return (
        <div style={base}>
          {r.lines.map((ln, i) => {
            const k = Math.max(0, Math.min(ln.length, n - used));
            used += ln.length;
            return (
              <div key={i} style={{whiteSpace: 'pre', position: 'relative'}}>
                <span>{ln.slice(0, k)}</span>
                <span style={{color: 'transparent', textShadow: 'none'}}>{ln.slice(k)}</span>
              </div>
            );
          })}
        </div>
      );
    }
    if (move === 'wipe') {
      return (
        <div style={base}>
          {r.lines.map((ln, i) => {
            const a0 = hAt + i * st;
            const half = Math.round(L.pulse * 0.4);
            const a = L.tween(0, 1, a0, half, 'move');
            const b = L.tween(0, 1, a0 + half, half, 'move');
            const o = end === null ? 0 : L.tween(0, 1, end + 3 + i * st, half, 'move');
            const o2 = end === null ? 0 : L.tween(0, 1, end + 3 + i * st + half, half, 'move');
            const bar = o > 0 ? (o2 > 0 ? {s: 1 - o2, at: '100%'} : {s: o, at: '0%'}) : b > 0 ? {s: 1 - b, at: '100%'} : {s: a, at: '0%'};
            const clip = o2 > 0 ? `inset(-0.2em -0.2em -0.2em ${o2 * 100}%)` : `inset(-0.2em ${(1 - a) * 100}% -0.2em -0.2em)`;
            if (a <= 0 || o2 >= 1) return <div key={i} style={{whiteSpace: 'nowrap', visibility: 'hidden'}}>{ln}</div>;
            return (
              <div key={i} style={{position: 'relative', whiteSpace: 'nowrap', display: 'block'}}>
                <div style={{position: 'absolute', left: '-0.05em', right: '-0.05em', top: '0.08em', bottom: '0.02em', background: color(layer.bar ?? 'accent'),
                  transformOrigin: `${bar.at} 50%`, transform: `scaleX(${bar.s})`}} />
                <span style={{position: 'relative', display: 'inline-block', clipPath: clip, transform: `translateX(${L.travel(0, 10)}px)`}}>{ln}</span>
              </div>
            );
          })}
        </div>
      );
    }
    if (move === 'split') {
      const rule = L.tween(0, 1, hAt - 2, Math.round(L.pulse * 0.5), 'move');
      const p = L.pop(hAt + Math.round(L.pulse * 0.25));
      const half = Math.ceil(r.lines.length / 2);
      const gap = L.travel(0, r.fontSize * 0.08);
      const close = headOut;
      return (
        <div style={{...base, position: 'relative'}}>
          {r.lines.map((ln, i) => {
            const upper = i < half;
            const y = (1 - p + close) * (upper ? 105 : -105);
            return (
              <div key={i} style={{...mask, transform: `translateY(${upper ? -gap : gap}px)`}}>
                <div style={{transform: `translateY(${y}%)`}}>{ln}</div>
              </div>
            );
          })}
          <div style={{position: 'absolute', left: 0, right: 0, top: '50%', height: Math.max(4, r.fontSize * 0.035), marginTop: -2, background: color(layer.bar ?? 'accent'),
            transformOrigin: `${origin} 50%`, transform: `scaleX(${rule * (1 - close)})`}} />
        </div>
      );
    }
    if (move === 'track') {
      return (
        <div style={base}>
          {r.lines.map((ln, i) => {
            const p = L.tween(0, 1, hAt + i * st, Math.round(L.pulse * 1.4), 'enter');
            const tr = face.tracking + (1 - p) * 0.55 + L.travel(0, 0.03) + headOut * 0.4;
            return (
              <div key={i} style={{whiteSpace: 'nowrap', letterSpacing: `${tr}em`, opacity: p * (1 - headOut), filter: p < 1 ? `blur(${(1 - p) * 10}px)` : undefined}}>
                {ln}
              </div>
            );
          })}
        </div>
      );
    }
    let w = 0;
    return (
      <div style={base}>
        {r.lines.map((ln, i) => (
          <div key={i} style={mask}>
            {ln.split(' ').map((wd, j, all) => {
              const k = w++;
              const p = Math.min(1, L.pop(hAt + k * Math.max(2, st - 1)));
              const o = end === null ? 0 : L.tween(0, 1, end + 3 + k * 2, Math.round(L.pulse * 0.5), 'exit');
              return (
                <span key={j} style={{display: 'inline-block', transform: `translateY(${(1 - p) * 110 - o * 110}%) rotate(${(1 - p) * 4}deg)`, transformOrigin: '0% 100%',
                  marginRight: j < all.length - 1 ? '0.24em' : 0}}>
                  {wd}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    );
  })();

  const kp = L.tween(0, 1, L.start + 3, Math.round(L.pulse * 0.6), 'enter');
  const krule = L.tween(0, 1, L.start, Math.round(L.pulse * 0.4), 'enter');
  const plate = layer.plate ? L.tween(0, 1, L.start - 2, Math.round(L.pulse * 0.6), 'move') * (1 - kickOut) : 0;
  const pc = layer.plate ? color(layer.plate) : '#000000';
  const scrim = justify === 'center'
    ? `linear-gradient(to bottom, ${tint(pc, 0)} 22%, ${tint(pc, 0.82)} 38%, ${tint(pc, 0.82)} 62%, ${tint(pc, 0)} 78%)`
    : `linear-gradient(to ${justify === 'end' ? 'top' : 'bottom'}, ${tint(pc, 0.92)} 0%, ${tint(pc, 0.8)} 32%, ${tint(pc, 0)} 62%)`;
  if (push !== null && L.frame >= push) return null;
  return (
    <>
    {layer.plate ? <AbsoluteFill style={{background: scrim, opacity: plate}} /> : null}
    <SafeBox name={`type-${layer.id ?? move}`} justify={justify} align={align} from={settled} until={end}
      top={layer.top !== undefined ? layer.top * s.H : undefined} bottom={layer.bottom !== undefined ? layer.bottom * s.H : undefined}>
      <div style={{position: 'relative', transform: `translateY(${justify === 'end' ? L.travel(0, -24) : justify === 'start' ? L.travel(0, 24) : L.travel(12, -12)}px)`, maxWidth: '100%'}}>
        <div style={{position: 'relative'}}>
          {layer.kicker ? (
            <div style={{display: 'flex', alignItems: 'center', gap: '0.6em', justifyContent: align === 'center' ? 'center' : 'flex-start', marginBottom: '0.6em'}}>
              <div style={{width: system.scale.label * 1.6, height: 4, background: color(layer.kickerColor ?? 'accent'), transformOrigin: '0% 50%', transform: `scaleX(${krule * (1 - kickOut)})`}} />
              <div style={{...faceStyle(system.text), fontSize: system.scale.label, fontWeight: 600, letterSpacing: '0.18em', textTransform: 'uppercase', whiteSpace: 'nowrap',
                color: color(layer.kickerColor ?? 'accent'), clipPath: kickOut > 0 ? `inset(0 0 0 ${kickOut * 100}%)` : `inset(0 ${(1 - kp) * 100}% 0 0)`, textShadow: shadow}}>
                {layer.kicker}
              </div>
            </div>
          ) : null}
          {headline}
          {layer.line ? (
            <div style={{...faceStyle(system.text), fontWeight: 500, textTransform: 'none', letterSpacing: '0', lineHeight: 1.3, fontSize: system.scale.body,
              color: color(layer.lineColor ?? layer.color ?? 'ink', 'ink'), marginTop: '0.7em', textShadow: shadow}}>
              {String(layer.line).split(' ').map((wd, j, all) => {
                const p = L.pop(lineAt + j * Math.max(1, Math.round(st / 2)));
                return (
                  <span key={j} style={{display: 'inline-block', opacity: Math.min(1, p * 1.4) * (1 - lineOut), transform: `translateY(${(1 - p) * 30 - lineOut * 20}px)`,
                    marginRight: j < all.length - 1 ? '0.28em' : 0}}>
                    {wd}
                  </span>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>
    </SafeBox>
    </>
  );
};

/**
 * Closer: the handle lands, "see you in <next year>" rises, "share yours" stamps in on its beat; the block keeps
 * floating, and the last frame is composed to be screenshotted. `place` puts the block at the top, centre or
 * bottom of the safe area, leaving the rest of the frame to the picture.
 */
export const Closer: React.FC<{layer: Layer}> = ({layer}) => {
  const L = useLayer(layer);
  const {system, board} = useSys();
  const s = useSafe();
  const color = useColor();
  const handle = `@${String(layer.handle ?? board.handle).replace(/^@/, '')}`;
  const year = String(layer.year ?? board.year + 1);
  const share = String(layer.share ?? 'share yours');
  const ink = color(layer.color ?? 'ink', 'ink');
  const a1 = L.start;
  const a2 = L.start + Math.round(L.pulse);
  const a3 = L.start + Math.round(L.pulse * 2);
  const p1 = L.hit(a1 - 4);
  const hSize = fit(handle, system.display, s.width * 0.9, system.scale.h2, 1).fontSize;
  const ySize = fit(year, system.display, s.width * 0.8, system.scale.hero, 1).fontSize;
  const see = 'see you in'.split(' ');
  const ps = L.hit(a3 - 3);
  const place = (layer.place ?? 'center') as 'top' | 'center' | 'bottom';
  const float = place === 'top' ? L.travel(0, 90) : place === 'bottom' ? L.travel(0, -90) : L.travel(60, -60);
  const accent = color(layer.accent ?? 'accent');
  return (
    <SafeBox name="closer" justify={({top: 'start', center: 'center', bottom: 'end'} as const)[place]}
      align="center" from={a3 + Math.round(L.pulse * 1.5)}>
      <div style={{transform: `translateY(${float}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <div style={{...faceStyle(system.display), fontSize: hSize, color: ink, whiteSpace: 'nowrap', opacity: L.frame >= a1 - 4 ? 1 : 0,
          transform: `scale(${1 + 1.2 * (1 - p1)})`, filter: p1 < 0.6 ? `blur(${(0.6 - p1) * 8}px)` : undefined}}>
          {handle}
        </div>
        <div style={{...mask, marginTop: '0.5em'}}>
          {see.map((wd, j) => {
            const p = L.pop(a2 + j * Math.max(2, L.stagger - 1));
            return (
              <span key={j} style={{display: 'inline-block', ...faceStyle(system.text), fontSize: system.scale.h3, textTransform: 'none', letterSpacing: '0.04em',
                color: accent, transform: `translateY(${(1 - p) * 110}%)`, marginRight: j < see.length - 1 ? '0.3em' : 0}}>
                {wd}
              </span>
            );
          })}
        </div>
        <div style={{...mask}}>
          <div style={{...faceStyle(system.display), fontSize: ySize, lineHeight: 0.92, color: ink,
            letterSpacing: `${system.display.tracking + L.travel(0.02, 0.06)}em`, transform: `translateY(${(1 - L.pop(a2 + 4)) * 105}%)`}}>
            {year}
          </div>
        </div>
        <div style={{marginTop: '0.6em', transform: `rotate(${L.travel(-7, -3)}deg) scale(${(1 + 1.1 * (1 - ps)) * L.travel(1, 1.08)})`, opacity: L.frame >= a3 - 3 ? 1 : 0, border: `6px solid ${accent}`,
          padding: '0.18em 0.6em', borderRadius: 10, ...faceStyle(system.display), fontSize: system.scale.h3, color: accent, whiteSpace: 'nowrap',
          textTransform: 'uppercase', letterSpacing: '0.06em', lineHeight: 1}}>
          {share}
        </div>
      </div>
    </SafeBox>
  );
};
