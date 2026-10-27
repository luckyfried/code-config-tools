// The person's place: a bright dot on the map with rings that pulse out from it, kept the same size on screen
// at any zoom.
import * as THREE from "three";

const vertexShader = `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;

const fragmentShader = `
uniform float uTime, uPaper, uPulse;
uniform vec3 cMarker, cEdge;
varying vec2 vUv;
void main() {
  float d = length(vUv - 0.5) * 2.0;
  float aa = fwidth(d) * 1.2;
  float core = 1.0 - smoothstep(0.13 - aa, 0.13 + aa, d);
  float rim = 1.0 - smoothstep(0.19 - aa, 0.19 + aa, d);
  float ring = 0.0;
  for (int i = 0; i < 2; i++) {
    float r = fract(uTime * 0.55 + float(i) * 0.5);
    float rr = 0.2 + r * 0.78;
    ring += (1.0 - smoothstep(0.0, aa * 1.5 + 0.018, abs(d - rr))) * (1.0 - r) * (1.0 - r) * uPulse;
  }
  float halo = exp(-d * d * 9.0) * 0.45 * (1.0 - uPaper);
  // a ring of the map's edge color sets the dot off the radar under it
  vec3 c = mix(cMarker, cEdge, rim - core);
  float alpha = max(max(ring * 0.9, halo), rim);
  gl_FragColor = vec4(c, alpha);
}`;

export function createMarker(tokens) {
  const uniforms = {
    uTime: { value: 0 },
    uPaper: { value: tokens.paper },
    uPulse: { value: 1 },
    cMarker: { value: tokens.marker.clone() },
    cEdge: { value: tokens.edge.clone() },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader,
    fragmentShader,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  const geometry = new THREE.PlaneGeometry(1, 1);
  geometry.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.renderOrder = 2;
  mesh.position.y = 0.0005;
  return {
    mesh,
    uniforms,
    setTokens(t) {
      uniforms.cMarker.value.copy(t.marker);
      uniforms.cEdge.value.copy(t.edge);
      uniforms.uPaper.value = t.paper;
    },
    // size: world units across for the marker's square at the current zoom
    update(time, size) {
      uniforms.uTime.value = time;
      mesh.scale.set(size, 1, size);
    },
  };
}
