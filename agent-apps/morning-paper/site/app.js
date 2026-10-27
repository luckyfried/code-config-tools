// Morning Paper: sets the front page from feed.json and the inputs in config.js, then runs the press.
// The sample edition (inputs with "live": false, or ?demo=1) uses only files in this folder. A live edition reads
// the feed.json the run wrote and asks Wikipedia and Open-Meteo for the day's boxes and the weather.

const config = window.__APP_CONFIG__ ?? {};
const params = new URLSearchParams(location.search);
const sampleOnly = params.get("demo") === "1" || config.live !== true;
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
const $ = (id) => document.getElementById(id);

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

let storiesById = new Map();
let edition = null;
let indexBox = null;
let motto = "";

// ---------- small helpers ----------

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function slug(text) {
  return String(text).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "section";
}

function dayParts(day) {
  const [y, m, d] = day.split("-").map(Number);
  return { y, m, d, weekday: new Date(Date.UTC(y, m - 1, d)).getUTCDay() };
}

function longDate(day) {
  const { y, m, d, weekday } = dayParts(day);
  return `${DAYS[weekday]}, ${MONTHS[m - 1]} ${d}, ${y}`;
}

function dayOfYear(day) {
  const { y, m, d } = dayParts(day);
  return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(y, 0, 0)) / 86400000);
}

function roman(n) {
  const table = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"], [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
  let out = "";
  for (const [value, letters] of table) while (n >= value) { out += letters; n -= value; }
  return out || "I";
}

// "5:10 a.m.", "6 p.m.", "noon"; with the weekday when it is not the edition's day.
function clock(iso) {
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/.exec(iso ?? "");
  if (!m) return null;
  const hour = Number(m[2]);
  const minutes = m[3];
  let words;
  if (hour === 12 && minutes === "00") words = "noon";
  else if (hour === 0 && minutes === "00") words = "midnight";
  else {
    const h = hour % 12 || 12;
    const half = hour < 12 ? "a.m." : "p.m.";
    words = minutes === "00" ? `${h} ${half}` : `${h}:${minutes} ${half}`;
  }
  return { day: m[1], words };
}

function when(iso) {
  const t = clock(iso);
  if (!t) return "";
  if (!edition || t.day === edition.day) return t.words;
  return `${DAYS[dayParts(t.day).weekday]}, ${t.words}`;
}

// Shortens a summary to about `limit` characters, at the end of a sentence when one is near.
function clip(text, limit) {
  if (!text || text.length <= limit) return text;
  const cut = `${text.slice(0, limit).replace(/\s+\S*$/, "")} `;
  const end = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("? "), cut.lastIndexOf("! "), cut.lastIndexOf(".” "));
  return end > limit * 0.5 ? cut.slice(0, end + 1).replace(/\s+$/, "") : `${cut.trimEnd().replace(/[,;:]$/, "")}…`;
}

