// The wall: the profile's grid of 3:4 cells, their posts at their slots, and each new post from the moment it seats.
// Every arrival steps every older post one place along at once, slot 0 first in line: across the row, and at a row's
// end off the wall's right side while the same post comes in from the left side of the row below, so the wall stays
// whole while it moves. Every cell carries the light wrap on its cut edges, brighter while it is lifted. Their posts
// stand muted toward a print of themselves in the card's light, so the new ones carry the film's color and no cold
// outlier of the old grid shows through.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span} from '../../system/three/motion';
import {cellBox, toWorld, type Box, type Cell, type Plan} from './plan';
import {cornersOf, quad, rimMaterial, setQuad, setRim, uvCorners, type Quad} from './quad';

/** The curve every step along the wall moves on, the card's move curve; a cell that slides in along the row moves on it too. */
export const reflowOf = (plan: Plan) => plan.ease.move;

/** Where a cell is at beat `t`: its slot as a continuous number, and how far off the wall its step lifts it. */
export const slotAt = (plan: Plan, c: Cell, t: number) => {
  let slot = c.slot;
  let lift = 0;
  const ease = bezier(reflowOf(plan));
  for (const [r0, len] of plan.reflows) {
    if (r0 <= c.from) continue;
    const u = ease(clamp01((t - r0) / len));
    if (u <= 0) break;
    slot = Math.floor(slot) + u;
    lift = Math.sin(Math.PI * u) * 18;
    if (u < 1) break;
    lift = 0;
  }
  return {slot, lift};
};

/** The boxes of a continuous slot: between the two cells it moves between along a row, or, between a row's end and
 * the next row's start, the part leaving past the right side and the part coming in from the left side. */
const boxesAt = (plan: Plan, slot: number): Box[] => {
  const j = Math.floor(slot);
  const u = slot - j;
  const a = cellBox(plan.grid, j), b = cellBox(plan.grid, j + 1);
  if (u === 0) return [a];
  if (j % plan.grid.cols !== plan.grid.cols - 1) return [[lerp(a[0], b[0], u), a[1], a[2], a[3]]];
  const step = plan.grid.cw + plan.grid.g;
  return [[a[0] + step * u, a[1], a[2], a[3]], [b[0] - step * (1 - u), b[1], b[2], b[3]]];
};

/** A cell's picture, taken `mute` of the way toward its own gray in the card's light (`light`, its burn). */
const cellMaterial = (texture: THREE.Texture, mute: number, light: string) => {
  const m = new THREE.MeshBasicMaterial({map: texture, toneMapped: false});
  if (mute > 0) {
    const c = new THREE.Color(light);
    const y = Math.max(0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b, 1e-3);
    const tint = [c.r / y, c.g / y, c.b / y].map((v) => v.toFixed(4)).join(', ');
    m.onBeforeCompile = (s) => {
      s.fragmentShader = s.fragmentShader.replace('#include <map_fragment>',
        `#include <map_fragment>\n  diffuseColor.rgb = mix(diffuseColor.rgb, min(vec3(dot(diffuseColor.rgb, vec3(0.2126, 0.7152, 0.0722))) * vec3(${tint}), vec3(1.0)), ${mute.toFixed(3)});`);
    };
    m.customProgramCacheKey = () => `mute-${mute.toFixed(3)}-${light}`;
  }
  return m;
};

const CellView: React.FC<{plan: Plan; cell: Cell; t: number; texture: THREE.Texture}> = ({plan, cell, t, texture}) => {
  const parts = useMemo(() => [0, 1].map(() => ({q: quad(cellMaterial(texture, cell.mute ?? 0, plan.light)), rim: quad(rimMaterial(plan.light))})), [texture, cell.mute, plan.light]);
  if (t < cell.from) return null;
  const {slot, lift} = slotAt(plan, cell, t);
  const boxes = boxesAt(plan, slot);
  const draw = ({q, rim}: {q: Quad; rim: Quad}, box: Box) => {
    const pts = cornersOf(box).map((p) => new THREE.Vector3(...toWorld(plan, p, lift)));
    setQuad(q, pts, uvCorners(cell.uv));
    q.mesh.castShadow = lift > 2;
    q.mesh.renderOrder = lift > 0.5 ? 2 : 1;
    setRim(rim, pts.map((v) => v.clone().setZ(v.z + 0.6)), 0.14 + 0.2 * clamp01(lift / 40), 0.05 * Math.min(box[2], box[3]), box[2], box[3]);
    rim.mesh.renderOrder = 3;
    return (
      <group key={q.mesh.uuid}>
        <primitive object={q.mesh} />
        <primitive object={rim.mesh} />
      </group>
    );
  };
  return <group>{boxes.map((box, i) => draw(parts[i], box))}</group>;
};

export const Wall: React.FC<{plan: Plan; t: number; textureOf: (file: string) => THREE.Texture}> = ({plan, t, textureOf}) => (
  <group>
    {plan.cells.map((c) => <CellView key={c.key} plan={plan} cell={c} t={t} texture={textureOf(c.file)} />)}
  </group>
);

/** How much of a reflow's steps are under way at beat `t`, for the dust it raises. */
export const reflowAt = (plan: Plan, t: number) => Math.max(0, ...plan.reflows.map(([r0, len]) => span(t, r0, len, (u) => Math.sin(Math.PI * u))));
