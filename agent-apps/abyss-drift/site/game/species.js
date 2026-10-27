// The eight species of the trench: where they live, how close a good photo needs, and the silhouette the log draws.
// Depths are meters below the surface; the trench floor is FLOOR_DEPTH.

export const FLOOR_DEPTH = 600;

const fish = (x, y, s) =>
  `M${x} ${y}c${3 * s} ${-2.6 * s} ${8 * s} ${-2.6 * s} ${11 * s} 0l${3 * s} ${-2.2 * s}v${4.4 * s}l${-3 * s} ${-2.2 * s}` +
  `c${-3 * s} ${2.6 * s} ${-8 * s} ${2.6 * s} ${-11 * s} 0z`;

export const SPECIES = [
  {
    id: "whale",
    name: "Humpback whale",
    short: "Humpback",
    band: [8, 40],
    maxDist: 75,
    selfLit: false,
    fill: "M4 22C8 14 22 12 36 14C46 15 52 17 57 19L62 12L61 21L63 29L56 23C50 26 40 28 30 28C25 28 21 31 15 35L17 28C10 28 5 26 4 22Z",
  },
  {
    id: "manta",
    name: "Giant manta",
    short: "Manta",
    band: [18, 60],
    maxDist: 40,
    selfLit: false,
    fill:
      "M32 9C36 9 38 12 40 15C48 15 56 17 63 22C54 22 46 24 40 27C38 30 35 32 33 34L32 40L31 34C29 32 26 30 24 27" +
      "C18 24 10 22 1 22C8 17 16 15 24 15C26 12 28 9 32 9ZM29 10L26 4L31 8ZM35 10L38 4L33 8Z",
  },
  {
    id: "school",
    name: "Sardine school",
    short: "Sardines",
    band: [30, 110],
    maxDist: 34,
    selfLit: false,
    fill: fish(6, 12, 1.4) + fish(30, 20, 1.5) + fish(10, 30, 1.3) + fish(38, 8, 1.1) + fish(40, 32, 1.1),
  },
  {
    id: "jellyfish",
    name: "Crown jelly",
    short: "Crown jelly",
    band: [80, 170],
    maxDist: 26,
    selfLit: true,
    fill: "M17 19C17 7 47 7 47 19C47 21 45 22 43 21C41 23 39 21 37 22C35 23 33 21 31 22C29 23 27 21 25 22C23 23 21 21 19 22C18 22 17 21 17 19Z",
    stroke: "M21 22C20 28 24 32 21 39M27 23C27 29 30 33 28 39M32 23C33 29 30 34 33 40M37 23C37 29 40 33 37 39M43 22C44 28 40 32 43 38",
  },
  {
    id: "lanternfish",
    name: "Lanternfish shoal",
    short: "Lanternfish",
    band: [190, 280],
    maxDist: 26,
    selfLit: true,
    fill: "M5 20C13 12 33 11 45 17L57 10L55 20L57 30L45 23C33 29 13 28 5 20ZM9 19A1.5 1.5 0 1 0 9 19.1Z",
    dots: [[16, 24], [21, 25], [26, 25.5], [31, 25.5], [36, 25], [41, 24]],
  },
  {
    id: "anglerfish",
    name: "Deep-sea anglerfish",
    short: "Anglerfish",
    band: [300, 380],
    maxDist: 20,
    selfLit: true,
    fill: "M10 23C10 13 22 8 34 10C42 12 48 17 50 21L60 15L58 23L61 32L50 26C46 32 36 35 26 34C18 33 13 30 10 27L16 25L11 24Z",
    stroke: "M22 10C20 3 11 2 7 8",
    dots: [[7, 9.5]],
  },
  {
    id: "squid",
    name: "Giant squid",
    short: "Giant squid",
    band: [400, 500],
    maxDist: 42,
    selfLit: false,
    fill: "M30 15C40 12 52 14 62 20C52 26 40 28 30 25ZM54 16L60 9L62 20ZM54 24L60 31L62 20Z",
    stroke: "M30 17C22 12 14 15 3 9M30 19C21 17 12 20 2 17M30 21C21 22 12 22 3 25M30 23C22 26 14 26 4 32M30 20C24 20 18 19 9 21",
  },
  {
    id: "crab",
    name: "Yeti crab",
    short: "Yeti crab",
    band: [560, 600],
    maxDist: 16,
    selfLit: false,
    fill: "M20 23C20 15 44 15 44 23C44 27 20 27 20 23ZM10 13C6 12 4 16 7 18C10 20 14 18 14 16ZM54 13C58 12 60 16 57 18C54 20 50 18 50 16Z",
    stroke: "M22 21L13 17M42 21L51 17M22 25L12 29L9 35M42 25L52 29L55 35M25 26L19 33L18 38M39 26L45 33L46 38M29 27L27 36M35 27L37 36",
  },
];

export const SPECIES_BY_ID = Object.fromEntries(SPECIES.map((s) => [s.id, s]));

export function zoneName(depth) {
  if (depth < 60) return "Sunlit zone";
  if (depth < 200) return "Twilight zone";
  if (depth < 520) return "Midnight zone";
  return "Vent field";
}

/** An SVG string for a species' silhouette, drawn in currentColor. */
export function silhouetteSvg(sp, className = "silhouette") {
  const stroke = sp.stroke ? `<path d="${sp.stroke}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>` : "";
  const dots = (sp.dots || []).map(([x, y]) => `<circle class="photophore" cx="${x}" cy="${y}" r="1.6"/>`).join("");
  return `<svg class="${className}" viewBox="0 0 64 40" aria-hidden="true"><path d="${sp.fill}" fill="currentColor"/>${stroke}${dots}</svg>`;
}
