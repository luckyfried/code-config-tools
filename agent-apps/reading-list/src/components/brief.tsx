import type { Deep, Topic } from "@/types"

/** The longer brief the agent wrote: its paragraphs under a drop cap, then the other coverage worth reading. */
export function Brief({ deep, topic }: { deep: Deep; topic: Topic }) {
  return (
    <>
      <div className="brief">
        {deep.paragraphs.map((text, i) => (
          <p key={i}>{text}</p>
        ))}
      </div>
      {deep.coverage.length > 0 && (
        <div className="coverage" aria-label={`Other coverage on ${topic.name}`}>
          {deep.coverage.map((c) => (
            <a key={c.link} className="cover" href={c.link} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
              <span className="cover-source">{c.source}</span>
              <span className="cover-headline">{c.headline}</span>
            </a>
          ))}
        </div>
      )}
    </>
  )
}
