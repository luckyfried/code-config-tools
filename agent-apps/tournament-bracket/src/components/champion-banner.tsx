import { useLayoutEffect, useRef, type CSSProperties } from "react"
import { EASE_OUT, SPRING } from "@/lib/motion"
import { inkOn } from "@/lib/layout"

type Props = { name: string; label: string; score?: string; animate: boolean; color: string; size?: "sheet" | "card" }

/** The champion's name in display type on one line, scaled down to the banner's width when it is long; on the night
 * it lands, each letter springs up into place in turn. The size is set before the letters move, so the line never reflows. */
export function ChampionBanner({ name, label, score, animate, color, size = "sheet" }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const nameRef = useRef<HTMLSpanElement>(null)

  useLayoutEffect(() => {
    const box = ref.current
    const line = nameRef.current
    if (!box || !line) return
    const fitLine = () => {
      line.style.fontSize = ""
      const room = box.clientWidth
      const need = line.scrollWidth
      if (room > 0 && need > room) line.style.fontSize = `${(parseFloat(getComputedStyle(line).fontSize) * room) / need}px`
    }
    fitLine()
    void document.fonts.ready.then(fitLine)
  }, [name, size])

  useLayoutEffect(() => {
    if (!animate || !ref.current) return
    const letters = ref.current.querySelectorAll<HTMLElement>(".banner-letter")
    const anims: Animation[] = []
    letters.forEach((el, i) => {
      anims.push(
        el.animate(
          [
            { transform: "translateY(70%) rotate(-10deg) scale(0.4)", opacity: 0 },
            { transform: "translateY(0) rotate(0) scale(1)", opacity: 1 },
          ],
          { duration: SPRING.letter.ms, delay: i * 16, easing: SPRING.letter.easing, fill: "backwards" },
        ),
      )
    })
    const sweep = ref.current.querySelector<HTMLElement>(".banner-sweep")
    if (sweep) {
      anims.push(sweep.animate([{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], { duration: 520, delay: 120 + letters.length * 16, easing: EASE_OUT, fill: "backwards" }))
    }
    const rest = ref.current.querySelectorAll<HTMLElement>(".banner-rest")
    rest.forEach((el) =>
      anims.push(el.animate([{ opacity: 0, transform: "translateY(6px)" }, { opacity: 1, transform: "none" }], { duration: 400, delay: 80, easing: EASE_OUT, fill: "backwards" })),
    )
    return () => anims.forEach((a) => a.cancel())
  }, [animate])

  const words = name.split(" ")
  const long = name.length > 14
  const nameSize = size === "card" ? (long ? "text-[2.1rem]" : "text-[2.6rem]") : long ? "text-[2.6rem]" : "text-[3.25rem]"

  return (
    <div ref={ref} className="flex w-full flex-col items-center gap-1 text-center" style={{ "--team": color, "--team-ink": inkOn(color) } as CSSProperties}>
      <span className="banner-rest display text-lg text-win">{label}</span>
      <span ref={nameRef} className={`display ${nameSize} whitespace-nowrap text-foreground [text-shadow:var(--banner-shadow)]`} aria-label={name}>
        {words.map((w, wi) => (
          <span key={wi} className="inline-block" aria-hidden>
            {[...w].map((ch, ci) => (
              <span key={ci} className="banner-letter">
                {ch}
              </span>
            ))}
            {wi < words.length - 1 && <span className="banner-letter">&nbsp;</span>}
          </span>
        ))}
      </span>
      <span className="banner-sweep block h-1.5 w-2/3 rounded-full" />
      {score && <span className="banner-rest figure text-sm font-semibold text-muted-foreground">{score}</span>}
    </div>
  )
}
