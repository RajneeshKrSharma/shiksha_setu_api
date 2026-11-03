/* Adds a show/hide (eye) button after every password box in the admin. */
(function () {
  var EYE =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  var EYE_OFF =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C5 20 1 12 1 12a18.5 18.5 0 0 1 5.06-5.94"/>' +
    '<path d="M9.9 4.24A10.9 10.9 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>' +
    '<path d="M14.12 14.12A3 3 0 1 1 9.88 9.88"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

  function addToggle(input) {
    if (input.dataset.eye) return;
    input.dataset.eye = "1";
    var button = document.createElement("button");
    button.type = "button";
    button.innerHTML = EYE;
    button.title = "Show password";
    button.setAttribute("aria-label", "Show password");
    button.style.cssText =
      "background:none;border:0;cursor:pointer;color:inherit;margin-left:8px;" +
      "padding:4px;vertical-align:middle;line-height:0;opacity:.8";
    button.addEventListener("click", function () {
      var showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.innerHTML = showing ? EYE : EYE_OFF;
      var label = showing ? "Show password" : "Hide password";
      button.title = label;
      button.setAttribute("aria-label", label);
      input.focus();
    });
    input.insertAdjacentElement("afterend", button);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("input[type=password]").forEach(addToggle);
  });
})();
