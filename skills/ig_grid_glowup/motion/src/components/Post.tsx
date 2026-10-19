import React from 'react';
import {Img, staticFile} from 'remotion';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {faceStyle, src, useSys} from '../system';
import {RETRIES} from '../photo';
import type {Look, Post} from '../types';

/** A designed post is laid out at its real size, 1080 by 1350; the sheet and the film scale it into place. */
export const PW = 1080;
export const PH = 1350;

const rgb = (hex: string) => {
  const n = parseInt(hex.replace('#', '').slice(0, 6), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};
const lum = (hex: string) => {
  const [r, g, b] = rgb(hex).map((c) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
/** The ink that reads on a fill: their ink on dark fills, their bg on light ones. */
export const inkOn = (fill: string, light: string, dark: string) => (lum(fill) > 0.32 ? dark : light);
const rgba = (hex: string, a: number) => {
  const [r, g, b] = rgb(hex);
  return `rgba(${r},${g},${b},${a})`;
};

/** The treatment each direction gives a photo: one shared grade so nine posts read as one feed. */
const grade = (look: Look) =>
  look === 'tonal'
    ? 'saturate(0.7) sepia(0.16) contrast(0.93) brightness(1.05)'
    : look === 'blocks'
      ? 'saturate(1.08) contrast(1.04)'
      : 'saturate(0.86) contrast(1.06) brightness(1.01)';

const Shot: React.FC<{post: Post; look: Look; inset?: number}> = ({post, look, inset = 0}) => {
  const {system} = useSys();
  const c = system.colors;
  return (
    <div style={{position: 'absolute', left: inset, top: inset, right: inset, bottom: inset * (post.matte ? 2.4 : 1), overflow: 'hidden', background: c.bg}}>
      {post.photo ? (
        <Img src={src(post.photo)} maxRetries={RETRIES}
          style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: post.focal ?? '50% 45%', display: 'block', filter: grade(look)}} />
      ) : null}
      {look === 'tonal' ? (
        <>
          <div style={{position: 'absolute', inset: 0, background: c.paper, mixBlendMode: 'soft-light', opacity: 0.35}} />
          <div style={{position: 'absolute', inset: 0, background: c.bg, mixBlendMode: 'lighten', opacity: 0.16}} />
        </>
      ) : null}
      {look === 'blocks' && post.tint ? (
        <>
          <div style={{position: 'absolute', inset: 0, background: post.tint, mixBlendMode: 'color', opacity: 0.3}} />
          <div style={{position: 'absolute', inset: 0, background: post.tint, mixBlendMode: 'multiply', opacity: 0.14}} />
        </>
      ) : null}
      {look === 'alternate' ? (
        <div style={{position: 'absolute', inset: 0, background: `linear-gradient(to top, ${rgba(c.bg, 0.22)}, ${rgba(c.bg, 0)} 40%)`}} />
      ) : null}
    </div>
  );
};

const fit = (text: string, face: ReturnType<typeof useSys>['system']['display'], width: number, lines: number, max: number) =>
  fitTextOnNLines({
    text,
    maxLines: lines,
    maxBoxWidth: width,
    fontFamily: `'${face.family}'`,
    fontWeight: face.weight,
    letterSpacing: `${face.tracking}em`,
    textTransform: face.case === 'none' ? undefined : face.case,
    maxFontSize: max,
  });

/** A type post: their own words set large on a fill from their palette. */
const TypeCard: React.FC<{post: Post; look: Look}> = ({post, look}) => {
  const {system, board} = useSys();
  const c = system.colors;
  const fill = post.bg ?? (look === 'blocks' ? post.tint ?? c.accent : c.bg);
  const ink = post.ink ?? inkOn(fill, c.ink, c.bg);
  const t = post.text ?? {};
  const pad = 96;
  const head = t.headline ? fit(t.headline, system.display, PW - 2 * pad, look === 'blocks' ? 3 : 4, look === 'blocks' ? 230 : 150) : null;
  return (
    <div style={{position: 'absolute', inset: 0, background: fill, color: ink}}>
      {t.kicker ? (
        <div style={{position: 'absolute', left: pad, top: pad, right: pad, ...faceStyle(system.text), fontSize: 34, letterSpacing: '0.14em',
          textTransform: 'uppercase', opacity: 0.82, whiteSpace: 'nowrap', overflow: 'hidden'}}>
          {t.kicker}
        </div>
      ) : null}
      {head ? (
        <div style={{position: 'absolute', left: pad, right: pad, top: 0, bottom: 0, display: 'flex', flexDirection: 'column',
          justifyContent: look === 'blocks' ? 'center' : 'flex-end', paddingBottom: look === 'blocks' ? 0 : 230}}>
          {head.lines.map((l, i) => (
            <div key={i} style={{...faceStyle(system.display), fontSize: head.fontSize, whiteSpace: 'nowrap',
              textAlign: look === 'blocks' ? 'center' : 'left'}}>{l}</div>
          ))}
        </div>
      ) : null}
      {t.line || look === 'alternate' ? (
        <div style={{position: 'absolute', left: pad, right: pad, bottom: pad, display: 'flex', justifyContent: 'space-between',
          ...faceStyle(system.text), fontSize: 30, opacity: 0.78, whiteSpace: 'nowrap', overflow: 'hidden'}}>
          <span>{t.line ?? ''}</span>
          <span>@{board.handle}</span>
        </div>
      ) : null}
      {look === 'alternate' ? <div style={{position: 'absolute', left: pad, right: pad, bottom: pad + 62, height: 3, background: ink, opacity: 0.5}} /> : null}
    </div>
  );
};

/** Film grain fixed in place, so a still post carries the same texture the film does. */
const PostGrain: React.FC = () => {
  const {system} = useSys();
  if (!system.texture.grain) return null;
  return (
    <div style={{position: 'absolute', inset: 0, backgroundImage: `url(${staticFile('fx/grain.png')})`, backgroundSize: '512px 512px',
      mixBlendMode: 'overlay', opacity: system.texture.grain * 0.8, pointerEvents: 'none'}} />
  );
};

/** One designed post at 1080 by 1350, in the board's direction. */
export const PostView: React.FC<{post: Post}> = ({post}) => {
  const {system, board} = useSys();
  const look = board.look;
  const c = system.colors;
  const matte = look === 'tonal' && post.matte;
  return (
    <div style={{position: 'relative', width: PW, height: PH, overflow: 'hidden', background: matte ? c.paper : c.bg}}>
      {post.kind === 'photo' ? <Shot post={post} look={look} inset={matte ? 64 : 0} /> : <TypeCard post={post} look={look} />}
      {matte && post.text?.line ? (
        <div style={{position: 'absolute', left: 64, right: 64, bottom: 44, ...faceStyle(system.text), fontSize: 30, color: c.bg, opacity: 0.7,
          whiteSpace: 'nowrap', overflow: 'hidden'}}>
          {post.text.line}
        </div>
      ) : null}
      {look === 'blocks' && post.kind === 'photo' && post.text?.headline ? (
        <div style={{position: 'absolute', left: 72, bottom: 64, ...faceStyle(system.display), fontSize: 120, color: c.ink, lineHeight: 0.9,
          textShadow: '0 8px 40px rgba(0,0,0,0.35)', whiteSpace: 'nowrap'}}>
          {post.text.headline}
        </div>
      ) : null}
      <PostGrain />
    </div>
  );
};

/** A post scaled into a box of the given width, keeping 4:5. */
export const PostFit: React.FC<{post: Post; width: number; style?: React.CSSProperties}> = ({post, width, style}) => (
  <div style={{width, height: (width * PH) / PW, overflow: 'hidden', position: 'relative', ...style}}>
    <div style={{transform: `scale(${width / PW})`, transformOrigin: '0 0', width: PW, height: PH}}>
      <PostView post={post} />
    </div>
  </div>
);
