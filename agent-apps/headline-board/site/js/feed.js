// Where the headlines come from: the snapshot the run wrote (feed.json), the sample board that ships with the page,
// and, once the board has been up a while, a fresh read of Wikipedia, Hacker News, and the weather from the browser.

const AGENT = "HeadlineBoard/1.0 (a Code Config agent app; https://code-config.com)";
const FIRST_REFRESH_MS = 90_000;
const REFRESH_MS = 10 * 60_000;

async function json(url, headers = {}) {
  const response = await fetch(url, { headers, cache: "no-store" });
  if (!response.ok) throw new Error(`${url} answered ${response.status}`);
  return response.json();
}

export async function loadFeed({ demo }) {
  if (!demo) {
    try {
      const feed = await json("./feed.json");
      if (feed.sources?.some((source) => source.items?.length)) return { ...feed, sample: false };
    } catch {
      // No snapshot yet: the sample board stands in.
    }
  }
  const sample = await json("./feed.sample.json");
  return { ...sample, sample: true };
}

// Mixes the sources so each page carries several of them, newest first within each.
export function interleave(feed, sources) {
  const order = new Map(sources.map((source, index) => [typeof source === "string" ? source : source.url, index]));
  const feeds = [...(feed.sources || [])]
    .filter((source) => source.items?.length)
    .sort((a, b) => (order.get(a.id) ?? 99) - (order.get(b.id) ?? 99));
  const tones = new Map(feeds.map((source, index) => [source.id, (index % 6) + 1]));
  const items = [];
  const longest = Math.max(0, ...feeds.map((source) => source.items.length));
  for (let index = 0; index < longest; index += 1) {
    for (const source of feeds) {
      const item = source.items[index];
      if (item) items.push({ ...item, tag: source.tag, source: source.name, tone: tones.get(source.id) });
    }
  }
  return items;
}

// Wikipedia's stories arrive as HTML; an inert parsed document gives their text without running or loading anything.
function clean(text) {
  const page = new DOMParser().parseFromString(text || "", "text/html");
  return (page.body.textContent || "").replace(/\s+/g, " ").trim();
}

async function wikipedia() {
  const day = new Date();
  const path = `${day.getUTCFullYear()}/${String(day.getUTCMonth() + 1).padStart(2, "0")}/${String(day.getUTCDate()).padStart(2, "0")}`;
  const data = await json(`https://en.wikipedia.org/api/rest_v1/feed/featured/${path}`, { "Api-User-Agent": AGENT });
  const items = [];
  for (const story of (data.news || []).slice(0, 8)) {
    const page = story.links?.[0]?.content_urls?.desktop?.page || "https://en.wikipedia.org/wiki/Portal:Current_events";
    const title = clean(story.story);
    if (title) items.push({ title, url: page, time: null, label: "TODAY" });
  }
  (data.mostread?.articles || []).slice(0, 5).forEach((article, index) => {
    const name = clean(article.titles?.normalized || article.title?.replace(/_/g, " "));
    const about = clean(article.description);
    const page = article.content_urls?.desktop?.page;
    if (name && page) items.push({ title: about ? `${name}: ${about}` : name, url: page, time: null, label: `TOP${index + 1}` });
  });
  if (!items.length) throw new Error("Wikipedia had no stories");
  return { id: "wikipedia", name: "Wikipedia", tag: "WIKI", items };
}

async function hackernews() {
  const ids = (await json("https://hacker-news.firebaseio.com/v0/topstories.json")).slice(0, 30);
  const stories = await Promise.all(ids.map((id) => json(`https://hacker-news.firebaseio.com/v0/item/${id}.json`).catch(() => null)));
  const items = stories
    .filter((story) => story?.title)
    .map((story) => ({
      title: story.title,
      url: story.url || `https://news.ycombinator.com/item?id=${story.id}`,
      time: story.time ? new Date(story.time * 1000).toISOString() : null,
    }));
  if (!items.length) throw new Error("Hacker News had no stories");
  return { id: "hackernews", name: "Hacker News", tag: "HN", items };
}

async function weather(place) {
  const query = new URLSearchParams({
    latitude: place.lat,
    longitude: place.lon,
    current: "temperature_2m,weather_code,is_day",
    daily: "temperature_2m_max,temperature_2m_min",
    timezone: "auto",
    forecast_days: "1",
  });
  const data = await json(`https://api.open-meteo.com/v1/forecast?${query}`);
  return {
    temp: data.current?.temperature_2m,
    code: data.current?.weather_code,
    day: Boolean(data.current?.is_day ?? 1),
    high: data.daily?.temperature_2m_max?.[0],
    low: data.daily?.temperature_2m_min?.[0],
    place: place.name || "",
  };
}

// Reads the live sources again after the board has been up a while, then every ten minutes. A source that does not
// answer keeps the snapshot's rows.
export function keepFresh(config, feed, onChange) {
  if (feed.sample) return;
  const names = (config.sources || []).map((source) => (typeof source === "string" ? source : source.url));
  const live = [];
  if (names.includes("wikipedia")) live.push(wikipedia);
  if (names.includes("hackernews")) live.push(hackernews);
  const refresh = async () => {
    const results = await Promise.allSettled(live.map((read) => read()));
    let changed = false;
    for (const result of results) {
      if (result.status !== "fulfilled") continue;
      const fresh = result.value;
      const others = (feed.sources || []).filter((source) => source.id !== fresh.id);
      feed.sources = [...others, fresh];
      changed = true;
    }
    if (config.location) {
      try {
        feed.weather = await weather(config.location);
        changed = true;
      } catch {
        // The last weather line stays up.
      }
    }
    if (changed) onChange(feed);
    setTimeout(refresh, REFRESH_MS);
  };
  setTimeout(refresh, FIRST_REFRESH_MS);
}

const SKY = [
  [[0], "CLEAR", "CLEAR"],
  [[1], "MOSTLY SUNNY", "MOSTLY CLEAR"],
  [[2], "PARTLY CLOUDY", "PARTLY CLOUDY"],
  [[3], "OVERCAST", "OVERCAST"],
  [[45, 48], "FOG", "FOG"],
  [[51, 53, 55, 56, 57], "DRIZZLE", "DRIZZLE"],
  [[61, 63, 66, 80, 81], "RAIN", "RAIN"],
  [[65, 67, 82], "HEAVY RAIN", "HEAVY RAIN"],
  [[71, 73, 77, 85], "SNOW", "SNOW"],
  [[75, 86], "HEAVY SNOW", "HEAVY SNOW"],
  [[95, 96, 99], "THUNDER", "THUNDER"],
];

export function sky(code, day) {
  const match = SKY.find(([codes]) => codes.includes(code));
  return match ? (day ? match[1] : match[2]) : "";
}

// Fahrenheit where people read it, Celsius everywhere else.
export function fahrenheit() {
  const region = (navigator.language || "en-US").split("-")[1] || "";
  return ["US", "LR", "MM", "BS", "BZ", "KY", "PW"].includes(region.toUpperCase());
}
