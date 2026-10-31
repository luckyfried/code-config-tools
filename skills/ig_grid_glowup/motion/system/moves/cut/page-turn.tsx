// page-turn: a page turns over the frame: a leaf of the card's ground, its fold shadowed and its edge lit, sweeps across
// on a slant while the camera travels to the next beat under it. The leaf is narrower than the frame, so the picture
// shows on one side of it or the other on every frame. Into a wall that gives its posts, the page the leaf has turned
// shows the posts rising under the turn and hands over to the wall itself by the window's end; into any other wall the
// turned page is the scene itself.
import React from 'react';
import {alpha, clamp01, fill, px, SINE} from '../kit';
import {Incoming, opensOnto, standOf} from '../arrival';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, into, u}) => {
  const k = SINE(u);
  const w = look.W * 0.62;
  // the leaf narrows as it lifts past the middle, the way a page foreshortens as it stands up
  const lift = Math.sin(Math.PI * k);
  const leaf = w * (1 - 0.45 * lift);
  const x = look.W * 1.1 - k * (look.W * 1.2 + w);
  const top = -look.H * 0.15, tall = look.H * 1.3;
  // the leaf's trailing edge, turned 8 degrees about the leaf's middle: everything right of it is the turned page
  const a = (8 * Math.PI) / 180, mx = x + leaf / 2, my = top + tall / 2;
  const edge = (dy: number) => [mx + (leaf / 2) * Math.cos(a) - dy * Math.sin(a), my + (leaf / 2) * Math.sin(a) + dy * Math.cos(a)];
  const [ex0, ey0] = edge(-tall / 2), [ex1, ey1] = edge(tall / 2);
  const reach = look.W * 3;
  const stand = into.form === 'wall' && opensOnto(look, into) ? standOf(u) : 0;
  return (
    <div style={{...fill, overflow: 'hidden'}}>
      {stand > 0 ? (
        <div style={{...fill, opacity: stand, clipPath: `polygon(${ex0}px ${ey0}px, ${reach}px ${ey0}px, ${reach}px ${ey1}px, ${ex1}px ${ey1}px)`}}>
          <Incoming look={look} into={into} rise={clamp01(u * 1.4)} />
        </div>
      ) : null}
      <div style={{position: 'absolute', top, height: tall, left: x, width: leaf, background: look.tone.ground,
        transform: 'rotate(8deg)', boxShadow: `${px(look, -30)}px 0 ${px(look, 50)}px ${alpha(look.tone.matte, 0.32)}, ${px(look, 24)}px 0 ${px(look, 40)}px ${alpha(look.tone.matte, 0.18)}`,
        backgroundImage: `linear-gradient(to right, ${alpha(look.tone.matte, 0.16 * (1 - lift))}, transparent ${px(look, 80)}px, transparent 70%, ${alpha(look.tone.light, 0.18)})`}} />
    </div>
  );
};

export default {beats: 1.4, jump: false, Overlay} satisfies Cut;
