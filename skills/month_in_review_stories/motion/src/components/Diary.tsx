import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {fitText, measureText} from '@remotion/layout-utils';
import {faceStyle, splits, SubShot, useMotion, useSafe, useSys} from '../system';
import {Headline, SafeBox} from '../text';
import {Photo} from '../photo';
import type {Beat} from '../types';

type Entry = {text: string; n?: string};
type Swatch = {hex: string; name: string};
type Page = {kicker?: string; headline?: string; lines?: Entry[]; photos?: string[]; swatches?: Swatch[]};

const RULE = 66;

/** The display face with Fraunces' soft, wonky cut when the system sets in Fraunces. */
const soft = (family: string): React.CSSProperties =>
  family === 'Fraunces' ? {fontVariationSettings: '"SOFT" 100, "WONK" 1'} : {};

/** A print taped to the page: a white border, a strip of tape across the top, a slight tilt that settles. */
const Taped: React.FC<{file: string; w: number; x: number; y: number; angle: number; delay: number}> = ({file, w, x, y, angle, delay}) => {
  const {system} = useSys();
  const {pop, drift} = useMotion();
  const q = pop(delay, {damping: 16});
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, transform: `translateY(${(1 - q) * 70}px) rotate(${angle * (0.6 + 0.4 * q)}deg)`, opacity: Math.min(1, q * 1.6)}}>
      <div style={{background: '#fbf8f1', padding: w * 0.045, paddingBottom: w * 0.16, boxShadow: '0 18px 40px rgba(40,30,20,0.28), 0 2px 6px rgba(40,30,20,0.18)'}}>
        <div style={{width: '100%', aspectRatio: '1 / 1', overflow: 'hidden'}}>
          <div style={{width: '100%', height: '100%', transform: `scale(${drift(1.03, 1.12)})`}}>
            <Photo file={file} />
          </div>
        </div>
      </div>
      <div style={{position: 'absolute', left: '50%', top: -w * 0.05, width: w * 0.42, height: w * 0.12, marginLeft: -w * 0.21,
        background: `${system.colors.accent2}55`, transform: `rotate(${-angle * 1.4}deg)`, boxShadow: '0 1px 2px rgba(0,0,0,0.08)'}} />
    </div>
  );
};

