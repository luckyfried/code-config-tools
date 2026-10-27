import { ArrowLeftIcon, ArrowRightIcon, CheckIcon, ListIcon, TimerIcon, XIcon } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { config, type Recipe } from "@/lib/config"
import { clock, firstDuration } from "@/lib/durations"
import { convertTemperatures, shownIngredient } from "@/lib/quantity"
import { go } from "@/lib/router"
import { leftOf, startTimer, timerId, toggleTimer, useNow, useTimers } from "@/lib/timers"
import { cn } from "@/lib/utils"
import { useWakeLock } from "@/lib/wake-lock"
import { IngredientStrip } from "./IngredientStrip"
import { ProgressRail } from "./ProgressRail"
import { useServings } from "./ServingsControl"
import { StepPager } from "./StepPager"
import { StepText } from "./StepText"

/** Timers of this recipe that are not on the step in view, so nothing simmers forgotten. */
function TimerTray({ recipe, stepIndex }: { recipe: Recipe; stepIndex: number }) {
  const timers = useTimers().filter((timer) => timer.recipeId === recipe.id && timer.step !== stepIndex + 1)
  const now = useNow()
  if (timers.length === 0) return null
  return (
    <ul className="flex flex-wrap justify-center gap-2" aria-label="Other timers">
      {timers.map((timer) => (
        <li key={timer.id}>
          <button
            type="button"
            onClick={() => go({ name: "cook", id: recipe.id, step: timer.step }, true)}
            className={cn(
              "flex h-9 cursor-pointer items-center gap-1.5 rounded-full px-3 text-sm font-semibold nums transition-transform duration-150 active:scale-[0.97]",
              timer.done ? "bg-done text-done-foreground" : "bg-chip text-chip-foreground",
            )}
          >
            <TimerIcon className="size-4" aria-hidden="true" />
            {timer.label}
            <span className="font-normal">{timer.done ? "done" : clock(leftOf(timer, now))}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function DoneAnnouncer() {
  const timers = useTimers()
  const done = timers.filter((timer) => timer.done).map((timer) => timer.label)
  return (
    <p className="sr-only" aria-live="assertive">
      {done.length ? `Timer done: ${done.join(", ")}` : ""}
    </p>
  )
}

export function CookMode({ recipe, step }: { recipe: Recipe; step: number }) {
  const count = recipe.steps.length
  const index = Math.min(Math.max(step, 1), count) - 1
  const { factor, servings } = useServings(recipe)
  const timers = useTimers()
  const [sheet, setSheet] = useState(false)
  const main = useRef<HTMLElement>(null)
  useWakeLock(true)

  const to = (next: number) => {
    if (next < 0 || next >= count) return
    go({ name: "cook", id: recipe.id, step: next + 1 }, true)
  }
  const leave = () => go({ name: "recipe", id: recipe.id })

  useEffect(() => {
    document.title = `Step ${index + 1}: ${recipe.title}`
    main.current?.scrollTo({ top: 0 })
  }, [index, recipe.title])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (sheet || event.metaKey || event.ctrlKey || event.altKey) return
      if (event.target instanceof HTMLElement && event.target.closest("input, textarea, [role=slider]")) return
      if (event.key === "ArrowRight") to(index + 1)
      else if (event.key === "ArrowLeft") to(index - 1)
      else if (event.key === "Escape") leave()
      else if (event.key === "t" || event.key === "T") {
        const text = convertTemperatures(recipe.steps[index], config.units)
        const first = firstDuration(text)
        if (!first) return
        const id = timerId(recipe.id, index + 1, first.index)
        if (timers.some((timer) => timer.id === id && !timer.done)) toggleTimer(id)
        else startTimer({ id, recipeId: recipe.id, step: index + 1, label: `Step ${index + 1}`, durationMs: first.ms })
      } else return
      event.preventDefault()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  })

  const last = index === count - 1

  return (
    <div className="cook-in stage-glow fixed inset-0 z-40 flex flex-col bg-stage text-stage-foreground" role="dialog" aria-modal="true" aria-label={`Cooking ${recipe.title}`}>
      <header className="safe-top gutter safe-x">
        <div className="mx-auto flex h-12 w-full max-w-[720px] items-center gap-2 sm:h-14">
          <Button variant="ghost" size="icon" onClick={leave} aria-label="Leave cook mode" className="-ml-2">
            <XIcon />
          </Button>
          <p className="min-w-0 flex-1 truncate text-sm text-muted-foreground">{recipe.title}</p>
          <p className="text-sm font-semibold nums">
            {index + 1}
            <span className="font-normal text-muted-foreground"> of {count}</span>
          </p>
          <Sheet open={sheet} onOpenChange={setSheet}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="All ingredients" className="-mr-2">
                <ListIcon />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[min(420px,100vw)] gap-0 bg-stage text-stage-foreground">
              <SheetHeader>
                <SheetTitle className="title-type text-2xl">Everything for this</SheetTitle>
                <SheetDescription className="nums">Scaled for {servings}.</SheetDescription>
              </SheetHeader>
              <ul className="flex flex-col overflow-y-auto px-4 pb-8">
                {recipe.ingredients.map((ingredient, position) => {
                  const shown = shownIngredient(ingredient, factor, config.units)
                  return (
                    <li key={position} className={cn("flex gap-3 border-b border-border/70 py-3 text-base", ingredient.step === index + 1 && "font-semibold")}>
                      <span className="w-20 shrink-0 nums">
                        {shown.amount} {shown.unit}
                      </span>
                      <span className="flex-1">{shown.name}</span>
                      {ingredient.step ? <span className="text-sm font-normal text-muted-foreground nums">Step {ingredient.step}</span> : null}
                    </li>
                  )
                })}
              </ul>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <main ref={main} className="gutter safe-x flex flex-1 flex-col overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[720px] flex-1 flex-col justify-center py-4">
          <TimerTray recipe={recipe} stepIndex={index} />
          <StepPager
            step={index}
            onSwipe={(direction) => to(direction === "next" ? index + 1 : index - 1)}
            className="flex-1 items-center py-6"
            render={(at) => (
              <p className="step-type">
                <StepText recipe={recipe} stepIndex={at} />
              </p>
            )}
          />
        </div>
      </main>

      <footer className="safe-bottom gutter safe-x">
        <div className="mx-auto flex w-full max-w-[720px] flex-col gap-2">
          <IngredientStrip recipe={recipe} stepIndex={index} factor={factor} />
          <div className="flex items-center justify-between gap-2">
            <Button variant="outline" size="icon-lg" onClick={() => to(index - 1)} disabled={index === 0} aria-label="Previous step" className="bg-transparent">
              <ArrowLeftIcon />
            </Button>
            <ProgressRail count={count} current={index} onPick={to} className="min-w-0 justify-center overflow-hidden" />
            {last ? (
              <Button size="lg" onClick={leave}>
                <CheckIcon data-icon="inline-start" />
                Done
              </Button>
            ) : (
              <Button size="icon-lg" onClick={() => to(index + 1)} aria-label="Next step">
                <ArrowRightIcon />
              </Button>
            )}
          </div>
        </div>
      </footer>
      <DoneAnnouncer />
    </div>
  )
}
