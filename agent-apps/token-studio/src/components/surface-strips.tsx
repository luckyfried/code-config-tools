import { memo } from "react"
import { SURFACE_ROLES, type System } from "@/lib/tokens"

const LABELS: Record<(typeof SURFACE_ROLES)[number], string> = {
  bg: "Page",
  surface: "Card",
  "surface-2": "Sunken",
  border: "Border",
  text: "Text",
  muted: "Muted",
  accent: "Brand",
  "on-accent": "On brand",
  "accent-soft": "Soft",
  "on-accent-soft": "On soft",
}

/** Both sets of surfaces, light and dark, made from the one hue. */
export const SurfaceStrips = memo(function SurfaceStrips({ light, dark }: { light: System["light"]; dark: System["dark"] }) {
  return (
    <section className="offscreen-skip flex flex-col gap-3" aria-labelledby="surfaces-title">
      <h2 id="surfaces-title" className="section-label">
        Surfaces
      </h2>
      {(["light", "dark"] as const).map((mode) => (
        <div key={mode} className="surface-row">
          <span className="text-xs text-muted-foreground">{mode === "light" ? "Light" : "Dark"}</span>
          <ol className="surface-strip" data-live="surface">
            {SURFACE_ROLES.map((role) => (
              <li
                key={role}
                className="surface-chip"
                data-bg={`${mode === "light" ? "l" : "d"}-${role}`}
                title={`${LABELS[role]} ${(mode === "light" ? light : dark)[role].hex}`}
              >
                <span className="sr-only">
                  {LABELS[role]} {(mode === "light" ? light : dark)[role].hex}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </section>
  )
})
