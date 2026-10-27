// The headline number: every digit a strip of 0 to 9 that rolls to its place when the number changes.
export function createRoll(root) {
  let shape = null;
  let strips = [];

  function build(text) {
    root.textContent = "";
    strips = [];
    for (const ch of text) {
      if (/\d/.test(ch)) {
        const digit = document.createElement("span");
        digit.className = "roll-digit";
        const strip = document.createElement("span");
        strip.className = "roll-strip";
        for (let n = 0; n < 10; n += 1) {
          const face = document.createElement("span");
          face.textContent = String(n);
          strip.appendChild(face);
        }
        digit.appendChild(strip);
        root.appendChild(digit);
        strips.push(strip);
      } else {
        const char = document.createElement("span");
        char.className = "roll-char";
        char.textContent = ch;
        root.appendChild(char);
      }
    }
  }

  const put = (strip, d) => {
    strip.dataset.d = String(d);
    strip.style.setProperty("--d", String(d));
  };

  return {
    /** Shows `text`; each digit rolls over `ms` milliseconds on the `ease` curve. */
    set(text, ms, ease = "var(--ease-out)") {
      root.style.setProperty("--roll-ms", `${Math.max(0, ms)}ms`);
      root.style.setProperty("--roll-ease", ease);
      const nextShape = text.replace(/\d/g, "0");
      const digits = [...text].filter((ch) => /\d/.test(ch)).map(Number);
      if (nextShape !== shape) {
        const previous = strips.map((strip) => Number(strip.dataset.d || 0));
        build(text);
        const offset = strips.length - previous.length;
        strips.forEach((strip, k) => put(strip, k - offset >= 0 ? previous[k - offset] : 0));
        shape = nextShape;
        void root.offsetWidth;
      }
      strips.forEach((strip, k) => put(strip, digits[k]));
    },
  };
}
