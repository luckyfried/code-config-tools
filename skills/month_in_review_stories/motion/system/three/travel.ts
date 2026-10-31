// The finishing pass: what the camera and the lab do to a frame once the scene is drawn. `zoom` blurs along the rays
// from `center` (a push through depth), `smear` blurs along one direction in frame units (a lateral move, as long as
// the move and the style's blur make it), `warp` displaces the picture by a moving noise (the crosswarp between two
// worlds), `burn` lays a film burn from the left edge in the style's burn color. Then the film's
// finish, the same on every frame: its one grade (lift, gamma, gain, saturation, in display values; IDENTITY leaves the
// picture as it is), one vignette ramp toward the corners outside the type area, and grain over the whole frame.
import {Effect, EffectAttribute} from 'postprocessing';
import {Uniform, Vector2, Vector3} from 'three';

/** `vignette` is the kit's ask for the vignette on this frame; the finish's vignette is never less than it. */
export type Travel = {zoom: number; center: [number, number]; smear: [number, number]; warp: number; burn?: number; vignette: number; time: number};

export const STILL: Travel = {zoom: 0, center: [0.5, 0.5], smear: [0, 0], warp: 0, burn: 0, vignette: 0, time: 0};

/** A grade in display values: the blacks lifted to `lift`, the whites brought to `gain`, the mids bent by `gamma`, then
 * the saturation. Lift and gain carry color, so the shadows and the highlights each lean toward their own hue. */
export type Grade = {lift: [number, number, number]; gamma: number; gain: [number, number, number]; saturation: number};

export const IDENTITY: Grade = {lift: [0, 0, 0], gamma: 1, gain: [1, 1, 1], saturation: 1};

/** The finish's vignette and grain strengths, and the place this frame's grain is drawn from (`shift`, in pixels). */
export type Finish = {vignette: number; grain: number; shift: [number, number]};

