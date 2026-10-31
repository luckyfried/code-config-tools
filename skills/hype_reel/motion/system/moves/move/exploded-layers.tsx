// exploded-layers: the picture comes apart into the planes it is printed from: a slab of the card's accent at the
// back, the mat in the card's rim tone, the photograph, and a slab with a rule and the beat's words in front. The
// stack arrives turned, springs apart in depth, holds turned in the air, then closes flat and lands on the print exactly
// as the shot draws it, its place, rim, tape and tilt. The close eases to exactly flat on the landing and the move
// hands the frame back with a cut there, so one subject is seen on every frame: the flying print until the landing,
// the shot's own print from it. On a grid the other cells stand on the ground while the one tile flies.
import React from 'react';
import {alpha, clamp01, fitTo, inkOn, px, SINE, Words} from '../kit';
import {arrivalOf, Incoming, landingOf, Print} from '../arrival';
import {spring} from '../spring';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, seed} = p;
  const {s, land} = arrivalOf(p, 1.15);
  const {box: [x, y, w, h]} = landingOf(p);
  if (s >= land) return null;
  // apart: the planes' separation; flat: the close back to one plane over the last half second, exactly flat at the
  // landing
  const apart = spring(s, 110, 11);
  const flat = SINE(clamp01((s - (land - 0.5)) / 0.5));
  const depth = apart * (1 - flat);
  const turn = 1 - flat;
  const side = seed % 2 ? 1 : -1;
  const shrink = 1 - 0.3 * turn;
  const gap = w * 0.16 * depth;
  const words = beat.say || beat.label || beat.words;
  const m = Math.max(look.print.rim, px(look, 26));
  const slab = look.colors.accent;
  const ink = inkOn(look.tone.ground, [look.tone.pen, look.colors.ink, look.colors.paper]);
  const plane = (z: number, style: React.CSSProperties, children?: React.ReactNode) => (
    <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, transform: `translateZ(${z}px)`, ...style}}>{children}</div>
  );
  // the words slab stands in the upper part of the picture and never in the frame's bottom third; it is gone by the
  // close's middle, so no word is seen over the print as it lands
  const top = Math.min(h * 0.08, look.H * 0.6 - y);
  const size = words ? fitTo([words], look.text, w * 0.8 - px(look, 60), {weight: 600, most: px(look, 54)}) : 0;
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden',
      perspective: look.H * 1.6, perspectiveOrigin: `${x + w / 2}px ${y + h / 2}px`}}>
      {/* the flight covers the frame with the ground, and with the grid's other cells where the beat gives them, so the
          wall stands while one of its tiles flies and the shot's own print is never seen beside the flying one */}
      <div style={{position: 'absolute', inset: 0}}>
        {beat.cells?.length ? <Incoming look={look} into={{...beat, photo: undefined}} />
          : <div style={{position: 'absolute', inset: 0, background: look.tone.ground}} />}
      </div>
      <div style={{position: 'absolute', left: x, top: y, width: w, height: h, transformStyle: 'preserve-3d',
        transform: `scale(${shrink}) rotateX(${12 * turn}deg) rotateY(${side * -30 * turn}deg) rotateZ(${side * 3 * turn}deg)`}}>
        {plane(-2.1 * gap, {background: slab, opacity: turn, transform: `translateZ(${-2.1 * gap}px) translate(${side * w * 0.06}px, ${h * 0.04}px)`,
          boxShadow: `0 ${px(look, 30)}px ${px(look, 80)}px ${alpha(look.tone.matte, 0.35 * turn)}`})}
        {plane(-gap, {left: -m, top: -m, width: w + 2 * m, height: h + 2 * m, background: look.tone.rim, opacity: Math.min(1, turn * 1.6),
          boxShadow: `0 ${px(look, 24)}px ${px(look, 60)}px ${alpha(look.tone.matte, 0.3 * turn)}`})}
        {plane(0, {boxShadow: `0 ${px(look, 18)}px ${px(look, 50)}px ${alpha(look.tone.matte, 0.35 * depth)}`}, (
          <div style={{position: 'absolute', left: -x, top: -y}}><Print look={look} beat={beat} /></div>
        ))}
        {words && turn > 0.5 ? plane(1.3 * gap, {opacity: 2 * turn - 1}, (
          <div style={{position: 'absolute', left: w * 0.1, top, width: w * 0.8, padding: `${px(look, 22)}px ${px(look, 28)}px`,
            background: alpha(look.tone.ground, 0.92), boxShadow: `0 ${px(look, 20)}px ${px(look, 50)}px ${alpha(look.tone.matte, 0.3)}`}}>
            <div style={{height: px(look, 5), width: w * 0.8 * (0.25 + 0.75 * apart) - px(look, 56), background: look.colors.accent, marginBottom: px(look, 16)}} />
            <Words text={words} family={look.text} size={size} color={ink} style={{fontWeight: 600, whiteSpace: 'nowrap'}} />
          </div>
        )) : null}
      </div>
    </div>
  );
};

export default {early: true, Overlay} satisfies Move;
