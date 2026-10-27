// Assembles the street: renderer, camera rig, sky, light, ground, the town, the banner with the town's name,
// the windmill, the desert, the two gunslingers, the effects, the post stack, and the sun's lens flare.
import * as THREE from "three";
import { Lensflare, LensflareElement } from "three/addons/objects/Lensflare.js";
import { createRenderer } from "./renderer.js";
import { CameraRig } from "./camera.js";
import { createSky, sunDirection } from "./sky.js";
import { createLights } from "./lights.js";
import { createGround } from "./ground.js";
import { Kit } from "./kit.js";
import { createMaterials, bannerCanvas } from "./materials.js";
import { buildStreet, createBanner, bannerRopes, BANNER_Y } from "./street.js";
import { buildLandmarks, createWindmill, buildPoles, buildDesert, createScatter, buildMesas } from "./props.js";
import { Gunslinger, figureColors } from "./figures.js";
import { createEffects } from "./effects.js";
import { createPost } from "./post.js";

function flareTexture(kind) {
  const S = 256;
  const c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d");
  const m = S / 2;
  if (kind === "glow") {
    const grad = g.createRadialGradient(m, m, 0, m, m, m);
    grad.addColorStop(0, "rgba(255,255,255,1)");
    grad.addColorStop(0.08, "rgba(255,255,255,0.8)");
    grad.addColorStop(0.3, "rgba(255,255,255,0.18)");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, S, S);
    g.globalCompositeOperation = "lighter";
    const streak = g.createLinearGradient(0, m, S, m);
    streak.addColorStop(0, "rgba(255,255,255,0)");
    streak.addColorStop(0.5, "rgba(255,255,255,0.55)");
    streak.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = streak;
    g.fillRect(0, m - 2, S, 4);
  } else if (kind === "ring") {
    g.strokeStyle = "rgba(255,255,255,0.5)";
    g.lineWidth = 10;
    g.filter = "blur(6px)";
    g.beginPath();
    g.arc(m, m, m * 0.7, 0, Math.PI * 2);
    g.stroke();
  } else {
    g.fillStyle = "rgba(255,255,255,0.55)";
    g.filter = "blur(3px)";
    g.beginPath();
    for (let i = 0; i < 6; i += 1) {
      const a = (i / 6) * Math.PI * 2 + Math.PI / 6;
      g.lineTo(m + Math.cos(a) * m * 0.8, m + Math.sin(a) * m * 0.8);
    }
    g.closePath();
    g.fill();
  }
  return new THREE.CanvasTexture(c);
}

async function fontsReady() {
  if (!document.fonts) return;
  const wait = new Promise((resolve) => setTimeout(resolve, 2500));
  await Promise.race([Promise.all([document.fonts.load("120px Rye"), document.fonts.load("64px Bitter")]), wait]);
}

