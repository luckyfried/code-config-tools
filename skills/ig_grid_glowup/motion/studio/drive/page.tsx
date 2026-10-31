// The card's page, drawn over the picture: the hook's title page, and the page each post the frame holds is read on.
// The card's ground stands round the picture box, where the camera holds the photograph's crop exactly, so the
// photograph sits on the card's paper with the card's margins; a card that rules its grid shows it in hairlines on
// the paper; a card that sets its words on the photograph runs the photograph to the frame's edges and lays a scrim
// under the words. The words are the card's display face at the card's size, entering on the card's entrance (a fade,
// a cut, a word at a time slammed or risen, or typed), under the label in the card's label face. The paper closes in
// round the picture as the frame locks, the words leave, and the paper opens out as the crop drops into the grid.
import {bezier, clamp01, lerp, span} from '../../system/three/motion';
import type {Page, PageLine, Plan} from './plan';

// how long a line takes to fade in, a word to slam home or rise, and the words to leave, beats; a letter types in
// every LETTER beats; how far a fading line and a rising word travel, a share of their size; how large a slammed word
// starts
const FADE = 0.5;
const SLAM = 0.18;
const RISE = 0.45;
const LEAVE = 0.3;
const LETTER = 0.05;
const DRIFT = 0.12;
const LIFT = 0.6;
const BIG = 1.35;
// the hairlines of a ruled grid: their width, px at 1080, and how strongly they show on the paper
const HAIR = 1.5;
const RULE_ALPHA = 0.2;

type Box4 = [number, number, number, number];

/** How far the paper has closed in round the picture at beat `t`, 0 (open) to 1 (round the picture). */
export const closedAt = (pg: Page, t: number, ease: (u: number) => number) => {
  const shut = pg.close ? ease(clamp01((t - pg.close[0]) / Math.max(1e-3, pg.close[1] - pg.close[0]))) : 1;
  return shut * (1 - ease(clamp01((t - pg.open[0]) / Math.max(1e-3, pg.open[1] - pg.open[0]))));
};

const Words: React.FC<{plan: Plan; pg: Page; ln: PageLine; t: number; out: number}> = ({plan, pg, ln, t, out}) => {
  const enter = bezier(plan.ease.enter);
  const style = {fontFamily: `'${plan.look.display}'`, fontWeight: pg.weight, letterSpacing: `${pg.tracking}em`};
  if (pg.enter === 'slam' || pg.enter === 'rise') {
    return (
      <g>
        {ln.words.map((w, i) => {
          if (t < w.at) return null;
          const u = enter(clamp01((t - w.at) / (pg.enter === 'slam' ? SLAM : RISE)));
          const k = pg.enter === 'slam' ? lerp(BIG, 1, u) : 1;
          const dy = pg.enter === 'rise' ? (1 - u) * LIFT * ln.size : 0;
          const cx = w.x, cy = ln.y - 0.35 * ln.size;
          return (
            <text key={i} x={w.x} y={ln.y + dy} fontSize={ln.size} fill={pg.color} opacity={(pg.enter === 'slam' ? 1 : u) * out} style={style}
              transform={`translate(${cx} ${cy}) scale(${k}) translate(${-cx} ${-cy})`}>
              {w.text}
            </text>
          );
        })}
      </g>
    );
  }
  if (t < ln.at) return null;
  const u = pg.enter === 'cut' ? 1 : pg.enter === 'type' ? 1 : enter(clamp01((t - ln.at) / FADE));
  const text = pg.enter === 'type' ? ln.text.slice(0, Math.floor((t - ln.at) / LETTER) + 1) : ln.text;
  return (
    <text x={ln.x} y={ln.y + (1 - u) * DRIFT * ln.size} fontSize={ln.size} fill={pg.color} opacity={u * out} style={style}>
      {text}
    </text>
  );
};

export const PageView: React.FC<{plan: Plan; pg: Page; t: number; id: string}> = ({plan, pg, t, id}) => {
  if (t < (pg.close ? pg.close[0] : -1) || t >= pg.open[1]) return null;
  const {W, H} = plan;
  const ease = bezier(plan.ease.move);
  const k = closedAt(pg, t, ease);
  const full: Box4 = [0, 0, W, H];
  const [x0, y0, x1, y1] = full.map((v, i) => lerp(v, pg.pic[i], k)) as Box4;
  const mat = `M0 0H${W}V${H}H0Z M${x0} ${y0}V${y1}H${x1}V${y0}Z`;
  const out = 1 - span(t, pg.sink, LEAVE);
  const first = pg.lines[0];
  const said = first ? clamp01(span(t, first.at, pg.enter === 'cut' || pg.enter === 'slam' ? 0.01 : FADE)) * out : 0;
  const hair = Math.max(1, (HAIR * Math.min(W, H)) / 1080);
  const g = plan.look.grid;
  const [, by0, , by1] = pg.box;
  const reach = 0.12 * H;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      <defs>
        <clipPath id={`paper-${id}`}>
          <path d={mat} clipRule="evenodd" />
        </clipPath>
        {pg.scrim > 0 ? (
          <linearGradient id={`scrim-${id}`} x1="0" y1={by0 - reach} x2="0" y2={by1 + reach} gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor={pg.scrimColor} stopOpacity={0} />
            <stop offset={reach / (by1 - by0 + 2 * reach)} stopColor={pg.scrimColor} stopOpacity={pg.scrim} />
            <stop offset={1 - reach / (by1 - by0 + 2 * reach)} stopColor={pg.scrimColor} stopOpacity={pg.scrim} />
            <stop offset="1" stopColor={pg.scrimColor} stopOpacity={0} />
          </linearGradient>
        ) : null}
      </defs>
      {pg.over ? null : <path d={mat} fill={pg.ground} fillRule="evenodd" />}
      {pg.rules && !pg.over ? (
        <g clipPath={`url(#paper-${id})`} stroke={plan.colors.ink} strokeOpacity={RULE_ALPHA * k} strokeWidth={hair}>
          {g.cols.map((x, i) => <line key={`c${i}`} x1={x} y1={0} x2={x} y2={H} />)}
          {g.rows.map((y, i) => <line key={`r${i}`} x1={0} y1={y} x2={W} y2={y} />)}
        </g>
      ) : null}
      {pg.scrim > 0 ? <rect x={0} y={by0 - reach} width={W} height={by1 - by0 + 2 * reach} fill={`url(#scrim-${id})`} opacity={said} /> : null}
      {pg.label ? (
        <text x={pg.label.x} y={pg.label.y} fontSize={pg.label.size} fill={pg.label.color} opacity={said}
          style={{fontFamily: `'${pg.label.face === 'display' ? plan.look.display : plan.look.text}'`, fontWeight: pg.label.weight, letterSpacing: `${pg.label.tracking}em`}}>
          {pg.label.text}
        </text>
      ) : null}
      {pg.lines.map((ln, i) => <Words key={i} plan={plan} pg={pg} ln={ln} t={t} out={out} />)}
    </svg>
  );
};

/** Every page on the screen at beat `t`: the hook's title, then the held post's. */
export const Pages: React.FC<{plan: Plan; t: number}> = ({plan, t}) => (
  <>
    {plan.title ? <PageView plan={plan} pg={plan.title} t={t} id="title" /> : null}
    {plan.posts.map((p) => (p.page ? <PageView key={p.beat} plan={plan} pg={p.page} t={t} id={p.beat} /> : null))}
  </>
);
