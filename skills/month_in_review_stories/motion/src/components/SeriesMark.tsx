import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, MARK, useFrameSafe, useMotion, useSys} from '../system';

/**
 * The mark every card of the series carries at the top of its safe area: the month on the left, the card's place
 * in the series on the right ("01 / 05"), and one segment per card under them with this card's segment filling
 * over the card's length, the way a story's progress bar does. Static cards show it full.
 */
export const SeriesMark: React.FC = () => {
  const {system, board, still} = useSys();
  const safe = useFrameSafe();
  const {frame, duration, tween} = useMotion();
  const series = board.series;
  if (!series) return null;
  const month = board.month ? `${board.month.name} ${board.month.year}` : String(board.year);
  const ink = system.colors.ink;
  const fill = still ? 1 : Math.min(1, frame / Math.max(1, duration - 1));
  const label: React.CSSProperties = {
    ...faceStyle(system.text),
    textTransform: 'uppercase',
    letterSpacing: '0.14em',
    fontSize: system.scale.label * 0.86,
    fontWeight: 600,
    color: ink,
    lineHeight: 1,
    whiteSpace: 'nowrap',
  };
  const shadow = system.direction === 'editorial' ? undefined : '0 2px 14px rgba(0,0,0,0.45)';
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: safe.left, right: safe.right, top: safe.top, height: MARK - 28, display: 'flex', flexDirection: 'column',
        justifyContent: 'flex-start', gap: 16, opacity: still ? 1 : tween(0, 1, 0, 10)}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', textShadow: shadow}}>
          <span style={label}>{month}</span>
          <span style={{...label, fontFeatureSettings: '"tnum" 1'}}>
            <span style={{color: system.colors.accent}}>{String(series.n).padStart(2, '0')}</span>
            {` / ${String(series.of).padStart(2, '0')}`}
          </span>
        </div>
        <div style={{display: 'flex', gap: 8}}>
          {Array.from({length: series.of}, (_, i) => (
            <div key={i} style={{flex: 1, height: 5, borderRadius: 3, background: `${ink}40`, overflow: 'hidden', boxShadow: shadow ? '0 1px 6px rgba(0,0,0,0.3)' : undefined}}>
              <div style={{height: '100%', background: i + 1 === series.n ? system.colors.accent : ink,
                width: `${(i + 1 < series.n ? 1 : i + 1 === series.n ? fill : 0) * 100}%`}} />
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