function listWords(items) {
  if (items.length <= 1) return items.join("");
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items.at(-1)}`;
}

function numberWords(n, one, many) {
  return `${n.toLocaleString("en-US")} ${n === 1 ? one : many}`;
}

async function getJSON(url, ms = 7000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    const response = await fetch(url, { signal: controller.signal, cache: "no-cache" });
    if (!response.ok) throw new Error(`${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------- the masthead ----------

function setMasthead() {
  const h1 = $("masthead");
  const text = (typeof config.masthead === "string" && config.masthead.trim()) || h1.textContent.trim();
  h1.textContent = "";
  const letters = el("span", "mast-letters");
  letters.setAttribute("aria-hidden", "true");
  [...text].forEach((ch, i) => {
    const letter = el("span", "mast-letter", ch);
    letter.style.setProperty("--i", String(i));
    letters.append(letter);
  });
  const measure = el("span", "mast-measure", text);
  measure.setAttribute("aria-hidden", "true");
  h1.append(el("span", "sr-only", text), letters, measure);
  if (typeof config.motto === "string") $("motto").textContent = config.motto;
  motto = $("motto").textContent.trim();
  $("motto").hidden = !motto;
  document.title = text;
  return { h1, measure, text };
}

// The masthead's size is the width of its box: measured once at 100px, set as a container-relative size.
function fitMasthead({ h1, measure }) {
  measure.style.setProperty("font-size", "100px");
  const width = measure.getBoundingClientRect().width;
  if (width > 0) h1.style.setProperty("--mast-fit", (10000 / width).toFixed(3));
  measure.remove();
}

// ---------- the weather ear ----------

const CLOUD = '<path class="wx-fill" d="M15 38h19.5a7.5 7.5 0 0 0 .6-15 10.5 10.5 0 0 0-20.1 2.6A6.2 6.2 0 0 0 15 38z"/>';
const GLYPHS = {
  sun: '<g class="wx-rays"><path d="M24 3.5v5.5M24 39v5.5M3.5 24H9M39 24h5.5M9.5 9.5l3.9 3.9M34.6 34.6l3.9 3.9M9.5 38.5l3.9-3.9M34.6 13.4l3.9-3.9"/></g><circle class="wx-fill" cx="24" cy="24" r="8.5"/>',
  moon: '<path class="wx-fill" d="M30.5 33.5A12.5 12.5 0 0 1 21 11a12.5 12.5 0 1 0 16 16 12.4 12.4 0 0 1-6.5 6.5z"/>',
  partly: `<g transform="translate(-6 -7) scale(.72)"><g class="wx-rays"><path d="M24 3.5v5.5M3.5 24H9M9.5 9.5l3.9 3.9M34.6 13.4l3.9-3.9M24 39v5.5M39 24h5.5"/></g><circle class="wx-fill" cx="24" cy="24" r="8.5"/></g><g class="wx-cloud">${CLOUD}</g>`,
  cloud: `<g class="wx-cloud">${CLOUD}</g>`,
  fog: '<g class="wx-fog"><line x1="8" y1="18" x2="40" y2="18"/><line x1="5" y1="25" x2="37" y2="25"/><line x1="10" y1="32" x2="42" y2="32"/></g>',
  rain: `<g transform="translate(0 -6)"><g class="wx-cloud">${CLOUD}</g></g><g><line class="wx-drop" x1="17" y1="37" x2="15" y2="42"/><line class="wx-drop" x1="25" y1="37" x2="23" y2="42"/><line class="wx-drop" x1="33" y1="37" x2="31" y2="42"/></g>`,
  snow: `<g transform="translate(0 -6)"><g class="wx-cloud">${CLOUD}</g></g><g><circle class="wx-drop" cx="16" cy="40" r="1.6" fill="currentColor"/><circle class="wx-drop" cx="24" cy="41" r="1.6" fill="currentColor"/><circle class="wx-drop" cx="32" cy="40" r="1.6" fill="currentColor"/></g>`,
  storm: `<g transform="translate(0 -6)"><g class="wx-cloud">${CLOUD}</g></g><path class="wx-bolt" d="M25 33l-5 8h5l-3 6" stroke-linejoin="round"/>`,
};

function weatherKind(code, isDay) {
  if (code === 0) return { glyph: isDay ? "sun" : "moon", words: isDay ? "Sunny" : "Clear" };
  if (code === 1) return { glyph: isDay ? "sun" : "moon", words: "Mostly clear" };
  if (code === 2) return { glyph: isDay ? "partly" : "cloud", words: "Partly cloudy" };
  if (code === 3) return { glyph: "cloud", words: "Overcast" };
  if (code === 45 || code === 48) return { glyph: "fog", words: "Fog" };
  if (code >= 51 && code <= 57) return { glyph: "rain", words: "Drizzle" };
  if (code >= 61 && code <= 67) return { glyph: "rain", words: code >= 65 ? "Heavy rain" : "Rain" };
  if (code >= 71 && code <= 77) return { glyph: "snow", words: "Snow" };
  if (code >= 80 && code <= 82) return { glyph: "rain", words: "Showers" };
  if (code === 85 || code === 86) return { glyph: "snow", words: "Snow showers" };
  if (code >= 95) return { glyph: "storm", words: "Thunderstorms" };
  return { glyph: "cloud", words: "Clouds" };
}

function renderWeather(w) {
  const ear = $("weather");
  ear.replaceChildren();
  const place = config.location?.name || w?.place || "";
  if (!w || typeof w.temperature !== "number") {
    ear.append(el("p", "ear-kicker", place || "Weather"), el("p", "ear-line", "No forecast this edition"));
    return;
  }
  const kind = weatherKind(w.code, w.isDay !== false);
  const box = el("div", "wx");
  const glyph = el("span", "wx-glyph");
  glyph.innerHTML = `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">${GLYPHS[kind.glyph]}</svg>`;
  const speed = (w.units ?? config.units) === "celsius" ? "km/h" : "mph";
  box.append(
    glyph,
    el("p", "wx-temp", `${Math.round(w.temperature)}°`),
    el("p", "wx-words", kind.words),
    el("p", "wx-more", `High ${Math.round(w.high)}°, low ${Math.round(w.low)}°`),
    el("p", "wx-more wx-wind", `Wind ${Math.round(w.wind)} ${speed}`),
  );
  const label = el("p", "sr-only", `Weather in ${place}: ${kind.words}, ${Math.round(w.temperature)} degrees.`);
  ear.append(el("p", "ear-kicker", place), box, label);
  ear.setAttribute("aria-label", `Weather in ${place}`);
}

async function liveWeather() {
  const loc = config.location;
  if (!loc || typeof loc.lat !== "number" || typeof loc.lon !== "number") return null;
  const celsius = config.units === "celsius";
  const url =
    "https://api.open-meteo.com/v1/forecast?" +
    new URLSearchParams({
      latitude: String(loc.lat),
      longitude: String(loc.lon),
      current: "temperature_2m,weather_code,wind_speed_10m,is_day",
      daily: "temperature_2m_max,temperature_2m_min",
      temperature_unit: celsius ? "celsius" : "fahrenheit",
      wind_speed_unit: celsius ? "kmh" : "mph",
      timezone: "auto",
      forecast_days: "1",
    });
  const data = await getJSON(url);
  return {
    place: loc.name ?? "",
    units: celsius ? "celsius" : "fahrenheit",
    code: data.current.weather_code,
    temperature: data.current.temperature_2m,
    high: data.daily.temperature_2m_max[0],
    low: data.daily.temperature_2m_min[0],
    wind: data.current.wind_speed_10m,
    isDay: data.current.is_day === 1,
  };
}

// ---------- Wikipedia's featured feed, in the page's own shape ----------

function trimWiki(raw, day) {
  const pick = (page) => page?.content_urls?.desktop?.page ?? null;
  const otd = (raw.onthisday ?? []).slice(0, 6).map((e) => ({ year: e.year, text: e.text, link: pick(e.pages?.[0]) }));
  const most = raw.mostread
    ? {
        date: String(raw.mostread.date ?? "").replace(/Z$/, ""),
        articles: raw.mostread.articles.slice(0, 6).map((a) => ({
          title: a.normalizedtitle ?? a.title,
          description: a.description ?? null,
          extract: a.extract ?? "",
          views: a.views ?? 0,
          link: pick(a),
        })),
      }
    : null;
  const im = raw.image;
  const picture = im?.thumbnail
    ? {
        src: im.thumbnail.source,
        width: im.image?.width ?? im.thumbnail.width,
        height: im.image?.height ?? im.thumbnail.height,
        caption: im.description?.text ?? "",
        credit: [im.artist?.text, im.license?.type].filter(Boolean).join(", ") + ", via Wikimedia Commons",
        link: im.file_page ?? null,
      }
    : null;
  return { date: day, onThisDay: otd, mostRead: most, picture };
}

async function liveWiki(day) {
  const { y, m, d } = dayParts(day);
  const path = `${y}/${String(m).padStart(2, "0")}/${String(d).padStart(2, "0")}`;
  return trimWiki(await getJSON(`https://api.wikimedia.org/feed/v1/wikipedia/en/featured/${path}`), day);
}

// ---------- stories ----------

function storyHref(story) {
  return `#story/${encodeURIComponent(story.id)}`;
}

function headline(story, tag, className) {
  const h = el(tag, `head ${className}`);
  const a = el("a", null, story.title);
  a.href = storyHref(story);
  h.append(a);
  return h;
}

function bylineFor(story) {
  const p = el("p", "byline");
  p.append(el("strong", null, story.source));
  const t = when(story.published);
  if (t) p.append(`, ${t}`);
  return p;
}

function photo(image, className, { eager = false } = {}) {
  const figure = el("figure", `photo ${className ?? ""}`.trim());
  const frame = el("div", "photo-frame");
  const img = el("img");
  img.src = image.src;
  img.alt = image.alt ?? "";
  if (image.width && image.height) {
    img.width = image.width;
    img.height = image.height;
  }
  img.decoding = "async";
  if (eager) img.fetchPriority = "high";
  else img.loading = "lazy";
  frame.append(img);
  figure.append(frame);
  if (image.caption || image.credit) {
    const cap = el("figcaption");
    if (image.caption) cap.append(`${image.caption} `);
    if (image.credit) cap.append(el("span", "credit", `Photograph: ${image.credit}`));
    figure.append(cap);
  }
  return figure;
}

function paragraphs(texts, className = "prose") {
  const div = el("div", className);
  for (const t of texts) if (t) div.append(el("p", null, t));
  return div;
}

// A quotation of a sensible length from the story's own text, and who said it when the text says.
function pullQuote(texts) {
  for (const t of texts) {
    const q = /[“"]([^”"]{36,170})[”"]/.exec(t);
    if (!q) continue;
    const quote = q[1].replace(/[,;:]\s*$/, ".");
    const who = /\bsaid ([A-Z][\w’'.-]+(?: [A-Z][\w’'.-]+){0,2})/.exec(t);
    return { quote, who: who ? who[1] : null };
  }
  return null;
}

