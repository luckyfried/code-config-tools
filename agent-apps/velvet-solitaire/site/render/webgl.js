// The WebGL table: an orthographic camera tipped a few degrees off straight down, the felt,
// the rail, the 52 lacquered cards in one instanced draw, their contact shadows in another,
// the halos for hints and the keyboard cursor, and the win cascade's ghost trails.

import * as THREE from "three";
import { createTable, fitTable, paintTable, setRails, paintPrint, loadEnvironment } from "../scene/table.js";
import { createAtlas, paintAtlas, createCards, createShadows, createHalo } from "../scene/card.js";
import { createCascade, startCascade, stepCascade, stopCascade, drawGhosts } from "../scene/cascade.js";
import { TILT_DEG, CARD_THICK } from "../game/layout.js";

const TILT = (TILT_DEG * Math.PI) / 180;

export function supportsWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

export async function createWebGLRenderer({ host, tier, reduced, envUrl, cardCssWidth }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  let ratio = Math.min(window.devicePixelRatio || 1, 2);
  renderer.setPixelRatio(ratio);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.domElement.className = "table-canvas";
  renderer.domElement.setAttribute("aria-hidden", "true");
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -2000, 4000);
  const table = createTable();
  scene.add(table.group);

  const atlas = createAtlas(cardCssWidth, ratio);
  atlas.texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const cards = createCards(atlas, { reduced });
  const shadows = createShadows();
  const halos = { hintFrom: createHalo(), hintTo: createHalo(), cursor: createHalo() };
  const cascade = createCascade(atlas);
  scene.add(cards.mesh, shadows.mesh, cascade.mesh, halos.hintFrom, halos.hintTo, halos.cursor);

  const view = { pxW: 1, pxH: 1, s: 1, width: 1, height: 1, cx: 0, cy: 0 };
  let layout = null;
  let clock = 0;
  let envReady = false;

  loadEnvironment(renderer, envUrl)
    .then((env) => {
      scene.environment = env;
      envReady = true;
      api.dirty = true;
    })
    .catch(() => {
      envReady = false;
    });

  const toWorld = (x, y, out) => {
    const scroll = layout ? layout.scroll || 0 : 0;
    out.x = (x - view.pxW / 2) / view.s;
    out.y = (view.pxH / 2 - (y - scroll)) / (view.s * Math.cos(TILT));
    return out;
  };

  const m4 = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const e = new THREE.Euler(0, 0, 0, "ZXY");
  const p = new THREE.Vector3();
  const sc = new THREE.Vector3();
  const sp = new THREE.Vector3();
  const AXIS_Z = new THREE.Vector3(0, 0, 1);

  const api = {
    kind: "webgl",
    dirty: true,
    atlas,
    cascade,
    canvas: renderer.domElement,

    /** Sizes the view to the window and the layout; rails are rects in CSS pixels. */
    setLayout(next, pxW, pxH, railRects) {
      layout = next;
      view.pxW = pxW;
      view.pxH = pxH;
      view.s = next.scale;
      view.width = pxW / view.s;
      view.height = pxH / (view.s * Math.cos(TILT));
      renderer.setSize(pxW, pxH, false);
      // The camera looks down at the felt, tipped toward the bottom edge of the screen.
      const halfW = view.width / 2;
      const halfH = pxH / view.s / 2;
      camera.left = -halfW;
      camera.right = halfW;
      camera.top = halfH;
      camera.bottom = -halfH;
      camera.position.set(0, -Math.sin(TILT) * 1500, Math.cos(TILT) * 1500);
      camera.up.set(0, 1, 0);
      camera.lookAt(0, 0, 0);
      camera.updateProjectionMatrix();
      const a = next.area;
      const c = toWorld(a.x + a.w / 2, a.y + a.h / 2, new THREE.Vector3());
      fitTable(table, {
        width: view.width,
        height: view.height,
        cx: 0,
        cy: 0,
        areaW: a.w / view.s,
        areaH: a.h / (view.s * Math.cos(TILT)),
        areaX: c.x,
        areaY: c.y,
        printX: 0,
        printY: 0,
      });
      setRails(
        table,
        railRects.map((r) => {
          // A side that meets the window's edge runs past it, so the block's rounded corners
          // and their rim-lit bevels stay off screen instead of clipping at the corner.
          const bleed = 64;
          const left = r.x <= 1 ? r.x - bleed : r.x;
          const right = r.x + r.w >= pxW - 1 ? r.x + r.w + bleed : r.x + r.w;
          const top = r.y <= 1 ? r.y - bleed : r.y;
          const bottom = r.y + r.h >= pxH - 1 ? r.y + r.h + bleed : r.y + r.h;
          const cxw = ((left + right) / 2 - pxW / 2) / view.s;
          const cyw = (pxH / 2 - (top + bottom) / 2) / (view.s * Math.cos(TILT));
          return { x: cxw, y: cyw, w: (right - left) / view.s, h: (bottom - top) / (view.s * Math.cos(TILT)) + 4 };
        }),
      );
      api.dirty = true;
    },

    /** Paints the theme into the scene: felt, print, rail, lights, card faces, and backs. */
    applyTheme(tok, look, back) {
      paintTable(table, tok);
      paintAtlas(atlas, look, back);
      renderer.setClearColor(tok.color("--felt-deep"));
      renderer.toneMappingExposure = tok.number("--exposure", 1);
      scene.environmentIntensity = tok.number("--env-power", 1);
      shadows.material.uniforms.uColor.value.set(tok.color("--shadow-ink"));
      shadows.material.uniforms.uStrength.value = tok.number("--shadow-strength", 0.55);
      const glow = tok.color("--hint-glow");
      for (const h of Object.values(halos)) h.material.uniforms.uColor.value.set(glow);
      halos.cursor.material.uniforms.uColor.value.set(tok.color("--cursor-glow"));
      api.dirty = true;
    },

    repaintCards(look, back) {
      paintAtlas(atlas, look, back);
      api.dirty = true;
    },

    paintPrint(tok, info) {
      if (!layout) return;
      paintPrint(table, layout, view, tok, info);
      api.dirty = true;
    },

    /** Halos: { hintFrom, hintTo, cursor } each null or { x, y, z, power }. */
    setHalos(spec) {
      for (const [name, mesh] of Object.entries(halos)) {
        const h = spec[name];
        mesh.visible = !!h;
        if (!h) continue;
        toWorld(h.x, h.y, p);
        mesh.position.set(p.x, p.y, h.z + CARD_THICK + 0.5);
        mesh.material.uniforms.uPower.value = h.power ?? 1;
      }
      api.dirty = true;
    },

    startCascade(motion, state, opts) {
      startCascade(cascade, motion, state, layout, opts);
      api.dirty = true;
    },
    stopCascade(motion) {
      stopCascade(cascade, motion);
      api.dirty = true;
    },
    stepCascade(motion, dt) {
      return stepCascade(cascade, motion, dt);
    },
    get cascadeRunning() {
      return cascade.running;
    },

    /** Draws a frame from the motion state. */
    draw(motion, dt) {
      clock += dt;
      const s = 1;
      for (let i = 0; i < 52; i += 1) {
        if (!motion.visible[i]) {
          m4.makeScale(0, 0, 0);
          cards.mesh.setMatrixAt(i, m4);
          shadows.alpha.array[i] = 0;
          continue;
        }
        const z = motion.z[i] + motion.lift[i];
        const rz = motion.free[i] ? 0 : motion.rz[i];
        const rise = Math.max(0, z - rz);
        toWorld(motion.x[i], motion.y[i], p);
        p.z = z + CARD_THICK / 2 + 0.05;
        e.set(motion.tiltX[i], motion.tiltY[i] + motion.flip[i], -motion.rot[i]);
        q.setFromEuler(e);
        // A card off the felt looks a touch larger, as it would come toward the eye.
        const grow = s + Math.min(0.08, rise * 0.0024);
        sc.set(grow, grow, 1);
        m4.compose(p, q, sc);
        cards.mesh.setMatrixAt(i, m4);
        cards.opacity.array[i] = motion.opacity[i];
        const lean = Math.abs(Math.sin(motion.tiltX[i])) + Math.abs(Math.sin(motion.tiltY[i] + motion.flip[i]));
        cards.gloss.array[i * 2] = Math.min(1, rise * 0.07 + lean * 4);
        cards.gloss.array[i * 2 + 1] = Math.max(-0.42, Math.min(0.42, Math.sin(motion.tiltX[i]) * 2.4 - Math.sin(motion.tiltY[i] + motion.flip[i]) * 0.9 - 0.08));

        // The contact shadow: tight on the felt, wider, softer, and further off as the card rises.
        const spread = 1.06 + rise * 0.014;
        const off = 0.8 + rise * 0.32;
        // Under the card's lowest corner, so a tilted or turning card never cuts its own shadow.
        const reach = 44 * Math.abs(Math.sin(motion.tiltX[i])) + 31.5 * Math.abs(Math.sin(motion.tiltY[i] + motion.flip[i]));
        sp.set(p.x + off * 0.55, p.y - off, Math.max(0.1, Math.min(motion.free[i] ? 9 : 12, z - 0.6 - reach)));
        if (rise < 0.5) sp.z = z - 0.32;
        sc.set(112 * spread, 141 * spread, 1);
        q.setFromAxisAngle(AXIS_Z, -motion.rot[i]);
        m4.compose(sp, q, sc);
        shadows.mesh.setMatrixAt(i, m4);
        shadows.alpha.array[i] = (rise < 0.5 ? 0.62 * motion.shade[i] : Math.max(0.3, 1.25 - rise * 0.014)) * motion.opacity[i];
      }
      cards.mesh.instanceMatrix.needsUpdate = true;
      cards.opacity.needsUpdate = true;
      cards.gloss.needsUpdate = true;
      shadows.mesh.instanceMatrix.needsUpdate = true;
      shadows.alpha.needsUpdate = true;
      drawGhosts(cascade, (x, y, out) => toWorld(x, y, out), 1);
      for (const h of Object.values(halos)) h.material.uniforms.uTime.value = clock;
      renderer.render(scene, camera);
      api.dirty = false;
    },

    /** Lowers the pixel ratio one step when frames run long. */
    lowerQuality() {
      if (ratio <= 1) return false;
      ratio = ratio > 1.5 ? 1.5 : 1;
      renderer.setPixelRatio(ratio);
      api.dirty = true;
      return true;
    },

    get envReady() {
      return envReady;
    },
    tier,
  };
  return api;
}
