import React from 'react';
import {AbsoluteFill, staticFile} from 'remotion';
import {LivePhoto, pick, useBox, useLayer} from './layer';
import {faceStyle, tint, useColor, useSafe, useSys} from './system';
import type {Layer} from './types';

type P = {layer: Layer};

/**
 * Ground: what the beat stands on, never dead.
 * color     a palette field with a soft light travelling across it
 * blur      the beat's photo, blurred, darkened, pushed and drifting
 * gradient  a wash between two palette colors whose angle turns across the beat
 * texture   a palette field with a paper tooth sliding under it
 */
export const Ground: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const c = color(layer.color ?? 'bg', 'bg');
  const style: string = layer.style ?? 'color';
  if (style === 'blur') {
    return (
      <AbsoluteFill style={{background: c, overflow: 'hidden'}}>
        <LivePhoto file={layer.photo ?? pick(layer.photos, 0)} from={1.3} to={1.45} dx={3} dy={2}
          style={{filter: `blur(${layer.blur ?? 38}px) brightness(${layer.dim ?? 0.6}) saturate(1.15)`}} />
      </AbsoluteFill>
    );
  }
  if (style === 'gradient') {
    const c2 = color(layer.to ?? 'accent2', 'accent2');
    return <AbsoluteFill style={{background: `linear-gradient(${L.travel(150, 210)}deg, ${c} 0%, ${c} 35%, ${c2} 100%)`}} />;
  }
  const x = L.travel(20, 80);
  return (
    <AbsoluteFill style={{background: c}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse 70% 45% at ${x}% ${L.travel(30, 60)}%, ${tint('#ffffff', 0.13)} 0%, rgba(255,255,255,0) 70%)`}} />
      {style === 'texture' ? (
        <AbsoluteFill style={{backgroundImage: `url(${staticFile('fx/grain.png')})`, backgroundSize: '1024px 1024px', backgroundPosition: `${L.travel(0, 240)}px ${L.travel(0, -160)}px`,
          mixBlendMode: 'multiply', opacity: 0.5}} />
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * Shape: palette graphics animated in with the type, each with its own motion after.
 * frame (outline drawn on), rule (drawn across), block (wiped in), circle (lands on the hit spring),
 * ring (dotted, turning), arc (drawn on, turning), grid (lines drawn in a stagger, sliding), bars (three bars from alternate sides)
 */
export const Shape: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {W, H} = useSafe();
  const b = useBox(layer.box, [0.07, 0.12, 0.86, 0.66]);
  const c = color(layer.color ?? 'accent');
  const sw = layer.stroke ?? 5;
  const draw = L.tween(0, 1, L.start, Math.round(L.pulse * (layer.draw ?? 1.2)), 'enter');
  const gone = L.leave();
  const spin = L.travel(0, (layer.spin ?? 8) * (L.duration / L.pulse));
  const shape: string = layer.shape ?? 'frame';
  const cx = b.left + b.width / 2;
  const cy = b.top + b.height / 2;
  const svg = (children: React.ReactNode) => (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 1 - gone, transform: layer.rotate ? `rotate(${layer.rotate}deg)` : undefined}}>
      {children}
    </svg>
  );
  if (shape === 'frame') {
    return svg(
      <rect x={b.left} y={b.top} width={b.width} height={b.height} fill="none" stroke={c} strokeWidth={sw} pathLength={1} strokeDasharray={1}
        strokeDashoffset={1 - draw} transform={`translate(${cx} ${cy}) scale(${L.travel(1, 1.035)}) translate(${-cx} ${-cy})`} />,
    );
  }
  if (shape === 'rule') {
    const vertical = b.height > b.width;
    return svg(
      <line x1={b.left} y1={b.top} x2={vertical ? b.left : b.left + b.width} y2={vertical ? b.top + b.height : b.top} stroke={c} strokeWidth={sw}
        pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} transform={`translate(${vertical ? 0 : L.travel(-12, 12)} ${vertical ? L.travel(-12, 12) : 0})`} />,
    );
  }
  if (shape === 'block') {
    const p = L.tween(0, 1, L.start, Math.round(L.pulse * 0.6), 'enter');
    const from: string = layer.from ?? 'left';
    const clip = {left: `inset(0 ${(1 - p) * 100}% 0 0)`, right: `inset(0 0 0 ${(1 - p) * 100}%)`, top: `inset(0 0 ${(1 - p) * 100}% 0)`, bottom: `inset(${(1 - p) * 100}% 0 0 0)`}[from];
    return (
      <div style={{position: 'absolute', left: b.left, top: b.top, width: b.width, height: b.height, background: c, clipPath: clip, opacity: layer.opacity ?? 1,
        transform: `translate(${L.travel(0, layer.dx ?? 0)}px, ${L.travel(0, layer.dy ?? -30)}px) scaleX(${1 - gone}) rotate(${layer.rotate ?? 0}deg)`}} />
    );
  }
  if (shape === 'circle') {
    const p = L.hit(L.start);
    const r = (Math.min(b.width, b.height) / 2) * p * L.travel(1, 1.08) * (1 - gone);
    return svg(<circle cx={cx} cy={cy} r={Math.max(0, r)} fill={c} opacity={layer.opacity ?? 1} />);
  }
  if (shape === 'ring' || shape === 'arc') {
    const r = Math.min(b.width, b.height) / 2;
    const ring = shape === 'ring';
    return svg(
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={c} strokeWidth={sw} pathLength={ring ? undefined : 1}
        strokeDasharray={ring ? layer.dash ?? '3 18' : `${0.72 * draw} 1`} strokeLinecap="round"
        transform={`rotate(${spin - 90} ${cx} ${cy})`} opacity={ring ? draw : 1} />,
    );
  }
  if (shape === 'grid') {
    const n = layer.lines ?? 6;
    const sx = b.width / n;
    const sy = sx;
    const ny = Math.ceil(b.height / sy);
    const slide = L.travel(0, sx);
    return svg(
      <g opacity={layer.opacity ?? 0.35} transform={`translate(${slide * 0.5} ${slide})`}>
        {Array.from({length: n + 1}, (_, k) => (
          <line key={`v${k}`} x1={b.left + k * sx} x2={b.left + k * sx} y1={b.top} y2={b.top + b.height} stroke={c} strokeWidth={Math.max(1, sw / 2)}
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - Math.max(0, Math.min(1, draw * 2 - k / n))} />
        ))}
        {Array.from({length: ny + 1}, (_, k) => (
          <line key={`h${k}`} x1={b.left} x2={b.left + b.width} y1={b.top + k * sy} y2={b.top + k * sy} stroke={c} strokeWidth={Math.max(1, sw / 2)}
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - Math.max(0, Math.min(1, draw * 2 - k / ny))} />
        ))}
      </g>,
    );
  }
  if (shape === 'bars') {
    const cols = [c, color('accent2'), color('ink')];
    const bh = b.height / 3;
    return (
      <>
        {cols.map((col, k) => {
          const p = L.tween(0, 1, L.start + k * Math.max(2, L.stagger), Math.round(L.pulse * 0.7), 'enter');
          const s = k % 2 ? 1 : -1;
          return (
            <div key={k} style={{position: 'absolute', left: b.left, top: b.top + k * bh, width: b.width, height: bh * 0.82, background: col,
              transform: `translateX(${(1 - p) * s * 110 + L.travel(0, -s * 4) - gone * s * 110}%)`}} />
          );
        })}
      </>
    );
  }
  console.log(`UNKNOWN_KIND Shape:${shape}`);
  return null;
};

/** Leak: warm light drifting across the frame in the palette's accents. */
export const Leak: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const a = layer.strength ?? 0.35;
  const x1 = L.travel(layer.from ?? 5, layer.to ?? 95);
  const pulse = 0.75 + 0.25 * Math.sin((L.frame / L.pulse) * Math.PI);
  return (
    <AbsoluteFill style={{mixBlendMode: 'screen', pointerEvents: 'none', opacity: a * pulse * L.tween(0, 1, L.start, Math.round(L.pulse))}}>
      <AbsoluteFill style={{background: `radial-gradient(circle at ${x1}% ${L.travel(18, 36)}%, ${color('accent')} 0%, rgba(0,0,0,0) 45%)`}} />
      <AbsoluteFill style={{background: `radial-gradient(ellipse 70% 40% at ${100 - x1}% 86%, ${color('accent2')} 0%, rgba(0,0,0,0) 60%)`}} />
    </AbsoluteFill>
  );
};

/** Stamp: a round stamp with its text running around a ring, stamped in on the hit spring and turning slowly. */
export const Stamp: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system} = useSys();
  const color = useColor();
  const {W, H} = useSafe();
  const p = L.hit(L.start);
  const r = (layer.size ?? 0.17) * W;
  const [x, y] = layer.center ?? [0.78, 0.2];
  const c = color(layer.color ?? 'accent');
  const ring = String(layer.ring ?? '').toUpperCase();
  const text = String(layer.text ?? '');
  const id = `stamp-${layer.id ?? Math.round(x * 1000 + y * 10)}`;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: Math.min(1, p * 3) * (1 - L.leave())}}>
      <g transform={`translate(${x * W} ${y * H}) scale(${2 - p}) rotate(${(layer.rotate ?? -12) + L.travel(0, 25)})`}>
        <circle r={r} fill={layer.fill ? color(layer.fill) : 'none'} stroke={c} strokeWidth={6} />
        <circle r={r * 0.72} fill="none" stroke={c} strokeWidth={3} />
        <path id={id} d={`M ${-r * 0.86} 0 a ${r * 0.86} ${r * 0.86} 0 1 1 ${r * 1.72} 0 a ${r * 0.86} ${r * 0.86} 0 1 1 ${-r * 1.72} 0`} fill="none" />
        <text style={{...faceStyle(system.text), fontSize: r * 0.16, letterSpacing: '0.2em', textTransform: 'uppercase'}} fill={c}>
          <textPath href={`#${id}`}>{`${ring} · ${ring} · `}</textPath>
        </text>
        <text textAnchor="middle" dominantBaseline="central" fill={c} style={{...faceStyle(system.display), fontSize: r * (text.length > 4 ? 0.32 : 0.5)}}>
          {text}
        </text>
      </g>
    </svg>
  );
};

