// Applies the look the person last picked with the in-page switch before the first paint, so nothing flashes.
(function () {
  try {
    var saved = JSON.parse(localStorage.getItem("spend-map") || "{}").theme;
    if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
  } catch (e) { /* storage is off; theme.css decides */ }
})();