function renderLead(story) {
  const art = el("article", "story lead");
  const top = el("div", "lead-top press");
  top.append(el("p", "kicker", story.section), headline(story, "h2", "lead-head"));
  const hasBody = Array.isArray(story.body) && story.body.length > 0;
  if (hasBody) top.append(el("p", "deck", clip(story.summary, 260)));
  art.append(top);
  if (story.image) {
    const pic = photo(story.image, "lead-photo press", { eager: true });
    pic.append(bylineFor(story));
    art.append(pic);
  } else top.append(bylineFor(story));
  const texts = hasBody ? story.body : [story.summary];
  const body = paragraphs(texts, "prose lead-body press");
  if (texts.join(" ").length < 420) body.classList.add("is-short");
  const pq = hasBody ? pullQuote(texts) : null;
  if (pq) {
    const block = el("blockquote", "pull", `“${pq.quote}”`);
    if (pq.who) block.append(el("cite", null, pq.who));
    body.children[0].after(block);
  }
  art.append(body);
  return art;
}

function renderSecond(story) {
  const art = el("article", "story press");
  art.append(el("p", "kicker", story.section), headline(story, "h2", "second-head"));
  if (story.image) art.append(photo(story.image));
  art.append(paragraphs(Array.isArray(story.body) && story.body.length ? story.body : [clip(story.summary, 420)]), bylineFor(story));
  return art;
}