const frag = /* glsl */ `
uniform float zoom;
uniform vec2 center;
uniform vec2 smear;
uniform float warp;
uniform float burn;
uniform vec3 burnHot;
uniform vec3 burnCore;
uniform float vignette;
uniform float time;
uniform vec3 lift;
uniform float gamma;
uniform vec3 gain;
uniform float saturation;
uniform float grain;
uniform vec2 shift;

const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);

// the lattice hash is exact integer arithmetic below 2^24, so a lattice point shared by two cells hashes the same in both
float perm(float x) { return mod((x * 34.0 + 1.0) * x, 289.0); }
float h21(vec2 i) { return perm(perm(mod(i.x, 289.0)) + mod(i.y, 289.0)) / 289.0; }
// gradient noise: a random direction at each lattice point, so its contours bend freely and never follow the lattice;
// centered and scaled so the burn covers the frame as much, and as brightly, as it is timed to
float grad(vec2 i, vec2 d) { float a = 6.2831853 * h21(i); return dot(vec2(cos(a), sin(a)), d); }
float gnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  float n = mix(mix(grad(i, f), grad(i + vec2(1.0, 0.0), f - vec2(1.0, 0.0)), u.x),
                mix(grad(i + vec2(0.0, 1.0), f - vec2(0.0, 1.0)), grad(i + vec2(1.0, 1.0), f - vec2(1.0, 1.0)), u.x), u.y);
  return 0.54 + 1.1 * n;
}
float fbm(vec2 p) { return 0.5 * gnoise(p) + 0.25 * gnoise(p * 2.03 + 7.1) + 0.125 * gnoise(p * 4.01 + 3.7); }
// a value in [0, 1) for a pixel, with no pattern a viewer can find
float h12(vec2 p) {
  vec3 q = fract(vec3(p.xyx) * 0.1031);
  q += dot(q, q.yzx + 33.33);
  return fract((q.x + q.y) * q.z);
}

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
    // one tap a pixel along this pixel's blur, at most 64: a short blur costs a few taps, a long one the full 64
    float n = clamp(ceil(length((smear + (p - center) * zoom) / texelSize)) + 1.0, 1.0, 64.0);
    for (int i = 0; i < 64; i++) {
      if (float(i) >= n) break;
      float t = n < 1.5 ? 0.0 : float(i) / (n - 1.0) - 0.5;
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
    c += burn * g * burnHot * 1.4;
    c = mix(c, burnCore, burn * g * g * 0.5);
  }

  // the finish, in display values: the frame's linear light is encoded, finished and decoded again
  vec3 g = pow(max(c, 0.0), vec3(1.0 / 2.2));
  g = lift + (gain - lift) * g;
  g = pow(max(g, 0.0), vec3(1.0 / gamma));
  g = mix(vec3(dot(g, LUMA)), g, saturation);
  // the vignette: nothing inside 0.45 of the way from the centre to a corner, so no line of type is darkened, then a
  // smoothstep to the vignette strength at the corners
  g *= 1.0 - vignette * smoothstep(0.45, 1.0, length(uv - 0.5) * 1.41421356);
  // the grain: one gray value a pixel around mid gray with a deviation of 0.18 (the mean of three, spread), drawn from
  // a new place on every frame and laid over the picture as an overlay at the grain strength, so it lives in the mid
  // tones and leaves black and white nearly as they are
  vec2 px = floor(uv * resolution) + shift;
  float n = 0.5 + 1.08 * ((h12(px) + h12(px + vec2(4099.0, 0.0)) + h12(px + vec2(0.0, 4099.0))) / 3.0 - 0.5);
  g = clamp(g, 0.0, 1.0);
  vec3 over = mix(2.0 * g * n, 1.0 - 2.0 * (1.0 - g) * (1.0 - n), step(0.5, g));
  g = mix(g, over, grain);
  c = pow(g, vec3(2.2));

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
        ['burnHot', new Uniform(new Vector3(1.0, 0.42, 0.1))],
        ['burnCore', new Uniform(new Vector3(1.0, 0.88, 0.66))],
        ['vignette', new Uniform(0)],
        ['time', new Uniform(0)],
        ['lift', new Uniform(new Vector3(0, 0, 0))],
        ['gamma', new Uniform(1)],
        ['gain', new Uniform(new Vector3(1, 1, 1))],
        ['saturation', new Uniform(1)],
        ['grain', new Uniform(0)],
        ['shift', new Uniform(new Vector2(0, 0))],
      ]),
    });
  }

  set(t: Travel) {
    const u = this.uniforms;
    u.get('zoom')!.value = t.zoom;
    (u.get('center')!.value as Vector2).set(t.center[0], t.center[1]);
    (u.get('smear')!.value as Vector2).set(t.smear[0], t.smear[1]);
    u.get('warp')!.value = t.warp;
    u.get('burn')!.value = t.burn ?? 0;
    u.get('time')!.value = t.time;
  }

  /** The burn's color (a hex): its hot edge as given, its core the same color most of the way to white. */
  burnColor(hex: string) {
    const n = parseInt(hex.slice(1), 16);
    const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => v / 255) as [number, number, number];
    (this.uniforms.get('burnHot')!.value as Vector3).set(...c);
    (this.uniforms.get('burnCore')!.value as Vector3).set(...(c.map((v) => v + (1 - v) * 0.7) as [number, number, number]));
  }

  grade(g: Grade) {
    const u = this.uniforms;
    (u.get('lift')!.value as Vector3).set(...g.lift);
    u.get('gamma')!.value = g.gamma;
    (u.get('gain')!.value as Vector3).set(...g.gain);
    u.get('saturation')!.value = g.saturation;
  }

  finish(f: Finish) {
    const u = this.uniforms;
    u.get('vignette')!.value = f.vignette;
    u.get('grain')!.value = f.grain;
    (u.get('shift')!.value as Vector2).set(f.shift[0], f.shift[1]);
  }
}
