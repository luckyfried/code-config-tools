// The camera rig: tilted 60 degrees from straight down, looking north at the place, framed into the space the
// top bar and the dock leave free. Drag pans, the wheel and a pinch zoom.
import * as THREE from "three";

const PITCH = (60 * Math.PI) / 180;
const HALF_FOV = Math.tan(((36 / 2) * Math.PI) / 180);
const FAR_EDGE = 0.9; // world units from the place to where the map's far side is fully drawn

export function createCamera() {
  const camera = new THREE.PerspectiveCamera(36, 1, 0.01, 60);
  const target = new THREE.Vector3();
  const rig = { camera, target, zoom: 1, base: 1.5, intro: 0, width: 1, height: 1 };
  const ray = new THREE.Raycaster();
  const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const hit = new THREE.Vector3();

  rig.distance = () => rig.base * rig.zoom * (1 + 0.28 * rig.intro * rig.intro);

  rig.update = () => {
    const d = rig.distance();
    camera.position.set(target.x, target.y + d * Math.cos(PITCH), target.z + d * Math.sin(PITCH));
    camera.lookAt(target);
    camera.updateMatrixWorld();
  };

  // top and bottom: the pixels the top bar and the dock cover
  rig.resize = (w, h, top, bottom) => {
    rig.width = w;
    rig.height = h;
    camera.aspect = w / h;
    const across = w < h ? 1.25 : 1.75; // world units across the middle of the view
    const freeMiddle = (top + (h - bottom)) / 2;
    // no closer to the far side than the map reaches: its far edge stays at or above the top bar
    const up = PITCH + Math.atan(((freeMiddle - top) / (h / 2)) * HALF_FOV);
    const room = Math.tan(up) * Math.cos(PITCH) - Math.sin(PITCH);
    const fit = room > 0 ? FAR_EDGE / room : Infinity;
    rig.base = Math.min(3.6, fit, across / (2 * HALF_FOV * camera.aspect));
    camera.setViewOffset(w, h, 0, h / 2 - freeMiddle, w, h);
    camera.updateProjectionMatrix();
    rig.update();
  };

  // world units per screen pixel at the target
  rig.unitsPerPixel = () => (2 * HALF_FOV * rig.distance()) / rig.height;

  rig.pan = (dx, dy) => {
    const k = rig.unitsPerPixel();
    target.x = Math.max(-0.75, Math.min(0.75, target.x - dx * k));
    target.z = Math.max(-0.75, Math.min(0.75, target.z - (dy * k) / Math.cos(PITCH)));
    rig.update();
  };

  rig.zoomBy = (factor) => {
    rig.zoom = Math.max(0.45, Math.min(1.8, rig.zoom * factor));
    rig.update();
  };

  // The map square in uv (0 to 1, x east, y south) that the screen shows, for spawning wind where it is seen.
  rig.visibleBox = () => {
    let x0 = 1;
    let y0 = 1;
    let x1 = 0;
    let y1 = 0;
    for (const [nx, ny] of [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, 1]]) {
      ray.setFromCamera({ x: nx, y: ny }, camera);
      if (!ray.ray.intersectPlane(ground, hit)) continue;
      const u = hit.x * 0.5 + 0.5;
      const v = hit.z * 0.5 + 0.5;
      x0 = Math.min(x0, u);
      x1 = Math.max(x1, u);
      y0 = Math.min(y0, v);
      y1 = Math.max(y1, v);
    }
    const pad = 0.04;
    return { x0: Math.max(0, x0 - pad), y0: Math.max(0, y0 - pad), x1: Math.min(1, x1 + pad), y1: Math.min(1, y1 + pad) };
  };

  rig.project = (v) => {
    const p = v.clone().project(camera);
    return { x: (p.x * 0.5 + 0.5) * rig.width, y: (-p.y * 0.5 + 0.5) * rig.height, behind: p.z > 1 };
  };

  return rig;
}
