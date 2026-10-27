// The route: a bezier ribbon from the drone to the next pickup or drop, pulsing in the theme's accent; the beacon and
// pad that mark a pickup roof or a drop balcony; lit doors on every balcony; the ring of light on a delivery; and
// the spark burst of a crash.
import * as THREE from "three";

const SEGMENTS = 72;

export function buildRoute(shared) {
  const group = new THREE.Group();
  group.name = "route";

  // Ribbon: a camera-facing strip whose centerline is rewritten every frame.
  const verts = (SEGMENTS + 1) * 2;
  const center = new Float32Array(verts * 3);
  const tangent = new Float32Array(verts * 3);
  const along = new Float32Array(verts * 2);
  const index = [];
  for (let i = 0; i <= SEGMENTS; i++) {
    along.set([i / SEGMENTS, -1], i * 4);
    along.set([i / SEGMENTS, 1], i * 4 + 2);
    if (i < SEGMENTS) {
      const a = i * 2;
      index.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const ribbonGeometry = new THREE.BufferGeometry();
  const centerAttr = new THREE.BufferAttribute(center, 3).setUsage(THREE.DynamicDrawUsage);
  const tangentAttr = new THREE.BufferAttribute(tangent, 3).setUsage(THREE.DynamicDrawUsage);
  ribbonGeometry.setAttribute("position", centerAttr);
  ribbonGeometry.setAttribute("aTangent", tangentAttr);
  ribbonGeometry.setAttribute("aAlong", new THREE.BufferAttribute(along, 2));
  ribbonGeometry.setIndex(index);
  const ribbonMaterial = new THREE.ShaderMaterial({
    uniforms: { ...shared, uColor: { value: new THREE.Color() }, uShow: { value: 1 }, uLength: { value: 100 } },
    vertexShader: /* glsl */ `
      attribute vec3 aTangent;
      attribute vec2 aAlong;
      varying float vT;
      varying float vSide;
      varying vec3 vWorld;
      void main() {
        vec3 toCam = normalize(cameraPosition - position);
        vec3 side = normalize(cross(aTangent, toCam));
        float dist = length(cameraPosition - position);
        float width = max(0.28, dist * 0.004);
        vec3 world = position + side * width * aAlong.y;
        vT = aAlong.x;
        vSide = aAlong.y;
        vWorld = world;
        gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uShow;
      uniform float uLength;
      uniform float uTime;
      varying float vT;
      varying float vSide;
      varying vec3 vWorld;
      void main() {
        float edge = 1.0 - abs(vSide);
        float core = smoothstep(0.0, 0.6, edge);
        // Chevrons of light run from the drone toward the target.
        float d = vT * uLength / 3.2 - uTime * 2.4;
        float chev = smoothstep(0.55, 0.0, abs(fract(d + abs(vSide) * 0.25) - 0.5) * 2.0 - 0.1);
        float pulse = 0.75 + 0.25 * sin(uTime * 3.0);
        float ends = smoothstep(0.0, 0.05, vT) * smoothstep(1.0, 0.94, vT);
        float a = (0.28 * core + 0.9 * chev * core) * ends * pulse * uShow;
        gl_FragColor = vec4(uColor * a * 2.2, a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  });
  const ribbon = new THREE.Mesh(ribbonGeometry, ribbonMaterial);
  ribbon.frustumCulled = false;
  ribbon.renderOrder = 8;
  group.add(ribbon);

  // Beacon: a column of light over the target, so it reads from across town.
  const beaconMaterial = new THREE.ShaderMaterial({
    uniforms: { ...shared, uColor: { value: new THREE.Color() } },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      varying vec3 vWorld;
      void main() {
        vUv = uv;
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uTime;
      varying vec2 vUv;
      varying vec3 vWorld;
      void main() {
        float fade = pow(1.0 - vUv.y, 2.2);
        float bands = 0.6 + 0.4 * smoothstep(0.3, 0.0, abs(fract(vUv.y * 18.0 - uTime * 0.9) - 0.5));
        float a = fade * bands * 0.32;
        gl_FragColor = vec4(uColor * a * 1.6, a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  });
  const beacon = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 1.1, 120, 20, 1, true).translate(0, 60, 0), beaconMaterial);
  beacon.renderOrder = 7;
  group.add(beacon);

  // Pad: a lit square with chevrons on the pickup roof, or a ring under the balcony hover point.
  const padMaterial = new THREE.ShaderMaterial({
    uniforms: { ...shared, uColor: { value: new THREE.Color() }, uKind: { value: 0 } },
    vertexShader: /* glsl */ `
      varying vec2 vP;
      void main() {
        vP = position.xz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uTime;
      uniform float uKind;
      varying vec2 vP;
      void main() {
        vec2 p = vP / 3.0;
        float a;
        if (uKind < 0.5) {
          vec2 q = abs(p);
          float box = smoothstep(0.06, 0.0, abs(max(q.x, q.y) - 0.86));
          float inner = smoothstep(0.04, 0.0, abs(max(q.x, q.y) - 0.62)) * 0.5;
          float chev = smoothstep(0.06, 0.0, abs(fract(q.y * 2.4 - q.x * 1.2 - uTime * 0.8) - 0.5) - 0.12) * step(max(q.x, q.y), 0.5);
          a = box + inner + chev * 0.6;
        } else {
          float r = length(p);
          float ring = smoothstep(0.05, 0.0, abs(r - 0.82)) + smoothstep(0.03, 0.0, abs(r - fract(uTime * 0.6) * 0.82)) * (1.0 - fract(uTime * 0.6));
          a = ring;
        }
        a *= 0.75 + 0.25 * sin(uTime * 4.0);
        gl_FragColor = vec4(uColor * a * 2.4, a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    polygonOffset: true,
    polygonOffsetFactor: -2,
  });
  const pad = new THREE.Mesh(new THREE.PlaneGeometry(6, 6).rotateX(-Math.PI / 2), padMaterial);
  pad.renderOrder = 7;
  group.add(pad);

  // Delivery ring: opens across the balcony and fades.
  const burstMaterial = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color() }, uAge: { value: 1 } },
    vertexShader: /* glsl */ `
      varying vec2 vP;
      void main() {
        vP = position.xz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uAge;
      varying vec2 vP;
      void main() {
        float r = length(vP);
        float edge = mix(0.05, 1.0, pow(uAge, 0.5));
        float ring = smoothstep(0.06, 0.0, abs(r - edge)) * (1.0 - uAge);
        float fill = smoothstep(edge, 0.0, r) * 0.25 * (1.0 - uAge);
        float a = ring + fill;
        gl_FragColor = vec4(uColor * a * 4.0, a);
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  });
  const burst = new THREE.Mesh(new THREE.PlaneGeometry(2, 2).rotateX(-Math.PI / 2), burstMaterial);
  burst.visible = false;
  burst.renderOrder = 9;
  group.add(burst);

  // Sparks for a crash: a small pool of points thrown out and pulled down.
  const SPARKS = 90;
  const sparkPos = new Float32Array(SPARKS * 3);
  const sparkVel = new Float32Array(SPARKS * 3);
  const sparkLife = new Float32Array(SPARKS);
  const sparkGeometry = new THREE.BufferGeometry();
  const sparkAttr = new THREE.BufferAttribute(sparkPos, 3).setUsage(THREE.DynamicDrawUsage);
  const lifeAttr = new THREE.BufferAttribute(sparkLife, 1).setUsage(THREE.DynamicDrawUsage);
  sparkGeometry.setAttribute("position", sparkAttr);
  sparkGeometry.setAttribute("aLife", lifeAttr);
  const sparks = new THREE.Points(
    sparkGeometry,
    new THREE.ShaderMaterial({
      uniforms: { uScale: { value: 600 } },
      vertexShader: /* glsl */ `
        attribute float aLife;
        uniform float uScale;
        varying float vLife;
        void main() {
          vLife = aLife;
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = aLife <= 0.0 ? 0.0 : clamp(0.16 * uScale / -mv.z, 1.0, 24.0);
        }
      `,
      fragmentShader: /* glsl */ `
        varying float vLife;
        void main() {
          vec2 c = gl_PointCoord * 2.0 - 1.0;
          float r = dot(c, c);
          if (r > 1.0 || vLife <= 0.0) discard;
          vec3 hot = mix(vec3(1.0, 0.35, 0.08), vec3(1.0, 0.95, 0.75), vLife);
          float g = exp(-r * 4.0) * vLife * 4.0;
          gl_FragColor = vec4(hot * g, g);
        }
      `,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  sparks.frustumCulled = false;
  sparks.renderOrder = 9;
  group.add(sparks);
  let sparksAlive = 0;
  let sparkSeed = 7;
  const rnd = () => ((sparkSeed = (sparkSeed * 16807) % 2147483647) / 2147483647);

  // Lit doors behind every balcony, one instanced quad each.
  let doors = null;

  const p0 = new THREE.Vector3(), p1 = new THREE.Vector3(), p2 = new THREE.Vector3(), p3 = new THREE.Vector3();
  const pt = new THREE.Vector3(), tg = new THREE.Vector3();
  let burstAge = 1;
  let burstOn = false;
  let show = 1;
  let showFor = 8;

  return {
    group,
    addDoors(balconies, palette) {
      const geometry = new THREE.PlaneGeometry(1.5, 2.4).translate(0, 1.2, 0);
      const material = new THREE.MeshBasicMaterial({ color: palette.windowWarm.clone().multiplyScalar(2.2), toneMapped: true });
      doors = new THREE.InstancedMesh(geometry, material, balconies.length);
      const m = new THREE.Matrix4();
      balconies.forEach((b, i) => {
        m.makeRotationY(Math.atan2(b.nx, b.nz));
        m.setPosition(b.x + b.nx * 0.03, b.y + 0.9, b.z + b.nz * 0.03);
        doors.setMatrixAt(i, m);
      });
      doors.computeBoundingSphere();
      group.add(doors);
    },
    setPalette(palette, accent) {
      ribbonMaterial.uniforms.uColor.value.copy(accent);
      burstMaterial.uniforms.uColor.value.copy(accent);
      if (doors) doors.material.color.copy(palette.windowWarm).multiplyScalar(2.2);
    },
    setTarget(target, kind, color) {
      beacon.position.copy(target.base);
      beaconMaterial.uniforms.uColor.value.copy(color);
      padMaterial.uniforms.uColor.value.copy(color);
      padMaterial.uniforms.uKind.value = kind === "pickup" ? 0 : 1;
      pad.position.copy(target.base).add(pt.set(0, kind === "pickup" ? 0.06 : 0.05, 0));
      pad.scale.setScalar(kind === "pickup" ? 1 : 0.7);
      pad.rotation.y = kind === "pickup" ? 0 : Math.atan2(target.nx || 0, target.nz || 0);
      beacon.visible = pad.visible = true;
      this.reveal();
    },
    clearTarget() {
      beacon.visible = pad.visible = false;
    },
    reveal() {
      show = 1;
      showFor = 8;
    },
    burstAt(position) {
      burst.position.copy(position);
      burst.scale.setScalar(5.5);
      burstAge = 0;
      burstOn = true;
      burst.visible = true;
    },
    sparksAt(position, scale = 1) {
      for (let i = 0; i < SPARKS; i++) {
        sparkPos.set([position.x, position.y, position.z], i * 3);
        const a = rnd() * Math.PI * 2, e = rnd() * 1.2 - 0.2;
        const v = (4 + rnd() * 9) * scale;
        sparkVel.set([Math.cos(a) * Math.cos(e) * v, Math.sin(e) * v + 2, Math.sin(a) * Math.cos(e) * v], i * 3);
        sparkLife[i] = 0.6 + rnd() * 0.4;
      }
      sparksAlive = 1.2;
    },
    setPointScale(scale) {
      sparks.material.uniforms.uScale.value = scale;
    },
    // Rebuilds the ribbon from the drone to the target, arcing over the roofs in between.
    update(dt, from, target, cruise) {
      if (target) {
        p0.copy(from).add(pt.set(0, -0.5, 0));
        p3.copy(target.point);
        const lift = Math.max(cruise, p0.y, p3.y);
        const horiz = Math.hypot(p3.x - p0.x, p3.z - p0.z);
        p1.set(p0.x + (p3.x - p0.x) * 0.25, Math.max(p0.y, lift + 2), p0.z + (p3.z - p0.z) * 0.25);
        p2.set(p3.x - (p3.x - p0.x) * 0.15, Math.max(p3.y + Math.min(horiz * 0.4, 30), lift + 2), p3.z - (p3.z - p0.z) * 0.15);
        let length = 0;
        let prevX = p0.x, prevY = p0.y, prevZ = p0.z;
        for (let i = 0; i <= SEGMENTS; i++) {
          const t = i / SEGMENTS, u = 1 - t;
          const b0 = u * u * u, b1 = 3 * u * u * t, b2 = 3 * u * t * t, b3 = t * t * t;
          pt.set(0, 0, 0).addScaledVector(p0, b0).addScaledVector(p1, b1).addScaledVector(p2, b2).addScaledVector(p3, b3);
          const d0 = -3 * u * u, d1 = 3 * u * u - 6 * u * t, d2 = 6 * u * t - 3 * t * t, d3 = 3 * t * t;
          tg.set(0, 0, 0).addScaledVector(p0, d0).addScaledVector(p1, d1).addScaledVector(p2, d2).addScaledVector(p3, d3).normalize();
          for (let s = 0; s < 2; s++) {
            const k = i * 2 + s;
            center[k * 3] = pt.x; center[k * 3 + 1] = pt.y; center[k * 3 + 2] = pt.z;
            tangent[k * 3] = tg.x; tangent[k * 3 + 1] = tg.y; tangent[k * 3 + 2] = tg.z;
          }
          length += Math.hypot(pt.x - prevX, pt.y - prevY, pt.z - prevZ);
          prevX = pt.x; prevY = pt.y; prevZ = pt.z;
        }
        centerAttr.needsUpdate = true;
        tangentAttr.needsUpdate = true;
        ribbonMaterial.uniforms.uLength.value = length;
        ribbon.visible = true;
        showFor -= dt;
        const goal = showFor > 0 ? 1 : 0.22;
        show += (goal - show) * Math.min(1, dt * 2);
        ribbonMaterial.uniforms.uShow.value = show;
      } else {
        ribbon.visible = false;
      }
      if (burstOn) {
        burstAge = Math.min(1, burstAge + dt / 0.9);
        burstMaterial.uniforms.uAge.value = burstAge;
        if (burstAge >= 1) burstOn = burst.visible = false;
      }
      if (sparksAlive > 0) {
        sparksAlive -= dt;
        for (let i = 0; i < SPARKS; i++) {
          if (sparkLife[i] <= 0) continue;
          sparkVel[i * 3 + 1] -= 14 * dt;
          sparkPos[i * 3] += sparkVel[i * 3] * dt;
          sparkPos[i * 3 + 1] += sparkVel[i * 3 + 1] * dt;
          sparkPos[i * 3 + 2] += sparkVel[i * 3 + 2] * dt;
          sparkLife[i] -= dt * 1.1;
        }
        sparkAttr.needsUpdate = true;
        lifeAttr.needsUpdate = true;
      }
    },
  };
}
