import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {useMotion, useSafe, useSys} from './system';

/**
 * The cut and its designed moves. Every cut lands on its downbeat frame: the outgoing beat plays the move's out
 * half over its last `frames`, the incoming beat plays the in half over its first `frames`.
 * cut          a hard cut, nothing else
 * whip         the picture slides and smears in `direction` under horizontal motion blur, scaled so it always fills the frame; the next smears in from the same side
 * match        the outgoing MultiFrame grows its focus tile to the full frame; the next beat opens settled on it
 * maskWipe     a palette ring sweeps out from `origin` across the frame and the picture pushes after it; the next
 *              beat opens under a second ring growing from the same point
 * zoomThrough  the camera pushes into `origin` until it fills and blurs; the next beat settles from a push. The
 *              crossing is at most four frames a side, and the outgoing type has left before it starts
 * flash        the incoming picture lifted under a light veil on the cut, falling back over five frames; it
 *              brightens the picture and never turns the frame white
 * dissolve     the next beat fades in over the outgoing one (Film overlaps the two by `frames`)
 * dip          toward the palette's dark (the darker of bg and ink) and back; the picture always shows through,
 *              so no frame is a flat field and none goes white
 */
/** The darker of two #rrggbb colors, by their luma. */
const darker = (a: string, b: string) => {
  const y = (h: string) => {
    const n = parseInt(h.slice(1, 7), 16);
    return 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
  };
  return y(a) <= y(b) ? a : b;
};

export const Move: React.FC<{children: React.ReactNode}> = ({children}) => {
  const {enter, exit, still, system, beat} = useSys();
  const frame = useCurrentFrame();
  const {duration, curves} = useMotion();
  const {W, H} = useSafe();
  if (still) return <>{children}</>;
  const ni = enter && enter.preset !== 'cut' ? enter.frames ?? 8 : 0;
  const ne = exit && exit.preset !== 'cut' ? exit.frames ?? 8 : 0;
  const pin = ni && frame < ni ? (frame + 1) / (ni + 1) : 1;
  const pout = ne && frame >= duration - ne && frame < duration ? (frame - (duration - ne) + 1) / (ne + 1) : 0;
  const inMove = pin < 1 ? enter : null;
  const outMove = pout > 0 ? exit : null;
  const id = `mv-${beat?.id ?? 'b'}`;
  const DIP = 0.6;
  const dip = darker(system.colors.bg, system.colors.ink);
  const diag = Math.hypot(W, H);
  let style: React.CSSProperties = {};
  let blur = 0;
  let over: React.ReactNode = null;
  if (outMove) {
    const e = curves.exit(pout);
    const [ox, oy] = outMove.origin ?? [0.5, 0.45];
    switch (outMove.preset) {
      case 'whip': {
        const sign = outMove.direction === 'right' ? 1 : -1;
        style = {transform: `translateX(${sign * e * 20}%) scale(${1 + 0.45 * e})`};
        blur = 90 * e;
        break;
      }
      case 'zoomThrough':
        style = {transformOrigin: `${ox * 100}% ${oy * 100}%`, transform: `scale(${1 + 3 * e})`, filter: `blur(${18 * e * e}px)`};
        break;
      case 'maskWipe':
        style = {transformOrigin: `${ox * 100}% ${oy * 100}%`, transform: `scale(${1 + 0.12 * e})`};
        over = (
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            <circle cx={ox * W} cy={oy * H} r={e * diag} fill="none" stroke={system.colors.accent} strokeWidth={60 * e + 8} />
          </svg>
        );
        break;
      case 'flash':
        style = {transform: `scale(${1 + 0.04 * e})`, filter: `brightness(${1 + 0.3 * e})`};
        break;
      case 'dip':
        over = <AbsoluteFill style={{background: dip, opacity: DIP * curves.move(pout)}} />;
        break;
      default:
        break;
    }
  }
  if (inMove) {
    const e = curves.enter(pin);
    const [ox, oy] = inMove.origin ?? [0.5, 0.45];
    switch (inMove.preset) {
      case 'whip': {
        const sign = inMove.direction === 'right' ? 1 : -1;
        style = {transform: `translateX(${-sign * (1 - e) * 20}%) scale(${1 + 0.45 * (1 - e)})`};
        blur = 90 * (1 - e);
        break;
      }
      case 'zoomThrough':
        style = {transformOrigin: `${ox * 100}% ${oy * 100}%`, transform: `scale(${1 + 0.5 * (1 - e)})`, filter: `blur(${14 * (1 - e)}px)`};
        break;
      case 'maskWipe':
        style = {transformOrigin: `${ox * 100}% ${oy * 100}%`, transform: `scale(${1.12 - 0.12 * e})`};
        over = (
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            <circle cx={ox * W} cy={oy * H} r={e * diag + 10} fill="none" stroke={system.colors.accent2} strokeWidth={26 * (1 - e) + 4} />
          </svg>
        );
        break;
      case 'flash': {
        const a = [1, 0.8, 0.5, 0.25, 0.1][frame] ?? 0;
        style = {filter: `brightness(${1 + 0.35 * a}) saturate(${1 - 0.3 * a})`};
        over = <AbsoluteFill style={{background: '#ffffff', opacity: 0.3 * a}} />;
        break;
      }
      case 'dissolve':
        style = {opacity: curves.move(pin)};
        break;
      case 'dip':
        over = <AbsoluteFill style={{background: dip, opacity: DIP * (1 - curves.move(pin))}} />;
        break;
      default:
        break;
    }
  }
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{...style, filter: blur > 0.5 ? `url(#${id})` : style.filter}}>{children}</AbsoluteFill>
      {blur > 0.5 ? (
        <svg width={0} height={0} style={{position: 'absolute'}}>
          <filter id={id} x="-20%" y="0%" width="140%" height="100%">
            <feGaussianBlur stdDeviation={`${blur} 0`} />
          </filter>
        </svg>
      ) : null}
      {over}
    </AbsoluteFill>
  );
};
