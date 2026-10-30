// The wall's ground: where the card lays its photographs full frame, the first month's photograph from the frame's top
// to its foot, softened and dimmed to the plan's `dim` of its light so the prints and the type stand off it; where the
// card stands them in a box or shows none, the card's photo ground, flat. The year is set into it from the first frame,
// each row's band laid over it as its month lands, and its foot under the sign-off.
import {useMemo} from 'react';
import * as THREE from 'three';
import type {Pt} from '../../system/three/motion';
import {coverUv} from './hook';
import {blurred, quad, setQuad} from './month';
import type {Month, Plan} from './plan';

export const Ground: React.FC<{plan: Plan; t: number; textures: (m: Month) => THREE.Texture}> = ({plan, textures}) => {
  const flat = plan.ground.flat ? (plan.colors[plan.ground.flat] ?? plan.colors.bg) : null;
  const q = useMemo(
    () => quad(flat ? new THREE.MeshBasicMaterial({color: flat, toneMapped: false}) : blurred(plan.dim, 0)),
    [plan.dim, flat],
  );
  const byId = (id: string) => plan.months.find((m) => m.id === id) ?? plan.months[0];
  const w = (p: Pt, z: number) => new THREE.Vector3(p[0] - plan.W / 2, plan.H / 2 - p[1], z);
  const m = byId(plan.ground.month);
  const [x0, y0, x1, y1] = plan.ground.box;
  const [a, b] = coverUv(m, x1 - x0, y1 - y0, 1);
  setQuad(q, [w([x0, y0], -1.5), w([x1, y0], -1.5), w([x1, y1], -1.5), w([x0, y1], -1.5)], [[a[0], a[1]], [b[0], a[1]], [b[0], b[1]], [a[0], b[1]]]);
  const mat = q.mesh.material as THREE.MeshBasicMaterial;
  if (!flat && mat.map !== textures(m)) {
    mat.map = textures(m);
    mat.needsUpdate = true;
  }
  q.mesh.renderOrder = -8;
  return <primitive object={q.mesh} />;
};
