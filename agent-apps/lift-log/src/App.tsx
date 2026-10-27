import { useEffect, useState } from "react"
import { useMedia } from "@/hooks/useMedia"
import { LogProvider, useLog } from "@/lib/log-context"
import { DesktopLayout } from "@/components/DesktopLayout"
import { PhoneLayout, type PhoneTab } from "@/components/PhoneLayout"
import { RestBar } from "@/components/Rest"
import { PrScreen } from "@/components/PrScreen"

const ARROWS_OWNED = '[cmdk-root], [role="tablist"], [role="listbox"], [role="radiogroup"], [role="group"], [role="slider"]'

/** Enter logs a set; up and down step the weight, left and right the reps. */
function useKeys(enabled: boolean) {
  const log = useLog()
  useEffect(() => {
    if (!enabled) return
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return
      if (document.querySelector('[role="dialog"], [role="alertdialog"]')) return
      const t = e.target as HTMLElement
      const stepper = t.matches?.("input[data-stepper]")
      if (!stepper && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return
      if (e.key === "Enter") {
        if (stepper) {
          window.setTimeout(log.logSet, 0)
          return
        }
        if (t.closest("button, a, [role]")) return
        e.preventDefault()
        log.logSet()
        return
      }
      if (stepper || t.closest(ARROWS_OWNED)) return
      const step = { ArrowUp: () => log.stepWeight(1), ArrowDown: () => log.stepWeight(-1), ArrowRight: () => log.stepReps(1), ArrowLeft: () => log.stepReps(-1) }[e.key]
      if (step) {
        e.preventDefault()
        step()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [enabled, log.logSet, log.stepWeight, log.stepReps])
}

function Shell() {
  const wide = useMedia("(min-width: 1024px)")
  const [tab, setTab] = useState<PhoneTab>("session")
  useKeys(wide || tab === "session")
  return (
    <>
      <RestBar />
      <PrScreen />
      {wide ? <DesktopLayout /> : <PhoneLayout tab={tab} onTab={setTab} />}
    </>
  )
}

export default function App() {
  return (
    <LogProvider>
      <Shell />
    </LogProvider>
  )
}
