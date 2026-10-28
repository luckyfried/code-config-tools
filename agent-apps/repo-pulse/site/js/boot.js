// Applies a saved light or dark choice before the first paint, so the page never flashes the other one.
(function () {
  try {
    var saved = localStorage.getItem("repo-pulse:theme");
    var config = window.__APP_CONFIG__ || {};
    if ((saved === "light" || saved === "dark") && (!config.theme || config.theme === "auto")) {
      document.documentElement.setAttribute("data-theme", saved);
    }
  } catch (e) {
    // Storage can be off; the device's setting decides.
  }
})();
