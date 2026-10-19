import React from 'react';
import {AbsoluteFill, Img, Sequence} from 'remotion';
import {src, splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {RETRIES} from '../photo';
import {Leaks} from '../texture';
import {PostFit} from './Post';
import type {Beat, Callout, Cell, Post} from '../types';

/** Their profile as the app draws it, at 1080 wide: the header, the tabs, then the grid in 4:5 cells. */
export const UI = 'Inter';
export const HEADER = 662;
export const CW = 358;
export const CH = 448;
export const GAP = 3;
export const cellAt = (slot: number) => ({x: (slot % 3) * (CW + GAP), y: HEADER + Math.floor(slot / 3) * (CH + GAP)});
export const profileHeight = (cells: number) => HEADER + Math.ceil(cells / 3) * (CH + GAP);

const fmt = (n: number) => (n >= 10000 ? `${(n / 1000).toFixed(n >= 100000 ? 0 : 1)}K` : n.toLocaleString('en-US'));

const Header: React.FC<{posts: number}> = ({posts}) => {
  const {board} = useSys();
  const p = board.profile;
  const t: React.CSSProperties = {fontFamily: `'${UI}'`, color: '#0a0a0a', position: 'absolute', whiteSpace: 'nowrap'};
  const stat = (n: number, label: string, x: number) => (
    <div style={{...t, left: x, top: 170, width: 240, textAlign: 'center'}}>
      <div style={{fontSize: 44, fontWeight: 700, lineHeight: 1.1}}>{fmt(n)}</div>
      <div style={{fontSize: 32, fontWeight: 400, lineHeight: 1.3}}>{label}</div>
    </div>
  );
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: HEADER, background: '#fff'}}>
      <div style={{...t, left: 40, top: 30, fontSize: 46, fontWeight: 700}}>{board.handle}</div>
      <div style={{position: 'absolute', left: 40, top: 130, width: 200, height: 200, borderRadius: 100, overflow: 'hidden', background: '#ddd',
        boxShadow: '0 0 0 4px #fff, 0 0 0 7px #dbdbdb'}}>
        {p.avatar ? <Img src={src(p.avatar)} maxRetries={RETRIES} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
      </div>
      {stat(posts, 'posts', 290)}
      {stat(p.followers, 'followers', 535)}
      {stat(p.following, 'following', 780)}
      <div style={{...t, left: 40, top: 358, fontSize: 34, fontWeight: 700}}>{p.name}</div>
      <div style={{...t, left: 40, top: 404, width: 1000, fontSize: 33, lineHeight: 1.3, whiteSpace: 'normal', height: 86, overflow: 'hidden'}}>{p.bio}</div>
      {['Following', 'Message'].map((b, i) => (
        <div key={b} style={{...t, left: 40 + i * 506, top: 512, width: 494, height: 76, borderRadius: 16, background: '#efefef', fontSize: 32,
          fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{b}</div>
      ))}
      <div style={{position: 'absolute', left: 0, top: 612, width: 1080, height: 50, borderBottom: '1px solid #dbdbdb'}}>
        <div style={{position: 'absolute', left: 0, bottom: -1, width: 360, height: 3, background: '#0a0a0a'}} />
        <div style={{position: 'absolute', left: 162, top: 2, width: 36, height: 36, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4}}>
          {Array.from({length: 9}, (_, i) => <div key={i} style={{background: '#0a0a0a', borderRadius: 1}} />)}
        </div>
        <div style={{position: 'absolute', left: 522, top: 2, width: 36, height: 36, border: '3.5px solid #8e8e8e', borderRadius: 9, boxSizing: 'border-box'}} />
        <div style={{position: 'absolute', left: 882, top: 2, width: 36, height: 36, border: '3.5px solid #8e8e8e', borderRadius: 18, boxSizing: 'border-box'}} />
      </div>
    </div>
  );
};

const CellView: React.FC<{cell: Cell; slot: number; dim?: number}> = ({cell, slot, dim = 0}) => {
  const {x, y} = cellAt(slot);
  return (
    <div style={{position: 'absolute', left: x, top: y, width: CW, height: CH, overflow: 'hidden', background: '#efefef'}}>
      {cell.photo ? <Img src={src(cell.photo)} maxRetries={RETRIES} style={{width: '100%', height: '100%', objectFit: 'cover', display: 'block'}} /> : null}
      {cell.kind === 'reel' ? (
        <div style={{position: 'absolute', right: 16, top: 14, width: 0, height: 0, borderTop: '14px solid transparent', borderBottom: '14px solid transparent',
          borderLeft: '22px solid #fff', filter: 'drop-shadow(0 1px 3px rgba(0,0,0,0.5))'}} />
      ) : null}
      {dim ? <div style={{position: 'absolute', inset: 0, background: '#fff', opacity: dim}} /> : null}
    </div>
  );
};

/**
 * The profile with the next nine in place (when posts are given) over the real grid.
 * land(n) is how far post n has landed, 0 to 1; a slot not landed yet shows as an empty frame.
 */
export const Profile: React.FC<{posts?: Post[]; land?: (n: number) => number; rows?: number; callouts?: Callout[];
  show?: (i: number) => number; dimOld?: number; divider?: boolean; labels?: boolean}> = ({posts, land, rows, callouts, show, dimOld = 0, divider, labels = true}) => {
  const {board, system} = useSys();
  const shift = posts ? 9 : 0;
  const total = rows ? rows * 3 : shift + board.grid.length;
  const cells = board.grid.filter((c) => c.pos + shift < total);
  const height = profileHeight(total) + (divider ? 64 : 0);
  const off = (slot: number) => (divider && slot >= 9 ? 64 : 0);
  return (
    <div style={{position: 'relative', width: 1080, height, background: '#fff', overflow: 'hidden'}}>
      <Header posts={board.profile.posts + (posts ? 9 : 0)} />
      {posts
        ? posts.map((p) => {
            const slot = 9 - p.n;
            const {x, y} = cellAt(slot);
            const k = land ? land(p.n) : 1;
            return (
              <div key={`n${p.n}`} style={{position: 'absolute', left: x, top: y, width: CW, height: CH}}>
                <div style={{position: 'absolute', inset: 0, background: '#f3f1ee', border: '3px dashed #c9c4bc', boxSizing: 'border-box', opacity: 1 - Math.min(1, k * 1.5)}} />
                <div style={{position: 'absolute', inset: 0, opacity: Math.min(1, k * 1.6), transform: `scale(${1.18 - 0.18 * k})`,
                  boxShadow: k < 1 ? `0 ${30 * (1 - k)}px ${60 * (1 - k)}px rgba(0,0,0,${0.35 * (1 - k)})` : undefined}}>
                  <PostFit post={p} width={CW} />
                </div>
              </div>
            );
          })
        : null}
      {divider ? (
        <div style={{position: 'absolute', left: 0, top: cellAt(9).y - 1, width: 1080, height: 64, background: '#f3f0ea', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', padding: '0 40px', boxSizing: 'border-box', fontFamily: `'${UI}'`, fontSize: 26, fontWeight: 600, letterSpacing: '0.12em',
          textTransform: 'uppercase', color: '#5c564d'}}>
          <span>the next nine, above</span>
          <span>your grid now, below</span>
        </div>
      ) : null}
      {cells.map((c) => (
        <div key={`c${c.pos}`} style={{position: 'absolute', left: 0, top: off(c.pos + shift), width: 1080}}>
          <CellView cell={c} slot={c.pos + shift} dim={dimOld} />
        </div>
      ))}
      {callouts?.map((co, i) => {
        const a = show ? show(i) : 1;
        if (a <= 0) return null;
        const first = Math.min(...co.positions);
        const {x, y} = cellAt(first + shift);
        return (
          <React.Fragment key={`co${i}`}>
            {co.positions.map((pos) => {
              const c = cellAt(pos + shift);
              return (
                <div key={pos} style={{position: 'absolute', left: c.x + 4, top: c.y + 4, width: CW - 8, height: CH - 8, boxSizing: 'border-box',
                  border: `8px solid ${system.colors.accent}`, opacity: a, transform: `scale(${1.08 - 0.08 * a})`}} />
              );
            })}
            {labels ? <div style={{position: 'absolute', left: Math.min(x + 18, 1080 - 520), top: y + 22, background: system.colors.accent, color: '#fff', padding: '10px 20px',
              fontFamily: `'${UI}'`, fontSize: 34, fontWeight: 700, whiteSpace: 'nowrap', opacity: a, transform: `translateY(${(1 - a) * 20}px)`,
              boxShadow: '0 10px 30px rgba(0,0,0,0.35)'}}>{co.label}</div> : null}
          </React.Fragment>
        );
      })}
    </div>
  );
};

/** The phone-sized panel the profile sits in on the film, under the words. */
const PANEL_TOP = 600;
const K = 0.86;

const Panel: React.FC<{scroll: number; children: React.ReactNode; k?: number; top?: number; enter?: number}> = ({scroll, children, k = K, top = PANEL_TOP, enter = 1}) => {
  const s = useSafe();
  return (
    <div style={{position: 'absolute', left: (s.W - 1080 * k) / 2, top: top + (1 - enter) * 300, width: 1080 * k, height: s.H - top + 200, overflow: 'hidden',
      borderRadius: 44, boxShadow: '0 40px 120px rgba(0,0,0,0.45)', background: '#fff', opacity: Math.min(1, enter * 1.5)}}>
      <div style={{transform: `scale(${k}) translateY(${-scroll}px)`, transformOrigin: '0 0', width: 1080}}>{children}</div>
    </div>
  );
};

const Words: React.FC<{beat: Beat; delay?: number; name: string}> = ({beat, delay = 0, name}) => {
  const s = useSafe();
  const t = beat.text ?? {};
  return (
    <SafeBox name={name} justify="end" bottom={s.H - PANEL_TOP + 30}>
      {t.kicker ? <Kicker text={t.kicker} delay={delay} /> : null}
      {t.headline ? <Headline text={t.headline} max="h2" lines={2} delay={delay + 4} /> : null}
      {t.line ? <Line text={t.line} delay={delay + 10} /> : null}
    </SafeBox>
  );
};

/** before: the real grid, scrolling down while each finding is drawn over the posts it covers. */
const Before: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const {tween, duration, pop} = useMotion();
  const callouts: Callout[] = beat.data?.callouts ?? [];
  const lowest = Math.max(0, ...callouts.flatMap((c) => c.positions));
  const view = (1920 - PANEL_TOP) / K;
  const target = Math.max(0, Math.min(cellAt(lowest).y + CH + 60 - view, profileHeight(30) - view));
  const scroll = tween(0, target, Math.round(duration * 0.12), Math.round(duration * 0.7), 'move');
  const step = Math.max(6, Math.round((duration * 0.62) / Math.max(1, callouts.length)));
  const show = (i: number) => tween(0, 1, 8 + i * step, 8);
  const s = useSafe();
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <Panel scroll={scroll} enter={pop(0, {damping: 18})}>
        <Profile callouts={callouts} show={show} labels={false} />
      </Panel>
      <div style={{position: 'absolute', left: (s.W - 1080 * K) / 2 + 28, top: PANEL_TOP + 28, display: 'flex', flexDirection: 'column',
        alignItems: 'flex-start', gap: 14}}>
        {callouts.map((co, i) => {
          const a = show(i);
          return a <= 0 ? null : (
            <div key={i} style={{background: system.colors.accent, color: '#fff', padding: '12px 24px', borderRadius: 999, fontFamily: `'${UI}'`,
              fontSize: 36, fontWeight: 700, whiteSpace: 'nowrap', opacity: a, transform: `translateX(${(1 - a) * -40}px)`,
              boxShadow: '0 12px 34px rgba(0,0,0,0.35)'}}>{co.label}</div>
          );
        })}
      </div>
      <Words beat={beat} name="before" />
    </AbsoluteFill>
  );
};

