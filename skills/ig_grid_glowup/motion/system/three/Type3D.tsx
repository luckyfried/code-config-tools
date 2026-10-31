// A line of type in the camera's space: flat or extruded glyphs on a baseline frame the caller places, rising through
// a window on its baseline, the whole line at once or each glyph on its own, tracked out and closing up as it lands.
import {useMemo} from 'react';
import * as THREE from 'three';
import {glyphGeometry, layout, type Font} from './type';

/** One em of the line's frame: x along the baseline, y up from it, z toward the camera. A line rises through this
 * window, which keeps its descenders. */
const WINDOW: [number, number] = [-0.3, 1.08];

export type Type3DProps = {
  font: Font;
  text: string;
  tracking?: number;
  color: string;
  /** the color of an extrusion's sides */
  side?: string;
  /** the line's baseline frame in world space, one em to a unit */
  matrix: THREE.Matrix4;
  depth?: number;
  /** 0 below its baseline, 1 risen */
  rise?: number;
  /** each glyph's own rise, from its index in the line and the index of its word; the whole line's `rise` when unset */
  riseOf?: (i: number, word: number) => number;
  /** em between glyphs, per glyph of the line, while a glyph has not risen: the line tracked out, closing up as it lands */
  track?: number;
  opacity?: number;
  anchor?: string;
  /** a flat ink copy offset down and right, the long shadow on the surface the line stands on */
  shadow?: number;
  castShadow?: boolean;
  renderOrder?: number;
};

export const Type3D: React.FC<Type3DProps> = ({
  font, text, tracking = 0, color, side, matrix, depth = 0, rise = 1, riseOf, track = 0, opacity = 1, anchor, shadow = 0, castShadow = false,
  renderOrder = 0,
}) => {
  const lay = useMemo(() => layout(font, text, tracking), [font, text, tracking]);
  // the index of each glyph's word: a word starts at a glyph that follows a space
  const words = useMemo(() => {
    let w = 0;
    return lay.glyphs.map((p, i) => (i > 0 && /\s/u.test(lay.glyphs[i - 1].char) && !/\s/u.test(p.char) ? ++w : w));
  }, [lay]);
  const make = () => ({
    face: new THREE.MeshBasicMaterial({toneMapped: false, transparent: true}),
    sides: new THREE.MeshStandardMaterial({roughness: 0.55, metalness: 0.05, transparent: true}),
  });
  const mats = useMemo(() => ({solid: make(), shade: new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, color: '#000000', depthWrite: false})}), []);
  const win = WINDOW;
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
  const draws = lay.glyphs
    .map((p, i) => {
      const r = riseOf ? riseOf(i, words[i]) : rise;
      return {i, g: p.glyph, x: p.x + shift + track * i * (1 - r), y: -(1 - r) * (win[1] - win[0]), r};
    })
    .filter((d) => d.r > 0);
  return (
    <group matrixAutoUpdate={false} matrix={matrix}>
      {shadow > 0
        ? draws.map((d) => (
            <mesh key={`s${d.i}`} geometry={glyphGeometry(font, d.g, 0)} material={mats.shade} position={[d.x + 0.035, d.y - 0.05, -0.002]} renderOrder={renderOrder} />
          ))
        : null}
      {draws.map((d) => (
        <mesh key={d.i} geometry={glyphGeometry(font, d.g, depth)} material={depth > 0 ? [mats.solid.face, mats.solid.sides] : mats.solid.face} position={[d.x, d.y, 0]}
          castShadow={castShadow} renderOrder={renderOrder + 1} />
      ))}
    </group>
  );
};
