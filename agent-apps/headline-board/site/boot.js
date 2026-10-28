// Applies the saved light or dark choice before the first paint, so the board never flashes the other look.
(function () {
  try {
    var scheme = localStorage.getItem("headline-board:scheme");
    if (scheme === "light" || scheme === "dark") document.documentElement.setAttribute("data-theme", scheme);
  } catch (error) {
    // Storage can be off in a private window; the board then follows the screen.
  }
})();
