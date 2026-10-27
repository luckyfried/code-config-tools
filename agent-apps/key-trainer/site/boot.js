// Applies the theme the person picked in Settings before the first paint, so neither color scheme flashes.
(function () {
  try {
    var saved = JSON.parse(localStorage.getItem("key-trainer:settings") || "{}");
    if (saved.theme === "dark" || saved.theme === "light") document.documentElement.setAttribute("data-theme", saved.theme);
  } catch (error) {
    // A settings entry that is not JSON leaves the default theme in place.
  }
})();
