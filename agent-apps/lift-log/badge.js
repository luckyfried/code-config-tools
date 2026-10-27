// "Get this app for yourself now." at the bottom of the page for five seconds, every visit.
// A tap opens this app's page on code-config.com in the same tab. Nothing is sent anywhere.
(function () {
  var NAME = "lift-log";
  var LINK = "https://app.code-config.com/agent-apps/01a17304-1abd-76d3-8226-b741f14d53ff";
  var SHOWN_FOR = 5000;
  var SLIDE = 350;
  var STYLE =
    ".code-config-toast{position:fixed;z-index:2147483647;left:0;right:0;bottom:0;box-sizing:border-box;" +
    "display:flex;align-items:center;gap:8px;margin:0 auto;padding:4px 4px calc(4px + env(safe-area-inset-bottom)) 16px;" +
    "border-radius:16px 16px 0 0;background:#16161a;color:#fff;font:15px/1.3 system-ui,-apple-system,sans-serif;" +
    "box-shadow:0 8px 28px rgba(0,0,0,.28);transition:transform " + SLIDE + "ms ease}" +
    ".code-config-toast.away{transform:translateY(calc(100% + 32px))}" +
    ".code-config-toast a{flex:1;min-height:44px;display:flex;align-items:center;margin:0;padding:0;color:inherit;" +
    "font:inherit;font-weight:600;text-decoration:underline;text-underline-offset:3px;cursor:pointer}" +
    ".code-config-toast button{flex:none;width:44px;height:44px;display:flex;align-items:center;justify-content:center;" +
    "margin:0;padding:0;border:0;border-radius:999px;background:none;color:inherit;font:22px/1 system-ui,sans-serif;" +
    "cursor:pointer}" +
    "@media (min-width: 640px){.code-config-toast{bottom:24px;width:max-content;max-width:calc(100% - 32px);" +
    "padding:6px 6px 6px 20px;border-radius:999px}}" +
    "@media (prefers-reduced-motion: reduce){.code-config-toast{transition:none}}";

  function show() {
    var style = document.createElement("style");
    style.textContent = STYLE;
    var toast = document.createElement("div");
    toast.className = "code-config-toast away";
    toast.setAttribute("role", "status");

    var tap = document.createElement("a");
    tap.href = LINK;
    tap.title = NAME + " on code-config.com";
    tap.textContent = "Get this app for yourself now.";

    var close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "Close");
    close.textContent = "×";

    toast.appendChild(tap);
    toast.appendChild(close);
    document.body.appendChild(style);
    document.body.appendChild(toast);

    // One timer: it runs out the time left to show, then the slide out. Holding clears it, and a hold during the
    // slide brings the toast back; with nothing left to show, letting go starts the slide again.
    var timer = 0;
    var left = SHOWN_FOR;
    var since = 0;
    var pointed = false;
    var focused = false;

    function run() {
      since = Date.now();
      timer = setTimeout(leave, left);
    }
    function leave() {
      left = 0;
      toast.classList.add("away");
      timer = setTimeout(remove, SLIDE);
    }
    function remove() {
      clearTimeout(timer);
      toast.remove();
      style.remove();
    }
    function settle() {
      if (!pointed && !focused) {
        if (!timer) run();
        return;
      }
      if (!timer) return;
      clearTimeout(timer);
      timer = 0;
      left = Math.max(0, left - (Date.now() - since));
      toast.classList.remove("away");
    }

    toast.addEventListener("pointerenter", function () {
      pointed = true;
      settle();
    });
    toast.addEventListener("pointerleave", function () {
      pointed = false;
      settle();
    });
    toast.addEventListener("focusin", function () {
      focused = true;
      settle();
    });
    toast.addEventListener("focusout", function (event) {
      focused = toast.contains(event.relatedTarget);
      settle();
    });
    close.addEventListener("click", remove);

    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        toast.classList.remove("away");
      });
    });
    run();
  }

  if (document.body) show();
  else document.addEventListener("DOMContentLoaded", show);
})();
