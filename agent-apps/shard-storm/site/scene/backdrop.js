// The far plane behind the play field: gradient light, a scrolling grid, and rings around the storm's eye.
import * as THREE from "three";
import { backdropMaterial } from "./materials.js";

export const BACKDROP_Z = -70;

export function createBackdrop(mode, tokens) {
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), backdropMaterial(mode, tokens));
  mesh.position.z = BACKDROP_Z;
  mesh.renderOrder = -10;
  mesh.frustumCulled = false;
  return {
    mesh,
    /** Covers the view at its depth with room for the drift and the dolly. */
    fit(W, H, distance) {
      const grow = (distance - BACKDROP_Z) / distance;
      mesh.scale.set(W * 2 * grow * 1.3, H * 2 * grow * 1.3, 1);
      mesh.material.uniforms.uSpan.value = Math.max(W, H) * grow;
    },
    setEye(x, y, distance) {
      const grow = (distance - BACKDROP_Z) / distance;
      mesh.material.uniforms.uEye.value.set(x * grow, y * grow);
    },
    setLook(mode, tokens) {
      mesh.material.dispose();
      mesh.material = backdropMaterial(mode, tokens);
    },
  };
}
