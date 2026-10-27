import { useMemo } from 'react'
import { cn } from '@/lib/utils'

// A row of Nixie tubes, one per character. A new text strikes in tube by tube.
export function Tubes({ text, className, label }: { text: string; className?: string; label: string }) {
  const chars = useMemo(() => Array.from(text), [text])
  return (
    <div className={cn('tubes', className)} role="img" aria-label={label}>
      <div key={text} className="tube-row tube-strike flex h-full justify-center gap-[3px]" style={{ "--len": Math.max(chars.length, 6) } as React.CSSProperties}>
        {chars.map((c, i) => (
          <span
            key={i}
            className={cn('tube', c === ' ' && 'is-space')}
            style={{ '--i': i } as React.CSSProperties}
          >
            <span className="tube-glyph">{c === ' ' ? ' ' : c}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
