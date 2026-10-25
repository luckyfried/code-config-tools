import { LATER, type DayKey } from "./dates"
import { type Board, type Settings, type Task } from "./board"

export type Action =
  | { type: "add"; id: string; title: string; day: DayKey; before?: string | null; demo?: true }
  | { type: "carry"; id: string; to: DayKey }
  | { type: "toggle"; id: string }
  | { type: "edit"; id: string; title?: string; notes?: string; carriedFrom?: null }
  | { type: "move"; id: string; day: DayKey; before?: string | null; manual?: boolean }
  | { type: "shift"; id: string; by: -1 | 1 }
  | { type: "remove"; id: string }
  | { type: "settings"; settings: Partial<Settings> }
  | { type: "replace"; board: Board }

function patch(tasks: Task[], id: string, change: Partial<Task>): Task[] {
  return tasks.map((t) => (t.id === id ? { ...t, ...change } : t))
}

/** Takes a task out and puts it back before `before`, or after the last card of its day when there is none. */
function place(tasks: Task[], task: Task, before: string | null | undefined): Task[] {
  const rest = tasks.filter((t) => t.id !== task.id)
  let at = before ? rest.findIndex((t) => t.id === before) : -1
  if (at < 0) {
    let last = -1
    rest.forEach((t, i) => {
      if (t.day === task.day) last = i
    })
    at = last + 1 || rest.length
  }
  return [...rest.slice(0, at), task, ...rest.slice(at)]
}

export function reduce(board: Board, a: Action): Board {
  const { tasks } = board
  switch (a.type) {
    case "add": {
      const task: Task = { id: a.id, title: a.title, notes: "", day: a.day, done: false, doneAt: null, carriedFrom: null }
      if (a.demo) task.demo = true
      return { ...board, tasks: place(tasks, task, a.before ?? null) }
    }
    case "carry": {
      const t = tasks.find((x) => x.id === a.id)
      if (!t || t.done || t.day === LATER || t.day >= a.to) return board
      const first = tasks.find((x) => x.day === a.to && !x.done && !x.carriedFrom && x.id !== a.id)
      const moved: Task = { ...t, day: a.to, carriedFrom: t.carriedFrom ?? t.day }
      return { ...board, tasks: place(tasks, moved, first?.id ?? null) }
    }
    case "toggle": {
      const t = tasks.find((x) => x.id === a.id)
      if (!t) return board
      if (t.done) {
        return { ...board, tasks: place(tasks, { ...t, done: false, doneAt: null }, null) }
      }
      return { ...board, tasks: patch(tasks, a.id, { done: true, doneAt: Date.now(), carriedFrom: null }) }
    }
    case "edit": {
      const change: Partial<Task> = {}
      if (a.title !== undefined) change.title = a.title
      if (a.notes !== undefined) change.notes = a.notes
      if (a.carriedFrom === null) change.carriedFrom = null
      return { ...board, tasks: patch(tasks, a.id, change) }
    }
    case "move": {
      const t = tasks.find((x) => x.id === a.id)
      if (!t) return board
      const sameSpot = t.day === a.day && a.before === undefined
      if (sameSpot) return board
      const moved: Task = { ...t, day: a.day, carriedFrom: t.day !== a.day && a.manual !== false ? null : t.carriedFrom }
      return { ...board, tasks: place(tasks, moved, a.before) }
    }
    case "shift": {
      const t = tasks.find((x) => x.id === a.id)
      if (!t) return board
      const peers = tasks.filter((x) => x.day === t.day && !x.done)
      const i = peers.findIndex((x) => x.id === a.id)
      const j = i + a.by
      if (j < 0 || j >= peers.length) return board
      const before = a.by === -1 ? peers[j].id : (peers[j + 1]?.id ?? null)
      const rest = tasks.filter((x) => x.id !== a.id)
      if (before) {
        const at = rest.findIndex((x) => x.id === before)
        return { ...board, tasks: [...rest.slice(0, at), t, ...rest.slice(at)] }
      }
      const after = rest.findIndex((x) => x.id === peers[j].id)
      return { ...board, tasks: [...rest.slice(0, after + 1), t, ...rest.slice(after + 1)] }
    }
    case "remove":
      return { ...board, tasks: tasks.filter((t) => t.id !== a.id) }
    case "settings":
      return { ...board, settings: { ...board.settings, ...a.settings } }
    case "replace":
      return a.board
  }
}
