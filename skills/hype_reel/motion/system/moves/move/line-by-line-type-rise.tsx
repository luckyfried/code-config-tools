// line-by-line-type-rise: the beat's words set in the display face flush left across the measure, the first line
// there as the beat begins and each line after it rising into place after the one before. A words beat owns the frame
// on the card's ground; on any other beat the lines rise over the picture in the type area's lower half, on a soft
// field of the card's ground that keeps them legible and leaves the picture showing above it.
import React from 'react';
import {alpha, balance, fill, fitTo, inkOn, OUT, px, span, Words} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local}) => {
  const text = beat.words || beat.label;
  if (!text) return null;
  const own = beat.form === 'words';
  const lines = balance(text, text.length > 20 ? 3 : 2);
  const left = px(look, 110), width = look.W - 2 * left;
  const size = Math.min(fitTo(lines, look.display, width, {most: px(look, own ? 170 : 130)}), (look.H * (own ? 0.4 : 0.22)) / (lines.length * 1.12));
  const block = lines.length * size * 1.12;
  const top = own ? look.H * 0.46 - block / 2 : look.H * 0.6 - block;
  const ink = inkOn(look.tone.ground, [look.colors.ink, look.colors.paper]);
  return (
    <div style={{...fill, background: own ? look.tone.ground : undefined}}>
      {own ? null : (
        <div style={{position: 'absolute', left: 0, right: 0, top: top - px(look, 140), height: block + px(look, 280),
          background: `linear-gradient(to bottom, transparent, ${alpha(look.tone.ground, 0.86)} 30%, ${alpha(look.tone.ground, 0.86)} 70%, transparent)`,
          opacity: span(local, 0, 0.3)}} />
      )}
      {lines.map((ln, i) => {
        const r = i === 0 ? 0.55 + 0.45 * span(local, 0, 0.6, OUT) : span(local, 0.2 + 0.35 * i, 0.8, OUT);
        return (
          <Words key={i} text={ln} family={look.display} size={size} color={ink}
            style={{position: 'absolute', left, top: top + i * size * 1.12 + (1 - r) * size * 0.5, opacity: r, whiteSpace: 'nowrap',
              fontStyle: look.italic && i === lines.length - 1 ? 'italic' : 'normal'}} />
        );
      })}
    </div>
  );
};

export default {Overlay} satisfies Move;
