export const MUSCLES = [
  "chest",
  "shoulders",
  "biceps",
  "triceps",
  "forearms",
  "traps",
  "lats",
  "abs",
  "obliques",
  "lower-back",
  "glutes",
  "quads",
  "hamstrings",
  "calves",
] as const
export type Muscle = (typeof MUSCLES)[number]

export const MUSCLE_LABEL: Record<Muscle, string> = {
  chest: "Chest",
  shoulders: "Shoulders",
  biceps: "Biceps",
  triceps: "Triceps",
  forearms: "Forearms",
  traps: "Traps",
  lats: "Lats",
  abs: "Abs",
  obliques: "Obliques",
  "lower-back": "Lower back",
  glutes: "Glutes",
  quads: "Quads",
  hamstrings: "Hamstrings",
  calves: "Calves",
}

export type Units = "kg" | "lb"
export type Equipment = "barbell" | "dumbbell" | "machine" | "bodyweight"

export type Exercise = {
  id: string
  label: string
  muscles: Muscle[]
  equipment: Equipment
}

export type AppConfig = {
  name: string
  units: Units
  exercises: Exercise[]
  restSeconds: number
  plates: number[]
  barWeight: number
  theme: string
}

type RawExercise = { id?: unknown; label?: unknown; muscles?: unknown; equipment?: unknown }

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<Omit<AppConfig, "exercises">> & { exercises?: RawExercise[] }
  }
}

export const DEFAULT_PLATES: Record<Units, number[]> = {
  kg: [25, 20, 15, 10, 5, 2.5, 1.25],
  lb: [45, 35, 25, 10, 5, 2.5],
}
export const DEFAULT_BAR: Record<Units, number> = { kg: 20, lb: 45 }

const isMuscle = (m: unknown): m is Muscle => typeof m === "string" && (MUSCLES as readonly string[]).includes(m)
const EQUIPMENT: Equipment[] = ["barbell", "dumbbell", "machine", "bodyweight"]

export function readConfig(): AppConfig {
  const raw = window.__APP_CONFIG__ ?? {}
  const units: Units = raw.units === "lb" ? "lb" : "kg"
  const exercises: Exercise[] = (Array.isArray(raw.exercises) ? raw.exercises : [])
    .filter((e): e is RawExercise => typeof e === "object" && e !== null)
    .filter((e) => typeof e.id === "string" && typeof e.label === "string")
    .map((e) => ({
      id: e.id as string,
      label: e.label as string,
      muscles: Array.isArray(e.muscles) ? e.muscles.filter(isMuscle) : [],
      equipment: EQUIPMENT.includes(e.equipment as Equipment) ? (e.equipment as Equipment) : "barbell",
    }))
  const plates = Array.isArray(raw.plates)
    ? raw.plates.filter((p): p is number => typeof p === "number" && p > 0).sort((a, b) => b - a)
    : []
  return {
    name: typeof raw.name === "string" ? raw.name.trim() : "",
    units,
    exercises: exercises.length ? exercises : FALLBACK_EXERCISES,
    restSeconds: typeof raw.restSeconds === "number" && raw.restSeconds > 0 ? Math.round(raw.restSeconds) : 120,
    plates: plates.length ? plates : DEFAULT_PLATES[units],
    barWeight: typeof raw.barWeight === "number" && raw.barWeight >= 0 ? raw.barWeight : DEFAULT_BAR[units],
    theme: typeof raw.theme === "string" ? raw.theme : "auto",
  }
}

const FALLBACK_EXERCISES: Exercise[] = [
  { id: "back-squat", label: "Back squat", muscles: ["quads", "glutes", "lower-back"], equipment: "barbell" },
  { id: "bench-press", label: "Bench press", muscles: ["chest", "triceps", "shoulders"], equipment: "barbell" },
  { id: "deadlift", label: "Deadlift", muscles: ["hamstrings", "glutes", "lower-back", "traps"], equipment: "barbell" },
  { id: "overhead-press", label: "Overhead press", muscles: ["shoulders", "triceps"], equipment: "barbell" },
  { id: "barbell-row", label: "Barbell row", muscles: ["lats", "traps", "biceps"], equipment: "barbell" },
]
