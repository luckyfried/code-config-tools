import React, {useEffect, useRef} from 'react';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {faceStyle, useMotion, useSafe, useSys} from './system';

const reported = new Set<string>();

/** Frames a beat's entrances take to come to rest: the longest text delay plus its spring. */
const ENTRANCE = 44;

/**
 * A box inside the format's safe area. A line box that leaves it, or text cut off by a clipping element inside it,
 * is reported to the renderer as SAFE_BREACH once the beat has settled.
 */
export const SafeBox: React.FC<{
  children: React.ReactNode;
  align?: 'start' | 'center' | 'end';
  justify?: 'start' | 'center' | 'end';
  top?: number;
  bottom?: number;
  name: string;
  style?: React.CSSProperties;
}> = ({children, align = 'start', justify = 'end', top, bottom, name, style}) => {
  const s = useSafe();
  const {beat, format} = useSys();
  const {frame, duration} = useMotion();
  const ref = useRef<HTMLDivElement>(null);
  const t = top ?? s.top;
  const b = bottom ?? s.bottom;
  useEffect(() => {
    const el = ref.current;
    if (!el || frame < (beat?.settle ?? Math.max(duration * 0.5, Math.min(duration - 2, ENTRANCE)))) return;
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

/** The display face, fitted to its box on balanced lines, revealed line by line through a mask. */
export const Headline: React.FC<{
  text: string;
  max?: 'hero' | 'h1' | 'h2' | 'h3';
  lines?: number;
  width?: number;
  delay?: number;
  color?: string;
  face?: 'display' | 'text';
  style?: React.CSSProperties;
}> = ({text, max = 'h1', lines = 2, width, delay = 0, color, face = 'display', style}) => {
  const {system} = useSys();
  const s = useSafe();
  const {pop, stagger, tween} = useMotion();
  const f = system[face];
  const w = width ?? s.width;
  const fit = fitTextOnNLines({
    text,
    maxLines: lines,
    maxBoxWidth: w * 0.98,
    fontFamily: `'${f.family}'`,
    fontWeight: f.weight,
    letterSpacing: `${f.tracking}em`,
    textTransform: f.case === 'none' ? undefined : f.case,
    maxFontSize: system.scale[max],
  });
  const kinetic = system.direction === 'kinetic';
  return (
    <div style={{...faceStyle(f), fontSize: fit.fontSize, color: color ?? system.colors.ink, ...style}}>
      {fit.lines.map((line, i) => {
        const p = pop(delay + i * stagger);
        const words = line.split(' ');
        return (
          // the mask reaches below the deepest descender of every display face, so a settled line is never clipped
          <div key={i} style={{overflow: 'hidden', paddingBottom: '0.24em', marginBottom: '-0.24em', whiteSpace: 'nowrap'}}>
            {kinetic ? (
              words.map((wd, j) => {
                const q = pop(delay + (i * words.length + j) * Math.max(1, stagger - 1));
                return (
                  <span
                    key={j}
                    style={{
                      display: 'inline-block',
                      transform: `translateY(${(1 - q) * 130}%) scale(${0.7 + 0.3 * q}) rotate(${(1 - q) * -6}deg)`,
                      transformOrigin: '50% 100%',
                      marginRight: j < words.length - 1 ? '0.24em' : 0,
                    }}
                  >
                    {wd}
                  </span>
                );
              })
            ) : (
              <span
                style={{
                  display: 'inline-block',
                  transform: `translateY(${(1 - p) * 130}%)`,
                  opacity: tween(0, 1, delay + i * stagger, 6),
                }}
              >
                {line}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};

/** The small label above a headline: the text face, tracked out. */
export const Kicker: React.FC<{text: string; delay?: number; color?: string; size?: number; style?: React.CSSProperties}> = ({
  text,
  delay = 0,
  color,
  size,
  style,
}) => {
  const {system} = useSys();
  const {tween} = useMotion();
  const doc = system.direction === 'documentary';
  const reveal = tween(0, 1, delay, 14);
  return (
    <div
      style={{
        ...faceStyle(system.text),
        fontSize: size ?? system.scale.label,
        fontWeight: doc ? 500 : 600,
        letterSpacing: doc ? '0.06em' : '0.18em',
        textTransform: 'uppercase',
        color: color ?? system.colors.accent,
        clipPath: `inset(0 ${(1 - reveal) * 100}% 0 0)`,
        whiteSpace: 'nowrap',
        marginBottom: '0.6em',
        ...style,
      }}
    >
      {text}
    </div>
  );
};

/** A sentence in the text face, fading up after the headline. */
export const Line: React.FC<{text: string; delay?: number; color?: string; size?: number; style?: React.CSSProperties}> = ({
  text,
  delay = 0,
  color,
  size,
  style,
}) => {
  const {system} = useSys();
  const {tween} = useMotion();
  return (
    <div
      style={{
        ...faceStyle(system.text),
        fontWeight: 400,
        letterSpacing: '0',
        textTransform: 'none',
        lineHeight: 1.3,
        fontSize: size ?? system.scale.body,
        color: color ?? system.colors.ink,
        opacity: tween(0, 0.92, delay, 12),
        transform: `translateY(${tween(24, 0, delay, 16)}px)`,
        marginTop: '0.7em',
        maxWidth: '100%',
      }}
    >
      {text}
    </div>
  );
};

/** A number that counts up on the system's entrance curve, set in tabular figures. */
export const Counter: React.FC<{value: number; delay?: number; dur?: number; size: number; color?: string; suffix?: string}> = ({
  value,
  delay = 0,
  dur = 24,
  size,
  color,
  suffix = '',
}) => {
  const {system} = useSys();
  const {tween, pop} = useMotion();
  const n = Math.round(tween(0, value, delay, dur));
  const p = pop(delay);
  return (
    <div
      style={{
        ...faceStyle(system.display),
        fontSize: size,
        lineHeight: 0.9,
        color: color ?? system.colors.ink,
        fontVariantNumeric: 'tabular-nums',
        transform: `scale(${0.85 + 0.15 * p})`,
        transformOrigin: '0% 100%',
        whiteSpace: 'nowrap',
      }}
    >
      {n.toLocaleString('en-US')}
      {suffix}
    </div>
  );
};
