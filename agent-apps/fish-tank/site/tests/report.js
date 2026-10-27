// Writes each check to the page and the console, and sets the verdict line to pass or fail.
export function createReport() {
  const list = document.getElementById("results");
  let failed = 0;
  return {
    check(name, ok, detail = "") {
      const li = document.createElement("li");
      li.className = ok ? "is-pass" : "is-fail";
      li.textContent = `${ok ? "pass" : "fail"}: ${name}${detail ? ` (${detail})` : ""}`;
      list.append(li);
      if (!ok) failed++;
      console.log(li.textContent);
    },
    done() {
      const v = document.getElementById("verdict");
      v.textContent = failed ? `${failed} failed` : "All checks pass";
      v.className = `verdict ${failed ? "is-fail" : "is-pass"}`;
      document.body.dataset.result = failed ? "fail" : "pass";
    },
  };
}
