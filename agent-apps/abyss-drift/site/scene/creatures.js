// The eight species, built from primitives and shaders. Each returns { group, targets, update(dt, t, ctx) }:
// `targets` are the points a photo can frame ({ pos, radius }), and `update` runs only while the camera is near the
// species' depth band. ctx carries the camera and the sub: { camPos, camDepth, subPos, subFwd, lampOn, reduced }.
import * as THREE from "three";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { underwater, shared, FOG_GLSL } from "./materials.js";
import { mergeGeometries } from "./trench.js";
import { SPECIES } from "../game/species.js";

const UP = new THREE.Vector3(0, 1, 0);
const tmpV = new THREE.Vector3();
const tmpV2 = new THREE.Vector3();
const tmpC = new THREE.Vector2();

export function createCreatures({ shape, rng, tier, tokens, include, scene }) {
  const builders = {
    whale: makeWhale, manta: makeMantas, school: makeSchool, jellyfish: makeJellies,
    lanternfish: makeLanterns, anglerfish: makeAnglers, squid: makeSquid, crab: makeCrabs,
  };
  const list = [];
  for (const sp of SPECIES) {
    if (!include.has(sp.id)) continue;
    const c = builders[sp.id]({ shape, rng: rng.fork(sp.id), tier, tokens, scene });
    c.id = sp.id;
    c.species = sp;
    c.active = true;
    c.group.name = sp.id;
    scene.add(c.group);
    list.push(c);
  }
  return {
    list,
    get(id) {
      return list.find((c) => c.id === id);
    },
    update(dt, t, ctx) {
      for (const c of list) {
        const [lo, hi] = c.species.band;
        const reach = c.id === "whale" ? 130 : 95;
        const active = ctx.camDepth > lo - reach && ctx.camDepth < hi + reach;
        if (active !== c.active) {
          c.active = active;
          c.group.visible = active;
          c.onActive?.(active);
        }
        if (active) c.update(dt, t, ctx);
      }
    },
    setResolution(w, h) {
      for (const c of list) c.setResolution?.(w, h);
    },
  };
}

// A point near the trench's axis at `depth`, `frac` of the way out toward the wall.
function nearAxis(shape, rng, depth, frac) {
  shape.center(depth, tmpC);
  const a = rng.range(0, Math.PI * 2);
  const r = shape.radius(depth) * frac * rng.range(0.3, 1);
  return new THREE.Vector3(tmpC.x + Math.cos(a) * r, -depth, tmpC.y + Math.sin(a) * r);
}

function colorize(geo, fn) {
  const p = geo.attributes.position;
  const c = new Float32Array(p.count * 3);
  const col = new THREE.Color();
  for (let i = 0; i < p.count; i++) {
    fn(p.getX(i), p.getY(i), p.getZ(i), col);
    c[i * 3] = col.r;
    c[i * 3 + 1] = col.g;
    c[i * 3 + 2] = col.b;
  }
  geo.setAttribute("color", new THREE.BufferAttribute(c, 3));
  return geo;
}

function stripTo(geo, names) {
  for (const name of Object.keys(geo.attributes)) if (!names.includes(name)) geo.deleteAttribute(name);
  return geo;
}

function lathe(profile, segments) {
  return new THREE.LatheGeometry(profile.map(([r, y]) => new THREE.Vector2(r, y)), segments);
}

function finShape(points) {
  const s = new THREE.Shape();
  s.moveTo(points[0][0], points[0][1]);
  for (let i = 1; i < points.length; i += 2) s.quadraticCurveTo(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1]);
  return s;
}

/** A soft round glow texture for halos. */
let glowTexture = null;
function getGlowTexture() {
  if (glowTexture) return glowTexture;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.25, "rgba(255,255,255,0.45)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  glowTexture = new THREE.CanvasTexture(c);
  return glowTexture;
}

// ---------------------------------------------------------------------------------------------------------------
// Humpback whale: a long dark shape that circles high in the trench and passes over the light.

