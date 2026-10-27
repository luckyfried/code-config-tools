export const CATEGORIES = ["top", "bottom", "dress", "layer", "shoes", "bag", "accessory"] as const
export type Category = (typeof CATEGORIES)[number]

export const SEASONS = ["spring", "summer", "fall", "winter"] as const
export type Season = (typeof SEASONS)[number]

/** One garment. `worn` lists the days it was worn that the closet knows of, oldest first. */
export interface Item {
  id: string
  name: string
  category: Category
  color: string
  price: number | null
  brand: string
  seasons: Season[]
  wears: number
  worn: string[]
  /** The day the item joined the closet; the Dusty clock starts here for an item never worn. */
  since: string
  /** The day the person chose Keep on the Dusty shelf; the clock restarts from it. */
  keptOn: string | null
}

/** One outfit: a slot name to the id of the item in it, or null for an empty slot. */
export interface Outfit {
  id: string
  name: string
  items: Record<string, string | null>
  wears: number
  worn: string[]
}

export interface GivenAway {
  id: string
  name: string
  on: string
}

export interface Closet {
  items: Item[]
  outfits: Outfit[]
  given: GivenAway[]
  /** The season's capsule as item ids; a season with no entry holds every item tagged with it. */
  capsule: Partial<Record<Season, string[]>>
  currency: string
  /** Ids from the starting closet already brought in, so a new run adds only what is new. */
  seededItems: string[]
  seededOutfits: string[]
}
