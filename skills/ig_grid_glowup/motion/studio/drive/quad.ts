// A four-cornered mesh the film moves corner by corner: a post, a strip of a photograph, a cell of the wall.
import * as THREE from 'three';
import type {Pt} from '../../system/three/motion';

export type Quad = {mesh: THREE.Mesh; geo: THREE.BufferGeometry};

export const quad = (mat: THREE.Material): Quad => {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(12), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(8), 2));
  geo.setIndex([0, 3, 1, 1, 3, 2]);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  return {mesh, geo};
};

/** Sets a quad's corners (world; top left, top right, bottom right, bottom left) and their texture coordinates. */
export const setQuad = (q: Quad, pts: THREE.Vector3[], uvs: Pt[]) => {
  const pos = q.geo.getAttribute('position') as THREE.BufferAttribute;
  const uv = q.geo.getAttribute('uv') as THREE.BufferAttribute;
  pts.forEach((p, i) => pos.setXYZ(i, p.x, p.y, p.z));
  uvs.forEach((u, i) => uv.setXY(i, u[0], u[1]));
  pos.needsUpdate = true;
  uv.needsUpdate = true;
  q.geo.computeBoundingSphere();
};

/** The corners of a box [x, y, w, h] in px, top left first, clockwise. */
export const cornersOf = (b: [number, number, number, number]): Pt[] => [[b[0], b[1]], [b[0] + b[2], b[1]], [b[0] + b[2], b[1] + b[3]], [b[0], b[1] + b[3]]];

/** The texture coordinates of a uv rect [u0, v0, u1, v1] at the same corners. */
export const uvCorners = (uv: [number, number, number, number]): Pt[] => [[uv[0], uv[3]], [uv[2], uv[3]], [uv[2], uv[1]], [uv[0], uv[1]]];

/** Unit texture coordinates at a quad's corners, for a pass drawn over the whole of it. */
export const UNIT: Pt[] = [[0, 1], [1, 1], [1, 0], [0, 0]];

/**
 * The light wrap: the key light (`light`, the card's light color) bleeding over the cut edges of a card, drawn additively over the card at the
 * same corners with UNIT coordinates. It runs `edge` of the card's width and height in from each side, strongest on
 * the top and left edges, which face the light.
 */
export const rimMaterial = (light: string) =>
  new THREE.ShaderMaterial({
    uniforms: {amount: {value: 0}, edge: {value: new THREE.Vector2(0.05, 0.04)}, color: {value: new THREE.Color(light)}},
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform float amount;
      uniform vec2 edge;
      uniform vec3 color;
      varying vec2 vUv;
      float near(float d) { return 1.0 - smoothstep(0.0, 1.0, d); }
      void main() {
        float lit = max(near(vUv.x / edge.x), near((1.0 - vUv.y) / edge.y));
        float shade = max(near((1.0 - vUv.x) / edge.x), near(vUv.y / edge.y));
        gl_FragColor = vec4(color, amount * max(lit, 0.5 * shade));
      }`,
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false,
  });

/** Sets a rim quad over a card's corners: its amount, and an edge `px` px wide on a card `w` by `h` px. */
export const setRim = (q: Quad, pts: THREE.Vector3[], amount: number, px: number, w: number, h: number) => {
  const m = q.mesh.material as THREE.ShaderMaterial;
  m.uniforms.amount.value = amount;
  m.uniforms.edge.value.set(px / Math.max(1, w), px / Math.max(1, h));
  setQuad(q, pts, UNIT);
  q.mesh.visible = amount > 0.002;
};
