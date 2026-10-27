import type { ActivityIndex, Track } from "./types"

const tracks = new Map<string, Promise<Track>>()

export async function loadIndex(): Promise<ActivityIndex> {
  const answer = await fetch("./data/index.json")
  if (!answer.ok) throw new Error("no activities")
  return answer.json()
}

export function loadTrack(id: string): Promise<Track> {
  let pending = tracks.get(id)
  if (!pending) {
    pending = fetch(`./data/${encodeURIComponent(id)}.json`).then((answer) => {
      if (!answer.ok) throw new Error(`no activity ${id}`)
      return answer.json() as Promise<Track>
    })
    tracks.set(id, pending)
  }
  return pending
}
