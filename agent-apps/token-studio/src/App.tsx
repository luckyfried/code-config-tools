import { useCallback, useEffect, useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ColorPanel } from "@/components/color-panel"
import { ExportGlyph } from "@/components/export-glyph"
import { ExportPanel } from "@/components/export-panel"
import { Logo } from "@/components/logo"
import { ModeSwitch } from "@/components/mode-switch"
import { PreviewStage } from "@/components/preview-stage"
import { Ramp } from "@/components/ramp"
import { SpacePanel } from "@/components/space-panel"
import { TypePanel } from "@/components/type-panel"
import { TypeSpecimen } from "@/components/type-specimen"
import { useChromeScheme } from "@/hooks/use-chrome-scheme"
import { useIntro } from "@/hooks/use-intro"
import { useLiveTokens } from "@/hooks/use-live-tokens"
import { useMedia } from "@/hooks/use-media"
import { download } from "@/lib/download"
import { loadSaved, readSeed, save } from "@/lib/settings"
import { buildSystem, toCss, type Settings } from "@/lib/tokens"

type Mode = "light" | "dark"
const TABS = [
  { value: "color", label: "Color", n: "01" },
  { value: "type", label: "Type", n: "02" },
  { value: "space", label: "Space", n: "03" },
  { value: "export", label: "Export", n: "04" },
]

export default function App() {
  useChromeScheme()
  const [seed] = useState(readSeed)
  const [saved] = useState(() => loadSaved(seed.settings))
  const [settings, setSettings] = useState<Settings>(saved ?? seed.settings)
  const sys = useMemo(() => buildSystem(settings), [settings])
  useLiveTokens(sys)

  const wide = useMedia("(min-width: 768px)")
  const [mode, setMode] = useState<Mode>(() => (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"))
  const [tab, setTab] = useState("color")
  const [exportRun, setExportRun] = useState(0)
  const [status, setStatus] = useState(() =>
    seed.fromConfig
      ? `Started from ${seed.hex ?? `hue ${Math.round(seed.settings.brand.hue)}`}. Your changes stay in this browser.`
      : "Sample system. Your changes stay in this browser.",
  )

  // A steady handler keeps the tab list from re-measuring its tabs on every change of a value.
  const pickTab = useCallback((v: unknown) => setTab(String(v)), [])
  const flip = useCallback(() => setMode((m) => (m === "light" ? "dark" : "light")), [])
  const touring = useIntro({ enabled: !saved, seed: seed.settings, setSettings, setTab, flip })

  useEffect(() => {
    if (touring) return
    const timer = setTimeout(() => save(seed.settings, settings), 250)
    return () => clearTimeout(timer)
  }, [settings, touring, seed])

  const exportCss = () => {
    download("tokens.css", toCss(sys), "text/css")
    setExportRun((n) => n + 1)
    setStatus("Saved tokens.css. Link it before your own styles and use the variables by name.")
  }

  const header = (
    <header className="studio-header">
      <Logo />
      <h1 className="wordmark">
        Token <span>Studio</span>
      </h1>
      {wide ? (
        <span className="brand-chip" data-live="brand">
          <span className="brand-chip-dot" aria-hidden="true" />
          <span className="font-mono tabular-nums">{sys.brand[5].hex}</span>
        </span>
      ) : null}
      <div className="ml-auto flex items-center gap-2">
        {wide ? null : <ModeSwitch mode={mode} onChange={setMode} className="mode-compact" />}
        <Button size="lg" className="studio-action" onClick={exportCss} aria-label="Download tokens.css">
          <ExportGlyph run={exportRun} />
          <span className="max-[420px]:sr-only">Export</span>
        </Button>
      </div>
    </header>
  )

  const panels = (
    <>
      <TabsContent value="color" className="panel">
        <ColorPanel sys={sys} mode={mode} showRamps={!wide} onChange={setSettings} />
      </TabsContent>
      <TabsContent value="type" className="panel">
        <TypePanel sys={sys} showSpecimen={!wide} mode={mode} onChange={setSettings} />
      </TabsContent>
      <TabsContent value="space" className="panel">
        <SpacePanel sys={sys} onChange={setSettings} />
      </TabsContent>
      <TabsContent value="export" className="panel">
        <ExportPanel
          sys={sys}
          exportRun={exportRun}
          onExportCss={exportCss}
          onImport={setSettings}
          status={status}
          setStatus={setStatus}
        />
      </TabsContent>
    </>
  )

  const tabList = useMemo(() => (
    <TabsList variant="line" className="tab-list">
      {TABS.map((t) => (
        <TabsTrigger key={t.value} value={t.value} className="tab-trigger">
          <span className="tab-num" aria-hidden="true">
            {t.n}
          </span>
          {t.label}
        </TabsTrigger>
      ))}
    </TabsList>
  ), [])

  if (!wide) {
    return (
      <div className="studio" data-layout="narrow">
        {header}
        <section className={`stage gen ${mode}`} aria-label="Preview" data-live="">
          <PreviewStage mode={mode} compact />
        </section>
        <Tabs value={tab} onValueChange={pickTab} className="editor-tabs">
          {tabList}
          <div className="editor-scroll">{panels}</div>
        </Tabs>
      </div>
    )
  }

  return (
    <div className="studio" data-layout="wide">
      <aside className="editor" aria-label="Controls">
        {header}
        <Tabs value={tab} onValueChange={pickTab} className="editor-tabs">
          {tabList}
          <div className="editor-scroll">{panels}</div>
        </Tabs>
      </aside>
      <main className={`canvas gen ${mode}`} aria-label="Preview" data-live="">
        <div className="canvas-bar">
          <p className="canvas-title">Preview</p>
          <p className="canvas-note">
            {mode === "light" ? "Light surfaces" : "Dark surfaces"} from hue <span className="tabular-nums">{Math.round(settings.brand.hue)}°</span>
          </p>
          <ModeSwitch mode={mode} onChange={setMode} className="ml-auto" />
        </div>
        <div className="canvas-ramps">
          <Ramp title="Brand" steps={sys.brand} size="lg" turn={settings.brand.hue} />
          <Ramp title="Neutral" steps={sys.neutral} />
        </div>
        <div className="canvas-grid">
          <PreviewStage mode={mode} />
          <TypeSpecimen />
        </div>
      </main>
    </div>
  )
}
