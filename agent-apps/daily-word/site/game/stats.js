// Everything the game keeps lives in this browser's localStorage under "daily-word:" and is never sent anywhere.

const PREFIX = "daily-word:";

export function load(key, fallback) {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw ? { ...fallback, ...JSON.parse(raw) } : { ...fallback };
  } catch {
    return { ...fallback };
  }
}

export function save(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // A full or blocked store keeps the game playable; it just forgets on reload.
  }
}

const EMPTY = { played: 0, wins: 0, streak: 0, best: 0, dist: [0, 0, 0, 0, 0, 0], lastDay: 0, lastWonDay: 0 };

/** The daily stats, with the streak shown as broken when a day was missed since the last win. */
export function readStats(today) {
  const stats = load("stats", EMPTY);
  stats.dist = Array.isArray(stats.dist) && stats.dist.length === 6 ? stats.dist : [...EMPTY.dist];
  if (stats.streak > 0 && stats.lastWonDay < today - 1) stats.streak = 0;
  return stats;
}

/** Records one finished daily game, once per day. */
export function recordDaily(today, won, tries) {
  const stats = readStats(today);
  if (stats.lastDay === today) return stats;
  stats.played += 1;
  stats.lastDay = today;
  if (won) {
    stats.wins += 1;
    stats.dist[tries - 1] += 1;
    stats.streak = stats.lastWonDay === today - 1 ? stats.streak + 1 : 1;
    stats.lastWonDay = today;
    stats.best = Math.max(stats.best, stats.streak);
  } else {
    stats.streak = 0;
  }
  save("stats", stats);
  return stats;
}

export function winRate(stats) {
  return stats.played ? Math.round((stats.wins / stats.played) * 100) : 0;
}
