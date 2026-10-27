// Streetlights as point sprites in rows with their poles, aviation lights on the tall roofs, and traffic as moving
// pairs of lights along the streets.
import * as THREE from "three";
import { FOG_GLSL } from "./palette.js";
import { PITCH } from "../game/gen.js";

const LAMP_HEIGHT = 7.2;
const ARM = 1.8;

const POINT_VERTEX = /* glsl */ `
  attribute float aSize;
  attribute vec3 aColor;
  attribute float aBlink;
  uniform float uScale;
  uniform float uTime;
  varying vec3 vColor;
  varying vec3 vWorld;
  varying float vOn;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorld = world.xyz;
    vColor = aColor;
    vOn = aBlink < 0.0 ? 1.0 : step(0.55, fract(uTime * 0.8 + aBlink));
    vec4 mv = viewMatrix * world;
    gl_Position = projectionMatrix * mv;
    gl_PointSize = clamp(aSize * uScale / -mv.z, 1.5, 96.0) * vOn;
  }
`;
const POINT_FRAGMENT = /* glsl */ `
  varying vec3 vColor;
  varying vec3 vWorld;
  varying float vOn;
  uniform float uGlow;
  ${FOG_GLSL}
  void main() {
    vec2 c = gl_PointCoord * 2.0 - 1.0;
    float r = dot(c, c);
    if (r > 1.0) discard;
    float core = exp(-r * 14.0);
    float halo = exp(-r * 3.5) * 0.35;
    vec3 color = vColor * (core * 3.2 + halo) * mix(0.7, 1.0, uGlow);
    vec3 fogged = applyFog(color, vWorld, cameraPosition);
    color = mix(fogged, color, 0.45);
    gl_FragColor = vec4(color, (core + halo));
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

function pointMaterial(shared, scale) {
  return new THREE.ShaderMaterial({
    uniforms: { ...shared, uScale: { value: scale } },
    vertexShader: POINT_VERTEX,
    fragmentShader: POINT_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}

export function buildLamps(plan, shared, pixelScale) {
  const group = new THREE.Group();
  group.name = "lamps";
  const lamps = plan.lamps;

  // Heads: one point each, warm, plus the red aviation lights blinking on the spires.
  const count = lamps.length + plan.aviation.length;
  const pos = new Float32Array(count * 3);
  const size = new Float32Array(count);
  const color = new Float32Array(count * 3);
  const blink = new Float32Array(count);
  lamps.forEach((l, i) => {
    pos.set([l.x + l.ax * ARM, LAMP_HEIGHT, l.z + l.az * ARM], i * 3);
    size[i] = 2.6;
    blink[i] = -1;
  });
  plan.aviation.forEach((a, k) => {
    const i = lamps.length + k;
    pos.set([a.x, a.y, a.z], i * 3);
    size[i] = 3.2;
    blink[i] = (k * 0.37) % 1;
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geometry.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
  geometry.setAttribute("aColor", new THREE.BufferAttribute(color, 3));
  geometry.setAttribute("aBlink", new THREE.BufferAttribute(blink, 1));
  const heads = new THREE.Points(geometry, pointMaterial(shared, pixelScale));
  heads.frustumCulled = false;
  heads.renderOrder = 3;
  group.add(heads);

  // Poles: a post and an arm, one instanced mesh.
  const post = new THREE.BoxGeometry(0.22, LAMP_HEIGHT, 0.22).translate(0, LAMP_HEIGHT / 2, 0);
  const arm = new THREE.BoxGeometry(ARM + 0.3, 0.16, 0.18).translate(ARM / 2, LAMP_HEIGHT - 0.05, 0);
  const hood = new THREE.BoxGeometry(0.7, 0.18, 0.4).translate(ARM, LAMP_HEIGHT + 0.06, 0);
  const poleGeometry = mergeBoxes([post, arm, hood]);
  const poleMaterial = new THREE.MeshStandardMaterial({ color: 0x15161b, roughness: 0.4, metalness: 0.7 });
  const poles = new THREE.InstancedMesh(poleGeometry, poleMaterial, lamps.length);
  const m = new THREE.Matrix4();
  lamps.forEach((l, i) => {
    m.makeRotationY(Math.atan2(-l.az, l.ax));
    m.setPosition(l.x, 0, l.z);
    poles.setMatrixAt(i, m);
  });
  poles.computeBoundingSphere();
  group.add(poles);

  // Traffic: cars as two lights each, driven along the street lines in the vertex shader.
  const lanes = [];
  for (let i = 0; i <= plan.blocksX; i++) lanes.push({ x: -plan.halfX + i * PITCH, z: -plan.halfZ, dx: 0, dz: 1, len: plan.halfZ * 2 });
  for (let j = 0; j <= plan.blocksZ; j++) lanes.push({ x: -plan.halfX, z: -plan.halfZ + j * PITCH, dx: 1, dz: 0, len: plan.halfX * 2 });
  const perLane = 7;
  const cars = lanes.length * perLane * 2;
  const tPos = new Float32Array(cars * 2 * 3);
  const tLane = new Float32Array(cars * 2 * 4);
  const tMove = new Float32Array(cars * 2 * 3);
  let k = 0;
  lanes.forEach((lane, li) => {
    for (let dir = -1; dir <= 1; dir += 2) {
      for (let c = 0; c < perLane; c++) {
        const phase = (c + ((li * 7 + (dir > 0 ? 3 : 0)) % 10) / 10) / perLane;
        const speed = 9 + ((li * 13 + c * 7) % 9);
        for (let side = -1; side <= 1; side += 2) {
          tPos.set([lane.x, 0.75, lane.z], k * 3);
          tLane.set([lane.dx, lane.dz, lane.len, dir], k * 4);
          tMove.set([phase * lane.len, speed, side], k * 3);
          k++;
        }
      }
    }
  });
  const tGeometry = new THREE.BufferGeometry();
  tGeometry.setAttribute("position", new THREE.BufferAttribute(tPos, 3));
  tGeometry.setAttribute("aLane", new THREE.BufferAttribute(tLane, 4));
  tGeometry.setAttribute("aMove", new THREE.BufferAttribute(tMove, 3));
  const traffic = new THREE.Points(
    tGeometry,
    new THREE.ShaderMaterial({
      uniforms: { ...shared, uScale: { value: pixelScale }, uHead: { value: new THREE.Color(0xfff4e0) }, uTail: { value: new THREE.Color(0xff2030) } },
      vertexShader: /* glsl */ `
        attribute vec4 aLane;
        attribute vec3 aMove;
        uniform float uScale;
        uniform float uTime;
        uniform vec3 uHead;
        uniform vec3 uTail;
        varying vec3 vColor;
        varying vec3 vWorld;
        void main() {
          vec2 dir = aLane.xy;
          float travel = mod(aMove.x + uTime * aMove.y, aLane.z);
          if (aLane.w < 0.0) travel = aLane.z - travel;
          vec2 across = vec2(dir.y, -dir.x);
          vec2 xz = position.xz + dir * travel + across * (aLane.w * 2.6) + across * aMove.z * 0.75;
          vec3 world = vec3(xz.x, position.y, xz.y);
          vec3 toCam = cameraPosition - world;
          float facing = dot(dir * aLane.w, normalize(toCam.xz + 0.0001));
          vColor = facing > 0.0 ? uHead * 1.4 : uTail * 1.1;
          vWorld = world;
          vec4 mv = viewMatrix * vec4(world, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = clamp((facing > 0.0 ? 1.4 : 1.0) * uScale / -mv.z, 1.0, 40.0);
        }
      `,
      fragmentShader: POINT_FRAGMENT.replace("varying float vOn;", ""),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  traffic.frustumCulled = false;
  traffic.renderOrder = 3;
  group.add(traffic);

  return {
    group,
    heads,
    traffic,
    poles,
    setPalette(palette) {
      const c = geometry.getAttribute("aColor");
      for (let i = 0; i < lamps.length; i++) c.setXYZ(i, palette.lamp.r, palette.lamp.g, palette.lamp.b);
      for (let i = lamps.length; i < count; i++) c.setXYZ(i, 1, 0.08, 0.06);
      c.needsUpdate = true;
      poleMaterial.color.copy(palette.roof).multiplyScalar(1.4);
    },
    setScale(scale) {
      heads.material.uniforms.uScale.value = scale;
      traffic.material.uniforms.uScale.value = scale;
    },
  };
}

function mergeBoxes(list) {
  const positions = [], normals = [], indices = [];
  let offset = 0;
  for (const g of list) {
    const p = g.getAttribute("position"), n = g.getAttribute("normal");
    for (let i = 0; i < p.count; i++) {
      positions.push(p.getX(i), p.getY(i), p.getZ(i));
      normals.push(n.getX(i), n.getY(i), n.getZ(i));
    }
    const idx = g.index.array;
    for (let i = 0; i < idx.length; i++) indices.push(idx[i] + offset);
    offset += p.count;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  out.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  out.setIndex(indices);
  return out;
}

