// One book: a box sized by page count with its spine, cover, back, and page edges painted on one atlas, so a book on
// the shelf is one draw call. It rests in a slot, tilts out on a spring when pointed at, flies to a new slot on a sort,
// and when opened floats to the camera as a hinged book whose cover swings open onto two typeset pages.
import * as THREE from "three";
import { atlasLayout, paintAtlas, paintLeftPage, paintRightPage, paintBookmark, hash } from "./textures.js";
import { bookDims } from "./dims.js";
import { BOOKMARK_RISE } from "./shelf.js";
import { Spring, ease, clamp, reducedMotion } from "./motion.js";
import { canvasTexture } from "./renderer.js";

const X = new THREE.Vector3(1, 0, 0);
const Y = new THREE.Vector3(0, 1, 0);
const COVER_T = 0.0032;
const BOOKMARK_H = 0.09;
const tmpQ = new THREE.Quaternion();
const tmpQ2 = new THREE.Quaternion();
const tmpV = new THREE.Vector3();

function remapFaces(geo, rects, A) {
  const uv = geo.attributes.uv;
  rects.forEach((r, f) => {
    if (!r) return;
    const u0 = r.x / A;
    const u1 = (r.x + r.w) / A;
    const vTop = 1 - r.y / A;
    const vBot = 1 - (r.y + r.h) / A;
    for (let k = 0; k < 4; k += 1) {
      const i = f * 4 + k;
      uv.setXY(i, u0 + uv.getX(i) * (u1 - u0), vBot + uv.getY(i) * (vTop - vBot));
    }
  });
  uv.needsUpdate = true;
}

function inset(r, px) {
  return { x: r.x + px, y: r.y + px, w: Math.max(1, r.w - px * 2), h: Math.max(1, r.h - px * 2) };
}

class Tween {
  constructor() {
    this.from = 0;
    this.to = 0;
    this.start = 0;
    this.dur = 1;
    this.curve = ease.inOutCubic;
    this.raw = 0;
  }

  set(to, now, dur, curve) {
    this.from = this.value(now);
    this.to = to;
    this.start = now;
    this.dur = reducedMotion() ? 0 : dur * Math.abs(to - this.from);
    this.curve = curve;
  }

  value(now) {
    const p = this.dur <= 0 ? 1 : clamp((now - this.start) / this.dur, 0, 1);
    this.raw = p;
    return this.from + (this.to - this.from) * this.curve(p);
  }

  done(now) {
    return this.dur <= 0 || now - this.start >= this.dur;
  }
}

export class Book {
  constructor(data, renderer, atlasSize) {
    this.data = data;
    this.id = data.id;
    this.renderer = renderer;
    this.dims = bookDims(data);
    this.glossy = hash(`${data.id}:gloss`) % 5 < 2;
    this.root = new THREE.Group();
    this.A = atlasSize;
    this.canvas = document.createElement("canvas");
    this.canvas.width = atlasSize;
    this.canvas.height = atlasSize;
    this.layout = atlasLayout(this.dims, atlasSize);
    this.texture = canvasTexture(this.canvas, renderer);
    this.material = new THREE.MeshStandardMaterial({ map: this.texture, roughness: this.glossy ? 0.4 : 0.8, metalness: 0 });
    const { t, h, d } = this.dims;
    const geo = new THREE.BoxGeometry(t, h, d);
    const L = this.layout;
    const edge = inset(L.edge, 2);
    remapFaces(geo, [inset(L.cover, 1), inset(L.back, 1), edge, edge, inset(L.spine, 1), edge], this.A);
    this.mesh = new THREE.Mesh(geo, this.material);
    this.mesh.castShadow = true;
    this.mesh.receiveShadow = true;
    this.mesh.userData.book = this;
    this.root.add(this.mesh);

    this.kind = "stand";
    this.rest = { pos: new THREE.Vector3(), quat: new THREE.Quaternion(), offset: new THREE.Vector3(), scale: 1 };
    this.tilt = 0;
    this.flight = null;
    this.hover = new Spring(240, 0.5);
    this.read = new Tween();
    this.hinge = new Tween();
    this.state = "shelf";
    this.readPose = { pos: new THREE.Vector3(), quat: new THREE.Quaternion() };
    this.open = null;
    this.bookmark = null;
    this.color = "#556677";
    this.image = null;
    this.visible = true;
    this.pageGlow = 0.4;
    this.lifted = false;
  }

