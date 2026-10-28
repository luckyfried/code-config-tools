// The card for one day: its date, its count, and the commit subjects. It sits in a column beside the heat map on a
// wide screen, floats over it where there is a pointer and less room, and sits under it on a phone.
import { DATA, el, longDay, fmt, plural, shortName, authorColor, docked, sideQuery, clamp, setVars } from "./util.js";

const tagByDay = new Map(DATA.tags.map(([name, day]) => [day, name]));

export function createDayCard(panel, heat) {
  const card = panel.querySelector(".daycard");
  card.setAttribute("aria-live", "polite");
  let shown = -1;
  let open = false;

  function fill(i) {
    const count = DATA.days[i];
    const subjects = DATA.subjects[String(i)] || [];
    const head = el("div", "dc-head");
    const when = el("div", "dc-when");
    when.append(el("p", "dc-date", longDay(i)));
    const flags = [];
    if (i === DATA.busiest) flags.push(["is-busy", "Busiest day of the year"]);
    if (tagByDay.has(i)) flags.push(["is-release", `Released ${tagByDay.get(i)}`]);
    if (flags.length) {
      const row = el("p", "dc-flags");
      for (const [cls, text] of flags) row.append(el("span", `dc-flag ${cls}`, text));
      when.append(row);
    }
    const tally = el("p", "dc-count");
    const num = el("span", "dc-num", fmt(count));
    tally.append(num, el("span", "dc-unit", count === 1 ? "commit" : "commits"));
    head.append(when, tally);

    const parts = [head];
    if (count === 0) {
      parts.push(el("p", "dc-empty", "Nothing was committed this day."));
    } else {
      const list = el("ol", "dc-list");
      for (const [sha, who, subject] of subjects) {
        const item = el("li", "dc-item");
        const dot = el("span", "dc-dot");
        dot.style.setProperty("--c", authorColor(who));
        const text = el("span", "dc-subject", subject);
        text.title = subject;
        const meta = el("span", "dc-meta");
        meta.append(el("span", "dc-sha", sha), el("span", "dc-who", shortName(DATA.authors[who].n)));
        item.append(dot, text, meta);
        list.append(item);
      }
      parts.push(list);
      const more = el("p", "dc-more");
      const tellMore = () => {
        const rest = count - list.children.length;
        more.textContent = rest > 0 ? `${plural(rest, "more commit")} that day` : "";
        more.hidden = rest <= 0;
      };
      tellMore();
      parts.push(more);
      card.replaceChildren(...parts);
      // The side column is as tall as the map: the list keeps the commits that fit whole and counts the rest.
      if (sideQuery.matches) {
        while (list.children.length > 1 && card.scrollHeight > card.clientHeight + 1) {
          list.lastElementChild.remove();
          tellMore();
        }
      }
    }
    if (count === 0) card.replaceChildren(...parts);
    card.dataset.day = i;
  }

  function place(i) {
    if (docked()) return;
    const cell = heat.cellRect(i);
    if (!cell) return;
    const box = panel.getBoundingClientRect();
    const w = card.offsetWidth;
    const h = card.offsetHeight;
    const cx = cell.left - box.left + cell.width / 2;
    const above = cell.top - box.top - h - 14;
    const below = cell.bottom - box.top + 14;
    const y = above >= 8 ? above : below;
    const x = clamp(cx - w / 2, 12, box.width - w - 12);
    setVars(card, {
      "--cx": `${Math.round(x)}px`,
      "--cy": `${Math.round(y)}px`,
      "--ox": `${Math.round(clamp(cx - x, 16, w - 16))}px`,
      "--oy": above >= 8 ? "100%" : "0%",
    });
    card.classList.toggle("is-below", above < 8);
  }

  function show(i) {
    if (i === shown && open) return;
    const wasOpen = open;
    fill(i);
    if (!wasOpen) card.classList.add("no-glide");
    place(i);
    if (!wasOpen) {
      // The first frame lands at the cell; later moves glide between cells.
      card.getBoundingClientRect();
      card.classList.remove("no-glide");
    }
    card.classList.add("is-open");
    shown = i;
    open = true;
    heat.setActive(i);
  }

  function hide() {
    open = false;
    card.classList.remove("is-open");
    heat.clearActive();
    if (docked()) show(DATA.busiest);
  }

  // A phone always shows a day under the map: the busiest one until another is tapped.
  function rest() {
    if (docked()) {
      fill(shown >= 0 ? shown : DATA.busiest);
      card.classList.add("is-open");
      heat.setActive(shown >= 0 ? shown : DATA.busiest);
      open = true;
    } else if (open && shown >= 0) {
      place(shown);
    }
  }

  return {
    show,
    hide,
    rest,
    get open() {
      return open;
    },
    get day() {
      return shown;
    },
  };
}
