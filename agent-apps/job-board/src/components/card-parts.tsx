import { initials, readPay } from "@/lib/company"
import { cn } from "@/lib/utils"

// The company's initials on its own color; the color comes from --hue, set on the card.
export function CompanyMark({ company, size }: { company: string; size: "lg" | "sm" }) {
  return (
    <span className="mark" data-size={size} aria-hidden="true">
      {initials(company)}
    </span>
  )
}

function Figure({ amount }: { amount: string }) {
  const m = /^([\d.,]+)([kKmM]?)$/.exec(amount)
  return (
    <>
      <span className="cur">$</span>
      {m ? m[1] : amount}
      {m?.[2] && <span className="unit">{m[2].toLowerCase()}</span>}
    </>
  )
}

// The pay set as a figure: the dollar sign raised and small, the thousands mark light, the range on one line.
export function PayFigure({ pay, size, className }: { pay: string; size: "lg" | "md"; className?: string }) {
  const p = readPay(pay)
  return (
    <p className={cn("pay-figure", className)} data-size={size}>
      {p ? (
        <>
          <span className="whitespace-nowrap">
            <Figure amount={p.low} />
            {p.high && (
              <>
                <span className="dash">–</span>
                <Figure amount={p.high} />
              </>
            )}
          </span>
          {p.rest && <span className="rest">{p.rest}</span>}
        </>
      ) : (
        pay
      )}
    </p>
  )
}
