// Type as geometry: a line set from a font file through opentype.js at the weight it names (a variable file set at that
// instance), each glyph a flat shape or an extruded solid at one em, cached by font and glyph, so a count can stand
// on an edge in the camera's space with its sides lit.
import opentype from 'opentype.js';
import {useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import * as THREE from 'three';
import {instanceOf} from './variation';
import {resolvedShapes} from './outline';

export type Font = {
  file: string;
  unitsPerEm: number;
  stringToGlyphs: (s: string) => Glyph[];
  charToGlyph: (c: string) => Glyph;
  getKerningValue: (a: Glyph, b: Glyph) => number;
  /** the font's own tables; os2 carries the cap height */
  tables?: {os2?: {sCapHeight?: number}};
};
type Glyph = {index: number; advanceWidth: number; getPath: (x: number, y: number, size: number) => {commands: Cmd[]}};
type Cmd = {type: string; x?: number; y?: number; x1?: number; y1?: number; x2?: number; y2?: number};

/** One face of a line as the boards name it: the font file of the card's face it is set in, and the line's weight. */
export type FaceKey = {file?: string; weight?: number};

/** The font a line is set in, as one key `<file>@<weight>`: the file of the card's face the board names on it, at the
 * line's weight. A variable file is drawn at that weight's instance (its default instance when the line names none), a
 * static file as it is. */
export const fileOf = ({file, weight}: FaceKey) => `${file ?? ''}@${weight ?? ''}`;

/** A count's words as it counts up: every number in `text` at `u` (0 to 1, eased out) of its value, grouped by commas
 * the way the text groups it, so "1,180 likes" passes through "590 likes" on its way. */
export const counted = (text: string, u: number) => {
  const k = 1 - Math.pow(1 - Math.min(1, Math.max(0, u)), 3);
  return text.replace(/\d[\d,]*/g, (m) => {
    const n = Math.round(Number(m.replace(/,/g, '')) * k);
    return m.includes(',') ? n.toLocaleString('en-US') : String(n);
  });
};

/** The words a line shows at beat `t`: a count counting up over its tally, any other line as it is. */
export const shownAt = (ln: {text: string; tally?: {at: number; beats: number}}, t: number) =>
  ln.tally ? counted(ln.text, (t - ln.tally.at) / Math.max(0.001, ln.tally.beats)) : ln.text;

const loading = new Map<string, Promise<Font>>();
const loaded = new Map<string, Font>();

const sources = new Map<string, Promise<{font: any; buf: ArrayBuffer}>>();

/** A font file fetched and parsed once, whatever weights its lines take. */
const parse = (file: string) => {
  if (!sources.has(file)) {
    sources.set(
      file,
      fetch(staticFile(file))
        .then((r) => {
          if (!r.ok) throw new Error(`FONT_ERROR ${file} answered ${r.status}`);
          return r.arrayBuffer();
        })
        .then((buf) => ({font: opentype.parse(buf), buf})),
    );
  }
  return sources.get(file)!;
};

/** The font a key from fileOf names: its file at its weight, or at the file's default instance when it names none. */
const load = (key: string) => {
  if (!loading.has(key)) {
    const at = key.lastIndexOf('@');
    const weight = Number(key.slice(at + 1));
    loading.set(
      key,
      parse(key.slice(0, at)).then(({font, buf}) => {
        const f = instanceOf(font, buf, weight ? {wght: weight} : {}, key) as Font;
        loaded.set(key, f);
        return f;
      }),
    );
  }
  return loading.get(key)!;
};

/** The fonts for `files`, holding the frame until every one is parsed and the render that uses them has committed; null
 * until then. No files to load holds nothing: the map is ready at once. */
export const useFonts = (files: string[]): Map<string, Font> | null => {
  const keys = [...new Set(files)].sort();
  const key = keys.join('|');
  const ready = keys.every((f) => loaded.has(f));
  const [handle] = useState(() => (ready ? null : delayRender(`type: ${key}`)));
  const [, bump] = useState(0);
  useEffect(() => {
    if (!ready) {
      Promise.all(keys.map(load)).then(() => bump((n) => n + 1));
    } else if (handle !== null) {
      continueRender(handle);
    }
  }, [key, ready, handle]);
  return ready ? loaded : null;
};

/** A glyph placed on a line: its advance position in em from the line's start. */
export type Placed = {glyph: Glyph; x: number; char: string};

/** The glyphs of `text` laid out in em, kerned, with `tracking` em after each, and the line's width in em. */
export const layout = (font: Font, text: string, tracking = 0): {glyphs: Placed[]; width: number} => {
  const chars = [...text];
  const u = font.unitsPerEm;
  // A space the font lacks (the thin and narrow no-break spaces between a count's thousands) takes a fifth of an em.
  const blank = font.charToGlyph(' ');
  const gs = font.stringToGlyphs(text).map((g, i) => (g.index === 0 && /\s/u.test(chars[i] ?? '') ? Object.assign(Object.create(blank), {advanceWidth: 0.2 * u}) : g));
  const out: Placed[] = [];
  let x = 0;
  gs.forEach((g, i) => {
    out.push({glyph: g, x, char: chars[i] ?? ''});
    const kern = i + 1 < gs.length ? font.getKerningValue(g, gs[i + 1]) : 0;
    x += (g.advanceWidth + kern) / u + tracking;
  });
  return {glyphs: out, width: x};
};

const shapes = new Map<string, THREE.Shape[]>();

/** A glyph's outline at one em, baseline at y 0, y up; a contour that crosses itself is resolved into simple loops. */
const shapesOf = (font: Font, g: Glyph) => {
  const key = `${font.file}#${g.index}`;
  if (!shapes.has(key)) {
    const p = new THREE.ShapePath();
    for (const c of g.getPath(0, 0, 1).commands) {
      if (c.type === 'M') p.moveTo(c.x!, -c.y!);
      else if (c.type === 'L') p.lineTo(c.x!, -c.y!);
      else if (c.type === 'Q') p.quadraticCurveTo(c.x1!, -c.y1!, c.x!, -c.y!);
      else if (c.type === 'C') p.bezierCurveTo(c.x1!, -c.y1!, c.x2!, -c.y2!, c.x!, -c.y!);
    }
    shapes.set(key, resolvedShapes(p) ?? p.toShapes());
  }
  return shapes.get(key)!;
};

const geoms = new Map<string, THREE.BufferGeometry>();

/**
 * A glyph's geometry at one em: flat (`depth` 0) or extruded `depth` em toward the camera from z 0, its edges rounded
 * by a small bevel so the key light catches them. Groups: 0 the face, 1 the sides.
 */
export const glyphGeometry = (font: Font, g: Glyph, depth = 0) => {
  const key = `${font.file}#${g.index}#${depth}`;
  if (!geoms.has(key)) {
    const s = shapesOf(font, g);
    const geo = depth > 0
      ? new THREE.ExtrudeGeometry(s, {depth, bevelEnabled: true, bevelThickness: depth * 0.12, bevelSize: 0.006, bevelSegments: 2, curveSegments: 8})
      : new THREE.ShapeGeometry(s, 8);
    geoms.set(key, geo);
  }
  return geoms.get(key)!;
};
