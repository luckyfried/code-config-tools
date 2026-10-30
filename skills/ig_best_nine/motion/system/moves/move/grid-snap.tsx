// grid-snap: the card's grid marked where the card shows its rules, never across a photograph: crop ticks at every
// column and row in the margins, drawn on with a snap, and the camera moving only in steps that land on the grid.
import React from 'react';
import {fill, heldOf, px, span, SNAP} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local, t}) => {
  const g = look.grid;
  if (g.rules === 'none') return null;
  const d = span(local, 0, 0.6, SNAP);
  const line = Math.max(1, px(look, 2));
  const tick = g.m * 0.62;
  const ink = look.colors.ink;
  const a = heldOf(beat, t);
  const marks: React.ReactNode[] = [];
  g.cols.forEach((x, i) => {
    marks.push(<div key={`ct${i}`} style={{position: 'absolute', left: x - line / 2, top: g.m - tick * d - px(look, 6), width: line, height: tick * d, background: ink}} />);
    marks.push(<div key={`cb${i}`} style={{position: 'absolute', left: x - line / 2, top: look.H - g.m + px(look, 6), width: line, height: tick * d, background: ink}} />);
  });
  g.rows.forEach((y, i) => {
    marks.push(<div key={`rl${i}`} style={{position: 'absolute', top: y - line / 2, left: g.m - tick * d - px(look, 6), height: line, width: tick * d, background: ink}} />);
    marks.push(<div key={`rr${i}`} style={{position: 'absolute', top: y - line / 2, left: look.W - g.m + px(look, 6), height: line, width: tick * d, background: ink}} />);
  });
  return <div style={{...fill, opacity: a}}>{marks}</div>;
};

// the camera steps back on the grid, so every line the board laid inside the safe area stays inside it
export default {Overlay, nudge: ({u}) => ({scale: 1 + 0.06 * Math.floor(u * 3) / 3})} satisfies Move;
