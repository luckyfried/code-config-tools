import { ArrowRightIcon, ChevronLeftIcon, ChevronRightIcon, ChefHatIcon } from "lucide-react"
import { useEffect, useState, type CSSProperties } from "react"
import { Button } from "@/components/ui/button"
import { config, type Recipe } from "@/lib/config"
import { cuisineTint } from "@/lib/cuisine"
import { firstDuration } from "@/lib/durations"
import { useReducedMotion } from "@/lib/motion"
import { go, href } from "@/lib/router"
import { cn } from "@/lib/utils"
import { IngredientStrip } from "./IngredientStrip"
import { ProgressRail } from "./ProgressRail"
import { ServingsControl, useServings } from "./ServingsControl"
import { StepPager } from "./StepPager"
import { StepText } from "./StepText"
import { TimeArc } from "./TimeArc"

const TOURED = "cook-mode:toured"
// The first step turns soon after load, so the slide between steps shows early; later steps rest longer to count down.
const FIRST_DWELL_MS = 1300
const DWELL_MS = 3400
const PILL_AFTER_MS = 400

/** A long step sets smaller on a phone, so the whole step and its timer fit the stage. */
function stepLength(text = "") {
  return text.length > 120 ? "step-long" : text.length > 76 ? "step-medium" : undefined
}

/**
 * Tonight's recipe as a live cook stage. On the first visit of a session it
 * plays through the steps once, each step's timer counting down, then rests on step one.
 */