/** One diary page: a date, prints taped in, a headline in the soft serif, entries that type themselves, chips. */
const Sheet: React.FC<{page: Page; index: number}> = ({page, index}) => {
  const {system, still} = useSys();
  const s = useSafe();
  const {tween, frame, duration} = useMotion();
  const ink = system.colors.ink;
  const photos = (page.photos ?? []).slice(0, 3);
  const lines = page.lines ?? [];
  const maxBody = system.scale.h3 * 0.74;
  const numW = Math.max(0, ...lines.map((l) => (l.n ? measureText({text: l.n, fontFamily: `'${system.display.family}'`, fontWeight: system.display.weight, fontSize: maxBody * 0.95}).width : 0)));
  const col = Math.max(68, Math.ceil(numW) + 30);
  const margin = s.left + col + 24;
  const pw = photos.length === 1 ? s.width * 0.56 : photos.length === 2 ? s.width * 0.44 : s.width * 0.38;
  const spots = photos.length === 1
    ? [[s.left + s.width * 0.22, s.top + 24, -3]]
    : photos.length === 2
      ? [[s.left + 10, s.top + 30, -5], [s.left + s.width * 0.5, s.top + 64, 4]]
      : [[s.left - 6, s.top + 30, -6], [s.left + s.width * 0.31, s.top + 80, 3], [s.left + s.width * 0.62, s.top + 20, -2]];
  // a print is its square photo plus the border: 0.045 of its width on three sides and 0.16 below
  const photoH = photos.length ? Math.max(...spots.slice(0, photos.length).map((p) => p[1] - s.top)) + pw * 1.25 : 0;
  const typeFrom = 18;
  // every entry has typed itself out by a little past half the page, so the page then holds, readable
  const typeSpan = Math.max(10, Math.floor((duration * 0.55 - typeFrom) / Math.max(1, lines.length)));
  const lineW = s.width - col - 24;
  const bodySize = Math.min(maxBody, ...lines.map((l) => fitText({text: l.text + '|', withinWidth: lineW * 0.94,
    fontFamily: `'${system.display.family}'`, fontWeight: 400, letterSpacing: '-0.01em'}).fontSize));
  return (
    <AbsoluteFill style={{background: system.colors.paper}}>
      <AbsoluteFill style={{backgroundImage: `repeating-linear-gradient(to bottom, transparent 0, transparent ${RULE - 2}px, ${system.colors.muted}38 ${RULE - 2}px, ${system.colors.muted}38 ${RULE}px)`,
        backgroundPositionY: s.top % RULE}} />
      <div style={{position: 'absolute', top: 0, bottom: 0, left: margin - 26, width: 2, background: `${system.colors.accent}88`}} />
      {photos.map((p, i) => (
        <Taped key={i} file={p} w={pw} x={spots[i][0]} y={spots[i][1]} angle={spots[i][2]} delay={4 + i * 6} />
      ))}
      <SafeBox name={`diary-${index}`} justify="end" top={s.top + photoH + 14}>
        {page.kicker ? (
          <div style={{...faceStyle(system.text), textTransform: 'uppercase', letterSpacing: '0.16em', fontSize: system.scale.label * 0.9, fontWeight: 600,
            color: system.colors.accent, marginLeft: margin - s.left, marginBottom: 14, opacity: tween(0, 1, 6, 10), fontFeatureSettings: '"tnum" 1'}}>
            {page.kicker}
          </div>
        ) : null}
        {page.headline ? (
          <div style={{marginLeft: margin - s.left, ...soft(system.display.family)}}>
            <Headline text={page.headline} max="h2" lines={2} delay={10} width={s.width - (margin - s.left)} style={soft(system.display.family)} />
          </div>
        ) : null}
        <div style={{marginTop: 18, width: '100%'}}>
          {lines.map((l, i) => {
            const at = typeFrom + i * typeSpan;
            const shown = still ? l.text.length : Math.floor(tween(0, l.text.length, at, Math.max(8, typeSpan * 0.8), 'move'));
            const caret = !still && frame >= at && shown < l.text.length;
            return (
              <div key={i} style={{display: 'flex', alignItems: 'baseline', minHeight: RULE, width: '100%'}}>
                <div style={{width: col + 24, flexShrink: 0, textAlign: 'right', paddingRight: 40, boxSizing: 'border-box', ...faceStyle(system.display), ...soft(system.display.family),
                  fontSize: bodySize * 0.95, color: system.colors.accent, opacity: l.n ? tween(0, 1, at, 8) : 0, whiteSpace: 'nowrap'}}>
                  {l.n ?? ''}
                </div>
                <div style={{...faceStyle(system.display), ...soft(system.display.family), fontWeight: 400, letterSpacing: '-0.01em', fontSize: bodySize, lineHeight: 1.12,
                  color: ink, whiteSpace: 'nowrap', overflow: 'hidden', flex: 1}}>
                  {l.text.slice(0, shown)}
                  <span style={{opacity: caret ? 1 : 0, color: system.colors.accent}}>|</span>
                </div>
              </div>
            );
          })}
        </div>
        {page.swatches?.length ? (
          <div style={{display: 'flex', gap: 14, marginTop: 26, marginLeft: margin - s.left}}>
            {page.swatches.slice(0, 4).map((w, i) => (
              <div key={i} style={{minWidth: 150, background: '#fbf8f1', padding: 8, paddingBottom: 10, boxShadow: '0 6px 14px rgba(40,30,20,0.18)',
                transform: `translateY(${tween(40, 0, 24 + i * 4, 14)}px) rotate(${(i % 2 ? 2 : -2) * tween(1, 0.6, 24 + i * 4, 14)}deg)`, opacity: tween(0, 1, 24 + i * 4, 10)}}>
                <div style={{height: 70, background: w.hex}} />
                <div style={{...faceStyle(system.text), textTransform: 'none', fontSize: system.scale.label * 0.7, fontWeight: 600, color: '#2a2219', marginTop: 8,
                  whiteSpace: 'nowrap'}}>
                  {w.name}
                </div>
                <div style={{...faceStyle(system.text), textTransform: 'none', fontSize: system.scale.label * 0.6, color: '#2a2219', opacity: 0.6}}>{w.hex.toUpperCase()}</div>
              </div>
            ))}
          </div>
        ) : null}
      </SafeBox>
    </AbsoluteFill>
  );
};

/** The month as diary pages, one page per sub-shot, cut where storyboard.py snapped the music. */
export const Diary: React.FC<{beat: Beat}> = ({beat}) => {
  const {still} = useSys();
  const pages: Page[] = beat.data?.pages ?? [];
  if (!pages.length) return null;
  if (still) return <Sheet page={pages[beat.data?.still ?? 0] ?? pages[0]} index={0} />;
  return (
    <AbsoluteFill>
      {splits(beat, pages.length).map(([from, dur], i) => (
        <Sequence key={i} from={from} durationInFrames={dur} layout="none">
          <SubShot frames={dur}>
            <Sheet page={pages[i]} index={i} />
          </SubShot>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
