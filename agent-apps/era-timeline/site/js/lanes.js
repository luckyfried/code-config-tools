// Lanes for the pins, recomputed at every zoom: a greedy interval pass that gives each pin the first lane where its
// flag fits, sliding the flags already in that lane along it to make room, and gathers the pins that fit in no lane
// into count badges on the axis, which open on zoom.

/**
 * Starts for flags kept in pin order along one lane: each inside its window `[lo, hi]`, clear of the one before by
 * `space`, outside its own `blocks` (start ranges it may not take), and as near its `pref` as the others let it.
 * Null when they cannot all fit.
 */
export function fitLane(list, space) {
  const up = (m, x) => {
    for (let moved = true; moved; ) {
      moved = false;
      for (const [a, b] of m.blocks ?? []) if (x > a && x < b) [x, moved] = [b, true];
    }
    return x;
  };
  const down = (m, x) => {
    for (let moved = true; moved; ) {
      moved = false;
      for (const [a, b] of m.blocks ?? []) if (x > a && x < b) [x, moved] = [a, true];
    }
    return x;
  };
  // The latest start each flag can take, from the far end back; a flag that cannot reach its window fails the lane.
  const late = [];
  let limit = Infinity;
  for (let i = list.length - 1; i >= 0; i -= 1) {
    const m = list[i];
    const x = down(m, Math.min(m.hi, limit - m.size - space));
    if (x < m.lo) return null;
    late[i] = x;
    limit = x;
  }
  // Then from the near end, each as near its preferred start as the flag before it and its latest start allow.
  const starts = [];
  let end = -Infinity;
  for (const [i, m] of list.entries()) {
    const x = up(m, Math.max(Math.min(Math.max(m.pref, m.lo), late[i]), end + space));
    starts.push(x);
    end = x + m.size;
  }
  return starts;
}

/**
 * `items`: `[{id, at, size, first}]`, `at` the pin's pixel on the time axis and `size` its flag's length along it
 * (rows mode) or across it (pack mode); pins marked `first` are placed before the rest, so the open pin never hides.
 * With `short`, the shorter flags are placed first, so the most of them find room.
 *
 * Rows mode (time runs across): flags are `size` wide starting `lead` pixels before the pin, in up to `rows` rows;
 * near the far `edge` a flag turns to hang back from its pin so it stays on screen. With `slide`, any flag in a row
 * may slide back along it, as far as hanging back from its pin and never before `start`, so a new flag finds room
 * in a row whenever the row can hold them all, before it tries the next row.
 * Pack mode (time runs down): flags are `thick` tall (or the item's own `thick`), centered on the pin, and slide
 * across from `from` to the first gap that holds them, cut short to no less than `minSize` before `to`; `slide` is
 * how near a flag's end its pin may sit when the flag slides along the axis to find room. A flag that finds no gap
 * goes next to the axis when the flags there can slide along it to make room.
 *
 * Returns `{placed: Map(id -> {lane, from, size}), lanes, clusters: [{at, ids}]}`; `lane` is a row index in rows mode
 * and the cross-axis pixel in pack mode.
 */
export function layoutLanes(items, options) {
  const order = [...items].sort((a, b) => (b.first === true) - (a.first === true) || (options.short ? a.size - b.size : 0) || a.at - b.at);
  const byAt = (p, q) => p.item.at - q.item.at;
  const placed = new Map();
  const hidden = [];
  let lanes = 0;
  if (options.mode === "rows") {
    const rows = Array.from({ length: options.rows }, () => ({ list: [], starts: [] }));
    for (const item of order) {
      let ahead = item.at - options.lead;
      if (options.edge !== undefined && ahead + item.size > options.edge) ahead = Math.max(item.at - item.size + options.lead, options.edge - item.size);
      const back = options.slide ? Math.max(item.at - item.size + options.lead, options.start ?? -Infinity) : ahead;
      const entry = { item, size: item.size, lo: Math.min(back, ahead), hi: ahead, pref: ahead };
      const row = rows.find((r) => {
        const list = [...r.list, entry].sort(byAt);
        const starts = fitLane(list, 2 * options.gap);
        if (starts) Object.assign(r, { list, starts });
        return Boolean(starts);
      });
      if (!row) hidden.push(item);
    }
    for (const [index, row] of rows.entries()) {
      for (const [k, entry] of row.list.entries()) placed.set(entry.item.id, { lane: index, from: row.starts[k], size: entry.size });
      if (row.list.length) lanes = index + 1;
    }
  } else {
    const boxes = [];
    // Where a flag `thick` tall starting at `from` along the axis would sit across it, and the boxes beside it.
    const across = (from, thick, size) => {
      const a = from - options.gap;
      const b = from + thick + options.gap;
      const near = boxes.filter((box) => a < box.b && b > box.a).sort((p, q) => p.x0 - q.x0);
      let x = options.from;
      for (const box of near) {
        if (x + size + options.gap <= box.x0) break;
        x = Math.max(x, box.x1 + options.gap);
      }
      return { a, b, x, near };
    };
    const put = (box, from) => {
      Object.assign(box, { a: from - options.gap, b: from + box.thick + options.gap });
      placed.set(box.item.id, { lane: box.x0, from, size: box.x1 - box.x0 });
    };
    for (const item of order) {
      const thick = item.thick ?? options.thick;
      const centered = item.at - thick / 2;
      let best = across(centered, thick, item.size);
      let from = centered;
      // With `slide`, a flag held off by its neighbors slides along the axis, never so far that its pin leaves its
      // side, to the spot nearest the axis.
      if (options.slide && best.x > options.from) {
        const lo = item.at - thick + options.slide;
        const hi = item.at - options.slide;
        const edges = boxes.flatMap((box) => [box.b + options.gap, box.a - options.gap - thick]).filter((f) => f >= lo && f <= hi);
        for (const f of [lo, hi, ...edges].sort((p, q) => Math.abs(p - centered) - Math.abs(q - centered))) {
          const spot = across(f, thick, item.size);
          if (spot.x < best.x) {
            best = spot;
            from = f;
          }
        }
      }
      const { a, b, x, near } = best;
      const room = options.to - x;
      const window = (it, t) => (options.slide ? { lo: it.at - t + options.slide, hi: it.at - options.slide } : { lo: it.at - t / 2, hi: it.at - t / 2 });
      if (room >= Math.min(item.size, options.minSize)) {
        const size = Math.min(item.size, room);
        const box = { item, thick, x0: x, x1: x + size };
        boxes.push(box);
        put(box, from);
        lanes = Math.max(lanes, near.length + 1);
        continue;
      }
      // No gap holds it: next to the axis, the flags there slide along it, clear of the flags beside them, to let it in.
      const size = Math.min(item.size, options.to - options.from);
      const entry = { item, thick, x0: options.from, x1: options.from + size };
      const column = [...boxes.filter((box) => box.x0 === options.from), entry];
      const others = boxes.filter((box) => box.x0 !== options.from);
      const list = column
        .map((box) => ({
          box,
          item: box.item,
          size: box.thick,
          pref: box.item.at - box.thick / 2,
          ...window(box.item, box.thick),
          blocks: others.filter((o) => o.x0 < box.x1 + options.gap).map((o) => [o.a - box.thick - options.gap, o.b + options.gap]),
        }))
        .sort(byAt);
      const starts = size >= Math.min(item.size, options.minSize) ? fitLane(list, 2 * options.gap) : null;
      if (!starts) {
        hidden.push(item);
        continue;
      }
      boxes.push(entry);
      for (const [k, m] of list.entries()) put(m.box, starts[k]);
      lanes = Math.max(lanes, 1);
    }
  }
  return { placed, lanes, clusters: cluster(hidden, options.badge) };
}

