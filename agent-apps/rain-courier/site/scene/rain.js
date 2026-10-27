// Rain: streaks in a box that follows the camera, stretched along their motion relative to the drone in the vertex
// shader; and splashes as rings on the roofs near the drone.
import * as THREE from "three";

export const RAIN_LAYER = 1;
const BOX = new THREE.Vector3(70, 46, 70);
const FALL = 24;

export function buildRain(shared, maxCount) {
  const geometry = new THREE.InstancedBufferGeometry();
  // Two triangles; x picks the side of the streak, y picks its head (0) or its tail (1).
  geometry.setAttribute("position", new THREE.Float32BufferAttribute([-1, 0, 0, 1, 0, 0, 1, 1, 0, -1, 1, 0], 3));
  geometry.setIndex([0, 1, 2, 0, 2, 3]);
  const seeds = new Float32Array(maxCount * 4);
  let s = 1234567;
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < maxCount; i++) seeds.set([rand(), rand(), rand(), rand()], i * 4);
  geometry.setAttribute("aSeed", new THREE.InstancedBufferAttribute(seeds, 4));
  geometry.instanceCount = maxCount;

  const material = new THREE.ShaderMaterial({
    uniforms: {
      ...shared,
      uBox: { value: BOX.clone() },
      uCenter: { value: new THREE.Vector3() },
      uRel: { value: new THREE.Vector3(0, -FALL, 0) },
      uWind: { value: new THREE.Vector3(3.5, 0, 1.2) },
      uRain: { value: new THREE.Color() },
      uPixel: { value: 1 },
    },
    vertexShader: /* glsl */ `
      attribute vec4 aSeed;
      uniform vec3 uBox;
      uniform vec3 uCenter;
      uniform vec3 uRel;
      uniform vec3 uWind;
      uniform float uTime;
      uniform float uPixel;
      varying float vFade;
      varying float vAlong;
      varying float vAcross;
      void main() {
        float speed = 0.85 + aSeed.w * 0.3;
        vec3 fall = vec3(uWind.x, -${FALL.toFixed(1)}, uWind.z) * speed;
        vec3 p = aSeed.xyz * uBox + fall * uTime;
        // Wrap into the box around the camera so the rain never runs out.
        p = uCenter + mod(p - uCenter + uBox * 0.5, uBox) - uBox * 0.5;
        vec3 rel = uRel * speed;
        float len = clamp(length(rel) * 0.045, 0.35, 2.8);
        vec3 dir = normalize(rel);
        vec3 toCam = normalize(cameraPosition - p);
        vec3 side = normalize(cross(dir, toCam));
        float dist = length(cameraPosition - p);
        float width = max(0.014, dist * 0.0024 / uPixel);
        vec3 world = p - dir * len * position.y + side * width * position.x;
        vAlong = position.y;
        vAcross = position.x;
        float edge = min(min(p.x - (uCenter.x - uBox.x * 0.5), (uCenter.x + uBox.x * 0.5) - p.x), min(p.z - (uCenter.z - uBox.z * 0.5), (uCenter.z + uBox.z * 0.5) - p.z));
        vFade = smoothstep(0.0, 8.0, edge) * smoothstep(1.2, 4.0, dist) * (0.55 + 0.45 * aSeed.w) * step(0.0, p.y);
        gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uRain;
      uniform vec3 uFlashColor;
      uniform float uFlash;
      varying float vFade;
      varying float vAlong;
      varying float vAcross;
      void main() {
        float a = (1.0 - abs(vAcross)) * smoothstep(0.0, 0.25, vAlong) * (1.0 - vAlong * 0.6) * vFade;
        vec3 c = (uRain + uFlashColor * uFlash * 1.5) * a * 0.9;
        gl_FragColor = vec4(c, a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  mesh.renderOrder = 5;
  mesh.name = "rain";
  mesh.layers.set(RAIN_LAYER);
  return {
    mesh,
    setCount(n) {
      geometry.instanceCount = Math.min(n, maxCount);
    },
    update(cameraPos, droneVel) {
      const u = material.uniforms;
      u.uCenter.value.set(cameraPos.x, cameraPos.y + 6, cameraPos.z);
      // Streaks stretch along the rain's motion as the drone sees it: falling, blown, and swept back by flight.
      u.uRel.value.set(u.uWind.value.x - droneVel.x, -FALL - droneVel.y, u.uWind.value.z - droneVel.z);
    },
    setPalette(palette) {
      u().uRain.value.copy(palette.rain).multiplyScalar(palette.light ? 0.6 : 1);
    },
  };
  function u() {
    return material.uniforms;
  }
}

// Splashes: rings that open and fade on the roofs around the drone; a few are respawned every frame.
export function buildSplashes(plan, shared, count) {
  const geometry = new THREE.InstancedBufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute([-1, 0, -1, 1, 0, -1, 1, 0, 1, -1, 0, 1], 3));
  geometry.setIndex([0, 2, 1, 0, 3, 2]);
  const at = new Float32Array(count * 4);
  const attr = new THREE.InstancedBufferAttribute(at, 4);
  attr.setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute("aAt", attr);
  geometry.instanceCount = count;
  const material = new THREE.ShaderMaterial({
    uniforms: { ...shared, uRain: { value: new THREE.Color() } },
    vertexShader: /* glsl */ `
      attribute vec4 aAt;
      uniform float uTime;
      varying vec2 vP;
      varying float vAge;
      void main() {
        float age = clamp((uTime - aAt.w) / 0.55, 0.0, 1.0);
        vAge = age;
        vP = position.xz;
        float r = 0.15 + age * 0.55;
        vec3 world = aAt.xyz + vec3(position.x * r, 0.03, position.z * r);
        gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uRain;
      varying vec2 vP;
      varying float vAge;
      void main() {
        float r = length(vP);
        float ring = smoothstep(0.16, 0.0, abs(r - 0.82)) * (1.0 - vAge);
        float a = ring * step(vAge, 0.999);
        gl_FragColor = vec4(uRain * a * 0.8, a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  mesh.renderOrder = 4;
  mesh.name = "splashes";
  mesh.layers.set(RAIN_LAYER);

  // Roof tops as rectangles; splashes land on those near the drone, refreshed twice a second.
  const roofs = [];
  for (const b of plan.boxes) if (b.solid && !b.frame && b.w > 2 && b.d > 2) roofs.push(b);
  let near = roofs;
  let refreshAt = 0;
  let next = 0;
  let seed = 99;
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  return {
    mesh,
    update(time, center) {
      if (time >= refreshAt) {
        refreshAt = time + 0.5;
        near = roofs.filter((b) => Math.abs(b.x - center.x) < 70 && Math.abs(b.z - center.z) < 70 && b.y1 < center.y + 30);
        if (near.length === 0) near = roofs;
      }
      const perFrame = Math.ceil(count / 33);
      for (let k = 0; k < perFrame; k++) {
        const b = near[Math.floor(rand() * near.length)];
        const i = next;
        next = (next + 1) % count;
        at[i * 4] = b.x + (rand() - 0.5) * (b.w - 0.6);
        at[i * 4 + 1] = b.y1;
        at[i * 4 + 2] = b.z + (rand() - 0.5) * (b.d - 0.6);
        at[i * 4 + 3] = time - rand() * 0.05;
      }
      attr.needsUpdate = true;
    },
    setPalette(palette) {
      material.uniforms.uRain.value.copy(palette.rain).multiplyScalar(palette.light ? 0.5 : 0.8);
    },
  };
}
