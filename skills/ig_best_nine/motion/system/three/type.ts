// Type as geometry: a line set from a static font file through opentype.js, each glyph a flat shape or an extruded
// solid at one em, cached by font and glyph, so a count can stand on an edge in the camera's space with its sides lit.
import opentype from 'opentype.js';
import {useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import * as THREE from 'three';

export type Font = {
  file: string;
  unitsPerEm: number;
  stringToGlyphs: (s: string) => Glyph[];
  getKerningValue: (a: Glyph, b: Glyph) => number;
};
type Glyph = {index: number; advanceWidth: number; getPath: (x: number, y: number, size: number) => {commands: Cmd[]}};
type Cmd = {type: string; x?: number; y?: number; x1?: number; y1?: number; x2?: number; y2?: number};

/** One face of a line as the boards name it: `display` is the condensed numeral face, `text` the text face at a weight. */
export type FaceKey = {face?: string; weight?: number};

const TEXT: Record<number, string> = {500: 'Medium', 600: 'SemiBold', 700: 'Bold', 800: 'ExtraBold'};

/** The static font file a line is set in: Archivo condensed extra bold for display, Archivo at the line's weight for text. */
export const fileOf = ({face, weight}: FaceKey) =>
  face === 'display' ? 'fonts/Archivo/Archivo-Condensed-ExtraBold.ttf' : `fonts/Archivo/Archivo-${TEXT[nearest(weight ?? 600)]}.ttf`;

const nearest = (w: number) => Number(Object.keys(TEXT).reduce((a, b) => (Math.abs(Number(b) - w) < Math.abs(Number(a) - w) ? b : a)));

const loading = new Map<string, Promise<Font>>();
const loaded = new Map<string, Font>();

const load = (file: string) => {
  if (!loading.has(file)) {
    loading.set(
      file,
      fetch(staticFile(file))
        .then((r) => {
          if (!r.ok) throw new Error(`FONT_ERROR ${file} answered ${r.status}`);
          return r.arrayBuffer();
        })
        .then((buf) => {
          const f = opentype.parse(buf) as Font;
          f.file = file;
          loaded.set(file, f);
          return f;
        }),
    );
  }
  return loading.get(file)!;
};

/** The fonts for `files`, holding the frame until every one is parsed and the render that uses them has committed; null until then. */
export const useFonts = (files: string[]): Map<string, Font> | null => {
  const key = [...new Set(files)].sort().join('|');
  const ready = key.split('|').every((f) => loaded.has(f));
  const [handle] = useState(() => (ready ? null : delayRender(`type: ${key}`)));
  const [, bump] = useState(0);
  useEffect(() => {
    if (!ready) {
      Promise.all(key.split('|').map(load)).then(() => bump((n) => n + 1));
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
    shapes.set(key, p.toShapes(false));
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
