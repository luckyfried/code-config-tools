// Type as geometry: a line set from a font file through opentype.js at the weight it names (a variable file set at that
// instance), each glyph a flat shape or an extruded solid at one em, cached by font and glyph, so a count can stand on
// an edge in the camera's space with its sides lit.
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
  tables?: {os2?: {sCapHeight?: number}};
};
type Glyph = {index: number; advanceWidth: number; getPath: (x: number, y: number, size: number) => {commands: Cmd[]}};
type Cmd = {type: string; x?: number; y?: number; x1?: number; y1?: number; x2?: number; y2?: number};

/** One face of a line as the boards name it: `display` the titles, names and lines of the film, `text` the text face;
 * `weight` the line's own weight, else its face's. */
export type FaceKey = {face?: string; weight?: number};

const faces = {display: {file: '', weight: 400}, text: {file: '', weight: 400}};

/** Names the board's two faces, from its style card (the system's `display` and `text`, each a file and a weight);
 * every fileOf after it reads them. */
export const setFaces = (system: {display: {file: string; weight: number}; text: {file: string; weight: number}}) => {
  faces.display = {file: system.display.file, weight: system.display.weight};
  faces.text = {file: system.text.file, weight: system.text.weight};
};

/** The font a line is set in, as one key `<file>@<weight>`: the board's display face for display, its text face for
 * everything else, at the line's weight or else its face's. A variable file is drawn at that weight's instance, a
 * static file as it is. */
export const fileOf = ({face, weight}: FaceKey) => {
  const f = face === 'display' ? faces.display : faces.text;
  if (!f.file) throw new Error('FONT_ERROR no faces named: setFaces runs before fileOf');
  return `${f.file}@${weight ?? f.weight}`;
};

const sources = new Map<string, Promise<{font: any; buf: ArrayBuffer}>>();
const loading = new Map<string, Promise<Font>>();
const loaded = new Map<string, Font>();

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

/** The font a key from fileOf names: its file at its weight. */
const load = (key: string) => {
  if (!loading.has(key)) {
    const at = key.lastIndexOf('@');
    loading.set(
      key,
      parse(key.slice(0, at)).then(({font, buf}) => {
        const f = instanceOf(font, buf, {wght: Number(key.slice(at + 1))}, key) as Font;
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

/** A glyph's outline at one em, baseline at y 0, y up. */
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
    shapes.set(key, p.toShapes());
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
