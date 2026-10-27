// The drone in the scene: the glTF model (or the same shape built from parts), rotor blur discs, blinking position
// lights, and a package on a three-segment verlet rope that swings into turns and lags on a climb.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { buildDroneShape, droneMaterials } from "./droneShape.js";

const SEGMENT = 0.55;
const GRAVITY = -9.8;

export async function loadDroneModel(url) {
  try {
    const gltf = await Promise.race([
      new GLTFLoader().loadAsync(url),
      new Promise((_, reject) => setTimeout(() => reject(new Error("slow")), 6000)),
    ]);
    return gltf.scene.getObjectByName("Drone") || gltf.scene;
  } catch {
    return buildDroneShape(droneMaterials());
  }
}

function blurDiscMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uSpin: { value: 0 }, uTint: { value: new THREE.Color(0xb8c0d0) }, uStrength: { value: 1 } },
    vertexShader: /* glsl */ `
      varying vec2 vP;
      void main() {
        vP = position.xy;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uSpin;
      uniform vec3 uTint;
      uniform float uStrength;
      varying vec2 vP;
      void main() {
        float r = length(vP) / 0.29;
        if (r > 1.0) discard;
        float a = atan(vP.y, vP.x) + uSpin;
        // Two smeared blades: brighter at the tips where the blade moves fastest.
        float blades = pow(abs(cos(a)), 6.0);
        float alpha = (0.07 + 0.2 * blades) * smoothstep(0.18, 0.45, r) * smoothstep(1.0, 0.92, r) * uStrength;
        alpha += smoothstep(0.9, 0.97, r) * smoothstep(1.0, 0.97, r) * 0.25 * uStrength;
        gl_FragColor = vec4(uTint * alpha * 1.4, alpha);
        #include <colorspace_fragment>
      }
    `,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}

function glowMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uScale: { value: 600 } },
    vertexShader: /* glsl */ `
      attribute vec3 aColor;
      attribute float aSize;
      uniform float uScale;
      varying vec3 vColor;
      void main() {
        vColor = aColor;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = clamp(aSize * uScale / -mv.z, 0.0, 80.0);
      }
    `,
    fragmentShader: /* glsl */ `
      varying vec3 vColor;
      void main() {
        vec2 c = gl_PointCoord * 2.0 - 1.0;
        float r = dot(c, c);
        if (r > 1.0) discard;
        float g = exp(-r * 10.0) * 2.5 + exp(-r * 3.0) * 0.4;
        gl_FragColor = vec4(vColor * g, g);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}

export function createDrone(model, envTexture) {
  const root = new THREE.Group();
  root.name = "courier";
  const body = new THREE.Group();
  root.add(body);
  body.add(model);
  model.scale.setScalar(1.45);

  const materials = {};
  model.traverse((o) => {
    if (o.isMesh) {
      materials[o.material.name] = o.material;
      if (o.material.isMeshStandardMaterial) {
        o.material.envMap = envTexture;
        o.material.envMapIntensity = 1.2;
      }
    }
  });

  // Rotor blur discs replace the props once they spin up.
  const rotors = [];
  const discGeometry = new THREE.CircleGeometry(0.29, 48);
  for (let i = 0; i < 4; i++) {
    const hub = model.getObjectByName(`Rotor${i}`);
    if (!hub) continue;
    const disc = new THREE.Mesh(discGeometry, blurDiscMaterial());
    disc.rotation.x = -Math.PI / 2;
    disc.position.y = 0.005;
    disc.renderOrder = 6;
    hub.add(disc);
    const prop = hub.children.find((c) => c.isMesh && c !== disc);
    rotors.push({ hub, disc, prop, dir: i % 3 === 0 ? 1 : -1 });
  }

  // Position-light glows, so the lights bloom and read at a distance.
  const lightNames = ["NavRed", "NavGreen", "Strobe", "Headlight"];
  const lightNodes = lightNames.map((n) => model.getObjectByName(n));
  const gGeometry = new THREE.BufferGeometry();
  gGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(12), 3));
  gGeometry.setAttribute("aColor", new THREE.BufferAttribute(new Float32Array([1, 0.08, 0.06, 0.1, 1, 0.35, 1, 1, 1, 1, 0.95, 0.85]), 3));
  gGeometry.setAttribute("aSize", new THREE.BufferAttribute(new Float32Array([0.5, 0.5, 0.7, 0.8]), 1));
  const glows = new THREE.Points(gGeometry, glowMaterial());
  glows.frustumCulled = false;
  glows.renderOrder = 7;
  lightNodes.forEach((node, i) => node && gGeometry.getAttribute("position").setXYZ(i, node.position.x, node.position.y, node.position.z + (i === 3 ? 0.03 : 0)));
  model.add(glows);

  // The headlight throws a cone ahead, and a soft light under the drone picks out the package.
  const under = new THREE.PointLight(0xffffff, 6, 7, 1.6);
  under.position.set(0, -0.6, 0);
  body.add(under);

  // Package and rope.
  const pkg = new THREE.Group();
  const box = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.34, 0.46), new THREE.MeshStandardMaterial({ color: 0x8a6a48, roughness: 0.85 }));
  const tape = new THREE.Mesh(new THREE.BoxGeometry(0.47, 0.345, 0.08), new THREE.MeshStandardMaterial({ color: 0xff2d95, roughness: 0.5, emissive: 0xff2d95, emissiveIntensity: 0.6 }));
  const tape2 = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.345, 0.47), tape.material);
  pkg.add(box, tape, tape2);
  pkg.visible = false;
  const ropeMaterial = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.6 });
  const ropeGeometry = new THREE.CylinderGeometry(0.012, 0.012, 1, 6).translate(0, 0.5, 0);
  const ropes = [0, 1, 2].map(() => {
    const r = new THREE.Mesh(ropeGeometry, ropeMaterial);
    r.visible = false;
    return r;
  });
  const holder = new THREE.Group();
  holder.add(pkg, ...ropes);

  const points = [0, 1, 2, 3].map(() => ({ p: new THREE.Vector3(), q: new THREE.Vector3() }));
  const hookNode = model.getObjectByName("Hook");
  const hookWorld = new THREE.Vector3();
  const up = new THREE.Vector3(0, 1, 0);
  const tmp = new THREE.Vector3();
  let carrying = false;
  let spin = 0;
  let blink = 0;

  const glowColor = gGeometry.getAttribute("aColor");

  function hookPosition(out) {
    if (hookNode) hookNode.getWorldPosition(out);
    else out.copy(root.position).add(tmp.set(0, -0.25, 0));
    return out;
  }

  return {
    root,
    holder,
    materials,
    setPalette(palette) {
      if (materials.Body) materials.Body.color.copy(palette.droneBody);
      if (materials.Trim) {
        materials.Trim.color.copy(palette.droneTrim);
        materials.Trim.emissive.copy(palette.droneTrim);
      }
      tape.material.color.copy(palette.droneTrim);
      tape.material.emissive.copy(palette.droneTrim);
      under.color.copy(palette.droneTrim).lerp(new THREE.Color(1, 1, 1), 0.5);
    },
    setGlowScale(scale) {
      glows.material.uniforms.uScale.value = scale;
    },
    attachPackage(at) {
      carrying = true;
      pkg.visible = true;
      ropes.forEach((r) => (r.visible = true));
      hookPosition(hookWorld);
      for (let i = 0; i < 4; i++) {
        const t = i / 3;
        points[i].p.lerpVectors(hookWorld, at, t);
        points[i].q.copy(points[i].p);
      }
    },
    releasePackage() {
      carrying = false;
      pkg.visible = false;
      ropes.forEach((r) => (r.visible = false));
      return points[3].p.clone();
    },
    get carrying() {
      return carrying;
    },
    packagePosition() {
      return points[3].p;
    },
    // Called at the fixed 60 Hz step.
    step(dt) {
      if (!carrying) return;
      hookPosition(hookWorld);
      points[0].p.copy(hookWorld);
      points[0].q.copy(hookWorld);
      for (let i = 1; i < 4; i++) {
        const pt = points[i];
        tmp.copy(pt.p).sub(pt.q).multiplyScalar(0.985);
        pt.q.copy(pt.p);
        pt.p.add(tmp);
        pt.p.y += GRAVITY * dt * dt * (i === 3 ? 1.6 : 1);
        if (pt.p.y < 0.2) pt.p.y = 0.2;
      }
      for (let k = 0; k < 6; k++) {
        for (let i = 0; i < 3; i++) {
          const a = points[i].p, b = points[i + 1].p;
          tmp.copy(b).sub(a);
          const d = tmp.length() || 1e-6;
          const diff = (d - SEGMENT) / d;
          if (i === 0) b.addScaledVector(tmp, -diff);
          else {
            a.addScaledVector(tmp, diff * 0.5);
            b.addScaledVector(tmp, -diff * 0.5);
          }
        }
      }
    },
    // Called once per rendered frame.
    update(dt, flight, time, reduced) {
      root.position.copy(flight.pos);
      body.rotation.set(0, 0, 0);
      body.rotation.order = "YXZ";
      body.rotation.y = flight.heading;
      body.rotation.x = flight.tiltForward;
      body.rotation.z = -flight.tiltSide;
      body.position.y = reduced ? 0 : Math.sin(time * 2.1) * 0.05;
      spin += dt * (38 + flight.throttle * 30);
      for (const r of rotors) {
        r.hub.rotation.y = spin * r.dir;
        r.disc.material.uniforms.uSpin.value = spin * r.dir * 0.12;
        if (r.prop) r.prop.visible = false;
      }
      // Lights: steady nav lights, a double-blink strobe on the tail.
      blink = time % 1.4;
      const strobe = blink < 0.06 || (blink > 0.16 && blink < 0.22) ? 1 : 0;
      const s = strobe ? 1 : 0;
      glowColor.setXYZ(2, s, s, s);
      glowColor.needsUpdate = true;
      if (!carrying) return;
      // Package hangs from the last rope point, turned along the last segment.
      const last = points[3].p;
      pkg.position.copy(last);
      tmp.copy(points[2].p).sub(last).normalize();
      pkg.quaternion.setFromUnitVectors(up, tmp);
      pkg.rotateY(flight.heading);
      pkg.position.addScaledVector(tmp, -0.17);
      for (let i = 0; i < 3; i++) {
        const a = points[i].p, b = points[i + 1].p;
        const r = ropes[i];
        r.position.copy(a);
        tmp.copy(b).sub(a);
        const len = tmp.length();
        r.scale.set(1, len, 1);
        r.quaternion.setFromUnitVectors(up, tmp.normalize());
      }
    },
  };
}
