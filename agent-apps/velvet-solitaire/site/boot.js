// Runs before the page paints: applies the table and light this device last chose, so the
// first frame is already the right theme and nothing flashes.
(function () {
  var cfg = window.__APP_CONFIG__ || {};
  var prefs = {};
  try {
    prefs = JSON.parse(localStorage.getItem("velvet-solitaire:prefs") || "{}") || {};
  } catch (e) {
    prefs = {};
  }
  var themes = ["velvet-green", "midnight-blue", "ivory-club"];
  var link = document.getElementById("theme-link");
  if (link && prefs.theme && prefs.theme !== cfg.theme && themes.indexOf(prefs.theme) >= 0) {
    link.href = "./themes/" + prefs.theme + ".css";
  }
  if (prefs.lighting === "light" || prefs.lighting === "dark") {
    document.documentElement.setAttribute("data-theme", prefs.lighting);
  }
  if (cfg.title) document.title = cfg.title;
})();
