import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {LivePhoto, Photo, Scrim} from '../photo';
import {Leaks} from '../texture';
import {ClipLayer} from './ClipShot';
import type {Beat, Row} from '../types';

const ROW = 92;
const GAP = 10;

/** One line of the board: rank, face, handle, and a bar for how much of the year they shared. */
const BoardRow: React.FC<{row: Row | null; rank: number; max: number; now: boolean; delay: number}> = ({row, rank, max, now, delay}) => {
  const {system} = useSys();
  const {tween, pop} = useMotion();
  const p = now ? pop(delay, {damping: 13, stiffness: 170}) : 1;
  const bar = row ? tween(0, row.score / Math.max(1, max), now ? delay + 4 : 0, now ? 18 : 1) : 0;
  const ink = row ? system.colors.ink : system.colors.muted;
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 20, height: ROW, width: '100%',
      transform: `translateX(${(1 - p) * 60}px) scale(${now ? 1 + 0.04 * (1 - p) : 1})`, opacity: row ? Math.min(1, 0.2 + p) : 0.5,
      background: now ? 'rgba(0,0,0,0.28)' : undefined, borderLeft: now ? `6px solid ${system.colors.accent}` : '6px solid transparent', paddingLeft: 14, boxSizing: 'border-box'}}>
      <div style={{...faceStyle(system.display), fontSize: 64, lineHeight: 1, width: 62, color: now ? system.colors.accent : ink, textAlign: 'right'}}>{rank}</div>
      <div style={{width: 72, height: 72, borderRadius: 36, overflow: 'hidden', flex: 'none', background: system.colors.muted,
        border: `3px solid ${now ? system.colors.accent : system.colors.ink}`}}>
        {row?.photo ? <Photo file={row.photo} position="50% 35%" /> : null}
      </div>
      <div style={{flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10}}>
        <div style={{...faceStyle(system.text), fontSize: 34, fontWeight: 600, letterSpacing: 0, textTransform: 'none', lineHeight: 1.1, color: ink, whiteSpace: 'nowrap'}}>
          {row ? `@${row.handle}` : '·  ·  ·'}
        </div>
        <div style={{height: 10, width: '100%', background: 'rgba(255,255,255,0.14)'}}>
          <div style={{height: '100%', width: `${bar * 100}%`, background: now ? system.colors.accent : system.colors.ink}} />
        </div>
      </div>
    </div>
  );
};

/**
 * The board building person by person: the rows already counted stay, this one lands over their photo with
 * their line, the ranks still to come wait as empty rows. With no `me` it is the whole board, held.
 */
export const Leaderboard: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const {tween} = useMotion();
  const t = beat.text ?? {};
  const d = system.direction;
  const rows: Row[] = beat.data?.rows ?? [];
  const shown: number[] = beat.data?.shown ?? rows.map((r) => r.rank);
  const me: number | null = beat.data?.me ?? null;
  const max = Math.max(1, ...rows.map((r) => r.score));
  const listH = rows.length * ROW + Math.max(0, rows.length - 1) * GAP;
  const listTop = s.H - s.bottom - listH;
  const photo = beat.photos?.[0] ?? rows.find((r) => r.rank === me)?.photo ?? '';
  const bg = beat.clip ? <ClipLayer clip={beat.clip} /> : <LivePhoto file={photo} treatment={beat.treatment ?? 'push'} />;
  const flash = me !== null && d === 'kinetic' ? tween(0.9, 0, 0, 7) : 0;
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {bg}
      {d === 'documentary' ? <Leaks strength={0.8} seed={beat.id} /> : null}
      <AbsoluteFill style={{background: system.colors.bg, opacity: 0.35}} />
      <Scrim side="both" strength={0.9} />
      <AbsoluteFill style={{background: system.colors.accent, opacity: flash}} />
      <SafeBox name="words" justify="start" bottom={s.H - listTop + 30}>
        {t.kicker ? <Kicker text={t.kicker} delay={4} color={system.colors.accent} /> : null}
        {t.headline ? <Headline text={t.headline} max="h2" lines={3} delay={6} /> : null}
        {t.line ? <Line text={t.line} delay={14} size={system.scale.label} /> : null}
      </SafeBox>
      <SafeBox name="board" justify="end" top={listTop}>
        <div style={{display: 'flex', flexDirection: 'column', gap: GAP, width: '100%'}}>
          {rows
            .slice()
            .sort((a, b) => a.rank - b.rank)
            .map((r, i) => (
              <BoardRow key={r.rank} row={shown.includes(r.rank) ? r : null} rank={r.rank} max={max} now={r.rank === me}
                delay={me === null ? i * 3 : 8} />
            ))}
        </div>
      </SafeBox>
    </AbsoluteFill>
  );
};