export function TonightHero({ recipe }: { recipe: Recipe }) {
  const reduce = useReducedMotion()
  const { factor } = useServings(recipe)
  const [at, setAt] = useState(0)
  const [touring, setTouring] = useState(() => {
    try {
      return !window.matchMedia("(prefers-reduced-motion: reduce)").matches && !sessionStorage.getItem(TOURED)
    } catch {
      return false
    }
  })
  const [demo, setDemo] = useState(false)
  const last = recipe.steps.length - 1

  useEffect(() => {
    if (!touring) return
    try {
      sessionStorage.setItem(TOURED, "1")
    } catch {
      // A session that cannot be marked plays the preview again next time.
    }
    setDemo(false)
    const showTimer = window.setTimeout(() => setDemo(Boolean(firstDuration(recipe.steps[at]))), PILL_AFTER_MS)
    const turn = window.setTimeout(() => {
      if (at < last) setAt(at + 1)
      else {
        setAt(0)
        setTouring(false)
      }
    }, at === 0 ? FIRST_DWELL_MS : DWELL_MS)
    return () => {
      window.clearTimeout(showTimer)
      window.clearTimeout(turn)
    }
  }, [touring, at, last, recipe.steps])

  useEffect(() => {
    if (reduce) setTouring(false)
  }, [reduce])

  const stopTour = () => {
    if (touring) {
      setTouring(false)
      setDemo(false)
    }
  }
  const step = (to: number) => {
    stopTour()
    setAt(Math.max(0, Math.min(last, to)))
  }
  const startAt = touring ? 1 : at + 1

  return (
    <section
      aria-labelledby="tonight-title"
      className="gutter safe-x pb-8 sm:pb-12"
      onPointerDownCapture={stopTour}
      onKeyDownCapture={stopTour}
    >
      <div className="grid grid-cols-1 gap-5 short:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] short:gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(340px,30%)] lg:gap-10">
        <div className="flex flex-col gap-3 short:justify-center short:gap-2 lg:order-2 lg:py-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-primary">
            <ChefHatIcon className="size-4" aria-hidden="true" />
            Tonight
          </p>
          <h1 id="tonight-title" className="title-type text-[30px] leading-[1.08] font-semibold short:text-[26px]! sm:text-[40px] xl:text-[46px]">
            <a href={href({ name: "recipe", id: recipe.id })} className="decoration-primary/40 decoration-2 underline-offset-[6px] hover:underline">
              {recipe.title}
            </a>
          </h1>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
            <TimeArc minutes={recipe.minutes} className="text-foreground" />
            <span className="nums">Serves {recipe.servings}</span>
            <span className="flex items-center gap-2">
              <span className="tint-edge size-2.5 rounded-full" style={{ "--tint": cuisineTint(recipe.cuisine) } as CSSProperties} />
              {recipe.cuisine}
            </span>
          </div>
          <ServingsControl recipe={recipe} className="mt-3 hidden lg:flex" />
          <Button size="lg" className="mt-2 hidden self-start short:inline-flex" onClick={() => go({ name: "cook", id: recipe.id, step: startAt })}>
            Start cooking
            <ArrowRightIcon data-icon="inline-end" />
          </Button>
          <div className="mt-2 hidden gap-2 lg:flex">
            <Button size="lg" className="flex-1" onClick={() => go({ name: "cook", id: recipe.id, step: startAt })}>
              Start cooking
              <ArrowRightIcon data-icon="inline-end" />
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href={href({ name: "recipe", id: recipe.id })}>Full recipe</a>
            </Button>
          </div>
          <ol className="mt-5 hidden flex-col border-t border-border pt-3 lg:flex" aria-label="Tonight's steps">
            {recipe.steps.map((text, index) => (
              <li key={index}>
                <button
                  type="button"
                  onClick={() => step(index)}
                  aria-current={index === at ? "step" : undefined}
                  className={cn(
                    "flex w-full cursor-pointer items-baseline gap-3 rounded-lg px-2 py-1.5 text-left text-sm transition-colors duration-150",
                    index === at ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span className="w-4 shrink-0 font-semibold nums">{index + 1}</span>
                  <span className="truncate">{text}</span>
                </button>
              </li>
            ))}
          </ol>
        </div>

        <div className="flex flex-col rounded-[28px] border border-stage-edge bg-stage p-4 text-stage-foreground shadow-sheet short:h-[calc(100dvh-4.5rem)] short:p-3! short:pt-2! sm:p-8 lg:order-1 lg:min-h-[min(580px,calc(100dvh-250px))] stage-glow lg:p-10 xl:p-12">
          <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <p className="pl-1 nums" aria-live="polite">
              Step {at + 1} of {recipe.steps.length}
            </p>
            <ProgressRail count={recipe.steps.length} current={at} onPick={step} className="hidden short:flex" />
            <div className="flex gap-1">
              <Button variant="ghost" size="icon" className="short:size-9" aria-label="Previous step" disabled={at === 0} onClick={() => step(at - 1)}>
                <ChevronLeftIcon />
              </Button>
              <Button variant="ghost" size="icon" className="short:size-9" aria-label="Next step" disabled={at === last} onClick={() => step(at + 1)}>
                <ChevronRightIcon />
              </Button>
            </div>
          </div>
          <StepPager
            step={at}
            onSwipe={(direction) => step(direction === "next" ? at + 1 : at - 1)}
            className="my-3 h-[16.2rem] items-center short:my-1.5! short:h-auto! short:min-h-0 short:flex-1 sm:my-6 sm:h-[18.6rem] lg:h-auto lg:min-h-[13rem] lg:flex-1"
            pageClassName="flex items-center"
            render={(index) => (
              <p className={cn("step-type hero-step line-clamp-5 px-1 sm:line-clamp-6 short:line-clamp-4", stepLength(recipe.steps[index]))}>
                <StepText recipe={recipe} stepIndex={index} demo={touring && demo && index === at} />
              </p>
            )}
          />
          <IngredientStrip recipe={recipe} stepIndex={at} factor={factor} />
          <div className="mt-2 flex flex-col gap-1 short:hidden! sm:flex-row sm:items-center sm:justify-between sm:gap-3">
            <ProgressRail count={recipe.steps.length} current={at} onPick={step} className="-ml-1" />
            <Button size="lg" className="w-full short:hidden sm:w-auto lg:hidden" onClick={() => go({ name: "cook", id: recipe.id, step: startAt })}>
              Start cooking
              <ArrowRightIcon data-icon="inline-end" />
            </Button>
          </div>
        </div>
      </div>
      <ServingsControl recipe={recipe} className="mt-5 lg:hidden" />
    </section>
  )
}

export function pinnedRecipe() {
  return config.recipes.find((recipe) => recipe.id === config.pinned) ?? config.recipes[0]
}
