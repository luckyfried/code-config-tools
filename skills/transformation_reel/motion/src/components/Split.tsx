import React from 'react';
import {AbsoluteFill} from 'remotion';
import {faceStyle, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {Photo, Scrim} from '../photo';
import type {Beat} from '../types';

type Box = {left: number; top: number; width: number; height: number};

/** One side of the pair: the photo cropped to its box, drifting slowly so the film never holds a dead frame. */
const Pane: React.FC<{file: string; box: Box; enter?: number; from?: 'left' | 'right' | 'top' | 'bottom'}> = ({file, box, enter = 1, from}) => {
  const {drift} = useMotion();
  const off = (1 - enter) * 100;
  const shift = from === 'left' ? `translateX(${-off}%)` : from === 'right' ? `translateX(${off}%)` : from === 'top' ? `translateY(${-off}%)` : from === 'bottom' ? `translateY(${off}%)` : '';
  return (
    <div style={{position: 'absolute', ...box, overflow: 'hidden'}}>
      <div style={{width: '100%', height: '100%', transform: `${shift} scale(${drift(1.04, 1.12)})`}}>
        <Photo file={file} />
      </div>
    </div>
  );
};

/** "then · august 9, 2025" set as a tracked word over its date. */
const Label: React.FC<{text: string; delay: number; align?: 'left' | 'right'}> = ({text, delay, align = 'left'}) => {
  const {system} = useSys();
  const {tween} = useMotion();
  const [word, date] = text.split(' · ');
  return (
    <div style={{textAlign: align}}>
      <Kicker text={word} delay={delay} color={system.colors.accent} style={{marginBottom: '0.3em'}} />
      {date ? <div style={{...faceStyle(system.text), fontWeight: 500, letterSpacing: 0, textTransform: 'none', fontSize: system.scale.label,
        color: system.colors.ink, whiteSpace: 'nowrap', opacity: tween(0, 1, delay + 3, 10)}}>{date}</div> : null}
    </div>
  );
};

/** The then/now card (1080x1350): the pair inside the margin, the span in the band under it. */
const PairCard: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const s = useSafe();
  const t = beat.text ?? {};
  const [a, b] = beat.photos ?? ['', ''];
  const labels: string[] = beat.data?.labels ?? [];
  const tb = beat.data?.layout === 'tb';
  const gap = 12;
  const band = 270;
  const area = {left: s.left, top: s.top, width: s.width, height: s.height - band};
  const boxes: Box[] = tb
    ? [{...area, height: (area.height - gap) / 2}, {...area, top: area.top + (area.height + gap) / 2, height: (area.height - gap) / 2}]
    : [{...area, width: (area.width - gap) / 2}, {...area, left: area.left + (area.width + gap) / 2, width: (area.width - gap) / 2}];
  const chip = (text: string, box: Box, key: string) => (
    <div key={key} style={{position: 'absolute', left: box.left + 20, top: box.top + box.height - 20, transform: 'translateY(-100%)',
      background: system.colors.bg, padding: '14px 18px 12px'}}>
      <Label text={text} delay={0} />
    </div>
  );
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <Pane file={a} box={boxes[0]} />
      <Pane file={b} box={boxes[1]} />
      {labels[0] ? chip(labels[0], boxes[0], 'a') : null}
      {labels[1] ? chip(labels[1], boxes[1], 'b') : null}
      <SafeBox name="card" justify="end" top={s.top + area.height + 24}>
        {t.kicker ? <Kicker text={t.kicker} color={system.colors.accent} /> : null}
        {t.headline ? <Headline text={t.headline} max="h1" lines={1} /> : null}
        {t.line ? <Line text={t.line} size={system.scale.label} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};

/**
 * The first and the latest, side by side (left and right, or top and bottom, the way the progress posts they like
 * are cut). split: the two sides slide in and the divider draws between them. wipe: the latest fills the frame and
 * the divider wipes back to the middle, bringing the first in beside it. card: the then/now card.
 */
export const Split: React.FC<{beat: Beat}> = ({beat}) => {
  const {system, format} = useSys();
  const s = useSafe();
  const {tween, pop, duration} = useMotion();
  if (format === 'portrait') return <PairCard beat={beat} />;
  const t = beat.text ?? {};
  const [a, b] = beat.photos ?? ['', ''];
  const labels: string[] = beat.data?.labels ?? [];
  const tb = beat.data?.layout === 'tb';
  const wipe = beat.data?.mode === 'wipe';
  const pos = wipe ? tween(0, 0.5, 2, Math.round(duration * 0.35), 'move') : 0.5;
  const ea = wipe ? 1 : pop(0);
  const eb = wipe ? 1 : pop(5);
  const line = wipe ? 1 : tween(0, 1, 8, 16);
  const W = s.W;
  const H = s.H;
  const first: Box = tb ? {left: 0, top: 0, width: W, height: H * pos} : {left: 0, top: 0, width: W * pos, height: H};
  const second: Box = tb ? {left: 0, top: H * pos, width: W, height: H * (1 - pos)} : {left: W * pos, top: 0, width: W * (1 - pos), height: H};
  const after = wipe ? Math.round(duration * 0.35) : 10;
  return (
    <AbsoluteFill style={{background: system.colors.bg}}>
      <Pane file={b} box={second} enter={eb} from={tb ? 'bottom' : 'right'} />
      <Pane file={a} box={first} enter={ea} from={tb ? 'top' : 'left'} />
      <div style={{position: 'absolute', background: system.colors.accent,
        ...(tb ? {left: 0, width: W, top: H * pos - 3, height: 6, transform: `scaleX(${line})`} : {top: 0, height: H, left: W * pos - 3, width: 6, transform: `scaleY(${line})`})}} />
      <Scrim side="both" strength={0.5} />
      {tb ? (
        <>
          <SafeBox name="then" justify="start">{labels[0] ? <Label text={labels[0]} delay={after} /> : null}</SafeBox>
          <SafeBox name="now" justify="start" top={H / 2 + 36} bottom={H - H / 2 - 36 - 200}>{labels[1] ? <Label text={labels[1]} delay={after + 4} /> : null}</SafeBox>
        </>
      ) : (
        <SafeBox name="labels" justify="start" style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start'}}>
          {labels[0] ? <Label text={labels[0]} delay={after} /> : <div />}
          {labels[1] ? <Label text={labels[1]} delay={after + 4} align="right" /> : null}
        </SafeBox>
      )}
      <SafeBox name="split" justify="end">
        {t.kicker ? <Kicker text={t.kicker} delay={after + 4} color={system.colors.ink} /> : null}
        {t.headline ? <Headline text={t.headline} max="h1" lines={2} delay={after + 6} /> : null}
        {t.line ? <Line text={t.line} delay={after + 14} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