function renderBandTop(story) {
  const art = el("article", `story band-top press${story.image ? "" : " has-no-photo"}`);
  art.append(headline(story, "h3", "band-head"));
  if (story.image) art.append(photo(story.image));
  art.append(paragraphs(Array.isArray(story.body) && story.body.length ? story.body : [clip(story.summary, 520)]), bylineFor(story));
  return art;
}

function renderBrief(story) {
  const art = el("article", "story brief press");
  art.append(headline(story, "h4", "brief-head"), paragraphs([clip(story.summary, 300)]), bylineFor(story));
  return art;
}

// ---------- boxes ----------

function box(title, className) {
  const section = el("section", `box press ${className}`);
  const head = el("h2", "box-head", title);
  head.id = `box-${slug(title)}`;
  section.setAttribute("aria-labelledby", head.id);
  section.append(head);
  return section;
}

function renderIndex(sections) {
  const section = box("Inside today", "index-box");
  const list = el("ul", "index-list");
  for (const s of sections) {
    const li = el("li");
    const a = el("a", null, s.name);
    a.href = `#section-${slug(s.name)}`;
    a.append(el("span", "index-count", String(s.stories.length)));
    li.append(a);
    list.append(li);
  }
  section.append(list);
  return section;
}

function renderOnThisDay(items) {
  const section = box("On this day", "otd");
  const list = el("ol", "otd-list");
  for (const item of items.slice(0, 6)) {
    const li = el("li");
    li.append(el("span", "otd-year", String(item.year)));
    if (item.link) {
      const a = el("a", null, item.text);
      a.href = item.link;
      a.target = "_blank";
      a.rel = "noopener";
      li.append(a);
    } else li.append(item.text);
    list.append(li);
  }
  section.append(list);
  return section;
}

