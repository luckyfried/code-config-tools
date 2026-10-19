import React, {useEffect, useRef} from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {fitTextOnNLines} from '@remotion/layout-utils';
import {faceStyle, useSys} from '../system';
import {Photo} from '../photo';
import type {GuideCardData, System} from '../types';

/** Every card is laid out at full size on one grid and scaled by whatever holds it. */
export const CW = 1080;
export const CH = 1350;
const PAD = 80;
const INNER = CW - 2 * PAD;
const BODY_TOP = 330;
const BODY_H = CH - BODY_TOP - 150;

const reported = new Set<string>();

const lumOf = (hex: string) => {
  const n = parseInt(hex.replace('#', ''), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
    const x = c / 255;
    return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
};

/** Ink that reads on a swatch: the card's ink on light colors, its paper on dark ones. */
const inkOn = (hex: string, s: System) => (lumOf(hex) > 0.28 ? s.colors.cardInk : s.colors.card);

export const fit = (text: string, face: System['display'], width: number, max: number, lines: number) =>
  fitTextOnNLines({
    text,
    maxLines: lines,
    maxBoxWidth: width * 0.98,
    fontFamily: `'${face.family}'`,
    fontWeight: face.weight,
    letterSpacing: `${face.tracking}em`,
    textTransform: face.case === 'none' ? undefined : face.case,
    maxFontSize: max,
  });

type Enter = (i: number) => number;

const Label: React.FC<{children: React.ReactNode; color?: string; size?: number; style?: React.CSSProperties}> = ({children, color, size = 26, style}) => {
  const {system} = useSys();
  return (
    <div style={{...faceStyle(system.text), fontSize: size, fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase',
      color: color ?? system.colors.cardMuted, lineHeight: 1.2, whiteSpace: 'nowrap', ...style}}>
      {children}
    </div>
  );
};

const Text: React.FC<{children: React.ReactNode; size?: number; color?: string; style?: React.CSSProperties}> = ({children, size = 32, color, style}) => {
  const {system} = useSys();
  return (
    <div style={{...faceStyle(system.text), fontWeight: 400, letterSpacing: 0, textTransform: 'none', fontSize: size, lineHeight: 1.32,
      color: color ?? system.colors.cardInk, ...style}}>
      {children}
    </div>
  );
};

const Display: React.FC<{text: string; width: number; max: number; lines: number; color?: string; style?: React.CSSProperties}> = ({
  text, width, max, lines, color, style,
}) => {
  const {system} = useSys();
  const f = fit(text, system.display, width, max, lines);
  return (
    <div style={{...faceStyle(system.display), fontSize: f.fontSize, color: color ?? system.colors.cardInk, ...style}}>
      {f.lines.map((l, i) => (
        <div key={i} style={{whiteSpace: 'nowrap'}}>{l}</div>
      ))}
    </div>
  );
};

const rise = (p: number): React.CSSProperties => ({opacity: Math.min(1, p * 1.3), transform: `translateY(${(1 - p) * 40}px)`});

const Palette: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  const colors: any[] = card.colors ?? [];
  const tot = colors.reduce((n, c) => n + (c.share ?? 0), 0) || 1;
  const gap = 14;
  const room = BODY_H - 70 - gap * (colors.length - 1);
  const min = 120;
  const flex = colors.map((c) => Math.max(min, (room * (c.share ?? 0)) / tot));
  const k = room / flex.reduce((a, b) => a + b, 0);
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap, height: '100%'}}>
      {colors.map((c, i) => {
        const p = enter(i + 2);
        const ink = inkOn(c.hex, system);
        return (
          <div key={i} style={{height: flex[i] * k, background: c.hex, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
            padding: '0 34px 22px', transformOrigin: '0 50%', transform: `scaleX(${0.2 + 0.8 * p})`, opacity: Math.min(1, p * 1.5)}}>
            <div style={{...faceStyle(system.display), fontSize: 64, color: ink, whiteSpace: 'nowrap'}}>{c.name}</div>
            <div style={{textAlign: 'right'}}>
              <Label color={ink} size={24}>{c.role}</Label>
              <Text size={28} color={ink} style={{whiteSpace: 'nowrap'}}>{c.label} · {String(c.hex).toLowerCase()}</Text>
            </div>
          </div>
        );
      })}
      <Text size={30} color={system.colors.cardMuted} style={{marginTop: 6, ...rise(enter(colors.length + 2))}}>{card.line}</Text>
    </div>
  );
};

