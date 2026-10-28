// The catalog: every star to magnitude 6, the constellation figures and names (d3-celestial), and each star's name,
// designation, distance, and spectral type.
import { eqVector } from "../scene/astro.js";

const GREEK = {
  α: "Alpha", β: "Beta", γ: "Gamma", δ: "Delta", ε: "Epsilon", ζ: "Zeta", η: "Eta", θ: "Theta", ι: "Iota",
  κ: "Kappa", λ: "Lambda", μ: "Mu", ν: "Nu", ξ: "Xi", ο: "Omicron", π: "Pi", ρ: "Rho", σ: "Sigma", τ: "Tau",
  υ: "Upsilon", φ: "Phi", χ: "Chi", ψ: "Psi", ω: "Omega",
};

// Star clusters and galaxies a person looks for by name.
const SIGHTS = [
  { name: "Pleiades", ra: 56.75, dec: 24.12, kind: "Star cluster in Taurus", detail: "444 light-years away", mag: 1.6 },
  { name: "Andromeda Galaxy", ra: 10.68, dec: 41.27, kind: "Galaxy in Andromeda", detail: "2.5 million light-years away", mag: 3.4 },
  { name: "Orion Nebula", ra: 83.82, dec: -5.39, kind: "Nebula in Orion", detail: "1,344 light-years away", mag: 4.0 },
];

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} answered ${res.status}`);
  return res.json();
}

export async function loadCatalog() {
  const [stars, lines, cons, info] = await Promise.all([
    getJson("./vendor/d3-celestial/data/stars.6.json"),
    getJson("./vendor/d3-celestial/data/constellations.lines.json"),
    getJson("./vendor/d3-celestial/data/constellations.json"),
    getJson("./data/stars-info.json"),
  ]);
  const constellations = cons.features.map((f, i) => ({
    index: i,
    id: f.id,
    name: f.properties.name,
    genitive: f.properties.gen,
    rank: parseInt(f.properties.rank, 10) || 3,
    label: eqVector(f.geometry.coordinates[0], f.geometry.coordinates[1]),
  }));
  const conIndex = new Map(constellations.map((c) => [c.id, c.index]));
  const features = stars.features;
  const starList = features.map((f) => {
    const row = info[String(f.id)] || ["", "", "", "", 0, ""];
    return {
      hip: f.id,
      mag: f.properties.mag,
      bv: parseFloat(f.properties.bv),
      ra: f.geometry.coordinates[0],
      dec: f.geometry.coordinates[1],
      name: row[0],
      bayer: row[1],
      flam: row[2],
      con: row[3],
      ly: row[4],
      spect: row[5],
    };
  });
  const sights = SIGHTS.map((s) => ({ ...s, dir: eqVector(s.ra, s.dec) }));
  return { features, lines, constellations, conIndex, stars: starList, sights };
}

export function designation(star, constellations, conIndex) {
  const c = constellations[conIndex.get(star.con)];
  const gen = c ? c.genitive : star.con;
  if (star.bayer) return `${star.bayer} ${gen}`;
  if (star.flam) return `${star.flam} ${gen}`;
  return `HIP ${star.hip}`;
}

export function greekName(letter) {
  return GREEK[letter] || letter;
}

export function colorWord(bv) {
  if (!Number.isFinite(bv)) return "white";
  if (bv < -0.1) return "blue-white";
  if (bv < 0.15) return "white";
  if (bv < 0.45) return "yellow-white";
  if (bv < 0.8) return "yellow";
  if (bv < 1.3) return "orange";
  return "red-orange";
}
