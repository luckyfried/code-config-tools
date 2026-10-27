// Assembles the world: renderer, trench, water, light, snow, creatures, the sub, the camera rig, and the post stack.
// One export, createWorld, and one per-frame call, update(dt, t, frame), that the game drives.
import * as THREE from "three";
import { createRenderer } from "./renderer.js";
import { createTrenchShape, buildTrench } from "./trench.js";
import { createSurface, createSunShafts } from "./water.js";
import { createLights, createHeadlights } from "./lights.js";
import { createSnow } from "./snow.js";
import { createCreatures } from "./creatures.js";
import { createCameraRig } from "./camera.js";
import { createPost } from "./post.js";
import { loadSubmarine } from "./objects.js";
import { shared } from "./materials.js";
import { createRng } from "../game/rng.js";

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

export async function createWorld({ canvas, tier, tokens, seed, include, reduced }) {
  const rng = createRng(seed);
  const shape = createTrenchShape(rng.fork("shape"));
  const renderer = createRenderer(canvas, tier);
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x000000, 0.02);
  scene.background = new THREE.Color();
  scene.environment = makeEnvironment(renderer, tokens);

  const trench = buildTrench({ shape, tier, tokens, rng: rng.fork("trench") });
  scene.add(trench.group);
  scene.userData.trench = trench;
  const surface = createSurface();
  scene.add(surface);
  const shafts = createSunShafts(tokens, rng.fork("shafts"), tier.name === "low" ? 8 : 14);
  scene.add(shafts);
  const lights = createLights(tokens);
  scene.add(lights.group);

  const subKit = await loadSubmarine(tokens, tier);
  scene.add(subKit.sub);
  const headlights = createHeadlights(tokens, subKit.sub);
  const snow = createSnow(tokens, rng.fork("snow"), tier.snow);
  scene.add(snow.points);
  const creatures = createCreatures({ shape, rng: rng.fork("creatures"), tier, tokens, include, scene });
  const rig = createCameraRig(shape);
  const post = createPost(renderer, scene, rig.camera, tier);

  const ventGlowAt = (() => {
    const c = shape.center(shape.floorDepth, new THREE.Vector2());
    return new THREE.Vector3(c.x, -shape.floorDepth + 26, c.y);
  })();
  const W = tokens.world;
  const stops = [
    [0, W.waterSurface.clone()],
    [45, W.waterSurface.clone().lerp(W.waterMid, 0.55)],
    [110, W.waterMid.clone()],
    [260, W.waterDeep.clone()],
    [600, W.waterAbyss.clone()],
  ];
  const water = new THREE.Color();
  const tint = new THREE.Color();
  const lampPos = [new THREE.Vector3(), new THREE.Vector3()];
  const lampDir = [new THREE.Vector3(), new THREE.Vector3()];
  const lurePos = new THREE.Vector3();
  const subFwd = new THREE.Vector3();
  const glowAt = new THREE.Vector3();
  const ctx = { camPos: rig.camera.position, camDepth: 0, subPos: subKit.sub.position, subFwd, lampOn: true, reduced };

  function waterAt(depth, out) {
    if (depth <= stops[0][0]) return out.copy(stops[0][1]);
    for (let i = 1; i < stops.length; i++) {
      if (depth <= stops[i][0]) {
        const [d0, c0] = stops[i - 1];
        const [d1, c1] = stops[i];
        return out.copy(c0).lerp(c1, (depth - d0) / (d1 - d0));
      }
    }
    return out.copy(stops[stops.length - 1][1]);
  }

  function setPixelRatio(pr) {
    renderer.setPixelRatio(pr);
    trench.setPixelRatio(pr);
    snow.setPixelRatio(pr);
    creatures.get("lanternfish")?.setPixelRatio(pr);
  }

  function resize() {
    const w = innerWidth, h = innerHeight;
    const pr = Math.min(devicePixelRatio || 1, tier.pixelRatio);
    setPixelRatio(pr);
    renderer.setSize(w, h, false);
    rig.resize(w, h);
    post.setSize(w, h, pr);
    creatures.setResolution(w * pr, h * pr);
  }
  resize();

  const world = {
    renderer, scene, shape, trench, creatures, rig, post, sub: subKit.sub, subKit, tier, lights,
    camera: rig.camera,
    resize,
    applyTier() {
      post.applyTier(tier);
      resize();
    },
    waterAt,
    /**
     * frame: { sub: {pos, yaw, pitch, roll}, thrust, lampsOn, wobble, flash, breath, surfaceGlow, focusDist }
     */
    update(dt, t, frame) {
      shared.uTime.value = t;
      const s = frame.sub;
      subKit.sub.position.copy(s.pos);
      subKit.sub.rotation.set(s.pitch, s.yaw, s.roll, "YXZ");
      subFwd.set(Math.sin(s.yaw), 0, Math.cos(s.yaw));
      subKit.spin(dt, frame.thrust);
      rig.update(dt, t, s, reduced);
      subKit.sub.visible = rig.state.mode !== "viewfinder";

      const cam = rig.camera;
      const depth = Math.max(0, -cam.position.y);
      ctx.camDepth = depth;
      waterAt(depth, water);
      scene.background.copy(water);
      scene.fog.color.copy(water);
      const density = 0.0105 + 0.0075 * smooth(0, 70, depth) + 0.012 * smooth(70, 300, depth) - 0.004 * smooth(520, 600, depth);
      scene.fog.density = density;
      shared.uFogDensity.value = density;
      shared.uFogColor.value.copy(water);

      lights.hemi.intensity = 2.5 * Math.exp(-depth / 36) + 0.07;
      lights.sun.intensity = 3.2 * Math.exp(-depth / 28);
      lights.sun.position.set(cam.position.x + 14, cam.position.y + 100, cam.position.z + 8);
      lights.sun.target.position.copy(cam.position);
      scene.environmentIntensity = 0.9 * Math.exp(-depth / 45) + 0.06;
      shared.uCausticStrength.value = tier.caustics ? 1 : 0;
      shared.uCausticColor.value.copy(W.caustic);
      shared.uLichenStrength.value = 0.35 + 0.65 * smooth(60, 220, depth);

      headlights.setOn(frame.lampsOn);
      subKit.setLamps(frame.lampsOn);
      headlights.beamMat.uniforms.uStrength.value = 0.15 + 0.85 * smooth(20, 140, depth);
      headlights.write(lampPos, lampDir);
      snow.update(cam.position, lampPos, lampDir, frame.lampsOn ? 1 : 0, 0.12 + 0.35 * Math.exp(-depth / 60));

      surface.visible = depth < 260;
      shared.uSurfaceSky.value.copy(W.sun).multiplyScalar(1 + frame.surfaceGlow * 2);
      shared.uSurfaceFade.value = Math.exp(-depth / 55);
      shafts.visible = depth < 110;
      shafts.material.uniforms.uStrength.value = smooth(95, 8, depth) * (1 + frame.surfaceGlow);

      // The deep's glow rims the sub: a cool light just behind it from the camera, and an edge glow on the hull.
      const deepGlow = smooth(45, 150, depth);
      glowAt.copy(subKit.sub.position).sub(cam.position).setY(0).normalize().multiplyScalar(4).add(subKit.sub.position);
      glowAt.y += 0.9;
      lights.glow.position.copy(glowAt);
      lights.glow.intensity = 40 * deepGlow;
      shared.uRimColor.value.copy(W.glow).multiplyScalar(0.55 * deepGlow);

      creatures.update(dt, t, ctx);
      const anglers = creatures.get("anglerfish");
      if (anglers && anglers.active) {
        const d = anglers.nearestLure(cam.position, lurePos);
        lights.lure.position.copy(lurePos);
        lights.lure.intensity = d < 60 ? 13 + Math.sin(t * 2.3) * 2.5 : 0;
      } else {
        lights.lure.intensity = 0;
      }
      trench.setCameraDepth(depth);
      lights.vent.position.copy(ventGlowAt);
      lights.vent.intensity = depth > 470 ? 380 * smooth(470, 560, depth) * (0.85 + 0.15 * Math.sin(t * 1.7) * Math.sin(t * 2.9)) : 0;

      // The passes: absorption deepens, bloom wakes as the light goes, god rays only near the surface.
      const u = post.underwater.uniforms;
      u.uTime.value = t;
      u.uWobble.value = reduced ? 0 : frame.wobble;
      const m = Math.max(water.r, water.g, water.b, 0.001);
      tint.setRGB(water.r / m, water.g / m, water.b / m).lerp(new THREE.Color(1, 1, 1), 0.35 * (1 - smooth(0, 200, depth)));
      u.uTint.value.copy(tint);
      u.uTintAmount.value = 0.3 + 0.5 * smooth(0, 300, depth) - 0.5 * smooth(470, 570, depth);
      u.uHaze.value.copy(water).multiplyScalar(0.035);
      u.uVignette.value = 0.45 + 0.3 * smooth(80, 500, depth);
      u.uFlash.value = frame.flash;
      u.uBreath.value = frame.breath;
      u.uSurfaceGlow.value = frame.surfaceFade;
      u.uSurfaceColor.value.copy(W.sun);
      post.bloom.strength = 0.42 + 0.6 * smooth(30, 200, depth);
      post.bloom.threshold = 0.95 - 0.5 * smooth(20, 160, depth);
      post.bloom.radius = 0.5 + 0.2 * smooth(30, 200, depth);
      post.aimGodRays(cam, tier.godRays ? 0.9 * smooth(62, 6, depth) * (1 + frame.surfaceGlow) : 0);
      if (post.bokeh.enabled) {
        post.bokeh.uniforms.focus.value = frame.focusDist;
        post.bokeh.uniforms.aperture.value = rig.state.mode === "viewfinder" ? 0.0028 : rig.state.mode === "attract" ? 0.0007 : 0.0005;
        post.bokeh.uniforms.maxblur.value = rig.state.mode === "viewfinder" ? 0.0065 : 0.0035;
      }
    },
    render(dt) {
      post.render(dt);
    },
  };
  return world;
}

// A tiny gradient sky baked to an environment map, so the silver fish and the hull have something to reflect.
function makeEnvironment(renderer, tokens) {
  const W = tokens.world;
  const env = new THREE.Scene();
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    uniforms: { uTop: { value: W.sun.clone() }, uMid: { value: W.waterSurface.clone() }, uLow: { value: W.waterDeep.clone() } },
    vertexShader: "varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
    fragmentShader: `uniform vec3 uTop, uMid, uLow; varying vec3 vDir;
      void main(){ float h = vDir.y; vec3 c = h > 0.0 ? mix(uMid, uTop * 1.6, pow(h, 1.5)) : mix(uMid, uLow * 0.4, pow(-h, 0.6)); gl_FragColor = vec4(c, 1.0); }`,
  });
  env.add(new THREE.Mesh(new THREE.SphereGeometry(10, 32, 16), mat));
  const pmrem = new THREE.PMREMGenerator(renderer);
  const tex = pmrem.fromScene(env, 0.02).texture;
  pmrem.dispose();
  return tex;
}
