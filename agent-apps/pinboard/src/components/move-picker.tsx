import { useState, type ReactNode } from "react"
import { Check, Plus } from "lucide-react"
import { cn } from "cn"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { slug } from "@/lib/data"
import type { BoardBody } from "@/types"

interface MovePickerProps {
  boards: BoardBody[]
  current: string | null
  disabled: boolean
  onMove: (board: string, name: string) => void
  children: ReactNode
}

export function MovePicker({ boards, current, disabled, onMove, children }: MovePickerProps) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const pick = (board: string, boardName: string) => {
    setOpen(false)
    setName("")
    onMove(board, boardName)
  }
  return (
    <Popover open={open && !disabled} onOpenChange={setOpen}>
      <PopoverTrigger asChild disabled={disabled}>
        {children}
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 p-1.5" onClick={(event) => event.stopPropagation()}>
        <p className="px-2 pt-1 pb-1.5 text-xs font-medium text-muted-foreground">Move to a board</p>
        <ul className="flex flex-col">
          {boards.map((board) => (
            <li key={board.id}>
              <button
                type="button"
                disabled={board.id === current}
                onClick={() => pick(board.id, board.name)}
                className={cn(
                  "flex min-h-10 w-full items-center justify-between rounded-md px-2 text-left text-sm transition-colors hover:bg-accent focus-visible:bg-accent focus-visible:outline-none",
                  board.id === current && "text-muted-foreground",
                )}
              >
                {board.name}
                {board.id === current && <Check className="size-4" aria-label="Here now" />}
              </button>
            </li>
          ))}
        </ul>
        <form
          className="mt-1 flex gap-1.5 border-t border-border p-1.5 pt-2.5"
          onSubmit={(event) => {
            event.preventDefault()
            const clean = name.trim()
            if (clean) pick(slug(clean), clean)
          }}
        >
          <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="A new board" aria-label="A new board's name" />
          <Button type="submit" size="icon" variant="secondary" aria-label="Make the board and move the pin there" disabled={!name.trim()}>
            <Plus />
          </Button>
        </form>
      </PopoverContent>
    </Popover>
  )
}
