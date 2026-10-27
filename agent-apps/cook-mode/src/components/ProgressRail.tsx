import { cn } from "@/lib/utils"

interface ProgressRailProps {
  count: number
  current: number
  onPick: (index: number) => void
  className?: string
}

/** One dot per step: the ones behind are filled, the current one is a bar. */
export function ProgressRail({ count, current, onPick, className }: ProgressRailProps) {
  return (
    <nav className={cn("flex items-center", className)} aria-label="Steps">
      <ol className="flex items-center">
        {Array.from({ length: count }, (_, index) => (
          <li key={index}>
            <button
              type="button"
              onClick={() => onPick(index)}
              aria-label={`Step ${index + 1}`}
              aria-current={index === current ? "step" : undefined}
              className="group flex h-11 min-w-5 cursor-pointer short:h-9 items-center justify-center px-0.5"
            >
              <span
                className={cn(
                  "block h-2 rounded-full transition-[width,background-color] duration-200 ease-out",
                  index === current ? "w-6 bg-primary" : "w-2",
                  index < current && "bg-primary/55",
                  index > current && "bg-foreground/20 group-hover:bg-foreground/35",
                )}
              />
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}