function renderMostRead(most) {
  const section = box("Most read", "most-read");
  const [first, ...rest] = most.articles;
  const top = el("article", "top-read");
  const h = el("h3", "head top-read-title");
  const a = el("a", null, first.title);
  a.href = first.link;
  a.target = "_blank";
  a.rel = "noopener";
  h.append(a);
  top.append(h);
  if (first.description) top.append(el("p", "top-read-desc", first.description));
  top.append(paragraphs([first.extract]));
  const day = most.date ? longDate(most.date.slice(0, 10)) : null;
  top.append(el("p", "byline", `${numberWords(first.views, "reader", "readers")} on Wikipedia${day ? `, ${day.replace(/, \d{4}$/, "")}` : ""}`));
  section.append(top);
  const list = el("ol", "read-list");
  for (const r of rest.slice(0, 5)) {
    const li = el("li");
    const div = el("div");
    const link = el("a", null, r.title);
    link.href = r.link;
    link.target = "_blank";
    link.rel = "noopener";
    div.append(link, el("span", "read-views", numberWords(r.views, "reader", "readers")));
    li.append(div);
    list.append(li);
  }
  section.append(list);
  return section;
}

function renderPicture(picture) {
  const wrap = el("section", "potd press");
  wrap.setAttribute("aria-label", "Picture of the day");
  const fig = el("figure", "photo");
  const frame = el("div", "photo-frame");
  const img = el("img");
  img.src = picture.src;
  img.alt = picture.caption;
  img.width = picture.width;
  img.height = picture.height;
  img.loading = "lazy";
  img.decoding = "async";
  frame.append(img);
  const cap = el("figcaption");
  cap.append(el("span", "potd-label", "Picture of the day"));
  const text = el("span");
  text.append(`${picture.caption} `, el("span", "credit", `Photograph: ${picture.credit}`));
  cap.append(text);
  fig.append(frame, cap);
  wrap.append(fig);
  return wrap;
}

// ---------- the page ----------

function groupSections(stories) {
  const names = [];
  if (!sampleOnly && Array.isArray(config.sections)) for (const s of config.sections) if (s?.name) names.push(s.name);
  for (const s of stories) if (!names.includes(s.section)) names.push(s.section);
  return names.map((name) => ({ name, stories: stories.filter((s) => s.section === name) })).filter((s) => s.stories.length);
}

