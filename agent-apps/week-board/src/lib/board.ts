import { addDays, getDay } from "date-fns"
import { LATER, fromKey, toKey, type DayKey, type WeekStart, type WeekView } from "./dates"

export interface Task {
  id: string
  title: string
  notes: string
  /** A date key such as 2026-10-21, or "later". */
  day: DayKey
  done: boolean
  doneAt: number | null
  /** The day a card was on before it carried into today; cleared when the card is moved or checked. */
  carriedFrom: DayKey | null
  /** The first-open walkthrough card: shown, never counted, never saved. */
  demo?: true
}

export interface Settings {
  weekStart: WeekStart
  columns: 5 | 7
  later: boolean
}

export interface Board {
  tasks: Task[]
  settings: Settings
}

export interface AppConfig {
  name: string
  weekStart: WeekStart
  columns: 5 | 7
  later: boolean
  seedTasks: { title: string; day: string }[]
}

const STORE_KEY = "week-board:board"

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
  }
}

export function readConfig(): AppConfig {
  const c = window.__APP_CONFIG__ ?? {}
  return {
    name: typeof c.name === "string" && c.name.trim() ? c.name.trim() : "This week",
    weekStart: c.weekStart === "sun" ? "sun" : "mon",
    columns: Number(c.columns) === 5 ? 5 : 7,
    later: c.later !== false,
    seedTasks: Array.isArray(c.seedTasks)
      ? c.seedTasks.filter((t) => t && typeof t.title === "string" && t.title.trim())
      : [],
  }
}

export function newId(): string {
  return `t-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

const SEED_DAYS: Record<string, number> = {
  sun: 0, sunday: 0, mon: 1, monday: 1, tue: 2, tues: 2, tuesday: 2, wed: 3, wednesday: 3,
  thu: 4, thur: 4, thurs: 4, thursday: 4, fri: 5, friday: 5, sat: 6, saturday: 6,
}

/** A seed task's day names a day of this week, past days included, so an unfinished one carries into today. */
function seedDay(word: string, view: WeekView, laterOn: boolean): DayKey {
  const w = String(word ?? "").trim().toLowerCase()
  if (w === "later") return laterOn ? LATER : view.anchor
  if (w === "today" || w === "") return view.anchor
  if (w === "tomorrow") {
    const k = toKey(addDays(fromKey(view.today), 1))
    return view.days.includes(k) ? k : laterOn ? LATER : view.anchor
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(w) && view.days.includes(w)) return w
  if (w in SEED_DAYS) {
    const k = view.days.find((d) => getDay(fromKey(d)) === SEED_DAYS[w])
    if (k) return k
  }
  return laterOn ? LATER : view.anchor
}

export function seedBoard(config: AppConfig, view: WeekView): Board {
  const settings: Settings = { weekStart: config.weekStart, columns: config.columns, later: config.later }
  const tasks: Task[] = config.seedTasks.map((t, i) => ({
    id: `t-seed-${i}`,
    title: t.title.trim(),
    notes: "",
    day: seedDay(t.day, view, config.later),
    done: false,
    doneAt: null,
    carriedFrom: null,
  }))
  return { tasks, settings }
}

function isTask(t: unknown): t is Task {
  const o = t as Task
  return !!o && typeof o.id === "string" && typeof o.title === "string" && typeof o.day === "string"
}

/** Accepts a stored board or an exported file; returns null for anything else. */
export function parseBoard(raw: unknown): Board | null {
  const o = raw as Board
  if (!o || !Array.isArray(o.tasks) || !o.settings) return null
  const tasks = o.tasks.filter(isTask).map((t) => ({
    id: t.id,
    title: t.title,
    notes: typeof t.notes === "string" ? t.notes : "",
    day: t.day,
    done: !!t.done,
    doneAt: typeof t.doneAt === "number" ? t.doneAt : null,
    carriedFrom: typeof t.carriedFrom === "string" ? t.carriedFrom : null,
  }))
  const s = o.settings
  return {
    tasks,
    settings: {
      weekStart: s.weekStart === "sun" ? "sun" : "mon",
      columns: Number(s.columns) === 5 ? 5 : 7,
      later: s.later !== false,
    },
  }
}

export function loadBoard(): Board | null {
  try {
    const raw = window.localStorage.getItem(STORE_KEY)
    return raw ? parseBoard(JSON.parse(raw)) : null
  } catch {
    return null
  }
}

export function saveBoard(b: Board): void {
  try {
    window.localStorage.setItem(STORE_KEY, JSON.stringify({ ...b, tasks: b.tasks.filter((t) => !t.demo) }))
  } catch {
    /* A full or blocked storage keeps the board working for this visit. */
  }
}

/** Undone cards dated before the anchor day; these slide into today on open. */
export function carryCandidates(b: Board, view: WeekView): string[] {
  return b.tasks.filter((t) => !t.done && t.day !== LATER && t.day < view.anchor).map((t) => t.id)
}
