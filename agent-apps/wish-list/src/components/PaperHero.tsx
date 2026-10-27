import { forwardRef } from "react"

/** One gift box: body, lid, a ribbon both ways, and a bow. Drawn from its bottom left corner. */
function Box({
  x,
  y,
  w,
  h,
  body,
  ribbon,
  bow = true,
  dots,
}: {
  x: number
  y: number
  w: number
  h: number
  body: string
  ribbon: string
  bow?: boolean
  dots?: string
}) {
  const lid = Math.max(18, h * 0.2)
  const top = y - h
  const mid = x + w / 2
  const band = Math.max(12, w * 0.12)
  return (
    <g>
      <rect x={x} y={top + lid * 0.6} width={w} height={h - lid * 0.6} className={body} />
      {dots && (
        <g className={dots}>
          {Array.from({ length: Math.floor(w / 34) * Math.floor((h - lid) / 34) }, (_, n) => {
            const cols = Math.floor(w / 34)
            const cx = x + 17 + (n % cols) * 34 + (Math.floor(n / cols) % 2) * 9
            const cy = top + lid + 18 + Math.floor(n / cols) * 34
            return cx < x + w - 8 ? <circle key={n} cx={cx} cy={cy} r={5} /> : null
          })}
        </g>
      )}
      <rect x={x} y={top + lid * 0.6} width={w * 0.22} height={h - lid * 0.6} className="p-shade" />
      <rect x={mid - band / 2} y={top} width={band} height={h} className={ribbon} />
      <rect x={x - 8} y={top} width={w + 16} height={lid} rx={3} className={body} />
      <rect x={x - 8} y={top + lid - 6} width={w + 16} height={6} className="p-shade" />
      <rect x={mid - band / 2} y={top} width={band} height={lid} className={ribbon} />
      {bow && (
        <g className={ribbon}>
          <path
            d={`M${mid} ${top} C ${mid - w * 0.12} ${top - w * 0.3}, ${mid - w * 0.42} ${top - w * 0.2}, ${mid - w * 0.3} ${top - 2} Z`}
          />
          <path
            d={`M${mid} ${top} C ${mid + w * 0.12} ${top - w * 0.3}, ${mid + w * 0.42} ${top - w * 0.2}, ${mid + w * 0.3} ${top - 2} Z`}
          />
          <path d={`M${mid - 4} ${top} L ${mid - w * 0.2} ${top + lid * 1.5} L ${mid - w * 0.12} ${top + lid * 1.2} Z`} />
          <path d={`M${mid + 4} ${top} L ${mid + w * 0.2} ${top + lid * 1.5} L ${mid + w * 0.12} ${top + lid * 1.2} Z`} />
          <ellipse cx={mid} cy={top - 3} rx={band * 0.6} ry={band * 0.45} />
        </g>
      )}
    </g>
  )
}

/** A gift tag on its string, hanging from the top edge. */
function HangingTag({ x, drop, fill, turn }: { x: number; drop: number; fill: string; turn: number }) {
  return (
    <g className="hanging-tag">
      <path d={`M${x} -10 L ${x} ${drop}`} className="s-string" strokeWidth={2} />
      <g transform={`translate(${x} ${drop}) rotate(${turn})`}>
        <path d="M -22 0 L 22 0 L 34 14 L 34 78 Q 34 84 28 84 L -28 84 Q -34 84 -34 78 L -34 14 Z" className={fill} />
        <circle cx={0} cy={13} r={5} className="p-sky" />
        <rect x={-20} y={40} width={40} height={4} rx={2} className="p-shade" />
        <rect x={-14} y={52} width={28} height={4} rx={2} className="p-shade" />
      </g>
    </g>
  )
}

const VIEW = "0 0 1600 420"

