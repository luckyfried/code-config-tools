// polaroid-drop: the picture becomes an instant print on the page: a frame of the card's rim with a deep foot drops in
// turned at the card's tilt, lands with a small bounce, and the beat's label (else its words) is written on its foot in
// the display face. The print is laid out from the safe area: it stands inside the safe area's top and foot, centred in
// its height, and the words are set as large as the foot and the safe area's width take them, so they read on every
// frame shape and no interface covers them. The print stands over the middle of the safe area's width.
import React from 'react';
import {alpha, fill, fitTo, hash, land, px, safeOf, Window, Words} from '../kit';
import type {Move, MoveProps} from '../types';

/** The print's height over its width: its picture (1.05) and its foot (0.26). */
const TALL = 1.31;

const Overlay: React.FC<MoveProps> = ({look, beat, local, seed}) => {
  const k = land(0.25 + local * 0.9);
  const tilt = look.print.tilt || -3;
  const title = beat.form === 'title';
  const turn = (title ? 0.5 : 1) * tilt * (0.6 + 0.4 * hash(seed + 1)) + 12 * (1 - k);
  const [sx0, sy0, sx1, sy1] = safeOf(look);
  // as wide as the frame allows and no taller than the safe area, standing in the middle of its height
  const w = Math.min(look.W * (title ? 0.96 : 0.78), (sy1 - sy0) / TALL), h = w * 1.05, foot = w * 0.26;
  const rim = Math.max(look.print.rim, w * (title ? 0.035 : 0.05));
  const rest = sy0 + Math.max(0, (sy1 - sy0 - w * TALL) / 2);
  const mid = Math.min(look.W - w / 2, Math.max(w / 2, (sx0 + sx1) / 2));
  const x = mid - w / 2, y = rest - (1 - k) * look.H * 0.5;
  const text = beat.label || beat.words;
  // the words: one line across the foot inside the rim, never past the safe area's sides,
  // never taller than half the foot, and no larger than the film's title
  const pad = rim + px(look, 24);
  const reach = Math.min(w - 2 * pad, 2 * Math.min(mid - sx0, sx1 - mid) - 2 * px(look, 24));
  const size = text ? fitTo([text], look.display, reach, {most: Math.min(foot * 0.5, px(look, 150))}) : 0;
  const band = foot + rim;
  return (
    <div style={fill}>
      <Window box={[x + rim, y + rim, w - 2 * rim, h - 2 * rim]} color="transparent" rotate={turn}
        style={{boxShadow: `0 0 0 ${rim}px ${look.tone.rim}, 0 ${foot}px 0 ${rim}px ${look.tone.rim}, 0 ${foot + px(look, 30)}px ${px(look, 60)}px ${rim}px ${alpha(look.tone.matte, 0.3)}, 0 0 0 6000px ${look.tone.ground}`}}>
        {text ? (
          <Words text={text} family={look.display} size={size} color={look.tone.pen}
            style={{position: 'absolute', left: -rim, width: w, top: h - 2 * rim + band / 2 - size * 0.56, textAlign: 'center', whiteSpace: 'nowrap'}} />
        ) : null}
      </Window>
    </div>
  );
};

export default {Overlay} satisfies Move;
