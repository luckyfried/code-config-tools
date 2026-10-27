import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"
import { Button } from "@/components/ui/button"

export function PeriodNav({ label, onPrev, onNext, onNow, nowLabel }: { label: string; onPrev: () => void; onNext: () => void; onNow: () => void; nowLabel: string }) {
  return (
    <div className="flex items-center gap-1">
      <Button variant="ghost" size="icon" aria-label="Earlier" onClick={onPrev} className="size-10">
        <ChevronLeftIcon />
      </Button>
      <h1 className="min-w-0 truncate px-1 text-xl font-semibold tracking-tight text-balance sm:text-2xl">{label}</h1>
      <Button variant="ghost" size="icon" aria-label="Later" onClick={onNext} className="size-10">
        <ChevronRightIcon />
      </Button>
      <Button variant="outline" onClick={onNow} className="ml-2 h-10 px-3">
        {nowLabel}
      </Button>
    </div>
  )
}
