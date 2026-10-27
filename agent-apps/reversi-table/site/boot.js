// Runs before the first paint: applies the saved table and light choice so the page never flashes the wrong look.
(function () {
  var KEY = "reversi-table:prefs";
  var THEMES = ["lacquer-green", "walnut", "neon"];
  var prefs = {};
  try {
    prefs = JSON.parse(localStorage.getItem(KEY) || "{}") || {};
  } catch (error) {
    prefs = {};
  }
  var config = window.__APP_CONFIG__ || {};
  if (prefs.theme && THEMES.indexOf(prefs.theme) >= 0 && prefs.theme !== config.theme) {
    var sheet = document.getElementById("theme-sheet");
    if (sheet) sheet.href = "./themes/" + prefs.theme + ".css";
  }
  if (prefs.scheme === "light" || prefs.scheme === "dark") {
    document.documentElement.setAttribute("data-theme", prefs.scheme);
  }
})();
