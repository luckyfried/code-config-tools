// The camera rig: behind and above the lighthouse looking out to sea, framed for a tall phone or a wide desktop,
// with a slow bob, a two-degree sway, and a shake on thunder, all still when the person asks for reduced motion.
import * as THREE from "three";

const PHONE = { pos: [3.5, 22, 26], look: [-1.5, -9, -44], fov: 62 };
const DESKTOP = { pos: [3, 19, 31], look: [-17, 4.5, -46], fov: 47 };

export function createRig(reducedMotion) {
  const camera = new THREE.PerspectiveCamera(50, 1, 0.5, 1000);
  const basePos = new THREE.Vector3();
  const look = new THREE.Vector3();
  const lookNow = new THREE.Vector3();
  let wide = true;
  const rig = {
    camera,
    wide: true,
    resize(width, height) {
      const aspect = width / height;
      wide = aspect >= 1;
      rig.wide = wide;
      const a = wide ? DESKTOP : PHONE;
      const t = THREE.MathUtils.clamp((aspect - 0.45) / 1.15, 0, 1);
      basePos.set(...a.pos);
      look.set(...a.look);
      camera.position.copy(basePos);
      camera.fov = wide ? a.fov - Math.min(6, (aspect - 1.6) * 6) : a.fov - t * 8;
      camera.aspect = aspect;
      camera.updateProjectionMatrix();
    },
    update(time, shake) {
      const still = reducedMotion.matches;
      camera.position.copy(basePos);
      lookNow.copy(look);
      if (!still) {
        camera.position.y += Math.sin(time * 0.42) * 0.35 + Math.sin(time * 0.23 + 1.3) * 0.2;
        camera.position.x += Math.sin(time * 0.17) * 0.4;
        if (shake > 0) {
          camera.position.x += Math.sin(time * 61) * shake * 0.25;
          camera.position.y += Math.sin(time * 47 + 2) * shake * 0.18;
        }
      }
      camera.lookAt(lookNow);
      if (!still) camera.rotateZ(THREE.MathUtils.degToRad(2) * Math.sin(time * 0.31));
    },
  };
  return rig;
}
