// Runs before the first paint: puts back the theme the person picked on this device, so the page never flashes the other one.
(function () {
  try {
    var saved = localStorage.getItem("life-in-weeks:theme");
    if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
  } catch (error) {
    // Storage can be off; the theme then follows the inputs and the device.
  }
})();
