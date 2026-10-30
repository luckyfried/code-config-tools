// A glyph's geometry in each face of the three looks covers exactly the ink the face draws: every point its outline
// fills by the nonzero rule is under a triangle, and no point the outline leaves empty is.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import opentype from 'opentype.js';
import {glyphGeometry, type Font} from './type.ts';

const face = (file: string) => {
  const bytes = readFileSync(fileURLToPath(new URL(`../../../${file}`, import.meta.url)));
  return Object.assign(opentype.parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)), {file}) as Font;
};

type Pt = [number, number];

/** The nonzero winding number of the outline at a point (outline y down, as the face draws it). */
const winding = (contours: Pt[][], [x, y]: Pt) => {
  let w = 0;
  for (const c of contours) {
    for (let i = 0; i < c.length; i++) {
      const [ax, ay] = c[i];
      const [bx, by] = c[(i + 1) % c.length];
      if ((ay <= y) !== (by <= y)) {
        const cx = ax + ((y - ay) * (bx - ax)) / (by - ay);
        if (x < cx) w += by > ay ? 1 : -1;
      }
    }
  }
  return w;
};

const inside = (p: Pt, a: Pt, b: Pt, c: Pt) => {
  const s = (u: Pt, v: Pt, q: Pt) => (v[0] - u[0]) * (q[1] - u[1]) - (v[1] - u[1]) * (q[0] - u[0]);
  const d1 = s(a, b, p), d2 = s(b, c, p), d3 = s(c, a, p);
  return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
};

const at = (rel: string) => fileURLToPath(new URL(`../../../${rel}`, import.meta.url));
const LOOKS = ['cinematic-letterbox', 'editorial-quiet', 'kinetic-type'];
const FILES = [...new Set(LOOKS.flatMap((s) => Object.values(JSON.parse(readFileSync(at(`styles/${s}.json`), 'utf8')).faces).map((f: any) => f.file as string)))];
const CHARS = 'AKMNRVWXYkmvwxyz0247';

for (const file of FILES) {
  test(`every letter of ${CHARS} in ${file.split('/').pop()} is filled as its face draws it`, () => {
    const chars = CHARS;
    const font = face(file);
    for (const ch of chars) {
      const g = font.charToGlyph(ch);
      // the outline straight from the face, curves sampled finely: y down, so the geometry's y up is its negative
      const contours: Pt[][] = [];
      for (const {type, x = 0, y = 0, x1 = 0, y1 = 0, x2 = 0, y2 = 0} of g.getPath(0, 0, 1).commands) {
        if (type === 'M') contours.push([[x, y]]);
        if (type === 'L') contours[contours.length - 1].push([x, y]);
        if (type === 'Q' || type === 'C') {
          const cur = contours[contours.length - 1];
          const [sx, sy] = cur[cur.length - 1];
          for (let k = 1; k <= 32; k++) {
            const t = k / 32, u = 1 - t;
            cur.push(type === 'Q'
              ? [u * u * sx + 2 * u * t * x1 + t * t * x, u * u * sy + 2 * u * t * y1 + t * t * y]
              : [u * u * u * sx + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x,
                 u * u * u * sy + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y]);
          }
        }
      }
      const geo = glyphGeometry(font, g, 0);
      const pos = geo.getAttribute('position');
      const idx = geo.getIndex();
      const tris: [Pt, Pt, Pt][] = [];
      const at = (k: number): Pt => [pos.getX(k), -pos.getY(k)];
      const n = idx ? idx.count : pos.count;
      for (let k = 0; k < n; k += 3) {
        const v = (m: number) => (idx ? idx.getX(m) : m);
        tris.push([at(v(k)), at(v(k + 1)), at(v(k + 2))]);
      }
      const xs = contours.flat().map((p) => p[0]), ys = contours.flat().map((p) => p[1]);
      const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
      let wrong = 0, ink = 0;
      const N = 80;
      for (let i = 0; i < N; i++) {
        for (let j = 0; j < N; j++) {
          const p: Pt = [x0 + ((i + 0.5) / N) * (x1 - x0), y0 + ((j + 0.5) / N) * (y1 - y0)];
          const filled = winding(contours, p) !== 0;
          const covered = tris.some(([a, b, c]) => inside(p, a, b, c));
          if (filled) ink++;
          if (filled !== covered) wrong++;
        }
      }
      // straight lines stand in for the curves, so a sliver along a bowl differs; a wrong shape differs by far more
      assert.ok(wrong < 0.02 * ink, `${ch}: ${wrong} of ${ink} ink samples differ from the face's own fill`);
    }
  });
}