const TypeCard: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  return (
    <div style={{display: 'flex', flexDirection: 'column', height: '100%'}}>
      <div style={{display: 'flex', alignItems: 'flex-end', gap: 40, ...rise(enter(2))}}>
        <div style={{...faceStyle(system.display), fontSize: 250, lineHeight: 0.85, color: system.colors.cardAccent}}>Aa</div>
        <div style={{paddingBottom: 18}}>
          <Label>display</Label>
          <div style={{...faceStyle(system.display), fontSize: 60, color: system.colors.cardInk}}>{card.display}</div>
        </div>
      </div>
      <div style={{marginTop: 36, ...rise(enter(3))}}>
        <Display text={card.sample ?? ''} width={INNER} max={74} lines={3} />
      </div>
      <div style={{marginTop: 40, borderTop: `2px solid ${system.colors.cardMuted}`, paddingTop: 28, ...rise(enter(4))}}>
        <Label>text · {card.text}</Label>
        <Text size={34} style={{marginTop: 14, whiteSpace: 'pre-line', maxHeight: 4 * 45, overflow: 'hidden'}}>{card.caption}</Text>
      </div>
      <Text size={28} color={system.colors.cardMuted} style={{marginTop: 'auto', ...rise(enter(5))}}>{card.why}</Text>
    </div>
  );
};

const Compositions: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  const habits: any[] = card.habits ?? [];
  const row = (BODY_H - 30 * (habits.length - 1)) / Math.max(1, habits.length);
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 30}}>
      {habits.map((h, i) => (
        <div key={i} style={{display: 'flex', gap: 40, height: row, alignItems: 'center', ...rise(enter(i + 2))}}>
          <div style={{width: row * 0.8, height: row, overflow: 'hidden', flex: 'none', background: system.colors.cardMuted}}>
            {h.photo ? <Photo file={h.photo} /> : null}
          </div>
          <div style={{minWidth: 0}}>
            <Display text={h.name} width={INNER - row * 0.8 - 40} max={56} lines={3} />
            {h.label ? <Label color={system.colors.cardAccent} style={{marginTop: 16}}>{h.label}</Label> : null}
          </div>
        </div>
      ))}
    </div>
  );
};

const Voice: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  const devices: any[] = card.devices ?? [];
  const examples: string[] = card.examples ?? [];
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 26, height: '100%'}}>
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px 30px', ...rise(enter(2))}}>
        {devices.map((d, i) => (
          <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: 16, minWidth: 0}}>
            <div style={{...faceStyle(system.display), fontSize: 44, color: system.colors.cardAccent, flex: 'none'}}>{d.label}</div>
            <Text size={28} style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{d.name}</Text>
          </div>
        ))}
      </div>
      {examples.map((x, i) => (
        <div key={i} style={{borderLeft: `6px solid ${system.colors.cardAccent}`, paddingLeft: 28, ...rise(enter(i + 3))}}>
          <Text size={31} style={{whiteSpace: 'pre-line', maxHeight: 4 * 41, overflow: 'hidden'}}>{x}</Text>
        </div>
      ))}
    </div>
  );
};

const Pillars: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  const pillars: any[] = card.pillars ?? [];
  const sw = system.colors.swatches;
  const row = (BODY_H - 120 - 22 * (pillars.length - 1)) / Math.max(1, pillars.length);
  const p0 = enter(2);
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 22}}>
      <div style={{display: 'flex', height: 80, marginBottom: 18, clipPath: `inset(0 ${(1 - p0) * 100}% 0 0)`}}>
        {pillars.map((p, i) => (
          <div key={i} style={{flex: p.share, background: sw[i % sw.length]?.hex, display: 'flex', alignItems: 'center', paddingLeft: 16, overflow: 'hidden'}}>
            <Label color={inkOn(sw[i % sw.length]?.hex ?? '#888888', system)} size={24}>{p.label}</Label>
          </div>
        ))}
      </div>
      {pillars.map((p, i) => (
        <div key={i} style={{display: 'flex', gap: 34, height: row, alignItems: 'center', ...rise(enter(i + 3))}}>
          <div style={{width: row * 0.8, height: row, overflow: 'hidden', flex: 'none', background: sw[i % sw.length]?.hex}}>
            {p.photo ? <Photo file={p.photo} /> : null}
          </div>
          <div style={{width: 18, alignSelf: 'stretch', background: sw[i % sw.length]?.hex, flex: 'none'}} />
          <div style={{minWidth: 0}}>
            <div style={{display: 'flex', alignItems: 'baseline', gap: 22}}>
              <div style={{...faceStyle(system.display), fontSize: Math.min(70, row * 0.36), color: system.colors.cardInk, whiteSpace: 'nowrap'}}>{p.name}</div>
              <Label color={system.colors.cardAccent} size={28}>{p.label}</Label>
            </div>
            <Text size={28} color={system.colors.cardMuted} style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
              {(p.words ?? []).join(' · ')}
            </Text>
          </div>
        </div>
      ))}
    </div>
  );
};

