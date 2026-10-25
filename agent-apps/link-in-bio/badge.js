// "Get it on code-config.com" in a bottom corner for ten seconds, once per visit.
// A tap copies one sentence that asks an agent to grab this app. Nothing is sent anywhere.
(function () {
  var NAME = "link-in-bio";
  var LINK = "https://app.code-config.com/agent-apps/01a1622c-dcf6-79cf-9dc8-decef710f69a";
  var KEY = "code-config-get-it-shown";
  try {
    if (window.sessionStorage.getItem(KEY)) return;
    window.sessionStorage.setItem(KEY, "1");
  } catch (e) {}
  var still = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  function copyText(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {
        copyByHand(text);
        done();
      });
    } else {
      copyByHand(text);
      done();
    }
  }

  function copyByHand(text) {
    var box = document.createElement("textarea");
    box.value = text;
    box.setAttribute("readonly", "");
    box.style.cssText = "position:fixed;top:-1000px;opacity:0;";
    document.body.appendChild(box);
    box.select();
    try {
      document.execCommand("copy");
    } catch (e) {}
    box.remove();
  }

  function show() {
    var panel = document.createElement("div");
    panel.setAttribute("role", "status");
    panel.style.cssText =
      "position:fixed;right:16px;bottom:16px;z-index:2147483647;display:flex;align-items:center;gap:10px;" +
      "padding:10px 12px;border-radius:10px;background:#16161a;color:#fff;font:14px/1.3 system-ui,sans-serif;" +
      "box-shadow:0 6px 20px rgba(0,0,0,.25);" +
      (still ? "" : "transition:transform .4s ease;transform:translateY(160%);");
    var tap = document.createElement("button");
    tap.type = "button";
    tap.textContent = "Get it on code-config.com";
    tap.style.cssText = "all:unset;cursor:pointer;";
    var close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "Close");
    close.textContent = "×";
    close.style.cssText = "all:unset;cursor:pointer;padding:0 4px;font-size:18px;line-height:1;";
    panel.appendChild(tap);
    panel.appendChild(close);
    document.body.appendChild(panel);

    var timer = 0;
    function leave() {
      clearTimeout(timer);
      if (still) {
        panel.remove();
        return;
      }
      panel.style.transform = "translateY(160%)";
      setTimeout(function () {
        panel.remove();
      }, 400);
    }
    tap.addEventListener("click", function () {
      copyText("Grab the " + NAME + " agent app from code-config.com (" + LINK + ") and set it up for me.", function () {
        tap.textContent = "Copied";
        clearTimeout(timer);
        timer = setTimeout(leave, 2000);
      });
    });
    close.addEventListener("click", leave);
    if (!still) {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          panel.style.transform = "none";
        });
      });
    }
    timer = setTimeout(leave, 10000);
  }

  if (document.body) show();
  else document.addEventListener("DOMContentLoaded", show);
})();
