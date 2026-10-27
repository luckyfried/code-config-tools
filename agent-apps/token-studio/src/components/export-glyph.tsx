/** A page dropping into a tray; each new `run` plays the drop once. */
export function ExportGlyph({ run }: { run: number }) {
  return (
    <span className="export-glyph" data-icon="inline-start" aria-hidden="true">
      <svg viewBox="0 0 20 20" className="export-file size-full" key={run} data-run={run > 0 ? "" : undefined}>
        <path d="M6 2.75h5.25L14.5 6v7.25H6z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M11 2.75V6.25h3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      </svg>
      <svg viewBox="0 0 20 20" className="export-tray size-full" key={`t${run}`} data-run={run > 0 ? "" : undefined}>
        <path d="M3 13.5v2.25c0 .7.55 1.25 1.25 1.25h11.5c.7 0 1.25-.55 1.25-1.25V13.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    </span>
  )
}
