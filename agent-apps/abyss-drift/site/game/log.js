// The creature log and the best dive, kept in this browser's storage under the app's own prefix. Nothing leaves the device.

const KEY = "abyss-drift:log";

function blank() {
  return { species: {}, dives: 0, best: null };
}

export function loadLog() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return blank();
    const data = JSON.parse(raw);
    return { ...blank(), ...data, species: data.species || {} };
  } catch {
    return blank();
  }
}

export function saveLog(log) {
  try {
    localStorage.setItem(KEY, JSON.stringify(log));
  } catch {
    // Storage full or blocked: the log lives for this visit only.
  }
}

/** Keeps a photo in the log when it beats the species' best. Answers whether it did. */
export function recordPhoto(log, photo) {
  const prev = log.species[photo.species];
  if (prev && prev.stars >= photo.stars) return false;
  log.species[photo.species] = { stars: photo.stars, depth: photo.depth, date: photo.date, thumb: photo.thumb };
  saveLog(log);
  return true;
}

/** Records a finished dive and answers whether it is the new best (most species, then most stars). */
export function recordDive(log, dive) {
  log.dives += 1;
  const better = !log.best || dive.species > log.best.species || (dive.species === log.best.species && dive.stars > log.best.stars);
  if (better) log.best = dive;
  saveLog(log);
  return better;
}
