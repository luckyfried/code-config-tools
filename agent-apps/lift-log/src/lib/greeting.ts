import { format } from "date-fns"

export function greeting(name: string, now = new Date()) {
  const h = now.getHours()
  const part = h < 5 ? "Late night" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"
  return name ? `${part}, ${name}` : part
}

/** The one line under the greeting: the date, or what the sample is. */
export const statusLine = (sample: boolean, now = new Date()) =>
  sample ? "Sample week. Log a set to start your own." : format(now, "EEEE, MMMM d")
