import { useMemo } from "react"
import { CATEGORIES, SEASONS, type Category, type Item, type Season } from "@/lib/types"
import { COLOR_FAMILIES, type ColorFamily } from "@/lib/color"
import { t } from "@/lib/config"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { ItemTile } from "./ItemTile"

export type Filters = { season: Season | "all"; color: ColorFamily | "all" }

function FilterBar({ filters, onFilters }: { filters: Filters; onFilters: (f: Filters) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <ToggleGroup
        type="single"
        size="sm"
        variant="outline"
        spacing={0}
        value={filters.season}
        onValueChange={(v) => onFilters({ ...filters, season: (v || "all") as Filters["season"] })}
      >
        <ToggleGroupItem value="all" className="h-8 px-2.5">{t("closet.all")}</ToggleGroupItem>
        {SEASONS.map((s) => (
          <ToggleGroupItem key={s} value={s} className="h-8 px-2.5">
            {t(`season.${s}`)}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <Select value={filters.color} onValueChange={(v) => onFilters({ ...filters, color: v as Filters["color"] })}>
        <SelectTrigger size="sm" className="h-8 w-[8.5rem]" aria-label={t("form.color")}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent position="popper">
          <SelectItem value="all">{t("closet.allColors")}</SelectItem>
          {COLOR_FAMILIES.map((c) => (
            <SelectItem key={c} value={c}>
              {t(`color.${c}`)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

/** The closet below the strip: shelves by category on a wide screen, category tabs on a phone. */
export function Closet({
  items,
  currency,
  desktop,
  filters,
  onFilters,
  onPick,
}: {
  items: Item[]
  currency: string
  desktop: boolean
  filters: Filters
  onFilters: (f: Filters) => void
  onPick: (id: string) => void
}) {
  const groups = useMemo(
    () => CATEGORIES.map((c) => [c, items.filter((i) => i.category === c)] as [Category, Item[]]).filter(([, list]) => list.length),
    [items],
  )
  const empty = <p className="py-10 text-center text-sm text-muted-foreground">{t("closet.empty")}</p>

  if (desktop) {
    let n = 0
    return (
      <section id="closet" aria-labelledby="closet-title" className="flex min-w-0 flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <h2 id="closet-title" className="font-display text-2xl font-medium tracking-tight">
            {t("closet.title")} <span className="ml-1 align-middle text-sm font-normal text-muted-foreground tabular-nums">{items.length}</span>
          </h2>
          <FilterBar filters={filters} onFilters={onFilters} />
        </div>
        {groups.length === 0 ? empty : (
          <div className="columns-2 gap-x-7">
            {groups.map(([cat, list]) => (
              <div key={cat} className="mb-5 break-inside-avoid">
                <h3 className="mb-2 flex items-baseline justify-between border-b border-border pb-1 text-[11px] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
                  {t(`category.${cat}`)}
                  <span className="tabular-nums">{list.length}</span>
                </h3>
                <div className="grid grid-cols-[repeat(auto-fill,minmax(64px,1fr))] gap-x-2.5 gap-y-3">
                  {list.map((item) => (
                    <ItemTile key={item.id} item={item} currency={currency} index={n++} onPick={onPick} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    )
  }

  return (
    <section id="closet" aria-labelledby="closet-title" className="flex min-w-0 flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <h2 id="closet-title" className="font-display text-2xl font-medium tracking-tight">{t("closet.title")}</h2>
        <span className="text-sm text-muted-foreground tabular-nums">{items.length}</span>
      </div>
      <FilterBar filters={filters} onFilters={onFilters} />
      <Tabs defaultValue="all" className="gap-3">
        <div className="-mx-4 overflow-x-auto px-4 [scrollbar-width:none]">
          <TabsList className="h-9">
            <TabsTrigger value="all" className="px-3">{t("closet.all")}</TabsTrigger>
            {groups.map(([cat]) => (
              <TabsTrigger key={cat} value={cat} className="px-3">
                {t(`category.${cat}`)}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        {[["all", items] as [string, Item[]], ...groups].map(([key, list]) => (
          <TabsContent key={key} value={key}>
            {list.length === 0 ? empty : (
              <div className="grid grid-cols-3 gap-x-3 gap-y-4">
                {list.map((item, n) => (
                  <ItemTile key={item.id} item={item} currency={currency} index={n} onPick={onPick} showName />
                ))}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </section>
  )
}
