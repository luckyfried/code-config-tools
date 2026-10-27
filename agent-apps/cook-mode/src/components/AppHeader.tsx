import { SearchIcon, ShoppingBasketIcon } from "lucide-react"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { config } from "@/lib/config"
import { minutesText } from "@/lib/durations"
import { go, href } from "@/lib/router"
import { useStore, weekStore } from "@/lib/store"
import { cn } from "@/lib/utils"

export function AppHeader({ current }: { current: "index" | "recipe" | "shopping" }) {
  const [open, setOpen] = useState(false)
  const week = useStore(weekStore)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const typing = event.target instanceof HTMLElement && event.target.closest("input, textarea, [contenteditable]")
      if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !typing)) {
        event.preventDefault()
        setOpen((value) => !value)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  return (
    <header className="gutter safe-x safe-top no-print">
      <div className="flex h-14 items-center justify-between gap-3 short:h-12! sm:h-16">
        <a href={href({ name: "index" })} className="title-type min-w-0 truncate text-xl font-semibold sm:text-2xl">
          {config.kitchen}
        </a>
        <nav className="flex items-center gap-1" aria-label="Main">
          <Button variant="ghost" onClick={() => setOpen(true)} aria-label="Search recipes" className="text-muted-foreground hover:text-foreground">
            <SearchIcon data-icon="inline-start" />
            <span className="hidden sm:inline">Search</span>
            <kbd className="ml-1 hidden rounded border border-border px-1.5 font-sans text-xs md:inline">/</kbd>
          </Button>
          <Button
            variant="ghost"
            asChild
            className={cn("text-muted-foreground hover:text-foreground", current === "shopping" && "bg-muted text-foreground")}
          >
            <a href={href({ name: "shopping" })} aria-current={current === "shopping" ? "page" : undefined}>
              <ShoppingBasketIcon data-icon="inline-start" />
              <span className="hidden sm:inline">Shopping</span>
              <span className="sr-only sm:hidden">Shopping list</span>
              {week.length > 0 ? (
                <span className="ml-0.5 inline-flex min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs leading-5 font-semibold text-primary-foreground nums">
                  {week.length}
                </span>
              ) : null}
            </a>
          </Button>
        </nav>
      </div>
      <CommandDialog open={open} onOpenChange={setOpen} title="Search recipes" description="Find a recipe by name, cuisine, tag, or ingredient.">
        <CommandInput placeholder="Recipe, cuisine, or ingredient" className="text-base" />
        <CommandList>
          <CommandEmpty>No recipe matches that.</CommandEmpty>
          <CommandGroup heading="Recipes">
            {config.recipes.map((recipe) => (
              <CommandItem
                key={recipe.id}
                value={recipe.id}
                keywords={[recipe.title, recipe.cuisine, ...recipe.tags, ...recipe.ingredients.map((item) => item.name.split(",")[0])]}
                onSelect={() => {
                  setOpen(false)
                  go({ name: "recipe", id: recipe.id })
                }}
                className="py-2.5"
              >
                <span className="min-w-0 flex-1 truncate">{recipe.title}</span>
                <span className="text-xs text-muted-foreground nums">
                  {recipe.cuisine}, {minutesText(recipe.minutes)}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </header>
  )
}
