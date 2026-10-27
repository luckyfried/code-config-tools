import { useState } from "react"
import { t } from "@/lib/config"
import { addItem, editItem, getCloset, type ItemDraft } from "@/lib/store"
import { CATEGORIES, SEASONS, type Category, type Item, type Season } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Garment } from "./Garment"

const HEX = /^#[0-9a-fA-F]{6}$/

/** Adds a piece, or edits one; the swatch beside the form shows it as it will sit in the closet. */
export function ItemForm({ open, item, onClose, onSaved }: { open: boolean; item?: Item; onClose: () => void; onSaved: (id: string) => void }) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">{open && <Form item={item} onSaved={onSaved} />}</DialogContent>
    </Dialog>
  )
}

function Form({ item, onSaved }: { item?: Item; onSaved: (id: string) => void }) {
  const [name, setName] = useState(item?.name ?? "")
  const [category, setCategory] = useState<Category>(item?.category ?? "top")
  const [color, setColor] = useState(item?.color ?? "#3b5b8a")
  const [price, setPrice] = useState(item?.price != null ? String(item.price) : "")
  const [brand, setBrand] = useState(item?.brand ?? "")
  const [seasons, setSeasons] = useState<Season[]>(item?.seasons ?? [])
  const ok = name.trim().length > 0 && HEX.test(color)

  const save = (e: React.FormEvent) => {
    e.preventDefault()
    if (!ok) return
    const n = parseFloat(price)
    const draft: ItemDraft = { name: name.trim(), category, color: color.toLowerCase(), price: Number.isFinite(n) && n >= 0 ? n : null, brand: brand.trim(), seasons }
    if (item) {
      editItem(item.id, draft)
      onSaved(item.id)
    } else onSaved(addItem(draft))
  }

  return (
    <form onSubmit={save} className="grid gap-5">
      <DialogHeader>
        <DialogTitle className="font-display text-2xl font-medium">{item ? t("form.editTitle", { name: item.name }) : t("form.addTitle")}</DialogTitle>
      </DialogHeader>
      <div className="grid grid-cols-[1fr_7rem] gap-5 max-sm:grid-cols-1">
        <FieldGroup className="gap-4">
          <Field>
            <FieldLabel htmlFor="item-name">{t("form.name")}</FieldLabel>
            <Input id="item-name" className="h-10" value={name} onChange={(e) => setName(e.target.value)} placeholder={t("form.namePlaceholder")} autoFocus required />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field>
              <FieldLabel htmlFor="item-kind">{t("form.category")}</FieldLabel>
              <Select value={category} onValueChange={(v) => setCategory(v as Category)}>
                <SelectTrigger id="item-kind" className="h-10 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent position="popper">
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {t(`categoryOne.${c}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel htmlFor="item-color">{t("form.color")}</FieldLabel>
              <div className="flex h-10 items-center gap-2 rounded-lg border border-input px-1.5">
                <input
                  id="item-color"
                  type="color"
                  value={HEX.test(color) ? color : "#000000"}
                  onChange={(e) => setColor(e.target.value)}
                  className="size-7 shrink-0 cursor-pointer rounded border-0 bg-transparent p-0"
                />
                <input
                  aria-label={t("form.color")}
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="min-w-0 flex-1 bg-transparent font-mono text-sm uppercase outline-none"
                  maxLength={7}
                />
              </div>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field>
              <FieldLabel htmlFor="item-price">
                {t("form.price")} <span className="text-muted-foreground">({getCloset().currency})</span>
              </FieldLabel>
              <Input id="item-price" className="h-10" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value.replace(/[^0-9.]/g, ""))} placeholder={t("form.pricePlaceholder")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="item-brand">{t("form.brand")}</FieldLabel>
              <Input id="item-brand" className="h-10" value={brand} onChange={(e) => setBrand(e.target.value)} />
            </Field>
          </div>
          <Field>
            <FieldLabel>{t("form.seasons")}</FieldLabel>
            <ToggleGroup type="multiple" variant="outline" spacing={0} value={seasons} onValueChange={(v) => setSeasons(v as Season[])}>
              {SEASONS.map((s) => (
                <ToggleGroupItem key={s} value={s} className="h-10 px-3">
                  {t(`season.${s}`)}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </Field>
        </FieldGroup>
        <div className="grid aspect-square place-items-center self-start rounded-xl bg-flatlay ring-1 ring-flatlay-edge max-sm:hidden">
          <Garment category={category} color={HEX.test(color) ? color : "#888888"} className="size-[78%]" />
        </div>
      </div>
      <DialogFooter>
        <Button type="submit" className="h-11 px-6" disabled={!ok}>
          {item ? t("form.save") : t("form.add")}
        </Button>
      </DialogFooter>
    </form>
  )
}
