// A line of type in the camera's space: flat or extruded glyphs on a baseline frame the caller places, rising through
// a window on its baseline, and, for a count, rolling its digits like an odometer, each drum drawn at every value the
// shutter saw so a fast roll blurs.
import {useMemo} from 'react';
import * as THREE from 'three';
import {glyphGeometry, layout, type Font} from './type';

/** One em of the line's frame: x along the baseline, y up from it, z toward the camera. A line rises through the
 * loose window, which keeps its descenders; a count rolls through the tight one, cut just outside its figures. */
const LOOSE: [number, number] = [-0.3, 1.08];

type Draw = {g: any; x: number; y: number; ghost: boolean};

/** A count rolling from `from` to `to`: `p` is the roll's progress at each instant the shutter saw, oldest first. */
export type Roll = {from: number; to: number; p: number[]};

const digitsOf = (v: number) => String(Math.max(0, Math.round(v))).length;
const digitAt = (v: number, i: number) => Math.floor(Math.max(0, Math.round(v)) / Math.pow(10, i)) % 10;
// a drum keeps its speed late and stops short, so a count reads as landed on the beat its roll ends on
const settle = (x: number) => 1 - Math.pow(1 - x, 2);

/** Column `i` (0 the units) of `n`: its drum turns forward from the start digit to the end digit, the low columns
 * spinning extra full turns, and each column lands a little before the one to its right. */
const drum = (r: Roll, i: number, n: number, p: number) => {
  const a = digitAt(r.from, i);
  const b = digitAt(r.to, i);
  const turns = i === 0 ? 2 : i === 1 ? 1 : 0;
  const span = ((b - a + 10) % 10) + 10 * turns;
  const end = 1 - 0.14 * Math.min(i, n - 1) / Math.max(1, n - 1);
  return {a, span, pos: span * settle(Math.min(1, Math.max(0, p / end)))};
};

export type Type3DProps = {
  font: Font;
  text: string;
  tracking?: number;
  color: string;
  /** the colour of an extrusion's sides */
  side?: string;
  /** the line's baseline frame in world space, one em to a unit */
  matrix: THREE.Matrix4;
  depth?: number;
  /** absent, the text is drawn as it is */
  roll?: Roll;
  /** 0 below its baseline, 1 risen */
  rise?: number;
  opacity?: number;
  anchor?: string;
  /** a flat ink copy offset down and right, the long shadow on the surface the line stands on */
  shadow?: number;
  castShadow?: boolean;
  renderOrder?: number;
};

export const Type3D: React.FC<Type3DProps> = ({
  font, text, tracking = 0, color, side, matrix, depth = 0, roll, rise = 1, opacity = 1, anchor, shadow = 0, castShadow = false, renderOrder = 0,
}) => {
  const lay = useMemo(() => layout(font, text, tracking), [font, text, tracking]);
  const make = () => ({
    face: new THREE.MeshBasicMaterial({toneMapped: false, transparent: true}),
    sides: new THREE.MeshStandardMaterial({roughness: 0.55, metalness: 0.05, transparent: true}),
  });
  const mats = useMemo(() => ({solid: make(), ghost: make(), shade: new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, color: '#000000', depthWrite: false})}), []);
  const u = font.unitsPerEm;
  const cap = (font.tables?.os2?.sCapHeight ?? 0.7 * u) / u;
  const win: [number, number] = roll ? [-0.07, cap + 0.07] : LOOSE;
  const row = win[1] - win[0] + 0.12;
  const planes = useMemo(() => [new THREE.Plane(), new THREE.Plane()], []);
  planes[0].set(new THREE.Vector3(0, 1, 0), -win[0]);
  planes[1].set(new THREE.Vector3(0, -1, 0), win[1]);
  planes.forEach((p) => p.applyMatrix4(matrix));
  const samples = roll ? (roll.p.length ? roll.p : [1]) : null;
  const ghostAlpha = samples && samples.length > 1 ? opacity * (1 - Math.pow(1 - 0.9, 1 / samples.length)) : opacity;
  for (const [m, a] of [[mats.solid, opacity], [mats.ghost, ghostAlpha]] as const) {
    m.face.color.set(color);
    m.face.opacity = a;
    m.sides.color.set(side ?? color);
    m.sides.opacity = a;
  }
  mats.shade.opacity = shadow * opacity;
  for (const m of [mats.solid.face, mats.solid.sides, mats.ghost.face, mats.ghost.sides, mats.shade]) {
    m.clippingPlanes = planes;
    m.clipShadows = true;
    m.depthWrite = m.opacity > 0.99 && m !== mats.shade;
  }
  if (opacity <= 0.002) return null;
  const shift = anchor === 'end' ? -lay.width : anchor === 'middle' ? -lay.width / 2 : 0;
  const lift = -(1 - rise) * (win[1] - win[0]);
  const draws: Draw[] = [];
  if (!roll || !samples) {
    for (const p of lay.glyphs) draws.push({g: p.glyph, x: p.x + shift, y: lift, ghost: false});
  } else {
    const slots = lay.glyphs.filter((p) => /\d/.test(p.char));
    const n = slots.length;
    const lead = (v: number, i: number) => i > 0 && i >= digitsOf(v);
    slots.forEach((slot, k) => {
      const i = n - 1 - k;
      const at = samples.map((p) => drum(roll, i, n, p));
      const still = at.every((d) => Math.abs(d.pos - at[at.length - 1].pos) < 0.01);
      for (const d of still ? [at[at.length - 1]] : at) {
        const whole = Math.floor(d.pos);
        const frac = d.pos - whole;
        for (const [step, y] of [[whole, frac * row], [whole + 1, (frac - 1) * row]] as const) {
          if (y < win[0] - cap - 0.05 || y > win[1] + 0.05) continue;
          if (step === 0 && lead(roll.from, i)) continue;
          if (step === d.span && lead(roll.to, i)) continue;
          const g = font.stringToGlyphs(String((d.a + step) % 10))[0];
          draws.push({g, x: slot.x + shift + (slot.glyph.advanceWidth - g.advanceWidth) / u / 2, y: y + lift, ghost: !still});
        }
      }
    });
    for (const p of lay.glyphs) if (!/\d/.test(p.char)) draws.push({g: p.glyph, x: p.x + shift, y: lift, ghost: false});
  }
  return (
    <group matrixAutoUpdate={false} matrix={matrix}>
      {shadow > 0
        ? draws.filter((d) => !d.ghost).map((d, i) => (
            <mesh key={`s${i}`} geometry={glyphGeometry(font, d.g, 0)} material={mats.shade} position={[d.x + 0.035, d.y - 0.05, -0.002]} renderOrder={renderOrder} />
          ))
        : null}
      {draws.map((d, i) => (
        <mesh key={i} geometry={glyphGeometry(font, d.g, depth)} material={(m => (depth > 0 ? [m.face, m.sides] : m.face))(d.ghost ? mats.ghost : mats.solid)} position={[d.x, d.y, 0]}
          castShadow={castShadow} renderOrder={renderOrder + 1} />
      ))}
    </group>
  );
};
