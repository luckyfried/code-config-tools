// The one SVG: era bands behind, a rect per week, hairline leaders from events to the right margin.
// Geometry is in screen pixels at the current pitch so every cell lands on whole pixels; print scales the same drawing.

const NS = "http://www.w3.org/2000/svg";

/** Where the right-margin words sit, in pitch units past the grid's right edge; margins.js reads the same numbers. */
export const LEADER = { run: 1.2, bend: 2.7, end: 3.2 };

function make(tag, attrs = {}) {
  const el = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  return el;
}

export function createGrid(svg, model) {
  const { rows, columns, cells, now, lived, eras, eraOf, eventsAt } = model;
  const bandLayer = svg.querySelector(".bands");
  const cellLayer = svg.querySelector(".cells");
  const leaderLayer = svg.querySelector(".leaders");

  // The sweep runs corner to corner across the lived weeks. Lived cells sit in one group per diagonal, and each
  // group's --i (its place along the sweep, 0 to 1) sets when it arrives, so a frame of the sweep restyles a few
  // dozen groups, never thousands of cells.
  const lastRow = Math.floor(Math.max(0, lived - 1) / columns);
  const farthest = Math.max(1, lastRow + (lastRow > 0 ? columns - 1 : Math.max(0, lived - 1)));
  const diagonals = [];
  const diagonal = (d) => {
    if (!diagonals[d]) {
      diagonals[d] = make("g", { class: "diag" });
      diagonals[d].style.setProperty("--i", (d / farthest).toFixed(4));
    }
    return diagonals[d];
  };
  const aheadGroup = make("g", { class: "ahead-cells" });

  const rects = new Array(cells);
  for (let cell = 0; cell < cells; cell += 1) {
    const row = Math.floor(cell / columns);
    const col = cell % columns;
    const rect = make("rect");
    let kind = "w";
    let parent = aheadGroup;
    if (cell < lived) {
      kind += " lived";
      parent = diagonal(row + col);
      if (eraOf[cell] >= 0) {
        kind += " in-era";
        rect.style.setProperty("--era-c", eras[eraOf[cell]].color);
      }
    } else if (cell === now) {
      kind += " now";
    }
    if (eventsAt.has(cell)) kind += " event";
    rect.setAttribute("class", kind);
    parent.append(rect);
    rects[cell] = rect;
  }
  cellLayer.replaceChildren(...diagonals.filter(Boolean), aheadGroup);

  const bands = eras.map((era) => {
    const path = make("path", { class: "band", "data-era": String(era.index) });
    path.style.setProperty("--era-c", era.color);
    return path;
  });
  bandLayer.replaceChildren(...bands);

  svg.dataset.lived = String(lived);
  svg.dataset.weeks = String(cells);
  svg.dataset.rows = String(rows);

  /** Lays every shape out at `pitch` pixels a week; `marginLeft` and the leader placements are in pitch units. */
  function layout({ pitch, marginLeft, wordRows }) {
    const gap = pitch >= 11 ? 2 : 1;
    const size = pitch - gap;
    const width = columns * pitch;
    const height = rows * pitch;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("width", String(width));
    svg.setAttribute("height", String(height));
    const s = String(size);
    for (let cell = 0; cell < cells; cell += 1) {
      const rect = rects[cell];
      rect.setAttribute("x", String((cell % columns) * pitch));
      rect.setAttribute("y", String(Math.floor(cell / columns) * pitch));
      rect.setAttribute("width", s);
      rect.setAttribute("height", s);
    }

    // A band covers its weeks as a stepped shape and reaches into the left margin across the rows they fill.
    eras.forEach((era, k) => {
      const r0 = Math.floor(era.from / columns);
      const c0 = era.from % columns;
      const r1 = Math.floor(era.to / columns);
      const c1 = era.to % columns;
      const p = pitch;
      let d;
      if (r0 === r1) {
        d = `M${c0 * p} ${r0 * p}H${(c1 + 1) * p}V${(r0 + 1) * p}H${c0 * p}Z`;
      } else {
        d = `M${c0 * p} ${r0 * p}H${width}V${r1 * p}H${(c1 + 1) * p}V${(r1 + 1) * p}H0V${(r0 + 1) * p}H${c0 * p}Z`;
      }
      // In the margin the band runs from where its first week falls in its first row to where its last week falls in
      // its last, so it spans the rows its weeks fill and meets the next era's band edge to edge.
      const top = Math.round((r0 + c0 / columns) * p);
      const bottom = Math.round((r1 + (c1 + 1) / columns) * p);
      d += `M${-marginLeft * p} ${top}H0V${bottom}H${-marginLeft * p}Z`;
      bands[k].setAttribute("d", d);
    });

    const leaders = [];
    for (const { cell, row } of wordRows) {
      const r = Math.floor(cell / columns);
      const c = cell % columns;
      const y = (r + 0.5) * pitch - gap / 2;
      const wordY = row * pitch - gap / 2;
      const path = make("path", {
        class: cell < lived ? "leader" : "leader ahead",
        d: `M${(c + 1) * pitch - gap} ${y}H${width + LEADER.run * pitch}L${width + LEADER.bend * pitch} ${wordY}H${width + LEADER.end * pitch}`,
      });
      leaders.push(path);
    }
    leaderLayer.replaceChildren(...leaders);
  }

  return { layout, rects };
}