/** after: the next nine land in their slots in posting order, one per cut, over the real grid. */
const After: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const {frame, pop, tween} = useMotion();
  const spans = splits(beat, 10);
  const landAt = (n: number) => spans[n - 1][0];
  const land = (n: number) => (frame >= landAt(n) ? pop(landAt(n), {damping: 15, stiffness: 190}) : 0);
  const view = (1920 - PANEL_TOP) / K;
  const target = Math.min(cellAt(0).y - 24, profileHeight(39) - view);
  const scroll = tween(0, target, spans[2][0], Math.max(8, spans[5][0] - spans[2][0]), 'move');
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <Leaks strength={0.5} seed={beat.id} />
      <Panel scroll={scroll}>
        <Profile posts={board.posts} land={land} />
      </Panel>
      <Words beat={beat} name="after" />
    </AbsoluteFill>
  );
};

/** posts: a few of the nine full size, one per cut, with what each one is. */
const Posts: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const show: number[] = beat.data?.show ?? [9, 5, 1];
  const spans = splits(beat, show.length);
  const s = useSafe();
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      {show.map((n, i) => {
        const p = board.posts.find((x) => x.n === n);
        if (!p) return null;
        const [a, len] = spans[i];
        return (
          <Sequence key={n} from={a} durationInFrames={len} layout="none">
            <SubShot frames={len}>
              <OnePost post={p} width={s.W - 2 * 110} top={PANEL_TOP + 20} label={`post ${n} of 9`} />
            </SubShot>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const OnePost: React.FC<{post: Post; width: number; top: number; label: string}> = ({post, width, top, label}) => {
  const {system} = useSys();
  const {pop, drift} = useMotion();
  const s = useSafe();
  const p = pop(0, {damping: 16});
  const kinetic = system.direction === 'kinetic';
  return (
    <>
      <div style={{position: 'absolute', left: (s.W - width) / 2, top, boxShadow: '0 40px 100px rgba(0,0,0,0.45)',
        transform: kinetic ? `translateX(${(1 - p) * 900}px) rotate(${(1 - p) * 6}deg)` : `translateY(${(1 - p) * 80}px) scale(${drift(1, 1.03)})`,
        opacity: kinetic ? 1 : Math.min(1, p * 1.5)}}>
        <PostFit post={post} width={width} />
      </div>
      <SafeBox name={`post-${post.n}`} justify="end" bottom={s.H - top + 30}>
        <Kicker text={label} delay={2} />
        {post.caption ? <Line text={post.caption} delay={6} /> : null}
      </SafeBox>
    </>
  );
};

/** end: the profile with all nine in place, small, under the last words. */
const End: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, board} = useSys();
  const {pop} = useMotion();
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <Panel scroll={0} k={0.7} top={PANEL_TOP} enter={pop(0, {damping: 20})}>
        <Profile posts={board.posts} rows={5} />
      </Panel>
      <Words beat={beat} name="end" delay={4} />
    </AbsoluteFill>
  );
};

export const Feed: React.FC<{beat: Beat}> = ({beat}) => {
  const mode = beat.data?.mode ?? 'after';
  if (mode === 'before') return <Before beat={beat} />;
  if (mode === 'posts') return <Posts beat={beat} />;
  if (mode === 'end') return <End beat={beat} />;
  return <After beat={beat} />;
};
