import { useMemo, useRef, useState } from "react"
import { CopyIcon, FileJsonIcon, UploadIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toSettings } from "@/lib/settings"
import { toCss, toJson, type Settings, type System } from "@/lib/tokens"
import { download } from "@/lib/download"
import { ExportGlyph } from "./export-glyph"

type Props = {
  sys: System
  exportRun: number
  onExportCss: () => void
  onImport: (settings: Settings) => void
  status: string
  setStatus: (status: string) => void
}

export function ExportPanel({ sys, exportRun, onExportCss, onImport, status, setStatus }: Props) {
  const css = useMemo(() => toCss(sys), [sys])
  const fileInput = useRef<HTMLInputElement>(null)
  const [copied, setCopied] = useState(false)
  const lines = css.split("\n")

  const importFile = async (file: File) => {
    try {
      const settings = toSettings(JSON.parse(await file.text()))
      if (!settings) throw new Error("not an export")
      onImport(settings)
      setStatus(`Picked up where ${file.name} left off.`)
    } catch {
      setStatus(`${file.name} isn't a Token Studio JSON export, so nothing changed.`)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-2">
        <Button size="lg" className="studio-action" onClick={onExportCss}>
          <ExportGlyph run={exportRun} />
          Download tokens.css
        </Button>
        <Button
          size="lg"
          variant="outline"
          className="studio-action"
          onClick={() => {
            download("token-studio.json", toJson(sys), "application/json")
            setStatus("Saved token-studio.json. Import it here to pick up again.")
          }}
        >
          <FileJsonIcon data-icon="inline-start" />
          Download JSON
        </Button>
        <Button size="lg" variant="outline" className="studio-action" onClick={() => fileInput.current?.click()}>
          <UploadIcon data-icon="inline-start" />
          Import JSON
        </Button>
        <input
          ref={fileInput}
          type="file"
          accept=".json,application/json"
          className="sr-only"
          tabIndex={-1}
          aria-label="Import a Token Studio JSON export"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void importFile(file)
            e.target.value = ""
          }}
        />
      </div>
      <p className="text-sm text-muted-foreground" role="status" aria-live="polite">
        {status}
      </p>
      <div className="code-well">
        <div className="code-bar">
          <span className="font-mono text-xs">tokens.css</span>
          <span className="text-xs text-muted-foreground tabular-nums">{lines.length} lines</span>
          <Button
            size="sm"
            variant="ghost"
            className="ml-auto"
            onClick={() => {
              void navigator.clipboard?.writeText(css).then(() => {
                setCopied(true)
                setTimeout(() => setCopied(false), 1600)
              })
            }}
          >
            <CopyIcon data-icon="inline-start" />
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
        <pre className="code-body font-mono">
          <code>
            {lines.map((line, i) => (
              <span key={i} className="code-line" data-kind={line.trimStart().startsWith("/*") ? "note" : line.includes("--") ? "token" : undefined}>
                {line || " "}
                {"\n"}
              </span>
            ))}
          </code>
        </pre>
      </div>
    </div>
  )
}
