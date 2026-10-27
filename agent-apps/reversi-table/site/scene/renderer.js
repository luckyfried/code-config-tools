// The WebGL renderer: pixel ratio, color space, tone mapping, and soft shadows.
import { WebGLRenderer, SRGBColorSpace, NeutralToneMapping, PCFSoftShadowMap } from "three";

export function createRenderer(host, settings) {
  const renderer = new WebGLRenderer({ antialias: true, powerPreference: "high-performance", alpha: false });
  renderer.setPixelRatio(settings.pixelRatio);
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = NeutralToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  host.appendChild(renderer.domElement);
  return renderer;
}
