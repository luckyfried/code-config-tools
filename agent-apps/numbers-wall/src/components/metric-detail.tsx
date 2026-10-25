import { useMemo } from "react"
import { Area, AreaChart, CartesianGrid, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts"

import { ChartContainer, type ChartConfig } from "@/components/ui/chart"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { DeltaChip } from "@/components/delta-chip"
import type { Copy, Metric, Point } from "@/lib/config"
import { decimalsOf, formatAxis, formatDay, formatLongDay, formatValue } from "@/lib/format"
import { deltaOf, domainOf, goalMet, latest } from "@/lib/metrics"

const config = { value: { label: "Reading", color: "var(--spark)" } } satisfies ChartConfig

type TooltipProps = { active?: boolean; payload?: { payload: Point }[]; metric: Metric; decimals: number }

function PointTooltip({ active, payload, metric, decimals }: TooltipProps) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null
  return (
    <div className="grid gap-0.5 rounded-lg border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-lg">
      <span className="text-muted-foreground">{formatLongDay(point.date)}</span>
      <span className="figure text-label font-semibold">{formatValue(metric, point.value, decimals)}</span>
    </div>
  )
}

/** The Tile screen: the whole history as a line with the goal, and every raw reading, newest first. */
export function MetricDetail({
  metric,
  group,
  copy,
  onClose,
}: {
  metric: Metric | null
  group: string
  copy: Copy
  onClose: () => void
}) {
  return (
    <Dialog open={metric !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] gap-6 overflow-y-auto p-6 sm:max-w-2xl">
        {metric && <DetailBody metric={metric} group={group} copy={copy} />}
      </DialogContent>
    </Dialog>
  )
}

function DetailBody({ metric, group, copy }: { metric: Metric; group: string; copy: Copy }) {
  const decimals = useMemo(() => decimalsOf(metric.history), [metric.history])
  const point = latest(metric)
  const delta = deltaOf(metric)
  const met = goalMet(metric)
  const values = metric.history.map((p) => p.value)
  const domain = domainOf(values, metric.goal)
  const first = metric.history[0]
  const rows = useMemo(
    () =>
      metric.history
        .map((p, i) => ({ ...p, change: i > 0 ? p.value - metric.history[i - 1].value : null }))
        .toReversed(),
    [metric.history],
  )
  const format = (value: number) => formatValue(metric, value, decimals)

  return (
    <>
      <DialogHeader className="gap-1 pr-8">
        <DialogTitle className="text-title font-semibold">{metric.label}</DialogTitle>
        <DialogDescription>
          {group} · {metric.history.length} {copy.readings}
          {first ? ` · ${formatLongDay(first.date)} – ${formatLongDay(metric.history.at(-1)!.date)}` : ""}
        </DialogDescription>
      </DialogHeader>

      <div className="flex flex-wrap items-center gap-3">
        <span className="figure text-figure font-semibold">{point ? format(point.value) : copy.noReadings}</span>
        {delta && <DeltaChip delta={delta} />}
        {delta && (
          <span className="text-label text-muted-foreground">
            {copy.since} {formatDay(delta.since)}
          </span>
        )}
      </div>

      {metric.history.length > 1 && (
        <ChartContainer config={config} className="aspect-auto h-60 w-full" initialDimension={{ width: 600, height: 240 }}>
          <AreaChart data={metric.history} margin={{ top: 12, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="detail-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-value)" stopOpacity={0.3} />
                <stop offset="100%" stopColor="var(--color-value)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey="date" tickFormatter={formatDay} tickLine={false} axisLine={false} minTickGap={40} tickMargin={8} />
            <YAxis
              domain={domain}
              tickFormatter={(v: number) => formatAxis(metric, v)}
              tickLine={false}
              axisLine={false}
              width={56}
              tickCount={5}
            />
            <Tooltip cursor={{ stroke: "var(--border)" }} content={<PointTooltip metric={metric} decimals={decimals} />} />
            {metric.goal != null && (
              <ReferenceLine
                y={metric.goal}
                stroke={met ? "var(--positive)" : "var(--goal)"}
                strokeDasharray="4 4"
                label={{
                  value: `${copy.goal} ${format(metric.goal)}`,
                  position: "insideTopLeft",
                  fill: met ? "var(--positive)" : "var(--muted-foreground)",
                  fontSize: 12,
                }}
              />
            )}
            <Area
              dataKey="value"
              type="monotone"
              stroke="var(--color-value)"
              strokeWidth={2}
              fill="url(#detail-fill)"
              baseValue={domain[0]}
              animationDuration={600}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
          </AreaChart>
        </ChartContainer>
      )}

      <div className="grid gap-2">
        <h3 className="text-label font-medium">{copy.everyReading}</h3>
        <ScrollArea className="h-56 rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">{copy.date}</TableHead>
                <TableHead className="text-right">{copy.reading}</TableHead>
                <TableHead className="pr-4 text-right">{copy.change}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="figure">
              {rows.map((row) => (
                <TableRow key={row.date}>
                  <TableCell className="pl-4 text-muted-foreground">{formatLongDay(row.date)}</TableCell>
                  <TableCell className="text-right">{format(row.value)}</TableCell>
                  <TableCell className="pr-4 text-right text-muted-foreground">
                    {row.change === null ? copy.first : changeText(metric, row.change, decimals)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      </div>
    </>
  )
}

function changeText(metric: Metric, change: number, decimals: number): string {
  const rounded = Number(change.toFixed(10))
  if (rounded === 0) return "0"
  const sign = rounded > 0 ? "+" : "−"
  if (metric.format === "percent") return `${sign}${Math.abs(rounded).toFixed(Math.max(1, decimals))} pt`
  return `${sign}${formatValue(metric, Math.abs(rounded), decimals)}`
}
