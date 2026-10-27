// Small drawn marks the cards share: the check that draws itself, the yes seal, and the paper clip on a maybe.
export function DrawnCheck({ delay = 0, className = "" }: { delay?: number; className?: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={`drawn-check ${className}`} style={{ ["--d" as string]: `${delay}ms` }}>
      <circle cx="8" cy="8" r="7" className="ring" />
      <path d="M4.6 8.3 7 10.6l4.4-5" className="tick" />
    </svg>
  )
}

export function Seal() {
  const teeth = Array.from({ length: 24 }, (_, i) => {
    const a = (i / 24) * Math.PI * 2
    const r = i % 2 ? 29 : 32
    return `${(32 + Math.cos(a) * r).toFixed(1)},${(32 + Math.sin(a) * r).toFixed(1)}`
  }).join(" ")
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" className="seal-svg">
      <polygon points={teeth} className="seal-edge" />
      <circle cx="32" cy="32" r="24" className="seal-face" />
      <circle cx="32" cy="32" r="20" className="seal-ring" />
      <path d="M22 33.5 29 40l13.5-15" className="seal-tick" />
    </svg>
  )
}

export function PaperClip() {
  return (
    <svg viewBox="0 0 24 64" aria-hidden="true" className="clip-svg">
      <path d="M8 46V14a6 6 0 0 1 12 0v36a9 9 0 0 1-18 0V18" />
    </svg>
  )
}
