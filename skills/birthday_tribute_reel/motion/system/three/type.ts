// Type as geometry: a line set from a font file through opentype.js at the weight it names (a variable file set at that
// instance), each glyph a flat shape or an extruded solid at one em, cached by font and glyph, so a count can stand
// on an edge in the camera's space with its sides lit.
import opentype from 'opentype.js';
import {useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import * as THREE from 'three';
import {instanceOf} from './variation';

export type Font = {
  file: string;
  unitsPerEm: number;
  stringToGlyphs: (s: string) => Glyph[];
  getKerningValue: (a: Glyph, b: Glyph) => number;
  charToGlyph: (c: string) => Glyph;
};
type Glyph = {index: number; advanceWidth: number; getPath: (x: number, y: number, size: number) => {commands: Cmd[]}};
type Cmd = {type: string; x?: number; y?: number; x1?: number; y1?: number; x2?: number; y2?: number};

/** A line's face as the boards name it: the font `file` compose.py set it in, from the board's style card. */
export type FaceKey = {file?: string; face?: string; weight?: number};

/** The font a line is set in, as one key `<file>@<weight>`: the file compose.py set it in, at the line's weight. A
 * variable file is drawn at that weight's instance (its default instance when the line names none), a static file as
 * it is. A line the board set in no file is a defect the render names. */
export const fileOf = ({file, weight}: FaceKey) => {
  if (!file) throw new Error('FONT_ERROR a line names no font file: compose.py sets every line in a face of the card');
  return `${file}@${weight ?? ''}`;
};

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

/** Where segment ab crosses segment cd, strictly inside both, or null. */
const crossing = (a: THREE.Vector2, b: THREE.Vector2, c: THREE.Vector2, d: THREE.Vector2) => {
  const r = b.clone().sub(a), s = d.clone().sub(c), den = r.x * s.y - r.y * s.x;
  if (Math.abs(den) < 1e-12) return null;
  const t = ((c.x - a.x) * s.y - (c.y - a.y) * s.x) / den, u = ((c.x - a.x) * r.y - (c.y - a.y) * r.x) / den;
  return t > 1e-9 && t < 1 - 1e-9 && u > 1e-9 && u < 1 - 1e-9 ? a.clone().add(r.multiplyScalar(t)) : null;
};

/** A closed outline cut at every place it crosses itself into the simple loops it bounds. */
const loopsOf = (p: THREE.Vector2[]): THREE.Vector2[][] => {
  const n = p.length;
  for (let i = 0; i < n; i++) for (let j = i + 2; j < n; j++) {
    if (i === 0 && j === n - 1) continue;
    const x = crossing(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n]);
    if (x) return [...loopsOf([x, ...p.slice(i + 1, j + 1)]), ...loopsOf([x, ...p.slice(j + 1), ...p.slice(0, i + 1)])];
  }
  return n >= 3 ? [p] : [];
};

/**
 * A glyph's contours, each point placed by `at`. A font fills by winding, so one contour may cross itself (a B whose
 * two counters are one contour); the triangulator fills only simple outlines, so such a contour is cut at each
 * crossing into its loops, and a loop that winds the other way is a counter.
 */
export const glyphPath = (g: Pick<Glyph, 'getPath'>, at: (x: number, y: number) => [number, number]) => {
  const p = new THREE.ShapePath();
  for (const c of g.getPath(0, 0, 1).commands) {
    if (c.type === 'M') p.moveTo(...at(c.x!, c.y!));
    else if (c.type === 'L') p.lineTo(...at(c.x!, c.y!));
    else if (c.type === 'Q') p.quadraticCurveTo(...at(c.x1!, c.y1!), ...at(c.x!, c.y!));
    else if (c.type === 'C') p.bezierCurveTo(...at(c.x1!, c.y1!), ...at(c.x2!, c.y2!), ...at(c.x!, c.y!));
  }
  p.subPaths = p.subPaths.flatMap((s) => {
    const pts = s.getPoints(8);
    if (pts.length > 1 && pts[0].equals(pts[pts.length - 1])) pts.pop();
    const loops = loopsOf(pts);
    return loops.length === 1 ? [s] : loops.map((l) => new THREE.Path(l));
  });
  return p;
};

const shapes = new Map<string, THREE.Shape[]>();

/** A glyph's outline at one em, baseline at y 0, y up. */
const shapesOf = (font: Font, g: Glyph) => {
  const key = `${font.file}#${g.index}`;
  if (!shapes.has(key)) shapes.set(key, glyphPath(g, (x, y) => [x, -y]).toShapes());
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
