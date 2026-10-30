// Flour in the air: a field of fine points drifting in front of the wall, lit by the colour of the field the camera
// is on and pushed aside by the blade as it passes; and a burst thrown off an edge as the blade crosses it. Every
// point's position is a function of the frame, worked out on the card. Both draw last, over everything the canvas holds,
// type included, so a mote is always in the air in front of the picture and never between a word and its card.
import {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import * as THREE from 'three';
import {useSys} from '../system';
import {finishOf} from './Stage';

/** The draw order of the flour: after everything a kit draws, with no depth test, so it lies over every card and every
 * word. The burst draws one above it. */
const ORDER = 100000;

const DISC = /* glsl */ `
varying float vAlpha;
uniform vec3 color;
uniform float opacity;
void main() {
  vec2 d = gl_PointCoord - 0.5;
  float r = length(d);
  float a = smoothstep(0.5, 0.15, r);
  gl_FragColor = vec4(color, a * vAlpha * opacity);
}
`;

const FIELD = /* glsl */ `
attribute vec4 seed;
uniform float time;
uniform vec3 boxMin;
uniform vec3 boxSize;
uniform float size;
uniform float height;
uniform vec3 sweep;
uniform vec2 sweepDir;
uniform float sweepAmt;
varying float vAlpha;
void main() {
  vec3 p = boxMin + seed.xyz * boxSize;
  float t = time;
  p.x += sin(t * 0.021 + seed.w * 40.0) * 34.0 + sin(t * 0.013 + seed.y * 21.0) * 22.0;
  p.y += cos(t * 0.017 + seed.x * 31.0) * 30.0 - t * (0.35 + 0.6 * seed.w);
  p.z += sin(t * 0.019 + seed.z * 25.0) * 24.0;
  p.y = boxMin.y + mod(p.y - boxMin.y, boxSize.y);
  vec2 d = p.xy - sweep.xy;
  float k = sweepAmt * exp(-dot(d, d) / (sweep.z * sweep.z));
  p.xy += sweepDir * k * sweep.z * 0.8;
  p.z += k * sweep.z * 0.5;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  float dist = -mv.z;
  gl_PointSize = min(22.0, size * (0.45 + seed.w) * height * projectionMatrix[1][1] * 0.5 / max(1.0, dist));
  vAlpha = (0.3 + 0.7 * fract(seed.w * 7.3)) * smoothstep(40.0, 260.0, dist);
}
`;

const BURST = /* glsl */ `
attribute vec4 seed;
uniform vec3 p0;
uniform vec3 p1;
uniform vec3 up;
uniform float age;
uniform float sweepLen;
uniform float reach;
uniform float size;
uniform float height;
varying float vAlpha;
void main() {
  float u = seed.x;
  float a = age - u * sweepLen;
  vec3 base = mix(p0, p1, u);
  float go = 1.0 - exp(-max(a, 0.0) * 3.2);
  vec3 along = normalize(p1 - p0);
  vec3 p = base + up * (seed.y * 0.9 + 0.1) * reach * go + along * (seed.z - 0.3) * reach * 0.7 * go
         + vec3(0.0, 0.0, 1.0) * seed.w * reach * 1.4 * go - up * a * a * reach * 0.12;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = min(18.0, size * (0.5 + seed.w) * height * projectionMatrix[1][1] * 0.5 / max(1.0, -mv.z));
  vAlpha = a < 0.0 ? 0.0 : (1.0 - smoothstep(0.4, 1.6, a)) * smoothstep(0.0, 0.05, a);
}
`;

const seeds = (n: number, k: number) => {
  const a = new Float32Array(n * 4);
  let x = 1234567 + k * 7919;
  for (let i = 0; i < a.length; i++) {
    x = (x * 1103515245 + 12345) & 0x7fffffff;
    a[i] = x / 0x7fffffff;
  }
  return a;
};

const pointsOf = (n: number, k: number, vertex: string, uniforms: Record<string, THREE.IUniform>) => {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  geo.setAttribute('seed', new THREE.BufferAttribute(seeds(n, k), 4));
  const mat = new THREE.ShaderMaterial({vertexShader: vertex, fragmentShader: DISC, uniforms, transparent: true, depthWrite: false, depthTest: false});
  const pts = new THREE.Points(geo, mat);
  pts.frustumCulled = false;
  return {pts, mat};
};

export type DustProps = {
  /** frames since the film began, held where the film holds still: from that frame the flour fades out over half a
   * second and is gone from the still */
  time: number;
  box: [[number, number, number], [number, number, number]];
  color: string;
  /** where the blade is (world x, y, and the radius it pushes in), which way it pushes, and how hard (0 to 1) */
  sweep: [number, number, number];
  sweepDir: [number, number];
  sweepAmt: number;
  height: number;
  count?: number;
  /** the flour's strength while the film moves: the style card's `dust` unless the kit names one; zero draws none. A
   * board without a card draws it at 0.85. */
  opacity?: number;
};

export const Dust: React.FC<DustProps> = ({time, box, color, sweep, sweepDir, sweepAmt, height, count = 5000, opacity}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const strength = opacity ?? finishOf(useSys().system)?.dust ?? 0.85;
  const d = useMemo(() => pointsOf(count, 1, FIELD, {
    time: {value: 0}, boxMin: {value: new THREE.Vector3()}, boxSize: {value: new THREE.Vector3()}, size: {value: 1.6}, height: {value: 1920},
    sweep: {value: new THREE.Vector3()}, sweepDir: {value: new THREE.Vector2()}, sweepAmt: {value: 0}, color: {value: new THREE.Color()}, opacity: {value: 0},
  }), [count]);
  const fade = Math.min(1, Math.max(0, 1 - (frame - time) / (fps / 2)));
  if (fade <= 0 || strength <= 0) return null;
  const u = d.mat.uniforms;
  u.opacity.value = strength * fade * fade * (3 - 2 * fade);
  u.time.value = time;
  u.boxMin.value.set(...box[0]);
  u.boxSize.value.set(box[1][0] - box[0][0], box[1][1] - box[0][1], box[1][2] - box[0][2]);
  u.height.value = height;
  u.sweep.value.set(...sweep);
  u.sweepDir.value.set(...sweepDir);
  u.sweepAmt.value = sweepAmt;
  (u.color.value as THREE.Color).set(color);
  d.pts.renderOrder = ORDER;
  return <primitive object={d.pts} />;
};

export type BurstProps = {
  seed: number;
  p0: THREE.Vector3;
  p1: THREE.Vector3;
  /** the direction the field lies in from the edge, in the wall's plane */
  up: THREE.Vector3;
  /** beats since the blade began to cross */
  age: number;
  sweepLen: number;
  reach: number;
  color: string;
  height: number;
  size: number;
  count?: number;
};

export const Burst: React.FC<BurstProps> = ({seed, p0, p1, up, age, sweepLen, reach, color, height, size, count = 900}) => {
  const b = useMemo(() => pointsOf(count, seed + 10, BURST, {
    p0: {value: new THREE.Vector3()}, p1: {value: new THREE.Vector3()}, up: {value: new THREE.Vector3()}, age: {value: 0}, sweepLen: {value: 0.25},
    reach: {value: 100}, size: {value: 2}, height: {value: 1920}, color: {value: new THREE.Color()}, opacity: {value: 1},
  }), [count, seed]);
  if (age < 0 || age > sweepLen + 1.8) return null;
  const u = b.mat.uniforms;
  u.p0.value.copy(p0);
  u.p1.value.copy(p1);
  u.up.value.copy(up);
  u.age.value = age;
  u.sweepLen.value = sweepLen;
  u.reach.value = reach;
  u.size.value = size;
  u.height.value = height;
  (u.color.value as THREE.Color).set(color);
  b.pts.renderOrder = ORDER + 1;
  return <primitive object={b.pts} />;
};
