const KNOWN: Record<string, number> = {
  italian: 1, spanish: 1, mexican: 1,
  greek: 2, mediterranean: 2, "middle eastern": 2, lebanese: 2,
  indian: 3, "sri lankan": 3, moroccan: 3,
  japanese: 4, korean: 4, nordic: 4,
  french: 5, british: 5, irish: 5,
  thai: 6, vietnamese: 6, chinese: 6,
  american: 7, baking: 7, southern: 7,
  german: 8, persian: 8, caribbean: 8,
}

/** The card edge's tint: a theme variable picked by cuisine, the same every time. */
export function cuisineTint(cuisine: string) {
  const key = cuisine.trim().toLowerCase()
  let index = KNOWN[key]
  if (!index) {
    let hash = 0
    for (const char of key) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
    index = (hash % 8) + 1
  }
  return `var(--tint-${index})`
}
