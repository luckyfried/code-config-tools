// The sky dome: warm horizon to deep zenith, with the sun's disc and glow, following the camera.
import { BackSide, Mesh, ShaderMaterial, SphereGeometry, Vector3 } from "three";

export function createSky(tokens) {
  const material = new ShaderMaterial({
    side: BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      top: { value: tokens.skyTop.clone() },
      mid: { value: tokens.skyMid.clone() },
      horizon: { value: tokens.horizon.clone() },
      sun: { value: tokens.sun.clone() },
      sunDir: { value: tokens.sunDir.clone() },
      ground: { value: tokens.fog.clone() },
    },
    vertexShader: /* glsl */ `
      varying vec3 vDir;
      void main() {
        vDir = normalize(position);
        vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        gl_Position = p.xyww;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 top;
      uniform vec3 mid;
      uniform vec3 horizon;
      uniform vec3 sun;
      uniform vec3 sunDir;
      uniform vec3 ground;
      varying vec3 vDir;
      void main() {
        vec3 d = normalize(vDir);
        float h = d.y;
        vec3 col = mix(horizon, mid, smoothstep(0.0, 0.28, h));
        col = mix(col, top, smoothstep(0.22, 0.95, h));
        col = mix(col, ground, smoothstep(0.0, -0.18, h));
        float s = max(dot(d, normalize(sunDir)), 0.0);
        col += sun * (pow(s, 900.0) * 6.0 + pow(s, 40.0) * 0.35 + pow(s, 6.0) * 0.12);
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
  const mesh = new Mesh(new SphereGeometry(1000, 48, 24), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1;
  return {
    mesh,
    follow(camera) {
      mesh.position.copy(camera.position);
    },
    apply(t) {
      material.uniforms.top.value.copy(t.skyTop);
      material.uniforms.mid.value.copy(t.skyMid);
      material.uniforms.horizon.value.copy(t.horizon);
      material.uniforms.sun.value.copy(t.sun);
      material.uniforms.sunDir.value.copy(t.sunDir);
      material.uniforms.ground.value.copy(t.fog);
    },
  };
}

export const skyDirection = (tokens) => new Vector3().copy(tokens.sunDir);
