// Sky and the day: a gradient dome with the sun's disk, stars that come out at dusk, a rising moon, and the
// atmosphere. Colors follow the sun's elevation at the explorer: noon, sunset, then night. From orbit (the title's
// wide shot) the sun and moon hang at places on the screen the planet leaves clear, and at dusk the sun sits just
// behind the planet's edge so the atmosphere burns amber on that side.
import * as THREE from "three";
import { RADIUS } from "../game/generation.js";
import { moonMaterial, rimMaterial, skyMaterial, starsMaterial } from "./materials.js";

const smooth = THREE.MathUtils.smoothstep;

export function buildSky(colors, settings, random) {
  const group = new THREE.Group();
  group.name = "sky";

  const dome = new THREE.Mesh(new THREE.SphereGeometry(420, 32, 16), skyMaterial());
  dome.renderOrder = -10;
  dome.frustumCulled = false;

  const count = settings.stars;
  const positions = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  const phases = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    const u = random() * 2 - 1;
    const t = random() * Math.PI * 2;
    const s = Math.sqrt(1 - u * u);
    positions.set([s * Math.cos(t) * 360, u * 360, s * Math.sin(t) * 360], i * 3);
    sizes[i] = 1.2 + random() * random() * 3;
    phases[i] = random() * 3;
  }
  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  starGeometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  starGeometry.setAttribute("aPhase", new THREE.BufferAttribute(phases, 1));
  const stars = new THREE.Points(starGeometry, starsMaterial(settings.ratio));
  stars.frustumCulled = false;
  stars.renderOrder = -9;

  const moon = new THREE.Mesh(new THREE.SphereGeometry(9, 24, 16), moonMaterial(colors.moon));
  moon.renderOrder = -8;

  const rim = new THREE.Mesh(new THREE.SphereGeometry(RADIUS * 1.35, 96, 48), rimMaterial(colors.rim));
  rim.material.uniforms.uShell.value = RADIUS * 1.35;
  rim.material.uniforms.uPlanet.value = RADIUS + 0.5;
  rim.renderOrder = 5;

  group.add(dome, stars, moon);

  const moonDir = new THREE.Vector3();
  const zenith = new THREE.Color();
  const horizon = new THREE.Color();
  const sunColor = new THREE.Color();
  const tmp = new THREE.Color();

  // e is the sine of the sun's elevation at the explorer.
  function light(e) {
    const day = smooth(e, 0.02, 0.5);
    const night = smooth(-e, 0.0, 0.42);
    zenith.copy(colors.skyDuskZenith).lerp(colors.skyNoonZenith, day).lerp(colors.skyNightZenith, night);
    horizon.copy(colors.skyDuskHorizon).lerp(colors.skyNoonHorizon, day).lerp(tmp.copy(colors.skyNightHorizon), night);
    sunColor.copy(colors.sunDusk).lerp(colors.sunNoon, smooth(e, 0.04, 0.55));
    const dusk = Math.max(0, 1 - Math.abs(e + 0.04) / 0.32);
    return { day, night, dusk };
  }

  // camera, up: the explorer's local up; skySun: where the sun's disk is drawn; lightDir: where the light comes
  // from; e: the sun's elevation (sine); orbit: 0 to 1, how much of the orbit shot is on screen; title: 0 to 1, how
  // much of the title screen; evening: 0 at noon to 1 at sunset, as the title sees the theme; moonAnchor: the
  // moon's direction from orbit; dip: sine of how far the planet's edge sits below the eye; frameRadius: the planet's
  // radius on the title, in CSS px.
  function update({ camera, up, skySun, lightDir, sunAz, e, orbit, title, evening, moonAnchor, dip, res, frameRadius }) {
    const { night, dusk } = light(e);
    group.position.copy(camera.position);
    const u = dome.material.uniforms;
    u.uUp.value.copy(camera.position).normalize();
    u.uDip.value = dip;
    u.uSun.value.copy(skySun);
    u.uZenith.value.copy(zenith);
    u.uHorizon.value.copy(horizon);
    // From orbit, the top of the sky deepens toward space: a richer blue at noon, the night's indigo at dusk.
    u.uSpaceTop.value.copy(zenith).lerp(colors.skyNightZenith, Math.max(night, evening * 0.85)).lerp(tmp.copy(colors.skyNoonZenith).multiplyScalar(0.62), (1 - evening) * 0.55);
    u.uSunColor.value.copy(sunColor);
    u.uGlow.value = 0.7 + dusk * 1.5;
    u.uRes.value.copy(res);
    u.uOrbit.value = orbit;
    // The halo keeps its size against the planet: where the planet is small on screen, it tightens.
    const planetDeg = THREE.MathUtils.radToDeg(Math.atan((frameRadius / (window.innerHeight / 2)) * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))));
    u.uTight.value = THREE.MathUtils.lerp(1, THREE.MathUtils.clamp(16 / planetDeg, 1, 3), orbit);

    const starsOut = Math.max(smooth(-e, 0.02, 0.35), title * evening * THREE.MathUtils.lerp(0.55, 1, orbit));
    stars.material.uniforms.uNight.value = starsOut;

    const rise = THREE.MathUtils.lerp(-0.35, 0.55, smooth(-e, -0.1, 0.45));
    moonDir.copy(up).multiplyScalar(Math.sin(rise)).addScaledVector(sunAz, -Math.cos(rise)).normalize();
    moonDir.lerp(moonAnchor, orbit).normalize();
    moon.position.copy(moonDir).multiplyScalar(300);
    moon.lookAt(camera.position);
    const moonOut = Math.max(smooth(-e, -0.15, 0.2), orbit * evening);
    moon.material.uniforms.uOpacity.value = moonOut;
    moon.visible = moonOut > 0.002;
    u.uMoon.value.copy(moonDir);
    u.uMoonColor.value.copy(colors.moon);
    u.uMoonGlow.value = moonOut;

    const far = smooth(camera.position.length(), 24, 32);
    const r = rim.material.uniforms;
    r.uIntensity.value = (0.75 + dusk * 0.35 + night * 0.2) * far;
    rim.visible = far > 0.001;
    r.uColor.value.copy(colors.rim);
    r.uSunColor.value.copy(colors.sunDusk);
    r.uDusk.value = Math.max(dusk, evening * orbit);
    r.uSunDir.value.copy(lightDir);
    r.uCam.value.copy(camera.position);
    return { night, dusk, zenith, horizon, sunColor };
  }

  return { group, rim, update, light };
}
