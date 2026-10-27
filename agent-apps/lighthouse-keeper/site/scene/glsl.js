// Shared shader code: hash noise and the four Gerstner waves the sea and the ships both follow.
export const NOISE = /* glsl */ `
float lkHash(vec3 p) {
  p = fract(p * 0.3183099 + 0.1);
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float lkNoise(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(lkHash(i + vec3(0, 0, 0)), lkHash(i + vec3(1, 0, 0)), f.x),
                 mix(lkHash(i + vec3(0, 1, 0)), lkHash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(lkHash(i + vec3(0, 0, 1)), lkHash(i + vec3(1, 0, 1)), f.x),
                 mix(lkHash(i + vec3(0, 1, 1)), lkHash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
float lkFbm(vec3 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) {
    v += a * lkNoise(p);
    p = p * 2.03 + vec3(1.7, 9.2, 3.1);
    a *= 0.5;
  }
  return v;
}
`;

// Beam lighting for points in the air: 1 on the beam's axis, falling to 0 at its edge, fading with distance.
export const BEAM_LIGHT = /* glsl */ `
uniform vec3 uLamp;
uniform vec3 uBeamDir;
uniform float uBeamTan;
uniform float uBeamOn;
float beamLight(vec3 p, float widen) {
  vec3 v = p - uLamp;
  float along = dot(v, uBeamDir);
  if (along <= 0.0) return 0.0;
  float perp = length(v - uBeamDir * along);
  float radius = 0.5 + along * uBeamTan * widen;
  return (1.0 - smoothstep(radius * 0.25, radius, perp)) * exp(-along * 0.011) * uBeamOn;
}
`;

// Wave rows: direction x, direction z, steepness, wavelength.
export const WAVES = [
  [0.82, -0.57, 0.17, 38],
  [-0.35, -0.94, 0.13, 21],
  [0.97, 0.24, 0.1, 12.5],
  [-0.62, 0.78, 0.07, 7.2],
];

export const GERSTNER = /* glsl */ `
uniform vec4 uWaves[4];
uniform float uRough;
uniform float uGridStep;
vec3 gerstner(vec2 p, float t, out vec3 normal, out float crest) {
  float ring = pow(length(p) / 700.0, 0.4545);
  float spacing = uGridStep * pow(max(ring, 0.001), 1.2);
  vec3 offset = vec3(0.0);
  vec3 tangent = vec3(1.0, 0.0, 0.0);
  vec3 binormal = vec3(0.0, 0.0, 1.0);
  crest = 0.0;
  float total = 0.0;
  for (int i = 0; i < 4; i++) {
    vec4 w = uWaves[i];
    vec2 d = normalize(w.xy);
    float steep = w.z * uRough * (1.0 - smoothstep(w.w * 0.18, w.w * 0.32, spacing));
    float k = 6.2831853 / w.w;
    float c = sqrt(9.8 / k);
    float f = k * (dot(d, p) - c * t);
    float a = steep / k;
    float s = sin(f);
    float co = cos(f);
    offset += vec3(d.x * a * co, a * s, d.y * a * co);
    tangent += vec3(-d.x * d.x * steep * s, d.x * steep * co, -d.x * d.y * steep * s);
    binormal += vec3(-d.x * d.y * steep * s, d.y * steep * co, -d.y * d.y * steep * s);
    crest += steep * s;
    total += steep;
  }
  normal = normalize(cross(binormal, tangent));
  crest /= max(total, 0.001);
  return offset;
}
`;

// The same waves on the CPU, heights only, so a ship rides the swell it sits on.
export function waveHeight(x, z, t, rough) {
  let y = 0;
  for (const [dx, dz, steepness, length] of WAVES) {
    const n = Math.hypot(dx, dz);
    const k = (Math.PI * 2) / length;
    const c = Math.sqrt(9.8 / k);
    const steep = steepness * rough;
    y += (steep / k) * Math.sin(k * ((dx / n) * x + (dz / n) * z - c * t));
  }
  return y;
}