export async function createWorld({ canvas, tier, tokens, config }) {
  await fontsReady();

  const renderer = createRenderer(canvas, tier, tokens);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(tokens.fog, tokens.fogNear, tokens.fogFar);
  const camera = new THREE.PerspectiveCamera(36, window.innerWidth / window.innerHeight, 0.1, 2500);
  const rig = new CameraRig(camera);

  const sky = createSky(tokens);
  scene.add(sky.mesh);
  const lights = createLights(tokens, tier);
  scene.add(lights.group);
  const ground = createGround(tokens);
  scene.add(ground.mesh);

  // the town, merged by material
  const { materials, signRect } = createMaterials(tokens);
  const mesaMaterial = new THREE.MeshBasicMaterial({ vertexColors: true, fog: false });
  const haze = { value: tokens.skyHorizon.clone() };
  mesaMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.uHaze = haze;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying float vMesaY;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvMesaY = (modelMatrix * vec4(position, 1.0)).y;");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform vec3 uHaze;\nvarying float vMesaY;")
      .replace("#include <color_fragment>", "#include <color_fragment>\ndiffuseColor.rgb = mix(uHaze, diffuseColor.rgb, 0.35 + 0.65 * smoothstep(-4.0, 70.0, vMesaY));");
  };
  materials.mesa = mesaMaterial;

  const kit = new Kit();
  const street = buildStreet(kit, tokens, signRect);
  bannerRopes(kit, tokens);
  buildLandmarks(kit, tokens);
  const windmill = createWindmill(kit, tokens, materials);
  buildPoles(kit, tokens);
  buildDesert(kit, tokens);
  const town = kit.build(materials);
  scene.add(town);
  const mesaKit = new Kit();
  buildMesas(mesaKit, tokens);
  const mesas = mesaKit.build(materials, { castShadow: false, receiveShadow: false });
  scene.add(mesas);
  scene.add(windmill);
  scene.add(createScatter(tokens, tier));

  // the banner across the street, with the town's name
  const css = getComputedStyle(document.documentElement);
  const bannerTex = new THREE.CanvasTexture(
    bannerCanvas(config.townName, "Saloon, Rooms, and Hot Baths", {
      canvas: "#efe3c8",
      letter: css.getPropertyValue("--color-stamp").trim() || "#a3281c",
      shadow: "rgba(40,20,10,0.35)",
      line: "#3a2414",
    }),
  );
  bannerTex.colorSpace = THREE.SRGBColorSpace;
  bannerTex.anisotropy = 8;
  const banner = createBanner(bannerTex, tokens);
  scene.add(banner.mesh);

  // the gunslingers
  const frame = rig.frame;
  const figures = [
    new Gunslinger({ side: -1, look: "duster", colors: figureColors(tokens, 0), x: -frame.duelX }),
    new Gunslinger({ side: 1, look: "poncho", colors: figureColors(tokens, 1), x: frame.duelX }),
  ];
  figures.forEach((f) => scene.add(f.root));

  const effects = createEffects(scene, tokens, tier, street.lanterns);

  // environment light from the sky itself, so metal and glass pick up the sunset
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envScene = new THREE.Scene();
  const envSky = createSky(tokens);
  envScene.add(envSky.mesh);
  scene.environment = pmrem.fromScene(envScene, 0, 0.1, 1000).texture;
  pmrem.dispose();

  let post = createPost(renderer, scene, camera, tier, tokens);

  // the sun's lens flare, drawn over the finished frame and hidden when something stands in front of the sun
  let flare = null;
  const flareScene = new THREE.Scene();
  const flareBase = [];
  const flareElements = [];
  if (tier.flare) {
    flare = new Lensflare();
    const glow = flareTexture("glow");
    const ring = flareTexture("ring");
    const hex = flareTexture("hex");
    const strength = tokens.moon > 0.5 ? 0.35 : 1;
    const warm = tokens.sunGlow.clone();
    const add = (tex, size, dist, color) => {
      const c = color.clone().multiplyScalar(strength);
      const el = new LensflareElement(tex, size, dist, c);
      flare.addElement(el);
      flareElements.push(el);
      flareBase.push(c.clone());
    };
    add(glow, 520, 0, tokens.sun.clone().lerp(warm, 0.4).multiplyScalar(0.55));
    add(hex, 70, 0.42, warm.clone().multiplyScalar(0.22));
    add(ring, 150, 0.6, warm.clone().multiplyScalar(0.16));
    add(hex, 46, 0.72, warm.clone().multiplyScalar(0.28));
    add(hex, 110, 0.9, warm.clone().multiplyScalar(0.12));
    add(ring, 260, 1.15, warm.clone().multiplyScalar(0.08));
    flareScene.add(flare);
  }
  const occluders = street.occluders.map(({ s, z0, len, front }) => {
    const x0 = s * 8.3;
    const x1 = s * 22;
    return new THREE.Box3(new THREE.Vector3(Math.min(x0, x1), 0, z0 - len), new THREE.Vector3(Math.max(x0, x1), front, z0));
  });
  occluders.push(new THREE.Box3(new THREE.Vector3(-5.6, BANNER_Y - 1.4, -8.8), new THREE.Vector3(5.6, BANNER_Y + 1.1, -8.4)));
  const figureBoxes = [new THREE.Box3(), new THREE.Box3()];
  const ray = new THREE.Ray();
  const sunDir = sunDirection(tokens);
  let flareVis = 0;

  let onEvent = () => {};
  const horizonPoint = new THREE.Vector3();
  const size = new THREE.Vector2();

  function resize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    renderer.setSize(w, h, false);
    const f = rig.layout(w, h);
    figures[0].home.x = -f.duelX;
    figures[1].home.x = f.duelX;
    if (post) post.setSize(w, h);
    // where the banner's lower edge lands in the resting shot, so the page can set the title beneath it
    const probe = camera.clone();
    probe.position.copy(f.wide.pos);
    probe.lookAt(f.wide.target);
    probe.fov = f.wide.fov;
    probe.setViewOffset(w, h, 0, -f.wide.shift * h, w, h);
    probe.updateProjectionMatrix();
    probe.updateMatrixWorld(true);
    const edge = new THREE.Vector3(0, BANNER_Y - 1.45, -8.6).project(probe);
    document.documentElement.style.setProperty("--banner-bottom", `${Math.round(((1 - edge.y) / 2) * h)}px`);
  }
  resize();

  function pointScale() {
    renderer.getDrawingBufferSize(size);
    return size.y / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
  }

  return {
    renderer,
    scene,
    camera,
    rig,
    figures,
    effects,
    post,
    tier,
    banner,
    resize,

    lights,

    /** dt: game seconds (slowed during the shot); real: wall seconds; gameTime and time: their clocks. */
    update(dt, real, gameTime, time) {
      rig.update(real);
      sky.update(time, camera);
      banner.uniforms.uTime.value = time;
      windmill.children[0].rotation.z -= real * 1.1;
      for (const f of figures) f.update(dt, gameTime);
      effects.update(dt, real, time, camera, onEvent);
      effects.setScale(pointScale());

      if (post) {
        horizonPoint.set(0, 0, camera.position.z - 600).project(camera);
        // a camera turned away from the far end of the street puts the band off screen
        if (horizonPoint.z > 1 || Math.abs(horizonPoint.x) > 1) horizonPoint.set(0, -4, 0);
        post.grade.uniforms.uHorizon.value.set((horizonPoint.x + 1) / 2, (horizonPoint.y + 1) / 2);
        post.grade.uniforms.uTime.value = time;
        if (post.bokeh && post.bokeh.enabled) {
          post.bokeh.uniforms.focus.value = camera.position.distanceTo(figures[0].root.position) * 0.5 + camera.position.distanceTo(figures[1].root.position) * 0.5;
        }
      }

      if (flare) {
        flare.position.copy(camera.position).addScaledVector(sunDir, 600);
        ray.origin.copy(camera.position);
        ray.direction.copy(sunDir);
        let blocked = occluders.some((b) => ray.intersectsBox(b));
        if (!blocked) {
          for (let i = 0; i < 2; i += 1) {
            const p = figures[i].root.position;
            figureBoxes[i].min.set(p.x - 0.32, 0, p.z - 0.32);
            figureBoxes[i].max.set(p.x + 0.32, 2.0, p.z + 0.32);
            if (ray.intersectsBox(figureBoxes[i])) blocked = true;
          }
        }
        flareVis += ((blocked ? 0 : 1) - flareVis) * Math.min(1, real * 10);
        flareElements.forEach((el, i) => el.color.copy(flareBase[i]).multiplyScalar(flareVis));
        flare.visible = flareVis > 0.02;
      }
    },

    render() {
      if (post) post.composer.render();
      else renderer.render(scene, camera);
      if (flare && flare.visible) {
        renderer.autoClear = false;
        renderer.clearDepth();
        renderer.render(flareScene, camera);
        renderer.autoClear = true;
      }
    },

    /** Steps quality down when frames run long: a lower pixel ratio, then no bloom or depth of field, then no post. */
    degrade(step) {
      if (step === 1) {
        renderer.setPixelRatio(Math.max(1, renderer.getPixelRatio() * 0.75));
        resize();
      } else if (step === 2 && post) {
        post.bloom.enabled = false;
        if (post.bokeh) post.bokeh.enabled = false;
        if (post.bokeh) post.bokeh = null;
      } else if (step === 3) {
        post = null;
        if (flare) flare.visible = false;
        flare = null;
      }
    },

    onEvent(fn) {
      onEvent = fn;
    },

    setDepthOfField(on) {
      if (post && post.bokeh) post.bokeh.enabled = on;
    },

    /** A head-and-shoulders photograph of one gunslinger, for the wanted poster. */
    portrait(index, out) {
      const f = figures[index];
      f.root.updateMatrixWorld(true);
      const head = f.head.getWorldPosition(new THREE.Vector3());
      const face = new THREE.Vector3(-f.side, 0, 0);
      const cam = new THREE.PerspectiveCamera(24, 0.8, 0.1, 2500);
      cam.position.copy(head).addScaledVector(face, 1.35).add(new THREE.Vector3(0, 0.08, 1.05));
      cam.lookAt(head.x, head.y - 0.16, head.z);
      const W = renderer.domElement.width;
      const H = renderer.domElement.height;
      const ph = Math.min(H, Math.round(W * 0.6), 560);
      const pw = Math.round(ph * 0.8);
      renderer.setScissorTest(true);
      renderer.setScissor(0, 0, pw / renderer.getPixelRatio(), ph / renderer.getPixelRatio());
      renderer.setViewport(0, 0, pw / renderer.getPixelRatio(), ph / renderer.getPixelRatio());
      const wasFlare = flare ? flare.visible : false;
      // a photograph is exposed for the face, which the low sun leaves in shade
      const exposure = renderer.toneMappingExposure;
      renderer.toneMappingExposure = exposure * 1.7;
      renderer.render(scene, cam);
      renderer.toneMappingExposure = exposure;
      out.width = pw;
      out.height = ph;
      out.getContext("2d").drawImage(renderer.domElement, 0, H - ph, pw, ph, 0, 0, pw, ph);
      renderer.setScissorTest(false);
      const s = renderer.getSize(new THREE.Vector2());
      renderer.setViewport(0, 0, s.x, s.y);
      if (flare) flare.visible = wasFlare;
      return out;
    },
  };
}
