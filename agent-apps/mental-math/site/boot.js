// Runs before first paint: marks the page for a kid player so the kid font, keys, and (under the auto theme) candy
// colors are there from the first frame, with no flash.
(function () {
  var config = window.__APP_CONFIG__ || {};
  var players = Array.isArray(config.players) ? config.players : [];
  var chosen = null;
  try {
    var prefs = JSON.parse(localStorage.getItem("mental-math:prefs") || "{}");
    chosen = prefs.player;
  } catch (error) {
    chosen = null;
  }
  var player = players.filter(function (p) { return p && p.name === chosen; })[0] || players[0];
  if (player && player.kid) document.documentElement.setAttribute("data-kid", "");
})();