/** Sticker: a pill of type that pops on with a wobble and keeps bobbing. */
export const Sticker: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system} = useSys();
  const color = useColor();
  const {W, H} = useSafe();
  const p = L.hit(L.start);
  const [x, y] = layer.center ?? [0.3, 0.2];
  const wob = Math.sin((L.local / L.pulse) * Math.PI) * 3;
  return (
    <div style={{position: 'absolute', left: x * W, top: y * H, transform: `translate(-50%, -50%) scale(${p * (1 - L.leave())}) rotate(${(layer.rotate ?? -6) + (1 - p) * 30 + wob}deg)`,
      background: color(layer.color ?? 'accent'), color: color(layer.ink ?? 'paper'), borderRadius: 999, padding: '0.35em 0.9em', whiteSpace: 'nowrap',
      ...faceStyle(system.text), fontSize: layer.size ?? system.scale.label * 1.3, textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 700,
      boxShadow: `0 10px 26px ${tint('#000000', 0.35)}`}}>
      {String(layer.text ?? '')}
    </div>
  );
};

/** Vignette: the frame's edges darkened, breathing with the bar. */
export const VignetteLayer: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const v = (layer.strength ?? 0.5) * (0.9 + 0.1 * Math.sin((L.frame / (L.pulse * 4)) * Math.PI * 2));
  return <AbsoluteFill style={{background: `radial-gradient(ellipse 75% 62% at 50% 46%, rgba(0,0,0,0) 50%, rgba(0,0,0,${v}) 100%)`, pointerEvents: 'none'}} />;
};
