import { forwardRef, type HTMLAttributes, type KeyboardEvent } from "react"
import { Check, CornerDownRight, NotebookText } from "lucide-react"
import { cn } from "@/lib/utils"
import { weekdayShort } from "@/lib/dates"
import type { Task } from "@/lib/board"

export interface TaskCardProps extends HTMLAttributes<HTMLDivElement> {
  task: Task
  compact?: boolean
  lifted?: boolean
  placeholder?: boolean
  collapsing?: boolean
  /** An entrance animation for the card body, kept off the node that dnd-kit moves. */
  animClass?: string
  onToggle?: () => void
  onOpen?: () => void
  onCardKey?: (e: KeyboardEvent<HTMLButtonElement>) => void
}

/** One task on the board: a round check, the title, and the small marks for notes and carry-over. */
export const TaskCard = forwardRef<HTMLDivElement, TaskCardProps>(function TaskCard(
  { task, compact, lifted, placeholder, collapsing, animClass, onToggle, onOpen, onCardKey, className, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      data-done={task.done}
      data-closed={collapsing}
      className={cn("wb-collapse select-none [-webkit-touch-callout:none]", className)}
      {...rest}
    >
      <div className={cn("min-h-0", animClass)}>
        <div
          data-placeholder={placeholder}
          className={cn(
            "wb-card group/card relative mb-2 flex items-start gap-1 rounded-lg border bg-card text-card-foreground",
            compact ? "bg-card/45 shadow-none" : "",
            lifted && "wb-lifted",
          )}
        >
          <button
            type="button"
            role="checkbox"
            aria-checked={task.done}
            aria-label={task.done ? `Mark "${task.title}" not done` : `Mark "${task.title}" done`}
            onClick={onToggle}
            className="grid size-11 shrink-0 place-items-center rounded-lg outline-none lg:w-9 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span
              className={cn(
                "grid size-[18px] place-items-center rounded-full border-[1.5px] transition-[background-color,border-color] duration-150",
                task.done ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground/55",
              )}
            >
              <Check className={cn("size-3 transition-opacity duration-150", task.done ? "opacity-100" : "opacity-0")} strokeWidth={3} />
            </span>
          </button>
          <button
            type="button"
            data-card-id={task.id}
            onClick={onOpen}
            onKeyDown={onCardKey}
            className={cn(
              "min-w-0 flex-1 rounded-md py-2.5 pr-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring",
              compact ? "py-2.5" : "",
            )}
          >
            <span
              className={cn(
                "wb-strike inline text-base leading-snug text-pretty break-words lg:text-[0.9375rem]",
                task.done && "text-muted-foreground",
              )}
            >
              {task.title}
            </span>
            {!compact && (task.carriedFrom || task.notes) && (
              <span className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                {task.carriedFrom && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/12 px-2 py-0.5 font-medium text-primary">
                    <CornerDownRight className="size-3" aria-hidden />
                    from {task.carriedFrom === "later" ? "Later" : weekdayShort(task.carriedFrom)}
                  </span>
                )}
                {task.notes && (
                  <span className="inline-flex items-center gap-1">
                    <NotebookText className="size-3" aria-hidden />
                    Notes
                  </span>
                )}
              </span>
            )}
          </button>
        </div>
      </div>
    </div>
  )
})
