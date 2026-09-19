/* Panel: tehlikeli işlemlerde onay penceresi. JS yoksa form onaysız gönderilir (PROJECT.md §15). */
(function () {
  "use strict";

  document.addEventListener("submit", function (event) {
    var message = event.target.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });
})();
