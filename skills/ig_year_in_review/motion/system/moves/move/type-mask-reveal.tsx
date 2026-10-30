// type-mask-reveal: the beat's words in the display face, set to fill the measure a word or two a line, cut out of the
// card's ground with the photograph showing through the letters from the first frame. Each line rises up through its
// own slot, the first already half up as the beat begins and each after it on the next musical beat, while the
// photograph inside the letters drifts slowly in. The letters read as words first: the photograph inside them is one
// region of it, softened and toned into a narrow range of the card's accent (darker against a light ground, lighter
// against a dark one), so it reads as a texture in a solid letter, and each letter is drawn round its edge in a solid
// rim of the card's pen, or of its accent where the pen would vanish into the ground, which sets it heavier and keeps
// its shape whole. On a photo beat the ground lifts off over the beat's last quarter and leaves the photograph whole. A
// film with no photograph sets the letters in the card's accent.
import React, {useId} from 'react';
import {balance, fill, fitTo, land, lumOf, px, span, SINE, usePhoto} from '../kit';
import type {Move, MoveProps} from '../types';

/** The photograph's region inside the letters: this much larger than the frame's cover, about the frame's middle. */
const REGION = 1.5;
/** The drift inside the letters over the beat, a share of the region. */
const DRIFT = 0.05;
/** The letters' tracking, em: open enough that the rim of one letter never runs into the next. */
const TRACK = -0.012;

/** A hex color's channels, 0 to 1, moved `u` of the way toward `to` (0 black, 1 white). */
const toward = (hex: string, to: number, u: number) => {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => (c / 255) * (1 - u) + to * u);
};
const Overlay: React.FC<MoveProps> = ({look, beat, local, u}) => {
  const id = useId().replace(/:/g, '');
  const ready = usePhoto(look.photo);
  const text = beat.words || beat.label;
  if (!text) return null;
  const n = text.length > 18 ? 3 : text.length > 7 && /\s/.test(text.trim()) ? 2 : 1;
  const lines = balance(text, n);
  const left = px(look, 50), width = look.W - 2 * left;
  const edge = px(look, 10);
  const size = Math.min(fitTo(lines, look.display, width - edge, {weight: 800, tracking: TRACK}), (look.H * 0.62) / (lines.length * 0.98));
  const lh = size * 0.98;
  const top = look.H * 0.45 - (lines.length * lh) / 2;
  const push = REGION * (1 + DRIFT - DRIFT * span(u, 0, 1, SINE));
  const rise = (i: number) => (1 - Math.min(1.08, land(0.35 + (local - i * 0.5) * 1.3))) * lh;
  const letters = (fill: string) => lines.map((ln, i) => (
    <g key={i} clipPath={`url(#${id}-slot-${i})`}>
      <text x={left + edge / 2} y={top + i * lh + size * 0.8 + rise(i)} fill={fill} fontFamily={`'${look.display}'`} fontWeight={800}
        fontSize={size} letterSpacing={`${TRACK * size}px`} style={{whiteSpace: 'pre'}}>{ln}</text>
    </g>
  ));
  const photo = look.photo && ready;
  const cx = look.W / 2, cy = look.H * 0.45;
  // the tone the photograph takes inside the letters: a deep shade of the accent to a tint of it, the range set darker
  // against a light ground and lighter against a dark one
  const light = lumOf(look.tone.ground) > 0.5;
  const [lo, hi] = light ? [toward(look.colors.accent, 0, 0.55), toward(look.colors.accent, 1, 0.1)]
    : [toward(look.colors.accent, 0, 0.1), toward(look.colors.accent, 1, 0.45)];
  const rim = Math.abs(lumOf(look.tone.pen) - lumOf(look.tone.ground)) > 0.2 ? look.tone.pen : look.colors.accent;
  const table = (k: number) => `${lo[k].toFixed(3)} ${hi[k].toFixed(3)}`;
  return (
    <svg width={look.W} height={look.H} style={{...fill, opacity: beat.box ? 1 - span(u, 0.75, 0.25, SINE) : 1}}>
      <defs>
        {lines.map((_, i) => (
          <clipPath key={i} id={`${id}-slot-${i}`}>
            <rect x={0} y={top + i * lh} width={look.W} height={lh} />
          </clipPath>
        ))}
        <filter id={`${id}-tone`} filterUnits="userSpaceOnUse" x={0} y={0} width={look.W} height={look.H} colorInterpolationFilters="sRGB">
          <feGaussianBlur stdDeviation={px(look, 2)} />
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncR type="table" tableValues={table(0)} />
            <feFuncG type="table" tableValues={table(1)} />
            <feFuncB type="table" tableValues={table(2)} />
          </feComponentTransfer>
        </filter>
        {/* the mask's luminance, never drawn: full keeps the photograph, none hides it */}
        <mask id={`${id}-letters`} maskUnits="userSpaceOnUse" x={0} y={0} width={look.W} height={look.H}>{letters('white')}</mask>
      </defs>
      <rect x={0} y={0} width={look.W} height={look.H} fill={look.tone.ground} />
      {photo ? (
        <g mask={`url(#${id}-letters)`}>
          <g filter={`url(#${id}-tone)`}>
            <image href={look.photo} x={0} y={0} width={look.W} height={look.H} preserveAspectRatio="xMidYMid slice"
              transform={`translate(${cx} ${cy}) scale(${push}) translate(${-cx} ${-cy})`} />
          </g>
        </g>
      ) : letters(look.colors.accent)}
      {photo ? <g fill="none" stroke={rim} strokeWidth={edge} strokeLinejoin="round">{lines.map((ln, i) => (
        <g key={i} clipPath={`url(#${id}-slot-${i})`}>
          <text x={left + edge / 2} y={top + i * lh + size * 0.8 + rise(i)} fontFamily={`'${look.display}'`} fontWeight={800}
            fontSize={size} letterSpacing={`${TRACK * size}px`} style={{whiteSpace: 'pre'}}>{ln}</text>
        </g>
      ))}</g> : null}
    </svg>
  );
};

export default {Overlay} satisfies Move;