function renderPage(feed) {
  const stories = feed.stories ?? [];
  storiesById = new Map(stories.map((s) => [s.id, s]));
  const sections = groupSections(stories);
  const used = new Set();
  const take = (section) => {
    const s = section?.stories.find((x) => !used.has(x.id));
    if (s) used.add(s.id);
    return s;
  };

  const front = $("front");
  front.replaceChildren();
  const leadStory = take(sections[0]);
  const seconds = [take(sections[1]), take(sections[2])].filter(Boolean);

  const cellLead = el("div", "cell cell-lead");
  if (leadStory) cellLead.append(renderLead(leadStory));
  const cellLeft = el("div", "cell cell-left");
  const cellRight = el("div", "cell cell-right");
  const cellPotd = el("div", "cell cell-potd");
  const cellSecond = el("div", "cell cell-second");
  const stack = el("div", "second-stack");
  seconds.forEach((s) => stack.append(renderSecond(s)));
  cellSecond.append(stack);
  front.append(cellLead, cellLeft, cellRight, cellPotd, cellSecond);
  indexBox = renderIndex(sections);
  fillWikiBoxes(feed.wiki);

  const bands = $("sections");
  bands.replaceChildren();
  for (const section of sections) {
    const rest = section.stories.filter((s) => !used.has(s.id));
    if (!rest.length) continue;
    const band = el("section", "band");
    band.id = `section-${slug(section.name)}`;
    const flag = el("div", "band-flag press");
    const name = el("h2", "band-name", section.name);
    name.id = `band-${slug(section.name)}`;
    band.setAttribute("aria-labelledby", name.id);
    const sources = [...new Set(section.stories.map((s) => s.source))];
    flag.append(name, el("p", "band-sources", `From ${listWords(sources)}`));
    const grid = el("div", "band-grid");
    const [top, ...briefs] = rest;
    grid.append(renderBandTop(top));
    if (briefs.length) {
      const col = el("div", `band-briefs${briefs.length <= 3 ? " is-few" : ""}`);
      briefs.forEach((s) => col.append(renderBrief(s)));
      grid.append(col);
    }
    band.append(flag, grid);
    bands.append(band);
  }

  const sourceCount = new Set(stories.map((s) => s.source)).size;
  $("edition-count").textContent = `${numberWords(stories.length, "story", "stories")} from ${numberWords(sourceCount, "source", "sources")}`;
}

// Fills the left rail's On this day, the right rail's Most read, and the picture; a missing box gives its place
// to a story so no cell stands empty.
function fillWikiBoxes(wiki) {
  const left = document.querySelector(".cell-left");
  const right = document.querySelector(".cell-right");
  const potd = document.querySelector(".cell-potd");
  if (!left || !right || !potd) return;
  left.replaceChildren();
  if (wiki?.onThisDay?.length) left.append(renderOnThisDay(wiki.onThisDay));
  right.replaceChildren();
  if (wiki?.mostRead?.articles?.length) right.append(renderMostRead(wiki.mostRead));
  else {
    const spare = [...storiesById.values()].filter((s) => !document.querySelector(`[href="${CSS.escape(storyHref(s))}"]`)).slice(0, 3);
    const extra = box("Also today", "also");
    spare.forEach((s) => extra.append(renderBrief(s)));
    right.append(extra);
  }
  if (indexBox) (left.childElementCount ? right : left).append(indexBox);
  potd.replaceChildren();
  if (wiki?.picture) potd.append(renderPicture(wiki.picture));
  else {
    const pictured = [...storiesById.values()].find((s) => s.image && !document.querySelector(`.lead [href="${CSS.escape(storyHref(s))}"]`));
    if (pictured) {
      const art = el("article", "story potd press");
      art.append(photo(pictured.image), headline(pictured, "h2", "second-head"));
      potd.append(art);
    }
  }
}

