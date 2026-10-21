// The ribbon: the nine photographs standing out of the finished wall as bars, each on its slice's lower edge and as
// tall as its share of the top post's likes, its photograph on its face and its count at its top, which the camera
// grazes along; then each folds flat onto its own slice and draws back into its edge, leaving the closer.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, span} from '../../system/three/motion';
import {layout, type Font} from '../../system/three/type';
import type {Plan} from './plan';

const TALL = 420;
const THICK = 26;
const FACE_W = 512;

type Cmd = {type: string; x?: number; y?: number; x1?: number; y1?: number; x2?: number; y2?: number};

/** `text` in `font` filled on `g` with its baseline's left end at (x, y), `size` px to the em. */
const fillText = (g: CanvasRenderingContext2D, font: Font, text: string, x: number, y: number, size: number) => {
  const {glyphs} = layout(font, text, -0.02);
  g.beginPath();
  for (const p of glyphs) {
    for (const c of p.glyph.getPath(x + p.x * size, y, size).commands as Cmd[]) {
      if (c.type === 'M') g.moveTo(c.x!, c.y!);
      else if (c.type === 'L') g.lineTo(c.x!, c.y!);
      else if (c.type === 'Q') g.quadraticCurveTo(c.x1!, c.y1!, c.x!, c.y!);
      else if (c.type === 'C') g.bezierCurveTo(c.x1!, c.y1!, c.x2!, c.y2!, c.x!, c.y!);
      else if (c.type === 'Z') g.closePath();
    }
  }
  g.fill();
};

/** A bar's face at its full height: its photograph filling it, its count across its top in the condensed numerals. */
const faceOf = (img: HTMLImageElement | undefined, font: Font | undefined, label: string, aspect: number, colors: Record<string, string>) => {
  const cv = document.createElement('canvas');
  cv.width = FACE_W;
  cv.height = Math.min(2048, Math.max(64, Math.round(FACE_W * aspect)));
  const g = cv.getContext('2d')!;
  g.fillStyle = colors.paper;
  g.fillRect(0, 0, cv.width, cv.height);
  if (img && img.width) {
    const k = Math.max(cv.width / img.width, cv.height / img.height);
    const w = img.width * k, h = img.height * k;
    g.drawImage(img, (cv.width - w) / 2, (cv.height - h) / 2, w, h);
  }
  const shade = g.createLinearGradient(0, 0, 0, Math.min(cv.height, FACE_W * 0.7));
  shade.addColorStop(0, 'rgba(0,0,0,0.45)');
  shade.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = shade;
  g.fillRect(0, 0, cv.width, cv.height);
  if (font) {
    const width = layout(font, label, -0.02).width;
    const size = Math.min(FACE_W * 0.42, (cv.width * 0.84) / Math.max(0.1, width));
    const x = cv.width * 0.08, y = size * 0.92;
    g.fillStyle = colors.ink;
    fillText(g, font, label, x + size * 0.04, y + size * 0.04, size);
    g.fillStyle = colors.paper;
    fillText(g, font, label, x, y, size);
  }
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
};

export const Ribbon: React.FC<{plan: Plan; t: number; image: (file: string) => HTMLImageElement | undefined; font?: Font}> = ({plan, t, image, font}) => {
  const {at: R, bars} = plan.ribbon;
  const geo = useMemo(() => new THREE.BoxGeometry(1, 1, 1).translate(0, 0, 0.5), []);
  const looks = useMemo(() => {
    const ink = new THREE.Color(plan.colors.ink);
    const accent = new THREE.Color(plan.colors.accent);
    // the far face and the ends a step off the ink, so the slab reads as card; the top edge a paper line
    const back = new THREE.MeshBasicMaterial({color: ink.clone().lerp(accent, 0.25), toneMapped: false});
    const cap = new THREE.MeshBasicMaterial({color: plan.colors.paper, toneMapped: false});
    const end = new THREE.MeshBasicMaterial({color: ink.clone().lerp(accent, 0.4), toneMapped: false});
    return bars.map((b) => {
      const len = Math.hypot(b.b[0] - b.a[0], b.b[1] - b.a[1]) * 0.84;
      const map = faceOf(image(b.file), font, b.label, (TALL * b.share) / len, plan.colors);
      const face = new THREE.MeshBasicMaterial({map, toneMapped: false});
      return {len, map, mats: [end, end, back, face, cap, back]};
    });
  }, [plan, bars, image, font]);
  if (t < R || t > plan.closer.at + 0.2) return null;
  const enter = bezier(plan.ease.enter);
  const move = bezier(plan.ease.move);
  return (
    <group>
      {bars.map((b, i) => {
        const rise = enter(Math.min(1, Math.max(0, (t - (R + 0.05 + i * 0.07)) / 0.55)));
        const fold = span(t, R + 2.0 + i * 0.05, 0.7, move);
        const back = span(t, R + 2.55 + i * 0.05, 0.6, move);
        const grown = Math.max(0, rise) * (1 - back);
        const tall = TALL * b.share * grown;
        if (tall < 0.5) return null;
        // the face shows the part of the photograph the bar has risen to, its count riding at its top
        const {len, map, mats} = looks[i];
        map.repeat.set(1, grown);
        map.offset.set(0, 1 - grown);
        const dx = b.b[0] - b.a[0], dy = b.b[1] - b.a[1];
        const mid: [number, number] = [(b.a[0] + b.b[0]) / 2, (b.a[1] + b.b[1]) / 2];
        const m = new THREE.Matrix4().makeTranslation(mid[0] - plan.W / 2, plan.H / 2 - mid[1], 0.5);
        m.multiply(new THREE.Matrix4().makeRotationZ(-Math.atan2(dy, dx)));
        // it folds up onto its own slice, its face (and so its photograph, upright) turned to the camera
        m.multiply(new THREE.Matrix4().makeRotationX(-fold * Math.PI * 0.5));
        m.multiply(new THREE.Matrix4().makeScale(len, THICK, tall));
        return <mesh key={b.rank} geometry={geo} material={mats} matrixAutoUpdate={false} matrix={m} castShadow renderOrder={2000 + i} />;
      })}
    </group>
  );
};
