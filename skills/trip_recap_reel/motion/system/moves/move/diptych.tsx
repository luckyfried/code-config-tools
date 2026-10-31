// diptych: the picture split into two panels by a gutter of the card's ground down its middle, the gutter widening as
// the beat settles. On a beat the card gives a box the gutter runs down the middle of the box, as tall as the box;
// otherwise down the middle of the frame, framed in the same ground. The gutter rides on the picture while the camera
// drifts across it, so it never slices across a moving picture, and on a box it leaves over the first of the pull back.
// A wall carries the film's title and labels across its middle, so a wall without a box is framed and never split.
import React from 'react';
import {fill, follow, heldOf, OUT, pictureOf, px, span} from '../kit';
import type {Look, Move, MoveProps} from '../types';

const nudge = ({u}: Pick<MoveProps, 'u'>) => ({dx: 0.015 * (u - 0.5)});

/** Whether the beat's picture is split: any beat with a box, and every form but a wall. */
export const splits = (beat: Pick<MoveProps['beat'], 'form' | 'box'>) => !!beat.box || beat.form !== 'wall';

/** The gutter's box, [x, y, w, h] px, on a picture standing in `box`, `m` of the way to settled. */
export const gutterOf = (look: Look, box: [number, number, number, number], m: number): [number, number, number, number] => {
  const w = px(look, 10 + 26 * m) * Math.min(1, box[2] / look.W) ** 0.5;
  return [box[0] + box[2] / 2 - w / 2, box[1], w, box[3]];
};

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, local, u, t} = p;
  const m = span(local, 0, 0.8, OUT);
  const edge = px(look, 60);
  const ground = look.tone.ground;
  const [gx, gy, gw, gh] = gutterOf(look, pictureOf(look, beat), m);
  return (
    <div style={fill}>
      {beat.box ? null : <div style={{...fill, border: `${edge}px solid ${ground}`, borderTopWidth: look.H * 0.14, borderBottomWidth: look.H * 0.14}} />}
      {splits(beat) ? (
        <div style={{...fill, opacity: beat.box ? heldOf(beat, t) : 1, ...follow(look, nudge({u}))}}>
          <div style={{position: 'absolute', left: gx, top: gy - 1, width: gw, height: gh + 2, background: ground}} />
        </div>
      ) : null}
    </div>
  );
};

export default {Overlay, nudge} satisfies Move;
