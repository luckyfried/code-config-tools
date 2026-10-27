import { useMemo, useState } from "react"
import { config, slotCategories, t } from "@/lib/config"
import { removeOutfit, saveOutfit } from "@/lib/store"
import type { Item, Outfit } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FlatLay } from "./Rack"
import { Garment } from "./Garment"

const NONE = "none"

/** Stacks an outfit one piece per slot, with the flat-lay drawn as it will sit on the rack. */
export function OutfitBuilder({
  open,
  outfit,
  items,
  onClose,
  onSaved,
}: {
  open: boolean
  outfit?: Outfit
  items: Item[]
  onClose: () => void
  onSaved: (id: string) => void
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-2xl">{open && <Builder outfit={outfit} items={items} onSaved={onSaved} onClose={onClose} />}</DialogContent>
    </Dialog>
  )
}

function Builder({ outfit, items, onSaved, onClose }: { outfit?: Outfit; items: Item[]; onSaved: (id: string) => void; onClose: () => void }) {
  const byId = useMemo(() => new Map(items.map((i) => [i.id, i])), [items])
  const [name, setName] = useState(outfit?.name ?? "")
  const [picks, setPicks] = useState<Record<string, string | null>>(() =>
    Object.fromEntries(config.slots.map((s) => [s, outfit?.items[s] && byId.has(outfit.items[s]!) ? outfit.items[s] : null])),
  )
  const any = Object.values(picks).some(Boolean)
  const ok = name.trim().length > 0 && any

  const save = (e: React.FormEvent) => {
    e.preventDefault()
    if (ok) onSaved(saveOutfit({ id: outfit?.id, name: name.trim(), items: picks }))
  }

  return (
    <form onSubmit={save} className="grid gap-5">
      <DialogHeader>
        <DialogTitle className="font-display text-2xl font-medium">{outfit ? t("builder.editTitle", { name: outfit.name }) : t("builder.newTitle")}</DialogTitle>
      </DialogHeader>
      <div className="grid grid-cols-[1fr_1.1fr] gap-5 max-sm:grid-cols-1">
        <div className="grid content-start gap-3">
          <Field>
            <FieldLabel htmlFor="outfit-name">{t("builder.name")}</FieldLabel>
            <Input id="outfit-name" className="h-10" value={name} onChange={(e) => setName(e.target.value)} placeholder={t("builder.namePlaceholder")} required />
          </Field>
          {config.slots.map((slot) => {
            const cats = slotCategories(slot)
            const choices = items.filter((i) => cats.includes(i.category))
            return (
              <Field key={slot}>
                <FieldLabel htmlFor={`slot-${slot}`}>{t(`slot.${slot}`) === `slot.${slot}` ? slot : t(`slot.${slot}`)}</FieldLabel>
                <Select value={picks[slot] ?? NONE} onValueChange={(v) => setPicks({ ...picks, [slot]: v === NONE ? null : v })}>
                  <SelectTrigger id={`slot-${slot}`} className="h-10 w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent position="popper" className="max-h-72">
                    <SelectItem value={NONE}>{t("builder.none")}</SelectItem>
                    {choices.map((i) => (
                      <SelectItem key={i.id} value={i.id}>
                        <span className="flex items-center gap-2">
                          <Garment category={i.category} color={i.color} className="size-5" />
                          {i.name}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            )
          })}
        </div>
        <FlatLay outfit={{ items: picks }} byId={byId} className="aspect-[16/11] self-start" />
      </div>
      <DialogFooter className="gap-2">
        {outfit && (
          <Button
            type="button"
            variant="ghost"
            className="mr-auto h-11 text-destructive hover:text-destructive"
            onClick={() => {
              removeOutfit(outfit.id)
              onClose()
            }}
          >
            {t("builder.remove")}
          </Button>
        )}
        <Button type="submit" className="h-11 px-6" disabled={!ok}>
          {outfit ? t("builder.save") : t("builder.add")}
        </Button>
      </DialogFooter>
    </form>
  )
}