/** Hidden pins gathered into badges at least `badge` pixels apart, each at the mean of its pins. */
export function cluster(hidden, badge) {
  const sorted = [...hidden].sort((a, b) => a.at - b.at);
  const out = [];
  for (const item of sorted) {
    const last = out[out.length - 1];
    if (last && item.at - last.at < badge) {
      last.ids.push(item.id);
      last.sum += item.at;
      last.at = last.sum / last.ids.length;
    } else {
      out.push({ at: item.at, sum: item.at, ids: [item.id] });
    }
  }
  // Moving a badge to its mean can bring it within reach of the one before; merge until none are.
  for (let i = 1; i < out.length; ) {
    if (out[i].at - out[i - 1].at < badge) {
      out[i - 1].ids.push(...out[i].ids);
      out[i - 1].sum += out[i].sum;
      out[i - 1].at = out[i - 1].sum / out[i - 1].ids.length;
      out.splice(i, 1);
      if (i > 1) i -= 1;
    } else {
      i += 1;
    }
  }
  return out.map(({ at, ids }) => ({ at, ids }));
}

/**
 * Moves each badge along the axis to the nearest spot where its ring (`radius`) clears every shown pin's dot
 * (`dots`: `[{at}]`, each `dot` in radius) by `gap` and the badges before it by four times that: first no further
 * than `reach` from the mean of its pins, then no further than three times that. A badge with no such spot joins the
 * badge before it when that one is near, or else sits at its mean across the stems; a shown pin is never taken in.
 * Returns `[{at, ids}]`.
 */
export function clearBadges(clusters, dots, { radius, dot, gap, reach }) {
  const clearDot = radius + dot + gap;
  const clearBadge = 2 * radius + 4 * gap;
  const out = [];
  for (const c of clusters) {
    let ids = [...c.ids];
    let sum = c.at * ids.length;
    for (;;) {
      const mean = sum / ids.length;
      const blocks = [...dots.map((d) => [d.at - clearDot, d.at + clearDot]), ...out.map((b) => [b.at - clearBadge, b.at + clearBadge])];
      const nearest = (far) => [mean, ...blocks.flat()].filter((p) => Math.abs(p - mean) <= far).sort((p, q) => Math.abs(p - mean) - Math.abs(q - mean));
      const clear = (p) => blocks.every(([a, b]) => p <= a || p >= b);
      const spot = nearest(reach).find(clear) ?? nearest(3 * reach).find(clear);
      if (spot !== undefined) {
        out.push({ at: spot, ids, sum });
        break;
      }
      const prev = out[out.length - 1];
      if (prev && Math.abs(prev.at - mean) < clearBadge + reach) {
        out.pop();
        ids = [...prev.ids, ...ids];
        sum += prev.sum;
      } else {
        out.push({ at: mean, ids, sum });
        break;
      }
    }
  }
  return out.map(({ at, ids }) => ({ at, ids }));
}

/** Pairs of boxes `{x, y, w, h}` that overlap by more than half a pixel. */
export function countOverlaps(boxes) {
  let count = 0;
  for (let i = 0; i < boxes.length; i += 1) {
    for (let j = i + 1; j < boxes.length; j += 1) {
      const a = boxes[i];
      const b = boxes[j];
      if (a.x + 0.5 < b.x + b.w && b.x + 0.5 < a.x + a.w && a.y + 0.5 < b.y + b.h && b.y + 0.5 < a.y + a.h) count += 1;
    }
  }
  return count;
}
