// The WebGL renderer: pixel ratio by tier, sRGB output, filmic tone mapping, soft shadows.
import { ACESFilmicToneMapping, PCFSoftShadowMap, SRGBColorSpace, WebGLRenderer } from "three";

export function createRenderer(canvas, tier, exposure) {
  const renderer = new WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, tier.pixelRatio));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = exposure;
  renderer.shadowMap.enabled = tier.shadows;
  renderer.shadowMap.type = PCFSoftShadowMap;
  return renderer;
}
