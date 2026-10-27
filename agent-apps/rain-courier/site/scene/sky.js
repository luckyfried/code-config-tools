// The sky dome: horizon haze lit by the city, low rain clouds drifting, lit from inside when thunder strikes.
import * as THREE from "three";

export function buildSky(shared) {
  const material = new THREE.ShaderMaterial({
    uniforms: shared,
    vertexShader: /* glsl */ `
      varying vec3 vDir;
      void main() {
        vDir = position;
        vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        gl_Position = p.xyww;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uSkyTop;
      uniform vec3 uSkyHorizon;
      uniform vec3 uCloud;
      uniform vec3 uFogFar;
      uniform vec3 uFogNear;
      uniform vec3 uFlashColor;
      uniform float uFlash;
      uniform float uTime;
      varying vec3 vDir;
      float h21(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
      float vnoise(vec2 p) {
        vec2 i = floor(p), f = fract(p);
        f = f * f * (3.0 - 2.0 * f);
        return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
      }
      float fbm(vec2 p) {
        float a = 0.5, s = 0.0;
        for (int i = 0; i < 4; i++) { s += a * vnoise(p); p = p * 2.03 + 11.7; a *= 0.5; }
        return s;
      }
      void main() {
        vec3 d = normalize(vDir);
        float t = d.y;
        vec3 col = mix(uSkyHorizon, uSkyTop, smoothstep(0.0, 0.55, t));
        // Cloud deck: projected onto a plane overhead, drifting with the wind.
        vec2 p = d.xz / max(t + 0.08, 0.04) * 1.4 + vec2(uTime * 0.012, uTime * 0.004);
        float c = fbm(p);
        float deck = smoothstep(0.35, 0.85, c) * smoothstep(-0.02, 0.25, t);
        vec3 under = mix(uCloud, uSkyHorizon, 0.45 * (1.0 - smoothstep(0.0, 0.4, t)));
        col = mix(col, under, deck * 0.75);
        // Thunder lights the clouds from within, brightest where they are thick.
        col += uFlashColor * uFlash * (0.25 + 0.9 * deck);
        // Toward the horizon the sky sinks into the far fog, so the city's edge never shows.
        col = mix(uFogFar, col, smoothstep(-0.05, 0.16, t));
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    side: THREE.BackSide,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(1000, 32, 16), material);
  mesh.name = "sky";
  mesh.renderOrder = -10;
  mesh.frustumCulled = false;
  mesh.onBeforeRender = (renderer, scene, camera) => mesh.position.copy(camera.position);
  return mesh;
}
