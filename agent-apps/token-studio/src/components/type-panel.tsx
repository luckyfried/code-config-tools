import { useCallback } from "react"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useHeldOffscreen } from "@/hooks/use-held-offscreen"
import { LIMITS, type Settings, type System } from "@/lib/tokens"
import { LabeledSlider } from "./labeled-slider"
import { Staircase } from "./staircase"
import { TypeSpecimen } from "./type-specimen"

const RATIOS = [
  { value: "1.067", label: "Minor second, 1.067" },
  { value: "1.125", label: "Major second, 1.125" },
  { value: "1.2", label: "Minor third, 1.2" },
  { value: "1.25", label: "Major third, 1.25" },
  { value: "1.333", label: "Perfect fourth, 1.333" },
  { value: "1.414", label: "Augmented fourth, 1.414" },
  { value: "1.5", label: "Perfect fifth, 1.5" },
  { value: "1.618", label: "Golden ratio, 1.618" },
]
const CUSTOM = { value: "custom", label: "Your own ratio" }

type Props = {
  sys: System
  showSpecimen: boolean
  mode: "light" | "dark"
  onChange: (update: (s: Settings) => Settings) => void
}

export function TypePanel({ sys, showSpecimen, mode, onChange }: Props) {
  const s = sys.settings
  const setRatio = useCallback((typeScaleRatio: number) => onChange((p) => ({ ...p, typeScaleRatio })), [onChange])
  const setBase = useCallback((baseSize: number) => onChange((p) => ({ ...p, baseSize })), [onChange])
  const [lowerRef, type] = useHeldOffscreen(sys.type)
  const named = RATIOS.find((r) => Math.abs(Number(r.value) - s.typeScaleRatio) < 0.0005)
  const items = named ? RATIOS : [...RATIOS, CUSTOM]
  return (
    <div className="flex flex-col gap-7">
      <FieldGroup className="gap-5">
        <Field>
          <FieldLabel>Scale</FieldLabel>
          <Select
            items={items}
            value={named?.value ?? CUSTOM.value}
            onValueChange={(value) => {
              if (value && value !== CUSTOM.value) onChange((p) => ({ ...p, typeScaleRatio: Number(value) }))
            }}
          >
            <SelectTrigger className="studio-select w-full" aria-label="Scale">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {items.map((r) => (
                  <SelectItem key={r.value} value={r.value} disabled={r.value === CUSTOM.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
        <LabeledSlider
          label="Ratio"
          value={s.typeScaleRatio}
          min={LIMITS.typeScaleRatio[0]}
          max={LIMITS.typeScaleRatio[1]}
          step={0.001}
          display={`× ${s.typeScaleRatio.toFixed(3)}`}
          onChange={setRatio}
        />
        <LabeledSlider
          label="Base size"
          value={s.baseSize}
          min={LIMITS.baseSize[0]}
          max={LIMITS.baseSize[1]}
          step={1}
          display={`${s.baseSize} px`}
          onChange={setBase}
        />
        <div className="grid grid-cols-2 gap-3">
          <Field>
            <FieldLabel htmlFor="font-sans">Text font</FieldLabel>
            <Input
              id="font-sans"
              className="studio-input"
              value={s.fonts.sans}
              spellCheck={false}
              onChange={(e) => {
                const sans = e.target.value
                onChange((p) => ({ ...p, fonts: { ...p.fonts, sans } }))
              }}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="font-mono">Code font</FieldLabel>
            <Input
              id="font-mono"
              className="studio-input"
              value={s.fonts.mono}
              spellCheck={false}
              onChange={(e) => {
                const mono = e.target.value
                onChange((p) => ({ ...p, fonts: { ...p.fonts, mono } }))
              }}
            />
          </Field>
        </div>
      </FieldGroup>
      <div ref={lowerRef} className="flex flex-col gap-7">
        <Staircase type={type} />
        {showSpecimen ? (
          <div className={`specimen-inset offscreen-skip gen ${mode}`} data-live="">
            <TypeSpecimen />
          </div>
        ) : null}
      </div>
    </div>
  )
}
