import { memo } from "react"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { MATRIX_BG, MATRIX_FG, type Pair } from "@/lib/tokens"

type Props = { pairs: Pair[]; mode: "light" | "dark" }

/** Every text color on every background, with its WCAG ratio; AA and AAA fade in as a pair passes. */
export const ContrastMatrix = memo(function ContrastMatrix({ pairs, mode }: Props) {
  const m = mode === "light" ? "l" : "d"
  return (
    <section className="offscreen-skip flex flex-col gap-3" aria-labelledby="matrix-title">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 id="matrix-title" className="section-label">
          Contrast
        </h2>
        <p className="text-xs text-balance text-muted-foreground">{mode === "light" ? "Light" : "Dark"} surfaces, text down, backgrounds across</p>
      </div>
      <Table className="matrix">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="matrix-corner">
              <span className="sr-only">Text color</span>
            </TableHead>
            {MATRIX_BG.map((bg) => (
              <TableHead key={bg.role} className="matrix-head">
                {bg.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {MATRIX_FG.map((fg, row) => (
            <TableRow key={fg.role} className="hover:bg-transparent">
              <TableHead scope="row" className="matrix-rowhead">
                {fg.label}
              </TableHead>
              {MATRIX_BG.map((bg, col) => {
                const pair = pairs[row * MATRIX_BG.length + col]
                return (
                  <TableCell key={bg.role} className="matrix-cell">
                    <div className="pair-frame">
                      <div className="pair" data-live="surface font" data-bg={`${m}-${bg.role}`} data-fg={`${m}-${fg.role}`} aria-hidden="true">
                        Aa
                      </div>
                      <Badge className="pair-badge" aria-hidden={!pair.level} data-on={pair.level ? "" : undefined} variant={pair.level === "AAA" ? "default" : "secondary"}>
                        {pair.level || "AA"}
                      </Badge>
                    </div>
                    <span className="pair-ratio font-mono tabular-nums" aria-label={`${fg.label} on ${bg.label}: ${pair.ratio.toFixed(2)} to 1`}>
                      {pair.ratio >= 10 ? pair.ratio.toFixed(1) : pair.ratio.toFixed(2)}
                    </span>
                  </TableCell>
                )
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  )
})
