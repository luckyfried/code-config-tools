import { useState, type FormEvent, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { AddedItem } from "@/lib/config"

const NEW_GROUP = "__new__"

type AddItemDialogProps = {
  groups: string[]
  showWeight: boolean
  onAdd: (item: AddedItem) => string | null
  children: ReactNode
}

export function AddItemDialog({ groups, showWeight, onAdd, children }: AddItemDialogProps) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [group, setGroup] = useState(groups[0] ?? NEW_GROUP)
  const [newGroup, setNewGroup] = useState("")
  const [weight, setWeight] = useState("")
  const [problem, setProblem] = useState<string | null>(null)

  const reset = () => {
    setName("")
    setNewGroup("")
    setWeight("")
    setProblem(null)
    setGroup((g) => (groups.includes(g) ? g : (groups[0] ?? NEW_GROUP)))
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const label = group === NEW_GROUP ? newGroup.trim() : group
    if (!name.trim()) return setProblem("Give the item a name.")
    if (!label) return setProblem("Name the new group.")
    const kg = weight.trim() === "" ? null : Number(weight.replace(",", "."))
    if (kg !== null && (!Number.isFinite(kg) || kg < 0)) return setProblem("Weight is a number of kilograms, like 0.4.")
    const refusal = onAdd({ name: name.trim(), group: label, weight: kg })
    if (refusal) return setProblem(refusal)
    reset()
    setOpen(false)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (!o) reset()
      }}
    >
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="gap-5 p-5 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-lg">Add an item</DialogTitle>
          <DialogDescription>It joins this trip's list in the group you pick.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-2">
            <Label htmlFor="add-name">Item</Label>
            <Input
              id="add-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Rain jacket"
              autoComplete="off"
              aria-invalid={problem !== null && !name.trim()}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="add-group">Group</Label>
            <Select value={group} onValueChange={setGroup}>
              <SelectTrigger id="add-group" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {groups.map((g) => (
                    <SelectItem key={g} value={g}>
                      {g}
                    </SelectItem>
                  ))}
                  <SelectItem value={NEW_GROUP}>A new group</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
            {group === NEW_GROUP ? (
              <Input
                aria-label="New group name"
                value={newGroup}
                onChange={(e) => setNewGroup(e.target.value)}
                placeholder="Gifts"
                autoComplete="off"
              />
            ) : null}
          </div>
          {showWeight ? (
            <div className="flex flex-col gap-2">
              <Label htmlFor="add-weight">Weight in kg</Label>
              <Input
                id="add-weight"
                inputMode="decimal"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                placeholder="0.4"
                autoComplete="off"
              />
            </div>
          ) : null}
          {problem ? (
            <p role="alert" className="text-sm font-medium text-destructive">
              {problem}
            </p>
          ) : null}
          <DialogFooter>
            <Button type="submit" size="lg" className="w-full sm:w-auto">
              Add to the list
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
