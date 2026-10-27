// The submersible, built from primitives. models/submarine.glb is this same build exported once; the page loads the
// glTF and falls back to this builder when the file is missing. Forward is +z, up is +y, about 4 m nose to stern.
// The builder takes THREE as an argument so the exporter can run it outside the page.

export function buildSubmarine(THREE) {
  const root = new THREE.Group();
  root.name = "submarine";

  const mat = {
    hull: new THREE.MeshStandardMaterial({ name: "hull", color: 0xe9a630, roughness: 0.42, metalness: 0.08 }),
    frame: new THREE.MeshStandardMaterial({ name: "frame", color: 0x2b333b, roughness: 0.45, metalness: 0.75 }),
    trim: new THREE.MeshStandardMaterial({ name: "trim", color: 0xdfe4e8, roughness: 0.5, metalness: 0.1 }),
    rubber: new THREE.MeshStandardMaterial({ name: "rubber", color: 0x111214, roughness: 0.9, metalness: 0 }),
    glass: new THREE.MeshStandardMaterial({
      name: "glass", color: 0xa8dcff, roughness: 0.05, metalness: 0.2, transparent: true, opacity: 0.32, depthWrite: false,
    }),
    lamp: new THREE.MeshStandardMaterial({ name: "lamp", color: 0x202020, emissive: 0xfff1d2, emissiveIntensity: 5 }),
    console: new THREE.MeshStandardMaterial({ name: "console", color: 0x0b1418, emissive: 0x3fe0ff, emissiveIntensity: 1.6 }),
    navRed: new THREE.MeshStandardMaterial({ name: "navRed", color: 0x200000, emissive: 0xff3030, emissiveIntensity: 4 }),
    navGreen: new THREE.MeshStandardMaterial({ name: "navGreen", color: 0x002000, emissive: 0x30ff70, emissiveIntensity: 4 }),
    stripe: new THREE.MeshStandardMaterial({ name: "stripe", color: 0x1a1d21, roughness: 0.6, metalness: 0.2 }),
    porthole: new THREE.MeshStandardMaterial({ name: "porthole", color: 0x2a2218, emissive: 0xffc977, emissiveIntensity: 2.4 }),
  };

  const add = (geo, material, name, parent = root) => {
    const mesh = new THREE.Mesh(geo, material);
    if (name) mesh.name = name;
    parent.add(mesh);
    return mesh;
  };

  // Pressure hull: a lathe along +z, open at the nose where the acrylic dome sits.
  const profile = [
    [0.0, -2.05], [0.2, -2.0], [0.4, -1.86], [0.6, -1.58], [0.75, -1.18], [0.84, -0.66],
    [0.86, 0.0], [0.85, 0.7], [0.8, 1.08], [0.73, 1.3],
  ].map(([r, y]) => new THREE.Vector2(r, y));
  const hullGeo = new THREE.LatheGeometry(profile, 48);
  hullGeo.rotateX(Math.PI / 2);
  add(hullGeo, mat.hull, "hull");

  // Dark bands where the hull sections bolt together.
  for (const z of [-1.18, -0.2, 0.7]) {
    const r = z < -1 ? 0.76 : z > 0.5 ? 0.856 : 0.866;
    const band = new THREE.TorusGeometry(r, 0.03, 8, 64);
    add(band, mat.stripe, "seam").position.z = z;
  }
  // A white belly stripe along both flanks.
  for (const side of [-1, 1]) {
    const stripe = new THREE.CylinderGeometry(0.868, 0.868, 1.7, 48, 1, true, side > 0 ? Math.PI * 0.42 : Math.PI * 1.46, Math.PI * 0.12);
    stripe.rotateX(Math.PI / 2);
    add(stripe, mat.trim, "flankStripe").position.z = -0.1;
  }

  // Portholes along both flanks, lit warm from the cabin, each in a dark clamp ring.
  const outward = new THREE.Vector3();
  const facing = new THREE.Vector3(0, 0, 1);
  for (const side of [-1, 1]) {
    for (const z of [-0.72, 0.22]) {
      const el = 0.38;
      outward.set(side * Math.cos(el), Math.sin(el), 0);
      const at = outward.clone().multiplyScalar(0.872).setZ(z);
      const q = new THREE.Quaternion().setFromUnitVectors(facing, outward);
      const pane = add(new THREE.CircleGeometry(0.1, 24), mat.porthole, "porthole");
      pane.position.copy(at);
      pane.quaternion.copy(q);
      const ring = add(new THREE.TorusGeometry(0.115, 0.026, 8, 28), mat.frame, "portholeRing");
      ring.position.copy(at);
      ring.quaternion.copy(q);
    }
  }

  // Acrylic viewport and its clamp ring, with the pilot's console glowing inside.
  const dome = new THREE.SphereGeometry(0.72, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2);
  dome.rotateX(Math.PI / 2);
  add(dome, mat.glass, "viewport").position.z = 1.3;
  add(new THREE.TorusGeometry(0.73, 0.055, 10, 56), mat.frame, "viewportRing").position.z = 1.3;
  const consoleGeo = new THREE.BoxGeometry(0.7, 0.14, 0.18);
  const consoleMesh = add(consoleGeo, mat.console, "console");
  consoleMesh.position.set(0, -0.32, 1.42);
  consoleMesh.rotation.x = -0.5;
  const seat = add(new THREE.CapsuleGeometry(0.2, 0.3, 4, 12), mat.rubber, "seat");
  seat.position.set(0, -0.15, 1.0);

  // Sail: an extruded stadium with a hatch, a mast, and navigation lights.
  const sailShape = new THREE.Shape();
  const sw = 0.34, sl = 0.62;
  sailShape.moveTo(-sw, -sl + sw);
  sailShape.lineTo(-sw, sl - sw);
  sailShape.absarc(0, sl - sw, sw, Math.PI, 0, true);
  sailShape.lineTo(sw, -sl + sw);
  sailShape.absarc(0, -sl + sw, sw, 0, Math.PI, true);
  const sailGeo = new THREE.ExtrudeGeometry(sailShape, { depth: 0.42, bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.05, bevelSegments: 3, curveSegments: 16 });
  sailGeo.rotateX(-Math.PI / 2);
  const sail = add(sailGeo, mat.hull, "sail");
  sail.position.set(0, 0.62, -0.15);
  const hatch = add(new THREE.CylinderGeometry(0.2, 0.22, 0.08, 28), mat.trim, "hatch");
  hatch.position.set(0, 1.1, -0.25);
  const hatchRing = add(new THREE.TorusGeometry(0.21, 0.02, 6, 28), mat.frame, "hatchRing");
  hatchRing.position.set(0, 1.14, -0.25);
  hatchRing.rotation.x = Math.PI / 2;
  const mast = add(new THREE.CylinderGeometry(0.018, 0.025, 0.55, 8), mat.frame, "mast");
  mast.position.set(0, 1.35, -0.55);
  add(new THREE.SphereGeometry(0.04, 12, 8), mat.navRed, "navLightPort").position.set(-0.36, 0.95, 0.25);
  add(new THREE.SphereGeometry(0.04, 12, 8), mat.navGreen, "navLightStarboard").position.set(0.36, 0.95, 0.25);
  add(new THREE.SphereGeometry(0.035, 10, 8), mat.navRed, "mastLight").position.set(0, 1.64, -0.55);
  // Light bar across the sail's leading edge.
  const bar = add(new THREE.BoxGeometry(0.5, 0.07, 0.07), mat.lamp, "lightBar");
  bar.position.set(0, 0.98, 0.43);

  // Photo camera housing on the brow, with its lens and a recording light.
  const camBox = add(new THREE.BoxGeometry(0.28, 0.22, 0.34), mat.frame, "cameraHousing");
  camBox.position.set(0, 0.7, 0.98);
  const lens = new THREE.CylinderGeometry(0.08, 0.09, 0.12, 20);
  lens.rotateX(Math.PI / 2);
  add(lens, mat.glass, "cameraLens").position.set(0, 0.7, 1.2);
  add(new THREE.SphereGeometry(0.025, 8, 6), mat.navRed, "recLight").position.set(0.1, 0.79, 1.12);

  // Ballast tanks along the flanks.
  for (const side of [-1, 1]) {
    const tank = new THREE.CapsuleGeometry(0.2, 1.6, 6, 20);
    tank.rotateX(Math.PI / 2);
    add(tank, mat.trim, "ballastTank").position.set(side * 0.8, -0.48, -0.1);
    for (const z of [-0.6, 0.4]) {
      const clamp = new THREE.TorusGeometry(0.205, 0.018, 6, 24);
      add(clamp, mat.frame, "tankClamp").position.set(side * 0.8, -0.48, z);
    }
  }

  // Skids with upturned noses, on struts.
  for (const side of [-1, 1]) {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(side * 0.55, -1.02, -1.5),
      new THREE.Vector3(side * 0.55, -1.05, 0.6),
      new THREE.Vector3(side * 0.55, -0.98, 1.25),
      new THREE.Vector3(side * 0.55, -0.78, 1.55),
    ]);
    add(new THREE.TubeGeometry(curve, 32, 0.05, 10, false), mat.frame, "skid");
    for (const z of [-1.1, 0.0, 1.0]) {
      const strut = add(new THREE.CylinderGeometry(0.03, 0.03, 0.45, 8), mat.frame, "strut");
      strut.position.set(side * 0.5, -0.82, z);
      strut.rotation.z = side * 0.25;
    }
  }

  // Ducted thrusters: two on outriggers, one at the stern. Each prop is a named group so the page can spin it.
  const makeThruster = (name, radius, length) => {
    const g = new THREE.Group();
    g.name = name;
    const duct = new THREE.CylinderGeometry(radius, radius * 0.92, length, 32, 1, true);
    duct.rotateX(Math.PI / 2);
    const ductMat = mat.frame.clone();
    ductMat.side = THREE.DoubleSide;
    ductMat.name = "duct";
    add(duct, ductMat, "duct", g);
    add(new THREE.TorusGeometry(radius, 0.03, 8, 32), mat.hull, "ductLip", g).position.z = length / 2;
    const hub = new THREE.CylinderGeometry(radius * 0.22, radius * 0.3, length * 0.9, 16);
    hub.rotateX(Math.PI / 2);
    add(hub, mat.frame, "hub", g);
    const prop = new THREE.Group();
    prop.name = `${name}Prop`;
    for (let i = 0; i < 4; i++) {
      const pivot = new THREE.Group();
      pivot.rotation.z = (i / 4) * Math.PI * 2;
      prop.add(pivot);
      const blade = add(new THREE.BoxGeometry(radius * 0.85, radius * 0.3, 0.02), mat.trim, "blade", pivot);
      blade.position.x = radius * 0.5;
      blade.rotation.x = 0.5;
    }
    g.add(prop);
    return g;
  };
  const stern = makeThruster("thrusterStern", 0.36, 0.38);
  stern.position.z = -2.12;
  root.add(stern);
  for (const side of [-1, 1]) {
    const t = makeThruster(side < 0 ? "thrusterPort" : "thrusterStarboard", 0.24, 0.34);
    t.position.set(side * 1.18, 0.05, -0.95);
    root.add(t);
    const arm = add(new THREE.BoxGeometry(0.42, 0.06, 0.16), mat.frame, "outrigger");
    arm.position.set(side * 0.92, 0.05, -0.95);
  }

  // Headlight pods low on the bow, with emissive lenses the spotlights sit in.
  for (const side of [-1, 1]) {
    const pod = new THREE.CylinderGeometry(0.12, 0.14, 0.3, 20);
    pod.rotateX(Math.PI / 2);
    add(pod, mat.frame, "lampPod").position.set(side * 0.66, -0.36, 1.18);
    const lensGeo = new THREE.CircleGeometry(0.105, 20);
    const lensMesh = add(lensGeo, mat.lamp, side < 0 ? "lampL" : "lampR");
    lensMesh.position.set(side * 0.66, -0.36, 1.335);
    const bracket = add(new THREE.BoxGeometry(0.2, 0.05, 0.12), mat.frame, "lampBracket");
    bracket.position.set(side * 0.52, -0.36, 1.1);
  }

  // Folded manipulator arm under the bow.
  const shoulder = add(new THREE.SphereGeometry(0.09, 14, 10), mat.frame, "armShoulder");
  shoulder.position.set(0.28, -0.78, 0.95);
  const upper = add(new THREE.CylinderGeometry(0.05, 0.05, 0.5, 10), mat.trim, "armUpper");
  upper.position.set(0.28, -0.82, 1.18);
  upper.rotation.x = Math.PI / 2 - 0.2;
  const fore = add(new THREE.CylinderGeometry(0.04, 0.04, 0.4, 10), mat.trim, "armFore");
  fore.position.set(0.2, -0.74, 1.4);
  fore.rotation.set(Math.PI / 2 + 0.5, 0, 0.6);
  for (const s of [-1, 1]) {
    const claw = add(new THREE.ConeGeometry(0.025, 0.14, 6), mat.frame, "armClaw");
    claw.position.set(0.1 + s * 0.03, -0.62, 1.52);
    claw.rotation.x = -0.8;
  }

  // Bolt heads around the viewport ring, merged into one mesh.
  const boltGeos = [];
  for (let i = 0; i < 24; i++) {
    const a = (i / 24) * Math.PI * 2;
    const b = new THREE.SphereGeometry(0.022, 6, 4);
    b.translate(Math.cos(a) * 0.73, Math.sin(a) * 0.73, 1.36);
    boltGeos.push(b);
  }
  add(mergeSimple(THREE, boltGeos), mat.trim, "bolts");

  return root;
}

// Merges non-indexed copies of geometries that share attributes (position, normal, uv).
function mergeSimple(THREE, geos) {
  const parts = geos.map((g) => (g.index ? g.toNonIndexed() : g));
  const names = ["position", "normal", "uv"];
  const out = new THREE.BufferGeometry();
  for (const name of names) {
    const size = parts[0].attributes[name].itemSize;
    const total = parts.reduce((n, g) => n + g.attributes[name].array.length, 0);
    const arr = new Float32Array(total);
    let o = 0;
    for (const g of parts) {
      arr.set(g.attributes[name].array, o);
      o += g.attributes[name].array.length;
    }
    out.setAttribute(name, new THREE.BufferAttribute(arr, size));
  }
  return out;
}
