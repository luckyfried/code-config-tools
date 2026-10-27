import { useEffect, useRef, useState } from "react"
import { APPLY_WORD, type ApplyStage } from "@/lib/board"

// Where an apply is: it breathes while it waits for the agent, holds while the agent has it, and a chip that turns
// to applied while it is on screen lands with a drawn check.
export function StateChip({ stage }: { stage: ApplyStage }) {
  const before = useRef(stage)
  const [landed, setLanded] = useState(false)
  useEffect(() => {
    if (before.current !== "applied" && stage === "applied") setLanded(true)
    before.current = stage
  }, [stage])
  return (
    <span className="chip" data-state={stage} data-landed={landed || undefined}>
      {stage === "applied" ? (
        <svg className="check" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ) : (
        <span className="dot" aria-hidden="true" />
      )}
      <span>{APPLY_WORD[stage]}</span>
    </span>
  )
}
