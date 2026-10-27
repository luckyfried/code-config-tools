// The person's life from config.js, worked out into cells: which are lived, which era tints each, which carry an event.

import { WEEKS, lifeOf, parseDay, today, yearOf } from "./life.js";

export const SAMPLE = {
  name: "Ines Halvorsen",
  birthdate: "1991-03-14",
  years: 90,
  eras: [
    { from: "1997-08", to: "2009-06", label: "School in Bergen", color: "#C9A23A" },
    { from: "2009-08", to: "2014-06", label: "Trondheim", color: "#5E8C6A" },
    { from: "2014-09", to: "2018-03", label: "First job, Oslo", color: "#B4656F" },
    { from: "2018-04", to: "2023-01", label: "Lisbon", color: "#3F8F9A" },
    { from: "2023-02", to: "now", label: "The studio", color: "#9A7A4E" },
  ],
  events: [
    { date: "2009-08-17", label: "Left home" },
    { date: "2016-06-11", label: "Met Tomas" },
    { date: "2018-04-02", label: "Moved to Lisbon" },
    { date: "2021-09-04", label: "Married" },
    { date: "2023-11-30", label: "Aud was born" },
    { date: "2025-05-17", label: "Opened the studio" },
    { date: "2031-03-14", label: "Forty" },
  ],
  quote: "How we spend our days is, of course, how we spend our lives. — Annie Dillard",
  paper: "A3",
  theme: "auto",
};

export function readConfig() {
  const config = window.__APP_CONFIG__;
  if (config && typeof config === "object" && parseDay(config.birthdate) !== null) return { config, sample: false };
  return { config: SAMPLE, sample: true };
}

export function buildModel(config) {
  const rows = Number.isInteger(config.years) ? config.years : 90;
  const life = lifeOf(config.birthdate, rows);
  const day = today();
  const nowCell = day > life.last ? null : Math.max(0, life.cellOf(day));
  const lived = nowCell === null ? life.cells : nowCell;

  const eras = (config.eras ?? []).map((era, index) => {
    const start = Math.max(parseDay(era.from) ?? life.first, life.first);
    const still = era.to === "now";
    const end = Math.min(still ? day : parseDay(era.to, true) ?? day, life.last);
    return {
      index,
      label: String(era.label ?? ""),
      color: era.color,
      still,
      firstDay: start,
      lastDay: end,
      from: life.cellOf(start),
      to: life.cellOf(end),
    };
  }).filter((era) => era.to >= era.from);
  eras.forEach((era, position) => { era.index = position; });

  // An era that ends in the same year the next one starts runs up to it: the months between are the move, not a gap.
  const inOrder = [...eras].sort((a, b) => a.firstDay - b.firstDay);
  inOrder.forEach((era, k) => {
    const next = inOrder[k + 1];
    if (!next || era.still || era.lastDay >= next.firstDay - 1) return;
    if (yearOf(era.lastDay) !== yearOf(next.firstDay)) return;
    era.lastDay = next.firstDay - 1;
    era.to = life.cellOf(era.lastDay);
  });

  // A week in two eras takes the one that started later: the newer chapter.
  const eraOf = new Int8Array(life.cells).fill(-1);
  [...eras].sort((a, b) => a.firstDay - b.firstDay).forEach((era) => {
    for (let cell = era.from; cell <= era.to; cell += 1) eraOf[cell] = era.index;
  });

  const events = (config.events ?? []).map((event) => {
    const when = parseDay(event.date);
    return { label: String(event.label ?? ""), day: when, cell: when === null ? -1 : life.cellOf(when) };
  }).filter((event) => event.cell >= 0 && event.cell < life.cells).sort((a, b) => a.day - b.day);
  const eventsAt = new Map();
  for (const event of events) eventsAt.set(event.cell, [...(eventsAt.get(event.cell) ?? []), event]);

  return { config, life, rows, cells: life.cells, columns: WEEKS, now: nowCell, lived, eras, eraOf, events, eventsAt };
}
