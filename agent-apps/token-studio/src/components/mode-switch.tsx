import { memo } from "react"
import { MoonIcon, SunIcon } from "lucide-react"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

type Props = { mode: "light" | "dark"; onChange: (mode: "light" | "dark") => void; className?: string }

/** Light or dark surfaces for the preview; turning it flips the sample card. */
export const ModeSwitch = memo(function ModeSwitch({ mode, onChange, className }: Props) {
  return (
    <ToggleGroup
      aria-label="Preview surfaces"
      variant="outline"
      className={className}
      spacing={0}
      value={[mode]}
      onValueChange={(value) => {
        const next = value[0]
        if (next === "light" || next === "dark") onChange(next)
      }}
    >
      <ToggleGroupItem value="light" className="mode-item" aria-label="Light surfaces">
        <SunIcon data-icon="inline-start" />
        <span className="mode-label">Light</span>
      </ToggleGroupItem>
      <ToggleGroupItem value="dark" className="mode-item" aria-label="Dark surfaces">
        <MoonIcon data-icon="inline-start" />
        <span className="mode-label">Dark</span>
      </ToggleGroupItem>
    </ToggleGroup>
  )
})
