// The illustrated map: land, a river, parks, a town, and roads drawn from the venue's coordinates, the same picture
// every time for the same place. The route runs in from the edge along a road and ends under the pin.
const NS = "http://www.w3.org/2000/svg";
const W = 1000;
const H = 700;
const VENUE = [560, 372];

function rng(lat, lon) {
  let s = Math.abs(Math.round(lat * 10007 + lon * 7919)) % 2147483646 || 1;
  return () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646;
}

function el(name, attrs, parent) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.append(node);
  return node;
}

function blob(cx, cy, r, rand, points = 9) {
  const pts = [];
  for (let i = 0; i < points; i++) {
    const a = (i / points) * Math.PI * 2;
    const k = r * (0.72 + rand() * 0.5);
    pts.push([cx + Math.cos(a) * k * 1.3, cy + Math.sin(a) * k]);
  }
  let d = "";
  for (let i = 0; i < points; i++) {
    const p0 = pts[(i - 1 + points) % points];
    const p1 = pts[i];
    const p2 = pts[(i + 1) % points];
    const p3 = pts[(i + 2) % points];
    if (i === 0) d += `M${p1[0].toFixed(1)} ${p1[1].toFixed(1)}`;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += `C${c1[0].toFixed(1)} ${c1[1].toFixed(1)} ${c2[0].toFixed(1)} ${c2[1].toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d + "Z";
}

function town(address) {
  const parts = address.split(",").map((p) => p.replace(/\d+/g, "").trim()).filter(Boolean);
  if (parts.length >= 3) return parts[parts.length - 2];
  return parts.length === 2 ? parts[1] : "";
}

export function drawMap(svg, place) {
  const rand = rng(place.lat, place.lon);
  const [vx, vy] = VENUE;
  const flipX = rand() > 0.5;
  const g = el("g", flipX ? { transform: `translate(${W} 0) scale(-1 1)` } : {}, svg);
  const mirror = (x) => (flipX ? W - x : x);

  el("rect", { class: "m-land", x: -50, y: -50, width: W + 100, height: H + 100 }, g);

  // Fields and parks, then the orchard rows around the venue.
  for (let i = 0; i < 5; i++) {
    const cx = 80 + rand() * 840;
    const cy = 60 + rand() * 580;
    if (Math.hypot(cx - vx, cy - vy) < 150) continue;
    el("path", { class: "m-park", d: blob(cx, cy, 50 + rand() * 70, rand) }, g);
  }
  el("path", { class: "m-park", d: blob(vx + 10, vy + 4, 118, rand, 11) }, g);
  const rows = el("g", { transform: `rotate(${(rand() * 30 - 15).toFixed(1)} ${vx} ${vy})` }, g);
  for (let y = -90; y <= 90; y += 22) {
    for (let x = -130; x <= 130; x += 22) {
      if ((x * x) / 17000 + (y * y) / 9500 > 1) continue;
      if (Math.abs(x) < 40 && Math.abs(y) < 30) continue;
      el("circle", { class: "m-block", cx: vx + x, cy: vy + y, r: 5.2 }, rows);
    }
  }

  // The river, wide and slow, across one corner.
  const ry = 90 + rand() * 120;
  el("path", {
    class: "m-river",
    d: `M-60 ${ry + 380} C180 ${ry + 300} 160 ${ry + 60} 380 ${ry} S700 ${ry - 160} 1060 ${ry - 60}`,
    "stroke-width": 54,
  }, g);
  el("path", { class: "m-water", d: blob(860, ry + 470, 64, rand) }, g);

  // The town: a tilted grid of streets and blocks.
  const tx = 230 + rand() * 60;
  const ty = 470 + rand() * 60;
  const grid = el("g", { transform: `rotate(${(rand() * 40 - 20).toFixed(1)} ${tx} ${ty})` }, g);
  for (let i = -5; i <= 5; i++) {
    el("path", { class: "m-minor", d: `M${tx - 230} ${ty + i * 36} L${tx + 230} ${ty + i * 36}` }, grid);
    el("path", { class: "m-minor", d: `M${tx + i * 42} ${ty - 190} L${tx + i * 42} ${ty + 190}` }, grid);
  }
  for (let i = -5; i < 5; i++) {
    for (let j = -5; j < 5; j++) {
      const d = Math.hypot(i * 42, j * 36);
      if (d > 200 || rand() < 0.25 + d / 420) continue;
      el("rect", { class: "m-block", x: tx + i * 42 + 6, y: ty + j * 36 + 6, width: 30, height: 24, rx: 4 }, grid);
    }
  }

  // Roads: a casing under each, the route's road last.
  const roads = [
    `M-40 ${ty - 140} C200 ${ty - 200} 420 ${ty - 60} 640 ${ty + 40} S900 ${ty + 10} 1040 ${ty - 30}`,
    `M${tx + 120} 740 C${tx + 160} 520 ${tx + 40} 300 ${tx + 160} 120 S${tx + 300} -20 ${tx + 340} -60`,
    `M${vx} ${vy} C${vx + 140} ${vy - 70} ${vx + 260} ${vy - 160} 1040 ${vy - 260}`,
  ];
  const route = `M${tx - 300} ${ty + 260} C${tx - 120} ${ty + 120} ${tx - 40} ${ty + 30} ${tx + 90} ${ty - 40}`
    + ` S${vx - 160} ${vy + 60} ${vx} ${vy}`;
  for (const d of [...roads, route]) el("path", { class: "m-casing", d, "stroke-width": 17 }, g);
  for (const d of [...roads, route]) el("path", { class: "m-road", d, "stroke-width": 11 }, g);

  el("path", { class: "m-glow m-glow--wide", d: route, "stroke-width": 34 }, g);
  el("path", { class: "m-glow m-glow--mid", d: route, "stroke-width": 16 }, g);
  el("path", { class: "m-route", d: route, pathLength: 1 }, g);
  el("path", { class: "m-pulse", d: route, pathLength: 1 }, g);

  // Labels sit outside the mirrored group so the words read the right way.
  const name = town(place.address);
  if (name) {
    const lx = Math.min(660, Math.max(340, mirror(tx)));
    const label = el("text", { class: "m-label m-label--town", x: lx, y: ty + 10, "text-anchor": "middle" }, svg);
    label.textContent = name;
  }
  const compass = el("g", { transform: `translate(${W - 70} 70)` }, svg);
  el("circle", { class: "m-casing", r: 26, "stroke-width": 1.5 }, compass);
  el("path", { class: "m-road", d: "M0 -16 L6 4 L0 0 L-6 4 Z", "stroke-width": 2 }, compass);
  el("text", { class: "m-label", y: -32, "text-anchor": "middle" }, compass).textContent = "N";

  return { venue: [mirror(vx), vy] };
}

// Where a point of the 1000 by 700 picture lands inside its box, in percent, for preserveAspectRatio slice.
export function placePin(map, venue) {
  const w = map.clientWidth;
  const h = map.clientHeight;
  const k = Math.max(w / W, h / H);
  const x = (venue[0] * k + (w - W * k) / 2) / w;
  const y = (venue[1] * k + (h - H * k) / 2) / h;
  map.style.setProperty("--px", (x * 100).toFixed(2));
  map.style.setProperty("--py", (y * 100).toFixed(2));
  map.querySelector("[data-pin-label]")?.classList.toggle("is-left", x > 0.62);
}