  paint(look) {
    this.color = look.color;
    this.image = look.image || null;
    paintAtlas(this.canvas, this.data, this.layout, look);
    this.texture.needsUpdate = true;
  }

  /** The bookmark card standing out of the top of a book being read, at how far through it the reader is. */
  syncBookmark(palette) {
    const want = this.kind === "face" && this.data.status === "reading";
    if (!want) {
      if (this.bookmark) this.bookmark.visible = false;
      return;
    }
    if (!this.bookmark) {
      const c = document.createElement("canvas");
      c.width = 160;
      c.height = Math.round((160 * BOOKMARK_H) / 0.062);
      const tex = canvasTexture(c, this.renderer);
      const mat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.7, side: THREE.DoubleSide, alphaTest: 0.5 });
      const card = new THREE.Mesh(new THREE.PlaneGeometry(0.062, BOOKMARK_H), mat);
      card.rotation.y = Math.PI / 2;
      card.userData.canvas = c;
      card.userData.tex = tex;
      card.castShadow = true;
      this.mesh.add(card);
      this.bookmark = card;
    }
    const { t, h, d } = this.dims;
    const p = this.data.pages ? clamp(this.data.page / this.data.pages, 0.06, 0.94) : 0.3;
    this.bookmark.visible = true;
    // The tag's top stands BOOKMARK_RISE above the book's front edge, however far the book leans back.
    const x = t / 2 - t * p;
    const top = h / 2 + BOOKMARK_RISE + (t / 2 - x) * Math.tan(this.tilt);
    this.bookmark.position.set(x, top - BOOKMARK_H / 2, -d * 0.24);
    paintBookmark(this.bookmark.userData.canvas, this.data, palette);
    this.bookmark.userData.tex.needsUpdate = true;
  }

  place(slot, now, { delay = 0, dur = 0.8, entrance = false } = {}) {
    const to = { pos: slot.pos.clone(), quat: slot.quat.clone(), offset: slot.offset.clone(), scale: slot.scale || 1 };
    this.tilt = slot.tilt || 0;
    const from = this.currentShelfPose(now);
    this.kind = slot.kind;
    this.row = slot.row;
    this.seg = slot.seg;
    if (reducedMotion() || (!entrance && from.pos.distanceTo(to.pos) < 1e-4 && from.quat.angleTo(to.quat) < 1e-3)) {
      this.rest = to;
      this.flight = null;
      return;
    }
    if (entrance) {
      const r = (hash(this.id) % 1000) / 1000;
      from.pos = to.pos.clone().add(new THREE.Vector3((r - 0.5) * 0.3, 0.42 + r * 0.2, 0.75));
      from.quat = to.quat.clone().premultiply(tmpQ.setFromAxisAngle(X, -0.5 + r * 0.3)).premultiply(tmpQ2.setFromAxisAngle(Y, (r - 0.5) * 0.8));
      from.offset = to.offset.clone();
      from.scale = to.scale;
    }
    this.flight = { from, to, start: now + delay, dur, entrance, lift: entrance ? 0 : 0.03 + (hash(this.id) % 100) / 2500 };
    this.rest = to;
  }

  currentShelfPose(now) {
    const out = { pos: new THREE.Vector3(), quat: new THREE.Quaternion(), offset: new THREE.Vector3(), scale: 1 };
    const f = this.flight;
    if (f) {
      const p = clamp((now - f.start) / f.dur, 0, 1);
      // A sort pulls each book clear of the shelf, carries it across, and slides it home.
      const e = f.entrance ? ease.outCubic(p) : ease.inOutCubic(clamp((p - 0.22) / 0.56, 0, 1));
      out.pos.lerpVectors(f.from.pos, f.to.pos, e);
      if (!f.entrance) {
        const out1 = ease.outCubic(clamp(p / 0.26, 0, 1));
        const in1 = ease.inOutCubic(clamp((p - 0.74) / 0.26, 0, 1));
        const clear = out1 * (1 - in1);
        out.pos.z += clear * 0.34;
        out.pos.y += Math.sin(Math.PI * e) * f.lift;
      }
      out.quat.slerpQuaternions(f.from.quat, f.to.quat, f.entrance ? ease.outBack(p) : e);
      out.offset.lerpVectors(f.from.offset, f.to.offset, e);
      out.scale = f.from.scale + (f.to.scale - f.from.scale) * e;
      if (p >= 1) this.flight = null;
    } else {
      out.pos.copy(this.rest.pos);
      out.quat.copy(this.rest.quat);
      out.offset.copy(this.rest.offset);
      out.scale = this.rest.scale;
    }
    return out;
  }

  applyHover(pose, s) {
    if (s === 0) return pose;
    if (this.kind === "face") {
      tmpQ.setFromAxisAngle(X, 0.17 * s);
      pose.quat.premultiply(tmpQ);
      pose.pos.add(tmpV.set(0, 0.012 * s, 0.035 * s));
    } else if (this.kind === "flat") {
      tmpQ.setFromAxisAngle(Y, -0.2 * s);
      pose.quat.premultiply(tmpQ);
      pose.pos.add(tmpV.set(0, 0.004 * s, 0.075 * s));
    } else {
      tmpQ.setFromAxisAngle(X, 0.436 * s);
      tmpQ2.setFromAxisAngle(Y, -0.42 * s);
      pose.quat.premultiply(tmpQ).premultiply(tmpQ2);
      pose.pos.add(tmpV.set(0, 0.004 * s, 0.085 * s));
    }
    return pose;
  }

  /**
   * While this book is out for reading it draws after the dimming veil, so it keeps its full colour and light above
   * the dimmed shelf; the shelf books in front of it still hide it where they should.
   */
  setLifted(on) {
    if (this.lifted === on) return;
    this.lifted = on;
    this.root.traverse((o) => {
      o.renderOrder = on ? 11 : 0;
      if (!o.isMesh) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (m.transparent === on) continue;
        m.transparent = on;
        m.needsUpdate = true;
      }
    });
  }

  setHover(on) {
    this.hover.target = on ? 1 : 0;
    if (reducedMotion()) this.hover.snap(this.hover.target);
  }

  get busy() {
    return this.state !== "shelf";
  }

  openBook(now) {
    if (this.state === "open" || this.state === "opening") return;
    this.state = "opening";
    this.read.set(1, now, 0.95, ease.inOutCubic);
  }

  closeBook(now) {
    if (this.state === "shelf" || this.state === "closing") return;
    this.state = "closing";
    this.hinge.set(0, now, 0.5, ease.inOutCubic);
  }

  /** Builds the hinged book the first time it opens; `pages` are the two page canvases. */
  buildOpen(pages) {
    if (this.open) return;
    const { t, h, d } = this.dims;
    const L = this.layout;
    const A = this.A;
    const group = new THREE.Group();
    const backRect = inset(L.back, 1);
    const edgeRect = inset(L.edge, 2);
    const paper = new THREE.MeshStandardMaterial({ color: "#efe6d0", roughness: 0.9 });
    const leftTex = canvasTexture(pages.left, this.renderer);
    const rightTex = canvasTexture(pages.right, this.renderer);
    const glow = { emissive: new THREE.Color("#ffffff"), emissiveIntensity: this.pageGlow };
    const leftMat = new THREE.MeshStandardMaterial({ map: leftTex, emissiveMap: leftTex, roughness: 0.92, ...glow });
    const rightMat = new THREE.MeshStandardMaterial({ map: rightTex, emissiveMap: rightTex, roughness: 0.92, ...glow });

    const backGeo = new THREE.BoxGeometry(COVER_T, h, d);
    remapFaces(backGeo, [backRect, backRect, backRect, backRect, backRect, backRect], A);
    const back = new THREE.Mesh(backGeo, [paper, this.material, this.material, this.material, this.material, this.material]);
    back.position.x = -t / 2 + COVER_T / 2;

    const blockGeo = new THREE.BoxGeometry(t - COVER_T * 2, h - 0.007, d - 0.006);
    remapFaces(blockGeo, [null, edgeRect, edgeRect, edgeRect, edgeRect, edgeRect], A);
    const block = new THREE.Mesh(blockGeo, [rightMat, this.material, this.material, this.material, this.material, this.material]);
    block.position.z = -0.003;

    const spineGeo = new THREE.BoxGeometry(t, h, COVER_T);
    remapFaces(spineGeo, [backRect, backRect, backRect, backRect, inset(L.spine, 1), backRect], A);
    const spine = new THREE.Mesh(spineGeo, this.material);
    spine.position.z = d / 2 - COVER_T / 2;

    const hinge = new THREE.Group();
    hinge.position.set(t / 2 - COVER_T / 2, 0, d / 2);
    const frontGeo = new THREE.BoxGeometry(COVER_T, h, d);
    remapFaces(frontGeo, [inset(L.cover, 1), null, backRect, backRect, backRect, backRect], A);
    const front = new THREE.Mesh(frontGeo, [this.material, leftMat, this.material, this.material, this.material, this.material]);
    front.position.z = -d / 2;
    hinge.add(front);

    group.add(back, block, spine, hinge);
    let ribbon = null;
    if (this.data.status === "reading") {
      ribbon = new THREE.Mesh(new THREE.PlaneGeometry(0.007, h * 0.82), new THREE.MeshStandardMaterial({ color: "#8f2f2a", roughness: 0.6, side: THREE.DoubleSide }));
      ribbon.rotation.y = Math.PI / 2;
      ribbon.position.set(t / 2 - COVER_T + 0.0009, h * 0.09, -d * 0.62);
      group.add(ribbon);
    }
    group.traverse((o) => {
      if (o.isMesh) {
        o.castShadow = true;
        o.userData.book = this;
      }
    });
    this.open = { group, hinge, leftTex, rightTex, leftMat, rightMat, paper, ribbon, geos: [backGeo, blockGeo, spineGeo, frontGeo] };
    this.root.add(group);
  }

  repaintPages(pages, palette, text, scale) {
    if (!this.open) return;
    paintLeftPage(pages.left, this.data, text, palette, scale);
    this.open.leftTex.needsUpdate = true;
    if (this.open.ribbon) this.open.ribbon.material.color.set(palette.pageAccent);
  }

  disposeOpen() {
    if (!this.open) return;
    const o = this.open;
    this.root.remove(o.group);
    o.geos.forEach((g) => g.dispose());
    [o.leftTex, o.rightTex].forEach((tx) => tx.dispose());
    [o.leftMat, o.rightMat, o.paper].forEach((m) => m.dispose());
    if (o.ribbon) {
      o.ribbon.geometry.dispose();
      o.ribbon.material.dispose();
    }
    this.open = null;
  }

  /** Advances the book one frame; returns true while it is moving. */
  update(now, dt, time) {
    const s = this.hover.step(dt);
    const pose = this.applyHover(this.currentShelfPose(now), s);
    let r = 0;
    if (this.state !== "shelf") {
      r = this.read.value(now);
      if (this.state === "opening" && this.read.done(now)) {
        this.state = "open";
        this.hinge.set(1, now, 0.85, ease.outCubic);
      }
      if (this.state === "closing" && this.hinge.done(now) && this.read.to !== 0) this.read.set(0, now, 0.85, ease.inOutCubic);
      if (this.state === "closing" && this.read.to === 0 && this.read.done(now)) {
        this.state = "shelf";
        r = 0;
      }
    }
    const open = this.state === "shelf" ? 0 : this.hinge.value(now);
    const { d } = this.dims;
    if (r > 0) {
      const rp = this.readPose;
      const target = tmpV.copy(pose.offset).applyQuaternion(rp.quat);
      const readRootPos = new THREE.Vector3().copy(rp.pos).sub(target);
      const arc = Math.sin(Math.PI * r);
      this.root.position.lerpVectors(pose.pos, readRootPos, r);
      this.root.position.y += arc * 0.08;
      this.root.position.z += arc * 0.05;
      this.root.quaternion.slerpQuaternions(pose.quat, rp.quat, r);
      const bob = Math.sin(time * 1.3) * 0.0025 * r;
      this.root.position.y += bob;
    } else {
      this.root.position.copy(pose.pos);
      this.root.quaternion.copy(pose.quat);
    }
    this.root.scale.setScalar(pose.scale + (1 - pose.scale) * r);
    this.mesh.position.copy(pose.offset);
    const showOpen = r > 0.001 || open > 0.001;
    if (showOpen && this.open) {
      this.mesh.visible = false;
      this.open.group.visible = true;
      this.open.group.position.copy(pose.offset);
      this.open.group.position.z -= (d / 2) * open;
      this.open.hinge.rotation.y = -Math.PI * 0.975 * open;
    } else {
      this.mesh.visible = this.visible;
      if (this.open) {
        this.open.group.visible = false;
        if (this.state === "shelf") this.disposeOpen();
      }
    }
    return Boolean(this.flight) || !this.hover.resting || this.state !== "shelf";
  }

  dispose() {
    this.disposeOpen();
    this.mesh.geometry.dispose();
    this.material.dispose();
    this.texture.dispose();
    if (this.bookmark) {
      this.bookmark.geometry.dispose();
      this.bookmark.material.dispose();
      this.bookmark.userData.tex.dispose();
    }
  }
}
