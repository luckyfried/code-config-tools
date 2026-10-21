// The travel pass: the finishing pass that carries a camera move. `zoom` blurs along the rays from `center` (a push
// through depth), `smear` blurs along one direction in frame units (a lateral move), `warp` displaces the picture by a
// moving noise (the crosswarp between two worlds), `burn` lays a warm film burn from the left edge, `vignette`
// darkens the corners. All zero leaves the frame untouched.
import {Effect, EffectAttribute} from 'postprocessing';
import {Uniform, Vector2} from 'three';

export type Travel = {zoom: number; center: [number, number]; smear: [number, number]; warp: number; burn: number; vignette: number; time: number};

export const STILL: Travel = {zoom: 0, center: [0.5, 0.5], smear: [0, 0], warp: 0, burn: 0, vignette: 0, time: 0};

const frag = /* glsl */ `
uniform float zoom;
uniform vec2 center;
uniform vec2 smear;
uniform float warp;
uniform float burn;
uniform float vignette;
uniform float time;

// the lattice hash is exact integer arithmetic below 2^24, so a lattice point shared by two cells hashes the same in both
float perm(float x) { return mod((x * 34.0 + 1.0) * x, 289.0); }
float h21(vec2 i) { return perm(perm(mod(i.x, 289.0)) + mod(i.y, 289.0)) / 289.0; }
// gradient noise: a random direction at each lattice point, so its contours bend freely and never follow the lattice;
// centred and scaled so the burn covers the frame as much, and as brightly, as it is timed to
float grad(vec2 i, vec2 d) { float a = 6.2831853 * h21(i); return dot(vec2(cos(a), sin(a)), d); }
float gnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  float n = mix(mix(grad(i, f), grad(i + vec2(1.0, 0.0), f - vec2(1.0, 0.0)), u.x),
                mix(grad(i + vec2(0.0, 1.0), f - vec2(0.0, 1.0)), grad(i + vec2(1.0, 1.0), f - vec2(1.0, 1.0)), u.x), u.y);
  return 0.54 + 1.1 * n;
}
float fbm(vec2 p) { return 0.5 * gnoise(p) + 0.25 * gnoise(p * 2.03 + 7.1) + 0.125 * gnoise(p * 4.01 + 3.7); }

void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  vec2 p = uv;
  if (warp > 0.0) {
    vec2 q = vec2(fbm(uv * 3.0 + time * 0.9), fbm(uv * 3.0 - time * 0.7 + 5.2)) - 0.5;
    p += q * warp;
  }
  vec3 c;
  if (zoom > 1e-4 || dot(smear, smear) > 1e-8) {
    vec3 acc = vec3(0.0);
    float wsum = 0.0;
    for (int i = 0; i < 64; i++) {
      float t = float(i) / 63.0 - 0.5;
      float w = 1.0 - abs(t) * 1.2;
      vec2 o = smear * t + (p - center) * zoom * t;
      acc += texture2D(inputBuffer, clamp(p - o, 0.0, 1.0)).rgb * w;
      wsum += w;
    }
    c = acc / wsum;
  } else if (warp > 0.0) {
    c = texture2D(inputBuffer, clamp(p, 0.0, 1.0)).rgb;
  } else {
    c = inputColor.rgb;
  }
  if (burn > 0.0) {
    float b = fbm(vec2(uv.x * 1.6 - time * 0.35, uv.y * 2.4 + time * 0.2));
    float g = smoothstep(0.25, 0.85, b * 0.9 + (1.0 - uv.x) * 0.55 - (1.0 - burn) * 0.9);
    c += burn * g * vec3(1.0, 0.42, 0.1) * 1.4;
    c = mix(c, vec3(1.0, 0.88, 0.66), burn * g * g * 0.5);
  }
  if (vignette > 0.0) {
    vec2 d = (uv - 0.5) * vec2(1.0, 1.25);
    c *= 1.0 - vignette * smoothstep(0.25, 0.85, length(d));
  }
  outputColor = vec4(c, inputColor.a);
}
`;

export class TravelEffect extends Effect {
  constructor() {
    super('TravelEffect', frag, {
      attributes: EffectAttribute.CONVOLUTION,
      uniforms: new Map<string, Uniform>([
        ['zoom', new Uniform(0)],
        ['center', new Uniform(new Vector2(0.5, 0.5))],
        ['smear', new Uniform(new Vector2(0, 0))],
        ['warp', new Uniform(0)],
        ['burn', new Uniform(0)],
        ['vignette', new Uniform(0)],
        ['time', new Uniform(0)],
      ]),
    });
  }

  set(t: Travel) {
    const u = this.uniforms;
    u.get('zoom')!.value = t.zoom;
    (u.get('center')!.value as Vector2).set(t.center[0], t.center[1]);
    (u.get('smear')!.value as Vector2).set(t.smear[0], t.smear[1]);
    u.get('warp')!.value = t.warp;
    u.get('burn')!.value = t.burn;
    u.get('vignette')!.value = t.vignette;
    u.get('time')!.value = t.time;
  }
}