const Cadence: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  const days: any[] = card.days ?? [];
  const most = Math.max(1, ...days.map((d) => d.posts ?? 0));
  const tall = 560;
  return (
    <div style={{display: 'flex', flexDirection: 'column', height: '100%'}}>
      <div style={{display: 'flex', gap: 18, alignItems: 'flex-end', height: tall + 150}}>
        {days.map((d, i) => {
          const p = enter(i + 2);
          const on = Boolean(d.time);
          return (
            <div key={i} style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12}}>
              <div style={{...faceStyle(system.display), fontSize: 38, color: on ? system.colors.cardInk : 'transparent', whiteSpace: 'nowrap', opacity: p}}>
                {d.time ?? '-'}
              </div>
              <div style={{width: '100%', height: Math.max(8, (tall * (d.posts ?? 0)) / most) * p, background: on ? system.colors.cardAccent : system.colors.cardMuted,
                opacity: on ? 1 : 0.45}} />
              <Label color={on ? system.colors.cardInk : system.colors.cardMuted} size={26}>{d.day}</Label>
            </div>
          );
        })}
      </div>
      <Text size={32} style={{marginTop: 40, ...rise(enter(9))}}>{card.line}</Text>
      {card.timezone ? <Label style={{marginTop: 14}}>times in {card.timezone}</Label> : null}
    </div>
  );
};

const Aspire: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  const photos: string[] = card.photos ?? [];
  const colors: any[] = card.colors ?? [];
  const w = (INNER - 2 * 20) / 3;
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 34, height: '100%'}}>
      <div style={{display: 'flex', gap: 20}}>
        {photos.slice(0, 3).map((p, i) => (
          <div key={i} style={{width: w, height: w * 1.25, overflow: 'hidden', ...rise(enter(i + 2))}}>
            <Photo file={p} />
          </div>
        ))}
      </div>
      <div style={{display: 'flex', gap: 22, flexWrap: 'wrap', ...rise(enter(5))}}>
        {colors.map((c, i) => (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 12}}>
            <div style={{width: 46, height: 46, borderRadius: 23, background: c.hex}} />
            <Text size={28} style={{whiteSpace: 'nowrap'}}>{c.name}</Text>
          </div>
        ))}
      </div>
      <Label color={system.colors.cardAccent} style={{whiteSpace: 'normal', ...rise(enter(6))}}>{(card.subjects ?? []).join(' · ')}</Label>
      <div style={{...rise(enter(7))}}>
        <Display text={card.line ?? ''} width={INNER} max={52} lines={4} />
      </div>
    </div>
  );
};

const Stop: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  const items: any[] = card.items ?? [];
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 56, height: '100%', justifyContent: items.length < 3 ? 'center' : 'flex-start'}}>
      {items.map((x, i) => (
        <div key={i} style={{display: 'flex', gap: 30, ...rise(enter(i + 2))}}>
          <div style={{...faceStyle(system.display), fontSize: 80, lineHeight: 0.9, color: system.colors.cardAccent, flex: 'none', width: 70}}>{i + 1}</div>
          <div style={{minWidth: 0}}>
            <Display text={x.line} width={INNER - 100} max={64} lines={3} />
            {x.why ? <Text size={30} color={system.colors.cardMuted} style={{marginTop: 14}}>{x.why}</Text> : null}
          </div>
        </div>
      ))}
    </div>
  );
};

const Week: React.FC<{card: GuideCardData; enter: Enter}> = ({card, enter}) => {
  const {system} = useSys();
  const days: any[] = card.days ?? [];
  return (
    <div style={{display: 'flex', flexDirection: 'column'}}>
      {days.map((d, i) => (
        <div key={i} style={{display: 'flex', gap: 26, alignItems: 'center', height: (BODY_H - 10) / 7, borderTop: i ? `2px solid ${system.colors.cardMuted}55` : undefined,
          ...rise(enter(i + 2))}}>
          <div style={{width: 150, flex: 'none'}}>
            <div style={{...faceStyle(system.display), fontSize: 46, color: system.colors.cardInk, whiteSpace: 'nowrap'}}>{d.day} {String(d.date).slice(8)}</div>
            <Label size={22}>{d.kind}{d.time ? ` ${d.time}` : ''}</Label>
          </div>
          <div style={{minWidth: 0, flex: 1}}>
            <Label color={system.colors.cardAccent} size={24}>{d.pillar}</Label>
            <Text size={30} style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{d.caption}</Text>
          </div>
        </div>
      ))}
    </div>
  );
};

const BODIES: Record<string, React.FC<{card: GuideCardData; enter: Enter}>> = {
  palette: Palette, type: TypeCard, compositions: Compositions, voice: Voice, pillars: Pillars, cadence: Cadence, aspire: Aspire,
  stop: Stop, week: Week,
};

