// A line of type in the camera's space: flat or extruded glyphs on a baseline frame the caller places, rising through
// a window on its baseline (the whole line at once, or letter by letter on the caller's curve).
import {useMemo} from 'react';
import * as THREE from 'three';
import {glyphGeometry, layout, type Font} from './type';

/** One em of the line's frame: x along the baseline, y up from it, z toward the camera. A line rises through this
 * window, which keeps its descenders. */
const WINDOW: [number, number] = [-0.3, 1.08];

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
  /** the share of the rise over which the letters start one after another, first to last: 0 the line rises whole */
  stagger?: number;
  /** the curve each letter rises on when the line rises letter by letter */
  ease?: (u: number) => number;
  opacity?: number;
  anchor?: string;
  /** a flat ink copy offset down and right, the long shadow on the surface the line stands on */
  shadow?: number;
  castShadow?: boolean;
  renderOrder?: number;
};

export const Type3D: React.FC<Type3DProps> = ({
  font, text, tracking = 0, color, side, matrix, depth = 0, rise = 1, stagger = 0, ease = (u: number) => u, opacity = 1, anchor, shadow = 0,
  castShadow = false, renderOrder = 0,
}) => {
  const lay = useMemo(() => layout(font, text, tracking), [font, text, tracking]);
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
  const lift = -(1 - rise) * (win[1] - win[0]);
  const n = Math.max(1, lay.glyphs.length - 1);
  const letter = (k: number) => {
    const u = Math.min(1, Math.max(0, (rise - (stagger * k) / n) / (1 - stagger)));
    return -(1 - ease(u)) * (win[1] - win[0]);
  };
  const draws: Draw[] = lay.glyphs.map((p, k) => ({g: p.glyph, x: p.x + shift, y: stagger > 0 ? letter(k) : lift}));
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
