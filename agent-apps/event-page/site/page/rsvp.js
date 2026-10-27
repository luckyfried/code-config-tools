// The reply form: the answer, names, how many, and a note become a filled text or email to the hosts. The draft is
// kept on this device, so a reload keeps what the guest typed.
import { load, save } from "./state.js";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
  "November", "December"];

export function setUpReply(doc, config) {
  const form = doc.querySelector("[data-rsvp]");
  if (!form) return;
  const count = form.querySelector("[data-count]");
  const minus = form.querySelector('[data-step="-1"]');
  const plus = form.querySelector('[data-step="1"]');
  const sms = form.querySelector('[data-send="sms"]');
  const email = form.querySelector('[data-send="email"]');
  const hosts = config.names.join(" & ");
  const when = new Date(config.date);
  const day = `${MONTHS[when.getMonth()]} ${when.getDate()}`;

  const draft = { answer: "yes", names: "", count: 2, note: "", ...(load().rsvp || {}) };
  form.elements.answer.value = draft.answer;
  form.elements.names.value = draft.names;
  form.elements.note.value = draft.note;

  const message = () => {
    const who = draft.names.trim() || "a guest";
    const lines = draft.answer === "yes"
      ? [`Hi ${hosts}! This is ${who}. We'll be there on ${day}, ${draft.count} of us.`]
      : [`Hi ${hosts}! This is ${who}. We're so sorry, we can't make it on ${day}.`];
    if (draft.note.trim()) lines.push("", draft.note.trim());
    return lines.join("\n");
  };

  const render = () => {
    count.textContent = String(draft.count);
    minus.disabled = draft.count <= 1;
    plus.disabled = draft.count >= 12;
    form.classList.toggle("is-no", draft.answer === "no");
    const body = encodeURIComponent(message());
    if (sms) sms.href = `sms:${config.rsvp.phone.replace(/[^\d+]/g, "")}?&body=${body}`;
    if (email) {
      const subject = encodeURIComponent(`${draft.answer === "yes" ? "Yes" : "No"} from ${draft.names.trim() || "a guest"}`);
      email.href = `mailto:${config.rsvp.email}?subject=${subject}&body=${body}`;
    }
  };

  const keep = () => {
    save({ rsvp: draft });
    render();
  };
  form.addEventListener("input", () => {
    draft.answer = form.elements.answer.value;
    draft.names = form.elements.names.value;
    draft.note = form.elements.note.value;
    keep();
  });
  for (const btn of [minus, plus]) {
    btn.addEventListener("click", () => {
      draft.count = Math.min(12, Math.max(1, draft.count + Number(btn.dataset.step)));
      keep();
    });
  }
  form.addEventListener("submit", (e) => e.preventDefault());
  render();
}
