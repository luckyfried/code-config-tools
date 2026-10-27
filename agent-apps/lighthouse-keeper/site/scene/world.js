// The world: one scene holding the sky, the sea, the lighthouse, the beam, the ships, the fog banks, and the
// weather, lit by the moon and the beam, updated once a frame from the game's state.
import * as THREE from "three";
import { readTokens } from "./tokens.js";
import { createSky } from "./sky.js";
import { createSea } from "./sea.js";
import { createLighthouse, LAMP_HEIGHT } from "./lighthouse.js";
import { createBeam, BEAM_HALF_ANGLE } from "./beam.js";
import { createShips } from "./ships.js";
import { createFogBanks } from "./fog.js";
import { createWeather } from "./weather.js";
import { createPost } from "./post.js";
import { createRig } from "./camera.js";
import { waveHeight } from "./glsl.js";
import { createGovernor, reducedMotion } from "./quality.js";

export const SHIP_POOL = 12;

export function createWorld(canvas, tier, config) {
  const tokens = readTokens();
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: tier.antialias, powerPreference: "high-performance" });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = tokens.exposure;
  renderer.setClearColor(tokens.fog);
  if (tier.shadow > 0) {
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
  }

  const scene = new THREE.Scene();
  const fog = new THREE.FogExp2(tokens.fog.clone(), tokens.fogDensity);
  scene.fog = fog;
  const rig = createRig(reducedMotion);
  const camera = rig.camera;

  const sky = createSky(tokens);
  scene.add(sky.mesh);
  const sea = createSea(tokens, tier);
  scene.add(sea.mesh);
  const lighthouse = createLighthouse(tokens, config.lighthouseName, tier);
  scene.add(lighthouse.group);
  const beam = createBeam(tokens, tier, lighthouse.lampPosition);
  scene.add(beam.group);
  scene.add(beam.flare);
  const fleet = createShips(tokens, tier, SHIP_POOL);
  scene.add(fleet.group);

  const beamUniforms = {
    uLamp: { value: lighthouse.lampPosition.clone() },
    uBeamDir: { value: beam.direction },
    uBeamTan: { value: Math.tan(BEAM_HALF_ANGLE) },
    uBeamOn: { value: 1 },
  };
  const fogBanks = createFogBanks(tokens, tier, beamUniforms);
  scene.add(fogBanks.mesh);
  const weather = createWeather(tokens, tier, lighthouse.reef, beamUniforms, reducedMotion);
  scene.add(weather.rain.lines, weather.spray.points);

  const hemi = new THREE.HemisphereLight(tokens.skyHorizon, tokens.seaDeep, tokens.ambient);
  scene.add(hemi);
  const moon = new THREE.DirectionalLight(tokens.moon, tokens.moonLight);
  scene.add(moon, moon.target);

  const post = createPost(renderer, scene, camera, tier, tokens);
  // A pale sky sits near the bloom threshold, so the light scheme takes a gentler flare.
  const darkScheme = window.matchMedia("(prefers-color-scheme: dark)");
  let postOn = tier.post;
  let pixelRatio = Math.min(devicePixelRatio || 1, tier.pixelRatio);
  const moonDir = new THREE.Vector3();
  const ndc = new THREE.Vector3();
  const flashEl = document.querySelector(".flash");
  const root = document.documentElement;
  let lastFlash = "";

  function placeMoon() {
    const mb = THREE.MathUtils.degToRad(tokens.moonBearing * (rig.wide ? 1 : 0.25) - (rig.wide ? 6 : 2));
    const me = THREE.MathUtils.degToRad(tokens.moonElev * (rig.wide ? 1 : 0.85));
    moonDir.set(Math.sin(mb) * Math.cos(me), Math.sin(me), -Math.cos(mb) * Math.cos(me));
    sky.uniforms.uMoonDir.value.copy(moonDir);
    moon.position.copy(moonDir).multiplyScalar(200);
  }

  function resize() {
    const w = innerWidth;
    const h = innerHeight;
    renderer.setPixelRatio(pixelRatio);
    renderer.setSize(w, h, false);
    post.setSize(w, h);
    rig.resize(w, h);
    lighthouse.faceName(camera.position);
    placeMoon();
    const scale = (h * pixelRatio) / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    fleet.setPixelScale(scale);
    weather.spray.uniforms.uScale.value = scale;
    const masthead = document.querySelector(".masthead");
    if (masthead) {
      const box = masthead.getBoundingClientRect();
      const ratio = renderer.getPixelRatio();
      weather.rain.uniforms.uClear.value.set(0, (h - box.bottom - 24) * ratio, (box.right + 24) * ratio, 48 * ratio);
    }
  }
  resize();
  addEventListener("resize", resize);
  addEventListener("orientationchange", resize);

  const governor = createGovernor((step) => {
    if (step === 1) pixelRatio = Math.max(1, pixelRatio * 0.75);
    else if (step === 2) pixelRatio = 1;
    else postOn = false;
    resize();
  });

  const tmp = new THREE.Vector3();
  function placeShip(i, s, time) {
    const { mesh, uniforms } = fleet.ships[i];
    mesh.visible = s.active;
    if (!s.active) return;
    const y = waveHeight(s.x, s.z, time, tokens.seaRough);
    const ahead = waveHeight(s.x + Math.sin(s.heading) * 4, s.z - Math.cos(s.heading) * 4, time, tokens.seaRough);
    const side = waveHeight(s.x + Math.cos(s.heading) * 1.5, s.z + Math.sin(s.heading) * 1.5, time, tokens.seaRough);
    mesh.position.set(s.x, y - 0.2 - s.sink * 7, s.z);
    mesh.rotation.set(Math.atan2(y - ahead, 4) * 0.8 + s.sink * 0.5, Math.PI - s.heading, Math.atan2(side - y, 1.5) * 0.6 + s.sink * 0.9, "YXZ");
    uniforms.uBurn.value = s.burn;
    uniforms.uHeat.value = s.heat;
  }

  return {
    tokens,
    renderer,
    scene,
    camera,
    rig,
    fog,
    lighthouse,
    beam,
    weather,
    shipPool: SHIP_POOL,
    // A point on the sea under a screen position, or null when the ray looks above the horizon.
    seaPoint(clientX, clientY, out) {
      ndc.set((clientX / innerWidth) * 2 - 1, -(clientY / innerHeight) * 2 + 1, 0.5).unproject(camera);
      ndc.sub(camera.position).normalize();
      if (ndc.y > -0.002) return null;
      const t = -camera.position.y / ndc.y;
      return out.copy(camera.position).addScaledVector(ndc, t);
    },
    // Whether a point in the world sits on screen, inside a margin.
    onScreen(x, y, z, margin = 0.85) {
      tmp.set(x, y, z).project(camera);
      return tmp.z < 1 && Math.abs(tmp.x) < margin && tmp.y > -1 && tmp.y < 1;
    },
    lampScreen(out) {
      tmp.copy(lighthouse.lampPosition).project(camera);
      out.set(((tmp.x + 1) / 2) * innerWidth, ((1 - tmp.y) / 2) * innerHeight);
      return out;
    },
    compile() {
      renderer.compile(scene, camera);
    },
    frame(state, dt) {
      const time = state.time;
      rig.update(time, state.shake);
      sky.update(time, camera);
      sea.update(time);
      fogBanks.update(time, camera);
      beam.update(time, camera, state.bearing, state.pitch, state.beamPower);
      lighthouse.setBearing(state.bearing);
      weather.update(time, state.now, camera, state.flare);
      const clearOn = weather.rain.uniforms.uClearOn;
      clearOn.value += ((document.body.dataset.mode === "title" ? 1 : 0) - clearOn.value) * Math.min(1, dt * 4);

      for (let i = 0; i < SHIP_POOL; i++) placeShip(i, state.ships[i], time);
      fleet.group.updateMatrixWorld(true);
      fleet.syncLanterns(state.ships);
      fleet.updateEmbers(state.ships, dt);

      const flash = weather.thunder.value;
      const flare = state.flare * (darkScheme.matches ? 1 : 0.6);
      const thick = state.fogThick;
      fog.density = tokens.fogDensity * thick * (1 - flare * 0.45);
      beam.setFog(fog.density);
      fogBanks.uniforms.uThick.value = Math.min(1.6, thick) * (1 - flare * 0.3);
      fogBanks.uniforms.uFlash.value = flash;
      fogBanks.uniforms.uFlare.value = flare;
      sky.uniforms.uFlash.value = flash;
      sky.uniforms.uFlare.value = flare;
      sky.uniforms.uDawn.value = state.dawn;
      sea.uniforms.uFlare.value = flare;
      sea.uniforms.uFlash.value = flash;
      hemi.intensity = tokens.ambient * (1 + flare * 1.3 + flash * 1.5 + state.dawn * 1.2);
      moon.intensity = tokens.moonLight * (1 + flare * 1.2 + flash * 2);
      renderer.toneMappingExposure = tokens.exposure * (1 + flare * 0.2);
      const flashCss = (reducedMotion.matches ? flash * 0.5 : flash * 0.3).toFixed(2);
      if (flashCss !== lastFlash) {
        lastFlash = flashCss;
        root.style.setProperty("--flash", flashCss);
        if (flashEl) flashEl.classList.toggle("is-on", flashCss !== "0.00");
      }

      if (postOn) {
        tmp.copy(lighthouse.lampPosition).project(camera);
        const visible = tmp.z < 1 ? 1 - THREE.MathUtils.smoothstep(Math.max(Math.abs(tmp.x), Math.abs(tmp.y)), 0.9, 1.3) : 0;
        post.setGodRays((tmp.x + 1) / 2, (tmp.y + 1) / 2, Math.pow(beam.state.facing, 3) * 1.6 * visible * state.beamPower);
        post.setBloom(flare * 1.1 + flash * 0.4, darkScheme.matches ? 0.62 : 0.82);
        post.render();
      } else {
        renderer.render(scene, camera);
      }
      if (!("drawn" in canvas.dataset)) canvas.dataset.drawn = "";
      governor(dt * 1000);
    },
  };
}

export { LAMP_HEIGHT };
