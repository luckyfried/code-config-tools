// A line of type in the camera's space: flat or extruded glyphs on a baseline frame the caller places, rising through
// a window on its baseline (the whole line at once, or each glyph on its own).
import {useMemo} from 'react';
import * as THREE from 'three';
import {glyphGeometry, layout, type Font} from './type';

/** One em of the line's frame: x along the baseline, y up from it, z toward the camera. A line rises through this
 * window, which keeps its descenders. */
const LOOSE: [number, number] = [-0.3, 1.08];

/** A glyph rising on its own is drawn once it has risen this share of its height, so no letter enters as a speck of
 * its top. */
const SPECK = 0.18;

const tops = new Map<string, number>();

/** The top of a glyph's outline, in em over its baseline. */
const topOf = (font: Font, g: any) => {
  const key = `${font.file}#${g.index}`;
  if (!tops.has(key)) {
    const ys = (g.getPath(0, 0, 1).commands as {y?: number}[]).filter((c) => c.y !== undefined).map((c) => -c.y!);
    tops.set(key, ys.length ? Math.max(...ys) : 0.7);
  }
  return tops.get(key)!;
};

type Draw = {g: any; x: number; y: number};

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
  /** 0 below its baseline, 1 risen */
  rise?: number;
  /** each glyph's own rise and its offset along the baseline in em, by its index of the line's `n`; absent, every glyph
   * takes `rise` and stands at its place */
  each?: (i: number, n: number) => [number, number];
  opacity?: number;
  anchor?: string;
  /** a flat ink copy offset down and right, the long shadow on the surface the line stands on */
  shadow?: number;
  castShadow?: boolean;
  renderOrder?: number;
};

export const Type3D: React.FC<Type3DProps> = ({
  font, text, tracking = 0, color, side, matrix, depth = 0, rise = 1, each, opacity = 1, anchor, shadow = 0, castShadow = false, renderOrder = 0,
}) => {
  const lay = useMemo(() => layout(font, text, tracking), [font, text, tracking]);
  const make = () => ({
    face: new THREE.MeshBasicMaterial({toneMapped: false, transparent: true}),
    sides: new THREE.MeshStandardMaterial({roughness: 0.55, metalness: 0.05, transparent: true}),
  });
  const mats = useMemo(() => ({solid: make(), shade: new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, color: '#000000', depthWrite: false})}), []);
  const win = LOOSE;
  const planes = useMemo(() => [new THREE.Plane(), new THREE.Plane()], []);
  planes[0].set(new THREE.Vector3(0, 1, 0), -win[0]);
  planes[1].set(new THREE.Vector3(0, -1, 0), win[1]);
  planes.forEach((p) => p.applyMatrix4(matrix));
  mats.solid.face.color.set(color);
  mats.solid.face.opacity = opacity;
  mats.solid.sides.color.set(side ?? color);
  mats.solid.sides.opacity = opacity;
  mats.shade.opacity = shadow * opacity;
  for (const m of [mats.solid.face, mats.solid.sides, mats.shade]) {
    m.clippingPlanes = planes;
    m.clipShadows = true;
    m.depthWrite = m.opacity > 0.99 && m !== mats.shade;
  }
  if (opacity <= 0.002) return null;
  const shift = anchor === 'end' ? -lay.width : anchor === 'middle' ? -lay.width / 2 : 0;
  const lift = -(1 - rise) * (win[1] - win[0]);
  const draws: Draw[] = [];
  const n = lay.glyphs.length;
  lay.glyphs.forEach((p, i) => {
    if (!each) {
      draws.push({g: p.glyph, x: p.x + shift, y: lift});
      return;
    }
    // each glyph rises its own height through the window's bottom, its top crossing it as its rise starts
    const [r, dx] = each(i, n);
    if (r < SPECK) return;
    draws.push({g: p.glyph, x: p.x + shift + dx, y: -(1 - r) * (topOf(font, p.glyph) - win[0])});
  });
  return (
    <group matrixAutoUpdate={false} matrix={matrix}>
      {shadow > 0
        ? draws.map((d, i) => (
            <mesh key={`s${i}`} geometry={glyphGeometry(font, d.g, 0)} material={mats.shade} position={[d.x + 0.035, d.y - 0.05, -0.002]} renderOrder={renderOrder} />
          ))
        : null}
      {draws.map((d, i) => (
        <mesh key={i} geometry={glyphGeometry(font, d.g, depth)} material={depth > 0 ? [mats.solid.face, mats.solid.sides] : mats.solid.face} position={[d.x, d.y, 0]}
          castShadow={castShadow} renderOrder={renderOrder + 1} />
      ))}
    </group>
  );
};
