// Runs before the first paint: the sheet's title, the page title, and the print settings from config.js.
(function () {
  var config = window.__APP_CONFIG__;
  document.title = config.title;
  document.getElementById("title").textContent = config.title;
  document.body.classList.add(config.paper === "A4" ? "paper-a4" : "paper-letter");
  document.documentElement.style.setProperty("--print-columns", String(config.columns));
})();
