// Shared shader text: value noise with fbm, and the funnel's shape. The funnel, its debris, its dust, and the props
// that orbit it all read the same shape, and funnel.js mirrors it in JavaScript so a lifted cow rides the same spiral.

export const NOISE = /* glsl */ `
float tt_hash(vec3 p) {
  p = fract(p * 0.1031);
  p += dot(p, p.zyx + 31.32);
  return fract((p.x + p.y) * p.z);
}
float tt_noise(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(mix(tt_hash(i), tt_hash(i + vec3(1.0, 0.0, 0.0)), f.x),
        mix(tt_hash(i + vec3(0.0, 1.0, 0.0)), tt_hash(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
    mix(mix(tt_hash(i + vec3(0.0, 0.0, 1.0)), tt_hash(i + vec3(1.0, 0.0, 1.0)), f.x),
        mix(tt_hash(i + vec3(0.0, 1.0, 1.0)), tt_hash(i + vec3(1.0, 1.0, 1.0)), f.x), f.y),
    f.z);
}
float tt_fbm(vec3 p) {
  float sum = 0.0;
  float amp = 0.5;
  for (int i = 0; i < 4; i++) {
    sum += amp * tt_noise(p);
    p = p * 2.03 + vec3(1.7, 9.2, 3.1);
    amp *= 0.5;
  }
  return sum;
}
`;

export const FUNNEL_SHAPE = /* glsl */ `
uniform vec3 uFunnelPos;
uniform float uHeight;
uniform float uRBottom;
uniform float uRTop;
uniform float uSway;
uniform vec2 uLean;
uniform float uTime;
vec3 funnelAxis(float h) {
  float lean = h * h * uHeight * 0.35;
  return uFunnelPos + vec3(
    uLean.x * lean + sin(h * 3.1 + uTime * 0.8) * uSway * h,
    h * uHeight,
    uLean.y * lean + cos(h * 2.3 + uTime * 0.63) * uSway * h);
}
float funnelRadius(float h) {
  return mix(uRBottom, uRTop, pow(h, 1.8));
}
`;

export const ROTATE = /* glsl */ `
vec3 tt_rotate(vec3 v, vec3 axis, float angle) {
  float c = cos(angle);
  float s = sin(angle);
  return v * c + cross(axis, v) * s + axis * dot(axis, v) * (1.0 - c);
}
`;
