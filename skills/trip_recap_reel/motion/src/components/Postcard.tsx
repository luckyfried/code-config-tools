import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Photo} from '../photo';
import type {Beat} from '../types';

const lum = (hex: string) => {
  const n = parseInt(hex.replace('#', '').slice(0, 6), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const x = v / 255;
    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const contrast = (a: string, b: string) => {
  const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m);
  return (x + 0.05) / (y + 0.05);
};

/** The system's ink or its background, whichever reads better on the paper the postcard is printed on. */
export const paperInk = (colors: {ink: string; bg: string; paper: string}) =>
  contrast(colors.ink, colors.paper) >= contrast(colors.bg, colors.paper) ? colors.ink : colors.bg;

/** The stamp in the print's corner: the place and the date on their accent, perforated, with a postmark over it. */
const Stamp: React.FC<{x: number; y: number; w: number; place: string; date: string; delay: number}> = ({x, y, w, place, date, delay}) => {
  const {system} = useSys();
  const ink = paperInk(system.colors);
  const {pop} = useMotion();
  const p = pop(delay, {damping: 16});
  const h = w * 1.2;
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, height: h, transform: `rotate(${6 - (1 - p) * 20}deg) scale(${1.6 - 0.6 * p})`,
      opacity: Math.min(1, p * 2)}}>
      <div style={{position: 'absolute', inset: 0, background: system.colors.accent, border: `${Math.round(w * 0.04)}px dotted ${system.colors.paper}`,
        boxShadow: '0 6px 16px rgba(0,0,0,0.25)', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: w * 0.1, boxSizing: 'border-box'}}>
        <div style={{...faceStyle(system.display), fontSize: w * 0.2, color: system.colors.paper, lineHeight: 1, overflowWrap: 'anywhere'}}>{place}</div>
        <div style={{...faceStyle(system.text), fontSize: w * 0.1, color: system.colors.paper, marginTop: w * 0.05, letterSpacing: '0.08em', textTransform: 'uppercase'}}>{date}</div>
      </div>
      <svg width={w * 1.5} height={w} style={{position: 'absolute', left: -w * 0.85, top: h * 0.45, overflow: 'visible', opacity: 0.55 * p}}>
        <circle cx={w * 0.45} cy={w * 0.45} r={w * 0.36} fill="none" stroke={ink} strokeWidth={3} />
        {[0, 1, 2].map((i) => (
          <path key={i} d={`M${w * 0.82} ${w * (0.3 + i * 0.15)} q ${w * 0.12} ${-w * 0.06} ${w * 0.24} 0 t ${w * 0.24} 0 t ${w * 0.24} 0`}
            fill="none" stroke={ink} strokeWidth={3} />
        ))}
      </svg>
    </div>
  );
};

/** A place as a postcard: their photo as a print, their own caption set as type, a stamp for the place and the day. */
export const Postcard: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {pop, drift} = useMotion();
  const t = beat.text ?? {};
  const data = beat.data ?? {};
  const wide = s.W > s.H;
  const pw = wide ? s.width * 0.52 : s.W * 0.86;
  const ph = wide ? pw * 0.72 : Math.min(600, pw * 0.74);
  const px = wide ? s.left : (s.W - pw) / 2;
  const py = wide ? s.top + (s.height - ph) / 2 : Math.max(110, s.top - 140);
  const rot = ((data.no ?? 1) % 2 ? -1 : 1) * 2.2;
  const p = pop(0);
  const sw = pw * (wide ? 0.2 : 0.22);
  const textLeft = px + pw + 70;
  const ink = paperInk(system.colors);
  return (
    <AbsoluteFill style={{background: system.colors.paper}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse 80% 60% at 30% 20%, rgba(255,255,255,0.35), rgba(0,0,0,0) 70%)`}} />
      <div style={{position: 'absolute', left: px, top: py, width: pw, height: ph, background: '#fbf8f1', padding: 18, boxSizing: 'border-box',
        boxShadow: '0 30px 70px rgba(0,0,0,0.28)', transform: `translateY(${(1 - p) * 90}px) rotate(${rot * (0.4 + 0.6 * p) + drift(0, 0.5)}deg)`,
        opacity: Math.min(1, p * 1.5)}}>
        <div style={{width: '100%', height: '100%', overflow: 'hidden'}}>
          <div style={{width: '100%', height: '100%', transform: `scale(${drift(1.04, 1.14)}) translateX(${drift(-1, 1)}%)`}}>
            <Photo file={beat.photos?.[0] ?? ''} />
          </div>
        </div>
      </div>
      <Stamp x={px + pw - sw * 0.8} y={py - sw * 0.3} w={sw} place={data.stamp?.place ?? t.kicker ?? ''} date={data.stamp?.date ?? ''} delay={12} />
      <SafeBox name="postcard" justify="start" top={wide ? s.top + s.height * 0.18 : py + ph + 50} style={wide ? {left: textLeft} : undefined}>
        {t.kicker ? <Kicker text={t.kicker} delay={10} color={system.colors.accent} /> : null}
        {t.headline ? <Headline text={t.headline} max="h2" lines={3} delay={14} color={ink} width={wide ? s.W - s.right - textLeft : undefined} /> : null}
        {t.line ? <Line text={t.line} delay={24} color={ink} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
