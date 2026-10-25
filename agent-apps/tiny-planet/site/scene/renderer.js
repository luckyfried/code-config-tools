// The WebGL renderer: pixel ratio, color space, tone mapping, and the shadow map type.
import * as THREE from "three";

export function createRenderer(canvas, settings) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: settings.antialias,
    powerPreference: "high-performance",
    stencil: false,
  });
  renderer.setPixelRatio(settings.ratio);
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  return renderer;
}
