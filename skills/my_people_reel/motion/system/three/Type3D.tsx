// A line of type in the camera's space: flat or extruded glyphs on a baseline frame the caller places, rising through
// a window on its baseline.
import {useMemo} from 'react';
import * as THREE from 'three';
import {glyphGeometry, layout, type Font} from './type';

/** One em of the line's frame: x along the baseline, y up from it, z toward the camera. A line rises through this
 * window, which keeps its descenders. */
const WIN: [number, number] = [-0.3, 1.08];

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
  opacity?: number;
  anchor?: string;
  /** a flat ink copy offset down and right, the long shadow on the surface the line stands on */
  shadow?: number;
  castShadow?: boolean;
  renderOrder?: number;
};

export const Type3D: React.FC<Type3DProps> = ({
  font, text, tracking = 0, color, side, matrix, depth = 0, rise = 1, opacity = 1, anchor, shadow = 0, castShadow = false, renderOrder = 0,
}) => {
  const lay = useMemo(() => layout(font, text, tracking), [font, text, tracking]);
  const mats = useMemo(() => ({
    face: new THREE.MeshBasicMaterial({toneMapped: false, transparent: true}),
    sides: new THREE.MeshStandardMaterial({roughness: 0.55, metalness: 0.05, transparent: true}),
    shade: new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, color: '#000000', depthWrite: false}),
  }), []);
  const planes = useMemo(() => [new THREE.Plane(), new THREE.Plane()], []);
  planes[0].set(new THREE.Vector3(0, 1, 0), -WIN[0]);
  planes[1].set(new THREE.Vector3(0, -1, 0), WIN[1]);
  planes.forEach((p) => p.applyMatrix4(matrix));
  mats.face.color.set(color);
  mats.face.opacity = opacity;
  mats.sides.color.set(side ?? color);
  mats.sides.opacity = opacity;
  mats.shade.opacity = shadow * opacity;
  for (const m of [mats.face, mats.sides, mats.shade]) {
    m.clippingPlanes = planes;
    m.clipShadows = true;
    m.depthWrite = m.opacity > 0.99 && m !== mats.shade;
  }
  if (opacity <= 0.002) return null;
  const shift = anchor === 'end' ? -lay.width : anchor === 'middle' ? -lay.width / 2 : 0;
  const lift = -(1 - rise) * (WIN[1] - WIN[0]);
  const draws = lay.glyphs.map((p) => ({g: p.glyph, x: p.x + shift, y: lift}));
  return (
    <group matrixAutoUpdate={false} matrix={matrix}>
      {shadow > 0
        ? draws.map((d, i) => (
            <mesh key={`s${i}`} geometry={glyphGeometry(font, d.g, 0)} material={mats.shade} position={[d.x + 0.035, d.y - 0.05, -0.002]} renderOrder={renderOrder} />
          ))
        : null}
      {draws.map((d, i) => (
        <mesh key={i} geometry={glyphGeometry(font, d.g, depth)} material={depth > 0 ? [mats.face, mats.sides] : mats.face} position={[d.x, d.y, 0]}
          castShadow={castShadow} renderOrder={renderOrder + 1} />
      ))}
    </group>
  );
};