function makeWhale({ shape, tokens, tier }) {
  const body = lathe(
    [[0, -11.2], [0.45, -10.8], [0.85, -9.6], [1.25, -7.6], [1.85, -4.6], [2.35, -1.2], [2.55, 1.8], [2.45, 4.8], [2.05, 7.4],
      [1.45, 9.5], [0.75, 10.8], [0, 11.3]],
    30,
  );
  body.rotateX(Math.PI / 2);
  body.scale(1, 0.8, 1);
  const fluke = new THREE.ExtrudeGeometry(
    finShape([[0, 0.5], [1.6, 0.3], [4.6, -1.3], [4.1, -2.3], [2.4, -1.9], [1.0, -1.6], [0, -1.0], [-1.0, -1.6], [-2.4, -1.9],
      [-4.1, -2.3], [-4.6, -1.3], [-1.6, 0.3], [0, 0.5]]),
    { depth: 0.22, bevelEnabled: false, curveSegments: 6 },
  );
  fluke.rotateX(Math.PI / 2);
  fluke.translate(0, 0.1, -10.6);
  const finGeo = (side) => {
    const g = new THREE.ExtrudeGeometry(
      finShape([[0, 0.55], [3.2, 0.5], [6.6, -2.3], [6.5, -2.9], [5.8, -2.8], [3.0, -1.0], [0, -0.5]]),
      { depth: 0.16, bevelEnabled: false, curveSegments: 6 },
    );
    g.rotateX(Math.PI / 2);
    if (side < 0) g.scale(-1, 1, 1);
    g.rotateZ(side * -0.45);
    g.translate(side * 1.8, -1.1, 4.6);
    return g;
  };
  const W = tokens.world;
  const back = W.rockDark.clone().lerp(new THREE.Color(0.1, 0.13, 0.16), 0.6);
  const belly = new THREE.Color(0.72, 0.76, 0.78);
  const parts = [body, fluke, finGeo(1), finGeo(-1)].map((g, i) =>
    colorize(stripTo(g, ["position", "normal"]), (x, y, z, c) => {
      if (i >= 2) c.copy(belly).lerp(back, 0.25);
      else c.copy(back).lerp(belly, THREE.MathUtils.smoothstep(-y, 0.4, 1.8) * (z > -9 ? 1 : 0.3));
    }),
  );
  const geo = mergeGeometries(parts);
  geo.computeVertexNormals();
  const mat = underwater(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.62, metalness: 0.05, side: THREE.DoubleSide }), {
    caustics: tier.caustics,
    key: "whale",
    vertex: `
      float wAmp = 1.25 * pow(smoothstep(3.0, -12.0, position.z), 2.0);
      transformed.y += wAmp * sin(uTime * 1.15 - position.z * 0.2);
      transformed.y += 0.35 * sin(uTime * 1.15 + 1.2) * smoothstep(1.5, 5.0, abs(position.x));`,
  });
  const mesh = new THREE.Mesh(geo, mat);
  const group = new THREE.Group();
  group.add(mesh);
  const target = { pos: new THREE.Vector3(), radius: 9 };
  let angle = 0;
  const loop = { a: 34, b: 26, depth: 21, period: 58 };
  return {
    group,
    targets: [target],
    setPhase(a) {
      angle = a;
    },
    update(dt) {
      angle += (dt * Math.PI * 2) / loop.period;
      shape.center(loop.depth, tmpC);
      const x = tmpC.x + Math.cos(angle) * loop.a;
      const z = tmpC.y + Math.sin(angle) * loop.b;
      const y = -loop.depth + Math.sin(angle * 2) * 3;
      group.position.set(x, y, z);
      const dx = -Math.sin(angle) * loop.a, dz = Math.cos(angle) * loop.b;
      group.rotation.set(Math.cos(angle * 2) * 0.08, Math.atan2(dx, dz), -0.12);
      target.pos.copy(group.position);
    },
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Giant mantas: a subdivided plane cut to a manta's outline, its wings riding a traveling wave.

function makeMantas({ shape, rng, tokens, tier }) {
  const geo = new THREE.PlaneGeometry(1, 1, 30, 22);
  geo.rotateX(-Math.PI / 2);
  geo.scale(7.2, 1, 5.2);
  stripTo(geo, ["position", "normal", "uv"]);
  const make = () =>
    underwater(new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.55, metalness: 0.0, side: THREE.DoubleSide }), {
      caustics: tier.caustics,
      key: "manta",
      uniforms: { uPhase: { value: rng.range(0, 6) } },
      vertexHead: "uniform float uPhase;\nvarying vec2 vMUv;",
      normal: `
        float mx = abs(uv.x - 0.5) * 2.0;
        float mArg = uTime * 2.1 + uPhase - uv.y * 3.2;
        float mW = sin(mArg);
        float dydx = 1.25 * 1.6 * pow(max(mx, 0.001), 0.6) * sign(uv.x - 0.5) * (2.0 / 7.2) * mW;
        float dydz = 1.25 * pow(mx, 1.6) * cos(mArg) * (3.2 / 5.2);
        objectNormal = normalize(vec3(-dydx, 1.0, -dydz));`,
      vertex: `
        transformed.y += 1.25 * pow(mx, 1.6) * mW + 0.25 * sin(uTime * 2.1 + uPhase) * (1.0 - mx);
        vMUv = uv;`,
      fragmentHead: "varying vec2 vMUv;",
      color: `
        float x = abs(vMUv.x - 0.5) * 2.0;
        float v = vMUv.y;
        float front = 0.12 + 0.36 * pow(x, 1.25);
        float back = 0.66 - 0.22 * pow(x, 0.9);
        bool wing = x < 1.0 && v > front && v < back;
        bool body = x < 0.14 && v > 0.05 + x * 0.3 && v < 0.74 - x;
        bool horn = x > 0.05 && x < 0.15 && v > 0.0 && v < 0.12;
        bool tail = x < 0.014 && v > 0.7;
        if (!(wing || body || horn || tail)) discard;
        float shoulder = smoothstep(0.14, 0.04, length(vec2(x - 0.3, (v - 0.3) * 1.4)));
        float edge = smoothstep(back - 0.08, back, v);
        vec3 top = mix(vec3(0.05, 0.06, 0.07), vec3(0.78, 0.82, 0.84), shoulder * 0.9);
        vec3 belly = mix(vec3(0.86, 0.9, 0.92), vec3(0.12, 0.13, 0.15), max(edge, smoothstep(0.85, 1.0, x)));
        belly *= 1.0 - 0.5 * step(0.93, fract(sin(dot(floor(vMUv * 24.0), vec2(12.9, 78.2))) * 43758.5));
        diffuseColor.rgb = gl_FrontFacing ? top : belly;`,
    });
  const group = new THREE.Group();
  const mantas = [];
  for (let i = 0; i < 2; i++) {
    const mesh = new THREE.Mesh(geo, make());
    mesh.frustumCulled = false;
    group.add(mesh);
    mantas.push({
      mesh,
      angle: rng.range(0, Math.PI * 2),
      radius: rng.range(12, 18),
      depth: rng.range(28, 44),
      speed: rng.range(0.85, 1.15) * (i % 2 ? -1 : 1),
      target: { pos: new THREE.Vector3(), radius: 3.6 },
    });
  }
  return {
    group,
    targets: mantas.map((m) => m.target),
    mantas,
    update(dt, t) {
      for (const m of mantas) {
        m.angle += (dt * Math.PI * 2 * m.speed) / 34;
        shape.center(m.depth, tmpC);
        const y = -m.depth + Math.sin(t * 0.2 + m.radius) * 4;
        m.mesh.position.set(tmpC.x + Math.cos(m.angle) * m.radius, y, tmpC.y + Math.sin(m.angle) * m.radius);
        const dir = Math.sign(m.speed);
        const dx = -Math.sin(m.angle) * dir, dz = Math.cos(m.angle) * dir;
        m.mesh.rotation.set(Math.cos(t * 0.2 + m.radius) * 0.12, Math.atan2(dx, dz), dir * -0.32, "YXZ");
        m.target.pos.copy(m.mesh.position);
      }
    },
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Sardine school: an InstancedMesh steered as a milling bait ball — each fish chases its own slot around a moving
// center, keeps apart from its cellmates, matches their heading, and scatters from the sub.

function makeSchool({ shape, rng, tier, tokens }) {
  const n = tier.fish;
  const body = lathe([[0, -0.5], [0.08, -0.42], [0.14, -0.2], [0.155, 0.05], [0.12, 0.27], [0.06, 0.43], [0, 0.5]], 8);
  body.rotateX(Math.PI / 2);
  body.scale(0.42, 1, 1);
  stripTo(body, ["position", "normal"]);
  const tail = new THREE.BufferGeometry();
  tail.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, -0.44, 0, 0.2, -0.74, 0, -0.2, -0.74, 0, 0, -0.44, 0, -0.2, -0.74, 0, 0.2, -0.74], 3));
  tail.computeVertexNormals();
  const back = tokens.world.waterDeep.clone().lerp(new THREE.Color(0.08, 0.16, 0.24), 0.6);
  const silver = new THREE.Color(0.86, 0.9, 0.93);
  const parts = [body, tail].map((g) => colorize(g, (x, y, z, c) => c.copy(silver).lerp(back, THREE.MathUtils.smoothstep(y, -0.01, 0.08))));
  const geo = mergeGeometries(parts);
  geo.scale(0.5, 0.5, 0.5);
  const mat = underwater(new THREE.MeshStandardMaterial({ vertexColors: true, metalness: 0.7, roughness: 0.26, envMapIntensity: 1.4, side: THREE.DoubleSide }), {
    caustics: tier.caustics,
    key: "school",
    vertex: `
      #ifdef USE_INSTANCING
        float fPhase = instanceMatrix[3].x * 3.1 + instanceMatrix[3].z * 1.7 + instanceMatrix[3].y;
      #else
        float fPhase = 0.0;
      #endif
      transformed.x += sin(uTime * 15.0 + fPhase) * 0.07 * smoothstep(0.07, -0.37, position.z);`,
  });
  const mesh = new THREE.InstancedMesh(geo, mat, n);
  mesh.frustumCulled = false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const group = new THREE.Group();
  group.add(mesh);

  const pos = new Float32Array(n * 3);
  const vel = new Float32Array(n * 3);
  const slot = new Float32Array(n * 3);
  const center = new THREE.Vector3();
  const home = { depth: 62, phase: rng.range(0, 6) };
  let override = null;
  const placeCenter = (t) => {
    if (override) return center.copy(override);
    const d = home.depth + Math.sin(t * 0.045 + home.phase) * 22;
    shape.center(d, tmpC);
    const r = shape.radius(d) * 0.28;
    return center.set(tmpC.x + Math.cos(t * 0.06 + home.phase) * r, -d, tmpC.y + Math.sin(t * 0.06 + home.phase) * r);
  };
  placeCenter(0);
  for (let i = 0; i < n; i++) {
    const u = rng.next() * 2 - 1, a = rng.range(0, Math.PI * 2), r = Math.cbrt(rng.next());
    const s = Math.sqrt(1 - u * u);
    slot[i * 3] = Math.cos(a) * s * r * 4.6;
    slot[i * 3 + 1] = u * r * 2.6;
    slot[i * 3 + 2] = Math.sin(a) * s * r * 4.6;
    pos[i * 3] = center.x + slot[i * 3];
    pos[i * 3 + 1] = center.y + slot[i * 3 + 1];
    pos[i * 3 + 2] = center.z + slot[i * 3 + 2];
    vel[i * 3] = Math.cos(a) * 2;
    vel[i * 3 + 2] = Math.sin(a) * 2;
  }
  const CELLS = 4096;
  const head = new Int32Array(CELLS);
  const next = new Int32Array(n);
  const cellOf = new Int32Array(n);
  const arr = mesh.instanceMatrix.array;
  const target = { pos: new THREE.Vector3(), radius: 5 };

  return {
    group,
    targets: [target],
    setCenter(v) {
      override = v ? v.clone() : null;
    },
    update(dt, t, ctx) {
      dt = Math.min(dt, 1 / 30);
      placeCenter(t);
      head.fill(-1);
      for (let i = 0; i < n; i++) {
        const k = ((Math.floor(pos[i * 3] / 1.1) * 73856093) ^ (Math.floor(pos[i * 3 + 1] / 1.1) * 19349663) ^ (Math.floor(pos[i * 3 + 2] / 1.1) * 83492791)) & (CELLS - 1);
        cellOf[i] = k;
        next[i] = head[k];
        head[k] = i;
      }
      const mill = t * 0.55;
      const cm = Math.cos(mill), sm = Math.sin(mill);
      const sx = ctx.subPos.x, sy = ctx.subPos.y, sz = ctx.subPos.z;
      let cx = 0, cy = 0, cz = 0;
      for (let i = 0; i < n; i++) {
        const i3 = i * 3;
        const px = pos[i3], py = pos[i3 + 1], pz = pos[i3 + 2];
        // Seek the slot, which turns around the center so the ball mills.
        const ox = slot[i3] * cm - slot[i3 + 2] * sm, oz = slot[i3] * sm + slot[i3 + 2] * cm;
        let ax = (center.x + ox - px) * 1.6, ay = (center.y + slot[i3 + 1] - py) * 1.6, az = (center.z + oz - pz) * 1.6;
        // Swim along the mill's tangent.
        ax += -oz * 0.5;
        az += ox * 0.5;
        // Cellmates: keep apart and match heading.
        let sxn = 0, syn = 0, szn = 0, avx = 0, avy = 0, avz = 0, m = 0;
        for (let j = head[cellOf[i]]; j !== -1; j = next[j]) {
          if (j === i) continue;
          const j3 = j * 3;
          const dx = px - pos[j3], dy = py - pos[j3 + 1], dz = pz - pos[j3 + 2];
          const d2 = dx * dx + dy * dy + dz * dz;
          if (d2 < 0.2 && d2 > 1e-6) {
            sxn += dx / d2;
            syn += dy / d2;
            szn += dz / d2;
          }
          avx += vel[j3];
          avy += vel[j3 + 1];
          avz += vel[j3 + 2];
          m++;
        }
        ax += sxn * 0.35;
        ay += syn * 0.35;
        az += szn * 0.35;
        if (m) {
          ax += (avx / m - vel[i3]) * 0.8;
          ay += (avy / m - vel[i3 + 1]) * 0.8;
          az += (avz / m - vel[i3 + 2]) * 0.8;
        }
        // Scatter from the sub.
        const ex = px - sx, ey = py - sy, ez = pz - sz;
        const e2 = ex * ex + ey * ey + ez * ez;
        if (e2 < 64) {
          const e = Math.sqrt(e2) || 1;
          const push = (8 - e) * 5 / e;
          ax += ex * push;
          ay += ey * push;
          az += ez * push;
        }
        let vx = vel[i3] + ax * dt, vy = vel[i3 + 1] + ay * dt, vz = vel[i3 + 2] + az * dt;
        const sp = Math.hypot(vx, vy, vz) || 1;
        const cl = Math.min(6.5, Math.max(2.2, sp)) / sp;
        vx *= cl;
        vy *= cl * 0.6;
        vz *= cl;
        vel[i3] = vx;
        vel[i3 + 1] = vy;
        vel[i3 + 2] = vz;
        const nx = px + vx * dt, ny = py + vy * dt, nz = pz + vz * dt;
        pos[i3] = nx;
        pos[i3 + 1] = ny;
        pos[i3 + 2] = nz;
        cx += nx;
        cy += ny;
        cz += nz;
        // Basis from heading: right, up, forward, then position (column-major).
        const s = Math.hypot(vx, vy, vz) || 1;
        const fx = vx / s, fy = vy / s, fz = vz / s;
        let rx = fz, rz = -fx;
        const rl = Math.hypot(rx, rz) || 1;
        rx /= rl;
        rz /= rl;
        const ux = -rz * fy, uy = rz * fx - rx * fz, uz = rx * fy;
        const o = i * 16;
        arr[o] = rx; arr[o + 1] = 0; arr[o + 2] = rz; arr[o + 3] = 0;
        arr[o + 4] = ux; arr[o + 5] = uy; arr[o + 6] = uz; arr[o + 7] = 0;
        arr[o + 8] = fx; arr[o + 9] = fy; arr[o + 10] = fz; arr[o + 11] = 0;
        arr[o + 12] = nx; arr[o + 13] = ny; arr[o + 14] = nz; arr[o + 15] = 1;
      }
      mesh.instanceMatrix.needsUpdate = true;
      target.pos.set(cx / n, cy / n, cz / n);
    },
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Crown jellies: bells pulsed in the vertex shader, glowing through bloom, trailing fat-line tentacles on a delay.

const BELL_VERT = /* glsl */ `
  uniform float uPulse;
  uniform float uTime;
  varying float vH;
  varying float vAng;
  varying vec3 vN;
  varying vec3 vV;
  varying float vDist;
  void main() {
    vec3 p = position;
    float h = clamp(p.y / 0.8, 0.0, 1.0);
    float ang = atan(p.z, p.x);
    p.xz *= 1.0 - 0.24 * uPulse * (1.0 - h * 0.65);
    p.y *= 1.0 + 0.14 * uPulse;
    p.xz *= 1.0 + 0.04 * sin(ang * 8.0 + uTime * 2.4) * (1.0 - h);
    vH = h;
    vAng = ang;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    vN = normalize(normalMatrix * normal);
    vV = normalize(-mv.xyz);
    vDist = -mv.z;
    gl_Position = projectionMatrix * mv;
  }`;
const BELL_FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uColor2;
  uniform float uPulse;
  varying float vH;
  varying float vAng;
  varying vec3 vN;
  varying vec3 vV;
  varying float vDist;
  ${FOG_GLSL}
  void main() {
    float fres = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2);
    float canals = pow(abs(cos(vAng * 8.0)), 28.0) * (1.0 - vH) * 0.8;
    float rim = smoothstep(0.2, 0.0, vH);
    float crown = smoothstep(0.12, 0.0, abs(vH - 0.42)) * (0.5 + 0.5 * cos(vAng * 16.0));
    float gonad = smoothstep(0.5, 0.0, length(vec2(abs(cos(vAng * 2.0)) - 0.72, vH - 0.62) * vec2(2.2, 3.0)));
    vec3 col = uColor * (0.1 + fres * 1.2 + canals + rim * 1.6 + crown * 0.5) * (0.75 + 0.7 * uPulse) + uColor2 * gonad * 1.1;
    col *= 1.0 - fogFactor(vDist);
    gl_FragColor = vec4(col, 1.0);
  }`;

function makeJellies({ shape, rng, tier, tokens }) {
  const W = tokens.world;
  const count = tier.name === "high" ? 8 : tier.name === "mid" ? 7 : 5;
  const bellGeo = lathe([[0, 0.8], [0.24, 0.78], [0.44, 0.7], [0.6, 0.58], [0.72, 0.4], [0.79, 0.22], [0.8, 0.06], [0.77, 0.0], [0.7, -0.02]], 36);
  const innerGeo = lathe([[0, 0.55], [0.2, 0.5], [0.34, 0.38], [0.38, 0.2], [0.3, 0.12]], 20);
  const TENT = 14, PTS = 12, SEG = 0.24;
  const group = new THREE.Group();
  const jellies = [];
  const homes = [];
  for (let i = 0; i < count; i++) {
    const depth = 88 + (i / Math.max(1, count - 1)) * 72 + rng.range(-6, 6);
    homes.push(nearAxis(shape, rng, depth, 0.42));
  }
  for (let i = 0; i < count; i++) {
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        uPulse: { value: 0 },
        uTime: shared.uTime,
        uColor: { value: W.glow.clone().lerp(W.glow2, rng.range(0, 0.35)) },
        uColor2: { value: W.glow2.clone() },
        uFogDensity: shared.uFogDensity,
        uFogColor: shared.uFogColor,
      },
      vertexShader: BELL_VERT,
      fragmentShader: BELL_FRAG,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
    });
    const bell = new THREE.Mesh(bellGeo, mat);
    const inner = new THREE.Mesh(innerGeo, mat);
    const body = new THREE.Group();
    body.add(bell, inner);
    const scale = rng.range(0.85, 1.35);
    body.scale.setScalar(scale);
    group.add(body);

    const segs = TENT * (PTS - 1);
    const lineGeo = new LineSegmentsGeometry();
    lineGeo.setPositions(new Float32Array(segs * 6));
    const colors = new Float32Array(segs * 6);
    const tc = W.glow.clone();
    for (let k = 0; k < TENT; k++) {
      for (let s = 0; s < PTS - 1; s++) {
        const o = (k * (PTS - 1) + s) * 6;
        const a = Math.pow(1 - s / (PTS - 1), 1.3), b = Math.pow(1 - (s + 1) / (PTS - 1), 1.3);
        const oral = k >= TENT - 4 ? 1.5 : 1;
        colors.set([tc.r * a * oral, tc.g * a * oral, tc.b * a * oral, tc.r * b * oral, tc.g * b * oral, tc.b * b * oral], o);
      }
    }
    lineGeo.setColors(colors);
    const lineMat = new LineMaterial({
      color: 0xffffff, linewidth: tier.name === "high" ? 1.8 : 1.5, vertexColors: true, transparent: true,
      blending: THREE.AdditiveBlending, depthWrite: false, worldUnits: false,
    });
    const lines = new LineSegments2(lineGeo, lineMat);
    lines.frustumCulled = false;
    group.add(lines);

    const pts = [];
    for (let k = 0; k < TENT; k++) {
      const chain = [];
      for (let s = 0; s < PTS; s++) chain.push(homes[i].clone().add(new THREE.Vector3(0, -s * SEG, 0)));
      pts.push(chain);
    }
    jellies.push({
      body, mat, lines, lineMat, lineGeo, pts, scale,
      pos: homes[i].clone(),
      home: homes[i],
      vel: new THREE.Vector3(),
      phase: rng.range(0, Math.PI * 2),
      rate: rng.range(0.75, 1.1),
      tilt: new THREE.Vector3(rng.range(-0.2, 0.2), 0, rng.range(-0.2, 0.2)),
      target: { pos: homes[i].clone(), radius: 1.0 * scale },
    });
  }
  const q = new THREE.Quaternion();
  const axis = new THREE.Vector3();
  const anchor = new THREE.Vector3();
  const down = new THREE.Vector3();
  return {
    group,
    targets: jellies.map((j) => j.target),
    jellies,
    setResolution(w, h) {
      for (const j of jellies) j.lineMat.resolution.set(w, h);
    },
    /** Moves the jellies' homes around a point, for the opening view. */
    gatherAround(point, rngLocal) {
      jellies.forEach((j, i) => {
        const a = (i / jellies.length) * Math.PI * 2 + 0.4;
        const r = 5 + (i % 3) * 3.2;
        j.home.set(point.x + Math.cos(a) * r, point.y + ((i % 4) - 1.5) * 2.6 + rngLocal.range(-1, 1), point.z + Math.sin(a) * r);
        j.pos.copy(j.home);
        for (const chain of j.pts) chain.forEach((p, s) => p.copy(j.pos).add(new THREE.Vector3(0, -s * SEG, 0)));
      });
    },
    update(dt, t, ctx) {
      dt = Math.min(dt, 1 / 30);
      for (const j of jellies) {
        j.phase += dt * Math.PI * 2 * (j.rate / 1.9);
        const c = Math.pow(Math.max(0, Math.sin(j.phase)), 2);
        j.mat.uniforms.uPulse.value = c;
        // Bell axis: tilted by its drift and a slow wobble.
        axis.set(j.tilt.x + Math.sin(t * 0.3 + j.rate * 7) * 0.12, 1, j.tilt.z + Math.cos(t * 0.27 + j.rate * 5) * 0.12).normalize();
        j.vel.addScaledVector(axis, c * dt * 1.9);
        j.vel.y -= 0.16 * dt;
        j.vel.addScaledVector(tmpV.copy(j.home).sub(j.pos), 0.025 * dt);
        j.vel.multiplyScalar(Math.exp(-dt * 1.25));
        j.pos.addScaledVector(j.vel, dt);
        j.body.position.copy(j.pos);
        q.setFromUnitVectors(UP, axis);
        j.body.quaternion.copy(q);
        j.target.pos.copy(j.pos);
        // Tentacles: each point eases toward the one above it, later points slower, so the strands trail.
        const rimR = 0.74 * j.scale * (1 - 0.24 * c * 0.35);
        const arr = j.lineGeo.attributes.instanceStart.data.array;
        for (let k = 0; k < j.pts.length; k++) {
          const chain = j.pts[k];
          const oral = k >= j.pts.length - 4;
          const a = (k / (j.pts.length - 4)) * Math.PI * 2;
          if (oral) anchor.set(Math.cos(a * 4) * 0.12 * j.scale, 0.1, Math.sin(a * 4) * 0.12 * j.scale);
          else anchor.set(Math.cos(a) * rimR, 0.02, Math.sin(a) * rimR);
          anchor.applyQuaternion(q).add(j.pos);
          chain[0].copy(anchor);
          down.copy(axis).multiplyScalar(-1);
          for (let s = 1; s < chain.length; s++) {
            const lag = 1 - Math.exp(-dt * (9 - s * 0.55));
            tmpV.copy(chain[s - 1]).addScaledVector(down, SEG);
            tmpV.x += Math.sin(t * 1.3 + s * 0.6 + k) * 0.04 * s;
            tmpV.z += Math.cos(t * 1.1 + s * 0.5 + k * 1.3) * 0.04 * s;
            chain[s].lerp(tmpV, lag);
            tmpV2.copy(chain[s]).sub(chain[s - 1]);
            const len = tmpV2.length() || 1;
            const segLen = oral ? SEG * 0.55 : SEG;
            chain[s].copy(chain[s - 1]).addScaledVector(tmpV2, segLen / len);
          }
          for (let s = 0; s < chain.length - 1; s++) {
            const o = (k * (chain.length - 1) + s) * 6;
            arr[o] = chain[s].x; arr[o + 1] = chain[s].y; arr[o + 2] = chain[s].z;
            arr[o + 3] = chain[s + 1].x; arr[o + 4] = chain[s + 1].y; arr[o + 5] = chain[s + 1].z;
          }
        }
        j.lineGeo.attributes.instanceStart.data.needsUpdate = true;
        const dist = j.pos.distanceTo(ctx.camPos);
        const f = shared.uFogDensity.value * dist;
        j.lineMat.opacity = Math.exp(-f * f);
      }
    },
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Lanternfish shoal: a swirl of photophores computed in the vertex shader, flickering, scattering from the sub.

function makeLanterns({ shape, rng, tier, tokens }) {
  const n = tier.name === "high" ? 260 : tier.name === "mid" ? 170 : 100;
  const pos = new Float32Array(n * 3);
  const seed = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) {
    seed[i * 4] = Math.sqrt(rng.next()) * 6 + 0.5;
    seed[i * 4 + 1] = rng.range(0.15, 0.5) * (rng.next() < 0.85 ? 1 : -1);
    seed[i * 4 + 2] = rng.range(0, Math.PI * 2);
    seed[i * 4 + 3] = rng.range(-2.6, 2.6);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 4));
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: shared.uTime,
      uCenter: { value: new THREE.Vector3() },
      uScatter: { value: 0 },
      uColor: { value: tokens.world.glow.clone().lerp(new THREE.Color(0.6, 1, 0.9), 0.3) },
      uPixel: { value: 1 },
      uFogDensity: shared.uFogDensity,
      uFogColor: shared.uFogColor,
    },
    vertexShader: /* glsl */ `
      attribute vec4 aSeed;
      uniform float uTime;
      uniform vec3 uCenter;
      uniform float uScatter;
      uniform float uPixel;
      varying float vFlick;
      varying float vDist;
      void main() {
        float phi = aSeed.z + uTime * aSeed.y;
        float r = aSeed.x * (1.0 + uScatter);
        vec3 p = uCenter + vec3(cos(phi) * r, aSeed.w * (1.0 + uScatter * 0.6) + sin(phi * 1.7 + aSeed.z) * 0.7, sin(phi) * r);
        vFlick = 0.25 + 0.75 * pow(0.5 + 0.5 * sin(uTime * (1.8 + abs(aSeed.y) * 5.0) + aSeed.z * 13.0), 6.0);
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vDist = -mv.z;
        gl_Position = projectionMatrix * mv;
        gl_PointSize = clamp(uPixel * 300.0 / max(1.0, -mv.z), 2.0, 34.0 * uPixel);
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      varying float vFlick;
      varying float vDist;
      ${FOG_GLSL}
      void main() {
        vec2 c = gl_PointCoord - 0.5;
        float r = length(c);
        float core = smoothstep(0.09, 0.0, r);
        float halo = pow(smoothstep(0.5, 0.0, r), 2.5) * 0.45;
        float b = (core * 2.6 + halo) * vFlick * (1.0 - fogFactor(vDist));
        gl_FragColor = vec4(uColor * b, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  const group = new THREE.Group();
  group.add(points);
  const target = { pos: new THREE.Vector3(), radius: 5 };
  const phase = rng.range(0, 6);
  let scatter = 0;
  return {
    group,
    targets: [target],
    setPixelRatio(pr) {
      mat.uniforms.uPixel.value = pr;
    },
    update(dt, t, ctx) {
      const d = 232 + Math.sin(t * 0.05 + phase) * 30;
      shape.center(d, tmpC);
      const r = shape.radius(d) * 0.25;
      target.pos.set(tmpC.x + Math.cos(t * 0.07 + phase) * r, -d, tmpC.y + Math.sin(t * 0.07 + phase) * r);
      mat.uniforms.uCenter.value.copy(target.pos);
      const near = ctx.subPos.distanceTo(target.pos) < 11 ? 1.6 : 0;
      scatter += (near - scatter) * (1 - Math.exp(-dt * 1.5));
      mat.uniforms.uScatter.value = scatter;
    },
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Anglerfish: a dark lumpy body, an underbite of glassy fangs, and a lure on a rod — the first thing seen in the dark.

function makeAnglers({ shape, rng, tier, tokens }) {
  const W = tokens.world;
  const skin = new THREE.MeshStandardMaterial({ color: 0x3a2c27, roughness: 0.38, metalness: 0.08, emissive: 0x0a0605, emissiveIntensity: 1 });
  const fang = new THREE.MeshStandardMaterial({ color: 0xe8e2d6, roughness: 0.2, metalness: 0, emissive: 0x1a1612, emissiveIntensity: 1 });
  const fin = new THREE.MeshStandardMaterial({ color: 0x2a1f1b, roughness: 0.6, transparent: true, opacity: 0.85, side: THREE.DoubleSide });
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0x9fb6c4, roughness: 0.08, metalness: 0.4, emissive: 0x203038, emissiveIntensity: 0.6 });
  const lureMat = new THREE.MeshStandardMaterial({ color: 0x111111, emissive: W.lure.clone(), emissiveIntensity: 3 });
  const haloMat = new THREE.SpriteMaterial({ map: getGlowTexture(), color: W.lure.clone(), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.55 });

  const bodyGeo = new THREE.SphereGeometry(1, 30, 22);
  {
    const p = bodyGeo.attributes.position;
    for (let i = 0; i < p.count; i++) {
      let x = p.getX(i) * 0.8, y = p.getY(i) * 0.84, z = p.getZ(i) * 1.45;
      // Taper to the tail, so the silhouette is a fish and not a ball.
      if (z < 0) {
        const k = Math.max(0.28, 1 + z * 0.42);
        x *= k;
        y *= k;
      }
      if (y > 0.5) y = 0.5 + (y - 0.5) * 0.7;
      if (z > 0.3 && y < 0.0) z += 0.18 * (z - 0.3) * (1 - y);
      const bump = Math.sin(x * 9) * Math.sin(y * 7 + 1) * Math.sin(z * 8) * 0.035;
      p.setXYZ(i, x * (1 + bump), y * (1 + bump), z * (1 + bump));
    }
    bodyGeo.computeVertexNormals();
  }
  const jawGeo = new THREE.SphereGeometry(0.86, 24, 10, 0, Math.PI * 2, Math.PI * 0.5, Math.PI * 0.32);
  jawGeo.scale(0.95, 0.7, 1.25);
  const teeth = (count, radius, y, z0, down) => {
    const geos = [];
    for (let i = 0; i < count; i++) {
      const a = -1.15 + (i / (count - 1)) * 2.3;
      const len = 0.16 + Math.abs(Math.sin(i * 2.7)) * 0.2;
      const g = new THREE.ConeGeometry(0.03, len, 5);
      if (down) g.rotateX(Math.PI);
      g.rotateX(down ? 0.3 : -0.35);
      g.translate(Math.sin(a) * radius, y + (down ? -len / 2 : len / 2), z0 + Math.cos(a) * radius * 0.9);
      geos.push(stripTo(g, ["position", "normal"]));
    }
    return mergeGeometries(geos);
  };
  const upperTeeth = teeth(15, 0.62, -0.1, 0.5, true);
  const lowerTeeth = teeth(13, 0.68, -0.12, 0.62, false);
  const pecGeo = new THREE.CircleGeometry(0.45, 12, -0.9, 1.8);
  const dorsalGeo = new THREE.ShapeGeometry(finShape([[0, 0], [0.1, 0.35], [-0.35, 0.42], [-0.5, 0.2], [-0.7, 0]]));
  dorsalGeo.rotateY(Math.PI / 2);
  const tailGeo = new THREE.ShapeGeometry(finShape([[0, 0], [0.5, 0.6], [0.9, 0.55], [0.7, 0], [0.9, -0.55], [0.5, -0.6], [0, 0]]));
  tailGeo.rotateY(Math.PI / 2);
  const rodCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.62, 0.35), new THREE.Vector3(0, 1.25, 0.7), new THREE.Vector3(0, 1.3, 1.4), new THREE.Vector3(0, 0.95, 1.85),
  ]);
  const rodGeo = new THREE.TubeGeometry(rodCurve, 20, 0.022, 6, false);
  const lureGeo = new THREE.SphereGeometry(0.075, 14, 10);
  const eyeGeo = new THREE.SphereGeometry(0.075, 12, 8);

  const group = new THREE.Group();
  const fish = [];
  for (let i = 0; i < 2; i++) {
    const root = new THREE.Group();
    const scale = i === 0 ? 1.35 : 1.0;
    root.scale.setScalar(scale);
    root.add(new THREE.Mesh(bodyGeo, skin));
    const jaw = new THREE.Group();
    jaw.position.set(0, -0.08, -0.15);
    const jawMesh = new THREE.Mesh(jawGeo, skin);
    jawMesh.position.set(0, 0.08, 0.3);
    jaw.add(jawMesh, new THREE.Mesh(lowerTeeth, fang));
    root.add(jaw, new THREE.Mesh(upperTeeth, fang));
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(eyeGeo, eyeMat);
      eye.position.set(s * 0.5, 0.32, 0.62);
      root.add(eye);
      const pec = new THREE.Mesh(pecGeo, fin);
      pec.position.set(s * 0.72, -0.15, -0.05);
      pec.rotation.set(0, s * 1.3, 0);
      root.add(pec);
    }
    const dorsal = new THREE.Mesh(dorsalGeo, fin);
    dorsal.position.set(0, 0.38, -0.55);
    root.add(dorsal);
    const tail = new THREE.Mesh(tailGeo, fin);
    tail.position.set(0, 0, -1.4);
    tail.rotation.y = Math.PI;
    root.add(tail);
    root.add(new THREE.Mesh(rodGeo, skin));
    const lure = new THREE.Mesh(lureGeo, lureMat);
    lure.position.copy(rodCurve.points[3]);
    const halo = new THREE.Sprite(haloMat);
    halo.scale.setScalar(0.5);
    lure.add(halo);
    root.add(lure);
    group.add(root);
    const depth = i === 0 ? 335 : 362;
    const home = nearAxis(shape, rng, depth, 0.3);
    root.position.copy(home);
    fish.push({ root, jaw, tail, lure, home, scale, yaw: rng.range(0, 6), phase: rng.range(0, 6), target: { pos: home.clone(), radius: 1.6 * scale } });
  }
  const lurePos = new THREE.Vector3();
  return {
    group,
    targets: fish.map((f) => f.target),
    fish,
    /** World position of the lure nearest `p`, for the one lure light. */
    nearestLure(p, out) {
      let best = Infinity;
      for (const f of fish) {
        f.lure.getWorldPosition(lurePos);
        const d = lurePos.distanceToSquared(p);
        if (d < best) {
          best = d;
          out.copy(lurePos);
        }
      }
      return Math.sqrt(best);
    },
    update(dt, t, ctx) {
      for (const f of fish) {
        const toSub = tmpV.copy(ctx.subPos).sub(f.root.position);
        const dist = toSub.length();
        const wantYaw = dist < 26 ? Math.atan2(toSub.x, toSub.z) : f.yaw + Math.sin(t * 0.05 + f.phase) * 0.8;
        let dy = wantYaw - f.root.rotation.y;
        dy = Math.atan2(Math.sin(dy), Math.cos(dy));
        f.root.rotation.y += dy * (1 - Math.exp(-dt * 0.5));
        f.root.position.set(
          f.home.x + Math.sin(t * 0.13 + f.phase) * 1.4,
          f.home.y + Math.sin(t * 0.37 + f.phase) * 0.5,
          f.home.z + Math.cos(t * 0.11 + f.phase) * 1.4,
        );
        f.root.rotation.z = Math.sin(t * 0.6 + f.phase) * 0.06;
        f.jaw.rotation.x = 0.12 + 0.22 * Math.pow(0.5 + 0.5 * Math.sin(t * 0.5 + f.phase), 3);
        f.tail.rotation.y = Math.PI + Math.sin(t * 2.2 + f.phase) * 0.35;
        f.lure.position.set(Math.sin(t * 1.3 + f.phase) * 0.06, 0.95 + Math.sin(t * 1.7 + f.phase) * 0.07, 1.85);
        f.target.pos.copy(f.root.position);
      }
      lureMat.emissiveIntensity = 2.6 + Math.sin(t * 2.3) * 0.6 + (Math.sin(t * 7.1) > 0.96 ? 1.5 : 0);
    },
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Giant squid: a long red mantle and ten arms bent in the vertex shader. It keeps to the edge of the beams and jets
// back into the dark when the sub comes too close.

function makeSquid({ shape, rng, tier, tokens }) {
  const geos = [];
  const mantle = lathe([[0.0, 5.6], [0.25, 5.3], [0.5, 4.6], [0.68, 3.4], [0.74, 2.0], [0.72, 1.0], [0.62, 0.55], [0.5, 0.3]], 22);
  mantle.rotateX(Math.PI / 2);
  geos.push(mantle);
  const head = new THREE.SphereGeometry(0.55, 18, 12);
  head.scale(1, 0.9, 1.15);
  geos.push(head);
  for (const s of [-1, 1]) {
    const finG = new THREE.ShapeGeometry(finShape([[0, 0], [0.9, 0.3], [1.2, 1.2], [0.7, 1.6], [0, 1.9]]));
    finG.rotateX(-Math.PI / 2);
    finG.scale(s, 1, -1);
    finG.translate(0, 0, 5.4);
    geos.push(finG);
  }
  const armData = [];
  const ARMS = 10;
  for (let k = 0; k < ARMS; k++) {
    const feeding = k >= 8;
    const len = feeding ? 9 : 3.4;
    const a = (k / 8) * Math.PI * 2 + (feeding ? 0.4 : 0);
    const bx = Math.cos(a) * 0.28, by = Math.sin(a) * 0.28;
    const rings = feeding ? 34 : 18, radial = 6;
    const pos = [], aT = [], aArm = [], idx = [];
    for (let i = 0; i <= rings; i++) {
      const t = i / rings;
      let r = (feeding ? 0.07 : 0.17) * (1 - t * 0.85);
      if (feeding && t > 0.82) r = 0.15 * Math.sin(((t - 0.82) / 0.18) * Math.PI) + 0.02;
      for (let j = 0; j < radial; j++) {
        const b = (j / radial) * Math.PI * 2;
        pos.push(bx * (1 + t * 1.5) + Math.cos(b) * r, by * (1 + t * 1.5) + Math.sin(b) * r, -0.35 - t * len);
        aT.push(t);
        aArm.push(k);
      }
    }
    for (let i = 0; i < rings; i++) {
      for (let j = 0; j < radial; j++) {
        const a0 = i * radial + j, a1 = i * radial + ((j + 1) % radial);
        idx.push(a0, a1, a0 + radial, a1, a1 + radial, a0 + radial);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    armData.push({ g, aT, aArm });
  }
  const red = new THREE.Color(0.48, 0.1, 0.08);
  const pale = new THREE.Color(0.75, 0.42, 0.34);
  const prepared = geos.map((g) => {
    stripTo(g, ["position", "normal"]);
    const n = g.attributes.position.count;
    g.setAttribute("aT", new THREE.BufferAttribute(new Float32Array(n), 1));
    g.setAttribute("aArm", new THREE.BufferAttribute(new Float32Array(n).fill(-1), 1));
    return colorize(g, (x, y, z, c) => c.copy(red).lerp(pale, THREE.MathUtils.smoothstep(-y, 0.1, 0.7) * 0.6).multiplyScalar(0.9 + 0.1 * Math.sin(z * 9) * Math.sin(x * 11)));
  });
  for (const { g, aT, aArm } of armData) {
    g.setAttribute("aT", new THREE.Float32BufferAttribute(aT, 1));
    g.setAttribute("aArm", new THREE.Float32BufferAttribute(aArm, 1));
    prepared.push(colorize(g, (x, y, z, c) => c.copy(red).lerp(pale, 0.35 + 0.2 * Math.sin(z * 14))));
  }
  const geo = mergeGeometries(prepared);
  geo.scale(1.25, 1.25, 1.25);
  const jet = { value: 0 };
  const mat = underwater(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.42, metalness: 0.05, side: THREE.DoubleSide }), {
    caustics: false,
    key: "squid",
    uniforms: { uJet: jet },
    vertexHead: "attribute float aT;\nattribute float aArm;\nuniform float uJet;",
    vertex: `
      if (aArm >= 0.0) {
        float bend = pow(aT, 1.5) * mix(1.0, 0.25, uJet);
        float reach = aArm >= 8.0 ? 1.8 : 0.9;
        transformed.x += sin(uTime * 1.3 + aArm * 1.9 + aT * 3.5) * bend * reach;
        transformed.y += cos(uTime * 1.05 + aArm * 2.6 + aT * 2.8) * bend * reach * 0.8;
        transformed.xy *= mix(1.0, 0.35, uJet * aT);
      }`,
  });
  const body = new THREE.Mesh(geo, mat);
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0x0b0d10, roughness: 0.05, metalness: 0.6, emissive: 0x7a8c96, emissiveIntensity: 0.35 });
  const group = new THREE.Group();
  const root = new THREE.Group();
  root.add(body);
  for (const s of [-1, 1]) {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.24, 16, 12), eyeMat);
    eye.position.set(s * 0.62, 0.12, 0.15);
    root.add(eye);
  }
  group.add(root);
  const home = nearAxis(shape, rng, 450, 0.3);
  root.position.copy(home);
  const vel = new THREE.Vector3();
  const target = { pos: home.clone(), radius: 4.2 };
  const want = new THREE.Vector3();
  let side = rng.next() < 0.5 ? -1 : 1;
  return {
    group,
    targets: [target],
    update(dt, t, ctx) {
      dt = Math.min(dt, 1 / 30);
      const toSub = tmpV.copy(ctx.subPos).sub(root.position);
      const dist = toSub.length();
      const subDepth = -ctx.subPos.y;
      let jetting = false;
      if (subDepth > 370 && subDepth < 530) {
        if (dist < 17) {
          // Too close: jet away from the sub, mantle first.
          jetting = true;
          vel.addScaledVector(toSub.normalize(), -14 * dt);
        } else {
          if (Math.sin(t * 0.07) > 0.98) side = -side;
          const a = Math.atan2(ctx.subFwd.x, ctx.subFwd.z) + side * 0.55;
          want.set(ctx.subPos.x + Math.sin(a) * 27, THREE.MathUtils.clamp(ctx.subPos.y + 2, -495, -405), ctx.subPos.z + Math.cos(a) * 27);
          vel.addScaledVector(tmpV2.copy(want).sub(root.position), 0.35 * dt);
        }
      } else {
        want.set(home.x + Math.cos(t * 0.05) * 8, home.y + Math.sin(t * 0.09) * 6, home.z + Math.sin(t * 0.05) * 8);
        vel.addScaledVector(tmpV2.copy(want).sub(root.position), 0.2 * dt);
      }
      vel.multiplyScalar(Math.exp(-dt * (jetting ? 0.6 : 1.4)));
      const sp = vel.length();
      if (sp > 10) vel.multiplyScalar(10 / sp);
      root.position.addScaledVector(vel, dt);
      // Stay inside the rock.
      const d = -root.position.y;
      shape.center(d, tmpC);
      const rx = root.position.x - tmpC.x, rz = root.position.z - tmpC.y;
      const rr = Math.hypot(rx, rz), lim = shape.radius(d) - 9;
      if (rr > lim) {
        root.position.x = tmpC.x + (rx / rr) * lim;
        root.position.z = tmpC.y + (rz / rr) * lim;
      }
      jet.value += ((jetting ? 1 : 0) - jet.value) * (1 - Math.exp(-dt * 3));
      // Mantle points along the motion when moving fast, else turns its side to the sub.
      const yawWant = sp > 2.5 ? Math.atan2(vel.x, vel.z) : Math.atan2(toSub.x, toSub.z) + Math.PI / 2;
      let dy = yawWant - root.rotation.y;
      dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      root.rotation.y += dy * (1 - Math.exp(-dt * 1.2));
      root.rotation.x = Math.sin(t * 0.4) * 0.12;
      target.pos.copy(root.position).addScaledVector(tmpV2.set(Math.sin(root.rotation.y), 0, Math.cos(root.rotation.y)), 2.5);
    },
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Yeti crabs: pale, hairy-clawed crabs walking slow circles around the chimneys, legs stepping in the vertex shader.

function makeCrabs({ shape, rng, tier, tokens, scene }) {
  const geos = [];
  const add = (g, leg, hip) => {
    stripTo(g, ["position", "normal"]);
    const n = g.attributes.position.count;
    g.setAttribute("aLeg", new THREE.BufferAttribute(new Float32Array(n).fill(leg), 1));
    const h = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) h.set([hip.x, hip.y, hip.z], i * 3);
    g.setAttribute("aHip", new THREE.BufferAttribute(h, 3));
    geos.push(g);
  };
  const segment = (a, b, r0, r1) => {
    const len = a.distanceTo(b);
    const g = new THREE.CylinderGeometry(r1, r0, len, 7);
    g.translate(0, len / 2, 0);
    const q = new THREE.Quaternion().setFromUnitVectors(UP, tmpV.copy(b).sub(a).normalize());
    g.applyQuaternion(q);
    g.translate(a.x, a.y, a.z);
    return g;
  };
  const carapace = new THREE.SphereGeometry(0.5, 18, 12);
  carapace.scale(0.62, 0.3, 0.52);
  carapace.translate(0, 0.36, 0);
  add(carapace, -1, new THREE.Vector3());
  let leg = 0;
  for (const s of [-1, 1]) {
    for (let k = 0; k < 4; k++) {
      const z = 0.16 - k * 0.12;
      const hip = new THREE.Vector3(s * 0.26, 0.33, z);
      const knee = new THREE.Vector3(s * 0.62, 0.5, z * 1.4);
      const foot = new THREE.Vector3(s * 0.88, 0.0, z * 1.7);
      add(segment(hip, knee, 0.045, 0.035), leg, hip);
      add(segment(knee, foot, 0.035, 0.012), leg, hip);
      leg++;
    }
    // Claw arm and the hairy pincer.
    const shoulder = new THREE.Vector3(s * 0.2, 0.36, 0.22);
    const elbow = new THREE.Vector3(s * 0.38, 0.42, 0.6);
    add(segment(shoulder, elbow, 0.05, 0.045), -1, shoulder);
    const claw = new THREE.SphereGeometry(0.16, 12, 8);
    claw.scale(0.75, 0.7, 1.9);
    const cp = claw.attributes.position;
    for (let i = 0; i < cp.count; i++) {
      const f = 1 + 0.12 * Math.sin(cp.getX(i) * 60) * Math.sin(cp.getZ(i) * 50) * Math.sin(cp.getY(i) * 40);
      cp.setXYZ(i, cp.getX(i) * f, cp.getY(i) * f, cp.getZ(i) * f);
    }
    claw.computeVertexNormals();
    claw.translate(s * 0.44, 0.42, 0.9);
    add(claw, -2, shoulder);
  }
  const shell = new THREE.Color(0.9, 0.84, 0.74);
  const fuzz = new THREE.Color(0.98, 0.95, 0.86);
  const prepared = geos.map((g) => {
    const legId = g.attributes.aLeg.array[0];
    return colorize(g, (x, y, z, c) => {
      if (legId === -2) c.copy(fuzz).multiplyScalar(z > 1.12 ? 0.35 : 1);
      else c.copy(shell).multiplyScalar(legId >= 0 ? 0.92 : 1 - 0.15 * Math.max(0, 0.3 - y));
    });
  });
  const geo = mergeGeometries(prepared);
  const walk = { value: 1 };
  const mat = underwater(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.68, metalness: 0.0 }), {
    caustics: false,
    key: "crab",
    uniforms: { uWalk: walk },
    vertexHead: "attribute float aLeg;\nattribute vec3 aHip;\nuniform float uWalk;",
    vertex: `
      if (aLeg >= 0.0) {
        #ifdef USE_INSTANCING
          float cPhase = instanceMatrix[3].x * 1.3 + instanceMatrix[3].z * 0.7;
        #else
          float cPhase = 0.0;
        #endif
        float stepW = sin(uTime * 6.5 + aLeg * 1.5708 + cPhase);
        float ang = stepW * 0.32 * uWalk;
        vec3 rel = transformed - aHip;
        float ca = cos(ang), sa = sin(ang);
        rel = vec3(rel.x * ca + rel.z * sa, rel.y, -rel.x * sa + rel.z * ca);
        rel.y += max(0.0, cos(uTime * 6.5 + aLeg * 1.5708 + cPhase)) * 0.07 * length(rel.xz) * uWalk;
        transformed = aHip + rel;
      }`,
  });
  const count = 6;
  const mesh = new THREE.InstancedMesh(geo, mat, count);
  mesh.frustumCulled = false;
  const group = new THREE.Group();
  group.add(mesh);
  const crabs = [];
  const trench = scene.userData.trench;
  for (let i = 0; i < count; i++) {
    const vt = trench.vents[i % trench.vents.length];
    crabs.push({
      vt, angle: rng.range(0, Math.PI * 2), r: vt.radius + rng.range(1.6, 3.2), speed: rng.range(0.05, 0.11) * (rng.next() < 0.5 ? -1 : 1),
      scale: rng.range(1.25, 1.6), target: { pos: new THREE.Vector3(), radius: 0.85 },
    });
  }
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const sc = new THREE.Vector3();
  return {
    group,
    targets: crabs.map((c) => c.target),
    update(dt, t) {
      for (let i = 0; i < crabs.length; i++) {
        const c = crabs[i];
        c.angle += dt * c.speed * (0.6 + 0.4 * Math.sin(t * 0.3 + i));
        const x = c.vt.x + Math.cos(c.angle) * c.r, z = c.vt.z + Math.sin(c.angle) * c.r;
        const y = trench.floorHeight(x, z) - 0.05;
        tmpV.set(x, y, z);
        q.setFromAxisAngle(UP, -c.angle + (c.speed > 0 ? 0 : Math.PI));
        m.compose(tmpV, q, sc.setScalar(c.scale));
        mesh.setMatrixAt(i, m);
        c.target.pos.set(x, y + 0.5 * c.scale, z);
      }
      mesh.instanceMatrix.needsUpdate = true;
    },
  };
}
