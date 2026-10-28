// A book's size from its page count: height and depth vary a little per title, thickness follows the pages.
import { hash, rng } from "./textures.js";

export function bookDims(book) {
  const r = rng(hash(book.id));
  const h = 0.198 + r() * 0.046;
  const d = h * (0.64 + r() * 0.05);
  const pages = book.pages || 300;
  const t = Math.min(0.075, Math.max(0.02, 0.016 + pages * 0.000058));
  return { t, h, d };
}