/** The paper-cut scene: four layers that the page moves by depth, each a sheet with its own shadow. */
export const PaperHero = forwardRef<HTMLDivElement, { eyebrow: string; title: string; line: string }>(
  function PaperHero({ eyebrow, title, line }, ref) {
    return (
      <header ref={ref} className="hero h-[248px] md:h-[352px]" aria-label={title}>
        <div className="hero-scene absolute inset-0" aria-hidden="true">
          <div className="hero-layer" data-depth="0.12" style={{ "--rise-delay": "0ms" } as React.CSSProperties}>
            <svg viewBox={VIEW} preserveAspectRatio="xMidYMax slice">
              <defs>
                <radialGradient id="sun-face" cx="40%" cy="36%" r="70%">
                  <stop offset="0" style={{ stopColor: "var(--sun)" }} />
                  <stop offset="1" style={{ stopColor: "var(--sun-edge)" }} />
                </radialGradient>
                <radialGradient id="sun-glow">
                  <stop offset="0.45" style={{ stopColor: "var(--sun-glow)" }} />
                  <stop offset="1" style={{ stopColor: "var(--sun-glow)", stopOpacity: 0 }} />
                </radialGradient>
              </defs>
              <circle cx={1250} cy={118} r={150} fill="url(#sun-glow)" />
              <circle cx={1250} cy={118} r={66} fill="url(#sun-face)" />
              {[
                [560, 70, 4], [1180, 26, 3], [1400, 60, 4], [1530, 150, 3], [1350, 166, 3],
                [1120, 190, 3], [1340, 230, 4], [470, 30, 3], [1580, 40, 4], [1500, 236, 3],
              ].map(([cx, cy, r], n) => (
                <circle key={n} cx={cx} cy={cy} r={r} className="p-speck" />
              ))}
              <HangingTag x={1105} drop={52} fill="p-5" turn={-6} />
              <HangingTag x={1455} drop={96} fill="p-6" turn={5} />
            </svg>
          </div>
          <div className="hero-layer" data-depth="0.3" style={{ "--rise-delay": "60ms" } as React.CSSProperties}>
            <svg viewBox={VIEW} preserveAspectRatio="xMidYMax slice">
              <path
                d="M-40 330 C 120 270, 260 300, 400 290 C 560 278, 650 236, 820 248 C 990 260, 1080 300, 1240 284 C 1380 270, 1480 250, 1660 268 L 1660 440 L -40 440 Z"
                className="p-1"
              />
              <path
                d="M-40 368 C 140 340, 300 356, 470 338 C 640 320, 760 352, 930 344 C 1120 334, 1260 312, 1440 330 C 1540 340, 1600 330, 1660 324 L 1660 440 L -40 440 Z"
                className="p-2"
              />
            </svg>
          </div>
          <div className="hero-layer" data-depth="0.55" style={{ "--rise-delay": "140ms" } as React.CSSProperties}>
            <svg viewBox={VIEW} preserveAspectRatio="xMidYMax slice">
              <Box x={668} y={402} w={200} h={168} body="p-4" ribbon="p-ribbon-2" />
              <Box x={872} y={402} w={142} h={112} body="p-3" ribbon="p-ribbon" />
              <Box x={574} y={402} w={92} h={76} body="p-6" ribbon="p-4" bow={false} />
              <Box x={1018} y={402} w={86} h={150} body="p-5" ribbon="p-ribbon" dots="p-3" />
              <Box x={1296} y={402} w={122} h={96} body="p-ribbon" ribbon="p-ribbon-2" />
              <Box x={300} y={402} w={96} h={70} body="p-3" ribbon="p-5" />
            </svg>
          </div>
          <div className="hero-layer" data-depth="0.85" style={{ "--rise-delay": "220ms" } as React.CSSProperties}>
            <svg viewBox={VIEW} preserveAspectRatio="xMidYMax slice">
              <path
                d="M-40 404 Q -20 388 0 404 T 40 404 T 80 404 T 120 404 T 160 404 T 200 404 T 240 404 T 280 404 T 320 404 T 360 404 T 400 404 T 440 404 T 480 404 T 520 404 T 560 404 T 600 404 T 640 404 T 680 404 T 720 404 T 760 404 T 800 404 T 840 404 T 880 404 T 920 404 T 960 404 T 1000 404 T 1040 404 T 1080 404 T 1120 404 T 1160 404 T 1200 404 T 1240 404 T 1280 404 T 1320 404 T 1360 404 T 1400 404 T 1440 404 T 1480 404 T 1520 404 T 1560 404 T 1600 404 T 1640 404 L 1660 440 L -40 440 Z"
                className="p-bg"
              />
              <path d="M520 388 c 14 -30, 40 -30, 36 -6 c -4 22, -32 14, -20 -10 c 10 -18, 40 -22, 52 -4" className="s-ribbon" strokeWidth={6} strokeLinecap="round" />
              <path d="M1140 392 c 18 -26, 44 -24, 38 0 c -6 20, -34 10, -20 -12 c 12 -16, 42 -16, 50 4" className="s-ribbon-2" strokeWidth={6} strokeLinecap="round" />
              {[
                [210, 372, 14, 8, 24, "p-ribbon-2"], [470, 360, 12, 7, -30, "p-4"], [610, 340, 10, 6, 50, "p-ribbon"],
                [1060, 356, 12, 7, -18, "p-ribbon-2"], [1228, 366, 14, 8, 36, "p-4"], [1480, 368, 12, 7, -40, "p-ribbon"],
                [130, 350, 10, 6, 60, "p-ribbon"], [1560, 342, 10, 6, 14, "p-ribbon-2"], [930, 330, 10, 6, -52, "p-4"],
              ].map(([x, y, w, h, r, c], n) => (
                <rect key={n} x={x as number} y={y as number} width={w as number} height={h as number} rx={2} className={c as string} transform={`rotate(${r} ${x} ${y})`} />
              ))}
              {[[330, 340, 6, "p-ribbon"], [770, 330, 5, "p-ribbon-2"], [1380, 344, 6, "p-4"], [40, 372, 5, "p-4"]].map(([cx, cy, r, c], n) => (
                <circle key={n} cx={cx as number} cy={cy as number} r={r as number} className={c as string} />
              ))}
            </svg>
          </div>
        </div>
        <div className="hero-copy relative z-10 mx-auto flex h-full w-full max-w-[1600px] flex-col items-center px-5 pt-[max(1.5rem,env(safe-area-inset-top))] text-center md:items-start md:justify-center md:px-10 md:pt-0 md:pb-16 md:text-left">
          <div className="hero-title max-w-[34rem]">
            <p className="text-[0.8rem] font-semibold tracking-[0.16em] text-primary uppercase">{eyebrow}</p>
            <h1 className="display mt-1 text-[2.3rem] leading-[1.02] font-semibold md:mt-2 md:text-[4.4rem]">{title}</h1>
            <p className="mt-3 hidden max-w-[26rem] text-[1.02rem] leading-relaxed text-muted-foreground md:block">{line}</p>
          </div>
        </div>
      </header>
    )
  },
)
