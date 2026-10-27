// Runs before the first paint: puts back the theme picked in Settings on this device, so the page never flashes another one.
(function () {
  try {
    var prefs = JSON.parse(localStorage.getItem("habit-rings:prefs") || "{}");
    var name = prefs.theme;
    if (name === "auto" || name === "ink" || name === "paper" || name === "neon") {
      var link = document.createElement("link");
      link.rel = "stylesheet";
      link.id = "theme-pick";
      link.href = "./themes/" + name + ".css";
      link.setAttribute("blocking", "render");
      document.head.appendChild(link);
    }
  } catch (error) {
    // Storage can be off; the theme then follows the inputs.
  }
})();
