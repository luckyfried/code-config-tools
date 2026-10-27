import { Mail, MessageCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { fill, type Copy, type Item, type Owner } from "@/lib/config"

function smsHref(phone: string, body: string): string {
  return `sms:${phone.replace(/[^\d+]/g, "")}?&body=${encodeURIComponent(body)}`
}

function mailHref(email: string, subject: string, body: string): string {
  return `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

/** "I'll get this": a note to the owner with the gift already named, by text or by email. */
export function GetDialog({
  item,
  owner,
  copy,
  priceText,
  onClose,
  onSent,
}: {
  item: Item | null
  owner: Owner
  copy: Copy
  priceText: string
  onClose: () => void
  onSent: (item: Item) => void
}) {
  const vars = { owner: owner.name, item: item?.name ?? "", price: priceText }
  const body = fill(copy.message, vars)
  return (
    <Dialog open={item !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="gap-5 rounded-2xl p-6 sm:max-w-md">
        <DialogHeader className="gap-2.5">
          <DialogTitle className="display pr-6 text-[1.5rem] leading-tight font-semibold">{fill(copy.getTitle, vars)}</DialogTitle>
          <DialogDescription className="text-[0.95rem] leading-relaxed">{fill(copy.getBody, vars)}</DialogDescription>
        </DialogHeader>
        <blockquote className="rounded-xl border border-border bg-muted/60 px-4 py-3 text-[0.95rem] leading-relaxed">{body}</blockquote>
        <div className="flex flex-col gap-2.5 sm:flex-row">
          {owner.phone && item && (
            <Button asChild className="h-11 flex-1 gap-2 rounded-full text-[0.95rem] font-semibold">
              <a href={smsHref(owner.phone, body)} onClick={() => onSent(item)}>
                <MessageCircle className="size-[18px]" />
                {fill(copy.text, vars)}
              </a>
            </Button>
          )}
          {owner.email && item && (
            <Button asChild variant={owner.phone ? "outline" : "default"} className="h-11 flex-1 gap-2 rounded-full text-[0.95rem] font-semibold">
              <a href={mailHref(owner.email, fill(copy.subject, vars), body)} onClick={() => onSent(item)}>
                <Mail className="size-[18px]" />
                {fill(copy.email, vars)}
              </a>
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
