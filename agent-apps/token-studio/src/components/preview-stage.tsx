import { memo } from "react"
import { Poster } from "./poster"

type Props = { mode: "light" | "dark"; compact?: boolean }

/** The poster on two faces, light and dark from the same hue; the mode switch turns it over. */
export const PreviewStage = memo(function PreviewStage({ mode, compact = false }: Props) {
  return (
    <div className="flip-stage" data-mode={mode}>
      <div className="flip-inner">
        <div className="flip-face gen light" inert={mode !== "light"} aria-hidden={mode !== "light"}>
          <Poster face="light" compact={compact} />
        </div>
        <div className="flip-face flip-back gen dark" inert={mode !== "dark"} aria-hidden={mode !== "dark"}>
          <Poster face="dark" compact={compact} />
        </div>
      </div>
    </div>
  )
})