function renderColophon(feed) {
  const foot = $("colophon");
  foot.replaceChildren();
  const wiki = el("a", null, "Wikipedia");
  wiki.href = "https://en.wikipedia.org/wiki/Main_Page";
  wiki.target = "_blank";
  wiki.rel = "noopener";
  foot.append("Set in Fraunces and Libre Franklin. On this day, Most read, and the picture of the day from ", wiki);
  if (feed.edition === "sample") foot.append(`, ${longDate(feed.wiki?.date ?? feed.day)}.`);
  else {
    const meteo = el("a", null, "Open-Meteo");
    meteo.href = "https://open-meteo.com/";
    meteo.target = "_blank";
    meteo.rel = "noopener";
    foot.append("; weather from ", meteo, ".");
  }
}

function renderDateline(feed) {
  const day = feed.day;
  const t = $("dateline");
  t.dateTime = day;
  t.textContent = longDate(day);
  const { y } = dayParts(day);
  $("volume").textContent = `Vol. ${roman(Math.max(1, y - 2025))}, No. ${dayOfYear(day)}`;
  const set = clock(feed.setAt);
  $("set-at").textContent = set ? `Set at ${set.words}` : "";
  $("edition-status").textContent = feed.edition === "sample" ? "Sample edition" : "";
  $("edition-status").hidden = feed.edition !== "sample";
  updateEditionLabel();
}

// The motto follows the edition on show: "morning" reads "evening" under the Evening Edition ear, and back.
function updateEditionLabel() {
  const label = getComputedStyle(document.documentElement).getPropertyValue("--edition-label").trim().replace(/^["']|["']$/g, "");
  if (label) $("edition-label").textContent = label;
  const evening = /evening/i.test(label);
  $("motto").textContent = evening ? motto.replace(/\bmorning(s?)\b/gi, (word, s) => (word[0] === "M" ? "Evening" : "evening") + s) : motto;
}

// ---------- the story view ----------

const dialog = $("story-view");

function openStory(id) {
  const story = storiesById.get(id);
  if (!story) return false;
  $("clipping-kicker").textContent = story.section;
  $("clipping-title").textContent = story.title;
  const by = bylineFor(story);
  $("clipping-byline").replaceChildren(...by.childNodes);
  const ph = $("clipping-photo");
  ph.replaceChildren();
  if (story.image) ph.append(photo(story.image, null, { eager: true }));
  const texts = Array.isArray(story.body) && story.body.length ? story.body : [story.summary];
  $("clipping-body").replaceChildren(...texts.map((t) => el("p", null, t)));
  const link = $("clipping-link");
  link.replaceChildren();
  if (story.link) {
    const a = el("a", null, `Read the full story at ${story.source}`);
    a.href = story.link;
    a.target = "_blank";
    a.rel = "noopener";
    link.append(a);
  } else link.append("This story ships with the sample edition.");
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop = 0;
  return true;
}

function route() {
  const m = /^#story\/(.+)$/.exec(location.hash);
  if (m && openStory(decodeURIComponent(m[1]))) return;
  if (dialog.open) dialog.close();
}

dialog.addEventListener("close", () => {
  if (location.hash.startsWith("#story/")) history.replaceState(null, "", location.pathname + location.search);
});
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});
$("clipping-close").addEventListener("click", () => dialog.close());
addEventListener("hashchange", route);

// ---------- the press ----------

function ink(block, delay) {
  block.style.setProperty("--press-delay", `${Math.round(delay)}ms`);
  block.classList.add("is-inking");
}

// The front page's columns on the first screen ink one after another, left to right and down each column, at
// fixed times from the page's start so a slow load never runs them before they can be seen.
const COLUMNS_AT = 550;
const COLUMN_STEP = 230;
const COLUMN_REVEAL = 600; // ms for the edge to cross the part of a block that is on screen
const BAND = 140;