/** The statement card is the one card in the lead color: the line, large, with the handle and the palette under it. */
const Statement: React.FC<{card: GuideCardData; enter: Enter; of: number}> = ({card, enter, of}) => {
  const {system} = useSys();
  const lead = (card.swatches ?? [])[0] ?? system.colors.cardAccent;
  const ink = inkOn(lead, system);
  return (
    <div style={{position: 'absolute', inset: 0, background: lead, padding: PAD, display: 'flex', flexDirection: 'column'}}>
      <Label color={ink} style={{opacity: 0.8}}>{String(card.n).padStart(2, '0')} / {of} · {card.title}</Label>
      <div style={{marginTop: 'auto', ...rise(enter(1))}}>
        <Display text={card.statement ?? ''} width={INNER} max={124} lines={5} color={ink} />
      </div>
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 70, ...rise(enter(3))}}>
        <Label color={ink} size={30}>{card.handle}</Label>
        <div style={{display: 'flex', gap: 10}}>
          {(card.swatches ?? []).map((h: string, i: number) => (
            <div key={i} style={{width: 56, height: 56, background: h, border: `3px solid ${ink}`}} />
          ))}
        </div>
      </div>
    </div>
  );
};

/**
 * One guide card at 1080x1350. delay is the frame its entrance starts; settled draws it at rest.
 * As a still (the Card composition) it reports the color names it shows (GUIDE_COLORS) and any text that ran out of
 * its body (SAFE_BREACH), so qa.py can hold the guide to brand.json.
 */
export const GuideCard: React.FC<{card: GuideCardData; delay?: number; settled?: boolean}> = ({card, delay = 0, settled}) => {
  const {system, board, still, format} = useSys();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const body = useRef<HTMLDivElement>(null);
  const rest = settled || still;
  // a card's contents arrive inside its beat: a quicker spring and a tighter stagger than the film's headlines
  const cfg = {...system.ease.spring, stiffness: system.ease.spring.stiffness * 2};
  const gap = Math.max(2, Math.round(system.ease.stagger * 0.6));
  const enter: Enter = (i) => (rest ? 1 : spring({frame: frame - delay - i * gap, fps, config: cfg}));
  const of = board.cards.length;
  const report = still && format === 'guide';
  useEffect(() => {
    if (!report) return;
    const key = card.id;
    if (reported.has(key)) return;
    reported.add(key);
    const names = [...(card.colors ?? []).map((c: any) => c.name)];
    console.log(`GUIDE_COLORS ${JSON.stringify({card: card.id, names})}`);
    const el = body.current;
    if (el && (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2)) {
      console.log(`SAFE_BREACH ${JSON.stringify({format: 'guide', beat: card.id, box: 'card body', content: [el.scrollWidth, el.scrollHeight],
        box_size: [el.clientWidth, el.clientHeight]})}`);
    }
  });
  const shell: React.CSSProperties = {position: 'relative', width: CW, height: CH, background: system.colors.card, overflow: 'hidden'};
  if (card.kind === 'statement') {
    return (
      <div style={shell}>
        <Statement card={card} enter={enter} of={of} />
      </div>
    );
  }
  const Body = BODIES[card.kind];
  const t0 = enter(0);
  return (
    <div style={shell}>
      <div style={{position: 'absolute', left: PAD, right: PAD, top: PAD, display: 'flex', justifyContent: 'space-between', opacity: t0}}>
        <Label color={system.colors.cardAccent}>{String(card.n).padStart(2, '0')} / {of}</Label>
        <Label>@{board.handle}</Label>
      </div>
      <div style={{position: 'absolute', left: PAD, right: PAD, top: PAD + 64, ...rise(enter(1))}}>
        <Display text={card.title} width={INNER} max={104} lines={1} />
      </div>
      <div ref={body} style={{position: 'absolute', left: PAD, right: PAD, top: BODY_TOP, height: BODY_H, overflow: 'hidden'}}>
        {Body ? <Body card={card} enter={enter} /> : null}
      </div>
      <div style={{position: 'absolute', left: PAD, right: PAD, bottom: 64, display: 'flex', gap: 8, opacity: t0}}>
        {system.colors.swatches.map((s, i) => (
          <div key={i} style={{flex: 1, height: 10, background: s.hex}} />
        ))}
      </div>
    </div>
  );
};

/** A card scaled into a box on screen, its top left corner at (x, y). */
export const PlacedCard: React.FC<{card: GuideCardData; x: number; y: number; scale: number; delay?: number; settled?: boolean; style?: React.CSSProperties}> = ({
  card, x, y, scale, delay, settled, style,
}) => (
  <div style={{position: 'absolute', left: x, top: y, width: CW, height: CH, transformOrigin: '0 0', transform: `scale(${scale})`,
    boxShadow: '0 50px 120px rgba(0,0,0,0.35)', ...style}}>
    <GuideCard card={card} delay={delay} settled={settled} />
  </div>
);
