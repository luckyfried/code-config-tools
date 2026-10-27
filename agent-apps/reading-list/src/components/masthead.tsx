import type { CSSProperties, ReactNode } from "react"
import type { Topic } from "@/types"
import { today } from "@/lib/words"

/** The paper's name, its date, the sections, and the later stack. */
export function Masthead({
  name,
  stories,
  topics,
  counts,
  section,
  onSection,
  stack,
}: {
  name: string
  stories: number
  topics: Topic[]
  counts: Map<string, number>
  section: string
  onSection: (id: string) => void
  stack: ReactNode
}) {
  const total = [...counts.values()].reduce((a, b) => a + b, 0)
  return (
    <header>
      <div className="masthead">
        <p className="ear">{today()}</p>
        <h1 className="masthead-title">{name ? `${name}’s Reading List` : "The Reading List"}</h1>
        <p className="ear ear-right">
          {stories} {stories === 1 ? "story" : "stories"} · {topics.length} {topics.length === 1 ? "section" : "sections"}
        </p>
      </div>
      <div className="rules" />
      <div className="bar">
        <nav className="sections" aria-label="Sections">
          <button type="button" className="section" aria-pressed={section === "all"} onClick={() => onSection("all")}>
            Front page <span className="section-count">{total}</span>
          </button>
          {topics.map((t) => (
            <button
              key={t.id}
              type="button"
              className="section"
              aria-pressed={section === t.id}
              style={{ "--topic": t.color } as CSSProperties}
              onClick={() => onSection(t.id)}
            >
              <span className="section-dot" aria-hidden="true" />
              {t.name} <span className="section-count">{counts.get(t.id) ?? 0}</span>
            </button>
          ))}
        </nav>
        {stack}
      </div>
    </header>
  )
}