function runPress() {
  const root = document.documentElement;
  if (reduceMotion.matches) {
    root.classList.remove("is-pressing");
    return;
  }
  const vh = innerHeight;
  const vw = innerWidth;
  const now = performance.now();
  const columns = [...document.querySelectorAll(".front .press")]
    .map((block) => ({ block, r: block.getBoundingClientRect() }))
    .filter(({ r }) => r.bottom > 0 && r.top < vh && r.height > 0)
    .sort((a, b) => Math.round(a.r.left / 40) - Math.round(b.r.left / 40) || a.r.top - b.r.top);
  columns.forEach(({ block, r }, i) => {
    const seen = Math.min(r.bottom, vh) - Math.max(r.top, 0);
    block.style.setProperty("--press-dur", `${Math.round((COLUMN_REVEAL * (r.height + BAND)) / (seen + BAND))}ms`);
    block.addEventListener("animationend", (event) => {
      if (event.animationName === "press-wipe") block.classList.add("is-printed");
    });
    ink(block, Math.max(0, COLUMNS_AT + i * COLUMN_STEP - now));
  });
  const later = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        later.unobserve(entry.target);
        ink(entry.target, 40 + (entry.boundingClientRect.left / vw) * 320);
      }
    },
    { rootMargin: "0px 0px -8% 0px" },
  );
  for (const block of document.querySelectorAll(".press:not(.is-inking)")) {
    const r = block.getBoundingClientRect();
    block.style.setProperty("--press-dur", `${Math.round(Math.min(1500, Math.max(900, 720 + r.height * 0.5)))}ms`);
    block.addEventListener("animationend", (event) => {
      if (event.animationName === "press-wipe") block.classList.add("is-printed");
    });
    if (r.bottom > 0 && r.top < vh) ink(block, 140 + (Math.max(0, r.top) / vh) * 1350 + (r.left / vw) * 460);
    else later.observe(block);
  }
}

function finishPress() {
  for (const block of document.querySelectorAll(".press")) block.classList.add("is-printed");
  $("masthead").classList.remove("is-waiting");
}

addEventListener("beforeprint", finishPress);
$("print").addEventListener("click", () => {
  finishPress();
  print();
});

// The weather glyph loops only while it is on screen.
new IntersectionObserver((entries) => {
  for (const entry of entries) entry.target.classList.toggle("is-offscreen", !entry.isIntersecting);
}).observe($("weather"));

matchMedia("(prefers-color-scheme: dark)").addEventListener("change", updateEditionLabel);

// ---------- start ----------

async function loadEdition() {
  if (!sampleOnly) {
    try {
      return await getJSON("./feed.json");
    } catch {
      // A page served without a run of its own falls back to the sample edition.
    }
  }
  const feed = await getJSON("./sample/feed.json");
  feed.edition = "sample";
  return feed;
}

async function start() {
  const mast = setMasthead();
  updateEditionLabel();
  const fontsReady = Promise.race([
    Promise.all([document.fonts.load(`900 100px Fraunces`, mast.text), document.fonts.load(`400 16px Fraunces`), document.fonts.load(`600 13px "Libre Franklin"`)]),
    wait(1200),
  ]);
  const feedReady = loadEdition();
  await fontsReady;
  fitMasthead(mast);
  mast.h1.classList.remove("is-waiting");

  edition = await feedReady;
  renderDateline(edition);
  renderWeather(edition.weather);
  renderPage(edition);
  renderColophon(edition);
  await document.fonts.ready;
  runPress();
  route();

  if (edition.edition !== "sample") {
    liveWeather().then((w) => w && renderWeather(w)).catch(() => {});
    liveWiki(edition.day)
      .then((wiki) => {
        const merged = { ...wiki, mostRead: wiki.mostRead ?? edition.wiki?.mostRead ?? null };
        fillWikiBoxes(merged);
        for (const block of document.querySelectorAll(".cell .press:not(.is-inking)")) block.classList.add("is-printed");
      })
      .catch(() => {});
  }
}

start();
