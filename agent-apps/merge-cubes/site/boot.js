// Runs before the first paint: applies the look this visitor picked (theme and light or dark) so nothing flashes.
(function () {
  try {
    var saved = JSON.parse(localStorage.getItem("merge-cubes:settings") || "{}");
    if (saved.appearance === "light" || saved.appearance === "dark") document.documentElement.setAttribute("data-theme", saved.appearance);
    if (typeof saved.theme === "string" && /^[a-z-]+$/.test(saved.theme)) {
      var link = document.getElementById("theme");
      if (link) link.setAttribute("href", "./themes/" + saved.theme + ".css");
    }
  } catch (error) {
    // A blocked or empty store keeps the defaults.
  }
})();
