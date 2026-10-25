import { cn } from "cn"

import { Badge } from "@/components/ui/badge"
import { formatDay } from "@/lib/format"
import type { Delta } from "@/lib/metrics"

export function DeltaChip({ delta, className }: { delta: Delta; className?: string }) {
  const variant = delta.good === null ? "neutral" : delta.good ? "positive" : "negative"
  return (
    <Badge
      variant={variant}
      className={cn("figure h-6 px-2 text-xs font-semibold", className)}
      aria-label={`${delta.spoken} since ${formatDay(delta.since)}`}
    >
      {delta.text}
    </Badge>
  )
}
