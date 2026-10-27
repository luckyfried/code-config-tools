import { useEffect, useRef, useState } from "react"
import { DownloadIcon, PrinterIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { TopBar } from "@/components/TopBar"
import { config } from "@/lib/config"
import { sportName } from "@/lib/format"
import { downloadPoster, drawPoster, posterFonts, POSTER_RATIO, type PosterOptions } from "@/lib/poster"
import { href, type Route } from "@/lib/route"
import { isDark, onSchemeChange } from "@/lib/tokens"
import type { Track } from "@/lib/types"

interface PosterScreenProps {
  track: Track
  route: Route
}

function defaultSubtitle(track: Track) {
  const who = config.athlete ? ` by ${config.athlete}` : ""
  return `${sportName(track.sport)}${who}`
}

export function PosterScreen({ track, route }: PosterScreenProps) {
  const [title, setTitle] = useState(track.name)
  const [subtitle, setSubtitle] = useState(defaultSubtitle(track))
  const [paper, setPaper] = useState<"light" | "dark">(isDark() ? "dark" : "light")
  const [profile, setProfile] = useState(Boolean(track.ele))
  const [saving, setSaving] = useState(false)
  const frame = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const options: PosterOptions = { title: title.trim() || track.name, subtitle, paper, profile, units: config.units }

  const [shownFor, setShownFor] = useState(track.id)
  if (shownFor !== track.id) {
    setShownFor(track.id)
    setTitle(track.name)
    setSubtitle(defaultSubtitle(track))
    setProfile(Boolean(track.ele))
  }

  useEffect(() => {
    const el = canvas.current
    const box = frame.current
    if (!el || !box) return
    let cancelled = false
    const drawn: PosterOptions = { title: title.trim() || track.name, subtitle, paper, profile, units: config.units }
    const render = () => {
      const rect = box.getBoundingClientRect()
      const ratio = Math.min(2, window.devicePixelRatio || 1)
      el.width = Math.round(rect.width * ratio)
      el.height = Math.round((rect.width / POSTER_RATIO) * ratio)
      drawPoster(el, track, drawn)
    }
    void posterFonts().then(() => {
      if (!cancelled) render()
    })
    render()
    const resize = new ResizeObserver(render)
    resize.observe(box)
    const unscheme = onSchemeChange(render)
    return () => {
      cancelled = true
      resize.disconnect()
      unscheme()
    }
  }, [track, title, subtitle, paper, profile])

  return (
    <div className="flex min-h-dvh flex-col gap-6 px-4 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(2rem,env(safe-area-inset-bottom))] sm:px-8 lg:h-dvh lg:min-h-0">
      <TopBar route={route} activityId={track.id} athlete={config.athlete} className="no-print" />
      <div className="flex min-h-0 flex-1 flex-col gap-8 lg:flex-row">
        <section className="poster-table flex min-h-0 flex-1 items-center justify-center rounded-2xl p-4 sm:p-10" aria-label="Poster preview">
          <div ref={frame} className="poster-frame w-full max-w-[min(100%,calc((100dvh-9rem)*0.6667))] lg:max-w-[min(100%,calc((100dvh-10rem)*0.6667))]">
            <canvas ref={canvas} className="print-poster block h-auto w-full rounded-[2px] shadow-[0_1px_2px_rgb(0_0_0/0.12),0_12px_40px_-8px_rgb(0_0_0/0.35)]" role="img" aria-label={`Poster of ${track.name}`} />
          </div>
        </section>
        <aside className="no-print flex w-full shrink-0 flex-col gap-6 lg:w-[360px] 2xl:w-[400px]">
          <div>
            <h1 className="font-display text-5xl leading-none font-bold">Poster</h1>
            <p className="mt-2 text-muted-foreground">The route as one line on paper, saved at 2400 by 3600 pixels, an 8 by 12 inch print at 300 dpi.</p>
          </div>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="poster-title">Title</FieldLabel>
              <Input id="poster-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={48} className="h-11 text-base" />
            </Field>
            <Field>
              <FieldLabel htmlFor="poster-subtitle">Line under the title</FieldLabel>
              <Input id="poster-subtitle" value={subtitle} onChange={(event) => setSubtitle(event.target.value)} maxLength={64} className="h-11 text-base" />
            </Field>
            <Field>
              <FieldLabel id="poster-paper">Paper</FieldLabel>
              <ToggleGroup
                aria-labelledby="poster-paper"
                value={[paper]}
                onValueChange={(value: string[]) => {
                  if (value[0] === "light" || value[0] === "dark") setPaper(value[0])
                }}
                variant="outline"
              >
                <ToggleGroupItem value="light" className="h-10 px-4">
                  Light
                </ToggleGroupItem>
                <ToggleGroupItem value="dark" className="h-10 px-4">
                  Dark
                </ToggleGroupItem>
              </ToggleGroup>
            </Field>
            <Field orientation="horizontal">
              <Switch id="poster-profile" checked={profile} onCheckedChange={(checked: boolean) => setProfile(checked)} disabled={!track.ele} />
              <FieldLabel htmlFor="poster-profile">Elevation profile under the route</FieldLabel>
            </Field>
          </FieldGroup>
          <div className="flex flex-wrap gap-3">
            <Button
              size="lg"
              className="h-11 flex-1 px-5"
              disabled={saving}
              onClick={async () => {
                setSaving(true)
                await downloadPoster(track, options)
                setSaving(false)
              }}
            >
              <DownloadIcon data-icon="inline-start" />
              {saving ? "Saving the poster" : "Download PNG"}
            </Button>
            <Button size="lg" variant="outline" className="h-11 px-5" onClick={() => window.print()}>
              <PrinterIcon data-icon="inline-start" />
              Print
            </Button>
          </div>
          <FieldDescription>
            A different activity? <a href={href({ screen: "activities" })}>Pick it from your activities</a>, then open Poster again.
          </FieldDescription>
        </aside>
      </div>
    </div>
  )
}
