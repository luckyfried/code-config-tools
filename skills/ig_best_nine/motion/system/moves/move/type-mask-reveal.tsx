// type-mask-reveal: the beat's words in the display face, set as large as the safe area's measure allows about two
// words a line, cut out of the card's ground with the photograph showing through the letters from the first frame, in
// its own color. Each line rises up through its own slot, the first already half up as the beat begins and each after
// it on the next musical beat, while the photograph inside the letters drifts slowly in. Each letter is drawn round its
// edge in a solid rim of the card's pen, or of its accent where the pen would vanish into the ground, which sets it
// heavier and keeps its shape whole over a pale part of the picture. On a photo beat the ground lifts off over the
// beat's last quarter and leaves the photograph whole. A film with no photograph sets the letters in the card's accent.
import React, {useId} from 'react';
import {fill, fitTo, land, lumOf, OPTICAL, px, safeOf, setLines, span, SINE, usePhoto} from '../kit';
import type {Move, MoveProps} from '../types';

/** The photograph's region inside the letters: this much larger than the frame's cover, about the frame's middle. */
const REGION = 1.5;
/** The drift inside the letters over the beat, a share of the region. */
const DRIFT = 0.05;
/** The letters' tracking, em: open enough that the rim of one letter never runs into the next. */
const TRACK = -0.012;

const Overlay: React.FC<MoveProps> = ({look, beat, local, u}) => {
  const id = useId().replace(/:/g, '');
  const ready = usePhoto(look.photo);
  const text = beat.words || beat.label;
  if (!text) return null;
  const [sx0, , sx1] = safeOf(look);
  const left = sx0, width = sx1 - sx0;
  const edge = px(look, 10);
  const {lines, size} = setLines(text, 2, (ls) => Math.min(fitTo(ls, look.display, width - edge, {weight: 800, tracking: TRACK}), (look.H * 0.62) / (ls.length * 0.98)));
  const lh = size * 0.98;
  const top = look.H * 0.45 - (lines.length * lh) / 2;
  const push = REGION * (1 + DRIFT - DRIFT * span(u, 0, 1, SINE));
  const rise = (i: number) => (1 - Math.min(1.08, land(0.35 + (local - i * 0.5) * 1.3))) * lh;
  const letters = (fill: string) => lines.map((ln, i) => (
    <g key={i} clipPath={`url(#${id}-slot-${i})`}>
      <text x={left + edge / 2} y={top + i * lh + size * 0.8 + rise(i)} fill={fill} fontFamily={`'${look.display}'`} fontWeight={800}
        fontSize={size} letterSpacing={`${TRACK * size}px`} style={{whiteSpace: 'pre', ...OPTICAL}}>{ln}</text>
    </g>
  ));
  const photo = look.photo && ready;
  const cx = look.W / 2, cy = look.H * 0.45;
  const rim = Math.abs(lumOf(look.tone.pen) - lumOf(look.tone.ground)) > 0.2 ? look.tone.pen : look.colors.accent;
  return (
    <svg width={look.W} height={look.H} style={{...fill, opacity: beat.box ? 1 - span(u, 0.75, 0.25, SINE) : 1}}>
      <defs>
        {lines.map((_, i) => (
          <clipPath key={i} id={`${id}-slot-${i}`}>
            <rect x={0} y={top + i * lh} width={look.W} height={lh} />
          </clipPath>
        ))}
        {/* the mask's luminance, never drawn: full keeps the photograph, none hides it */}
        <mask id={`${id}-letters`} maskUnits="userSpaceOnUse" x={0} y={0} width={look.W} height={look.H}>{letters('white')}</mask>
      </defs>
      <rect x={0} y={0} width={look.W} height={look.H} fill={look.tone.ground} />
      {photo ? (
        <g mask={`url(#${id}-letters)`}>
          <image href={look.photo} x={0} y={0} width={look.W} height={look.H} preserveAspectRatio="xMidYMid slice"
            transform={`translate(${cx} ${cy}) scale(${push}) translate(${-cx} ${-cy})`} />
        </g>
      ) : letters(look.colors.accent)}
      {photo ? <g fill="none" stroke={rim} strokeWidth={edge} strokeLinejoin="round">{lines.map((ln, i) => (
        <g key={i} clipPath={`url(#${id}-slot-${i})`}>
          <text x={left + edge / 2} y={top + i * lh + size * 0.8 + rise(i)} fontFamily={`'${look.display}'`} fontWeight={800}
            fontSize={size} letterSpacing={`${TRACK * size}px`} style={{whiteSpace: 'pre', ...OPTICAL}}>{ln}</text>
        </g>
      ))}</g> : null}
    </svg>
  );
};

export default {Overlay} satisfies Move;
