/* Berberim: mobil menü ve mesaj kapatma. Kütüphane yok. */
(function () {
  "use strict";

  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.getElementById("site-nav");

  function setNavOpen(open) {
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    nav.classList.toggle("is-open", open);
  }

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      setNavOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        setNavOpen(false);
        toggle.focus();
      }
    });

    // Geniş ekrana geçilince menü durumu sıfırlansın.
    window.matchMedia("(min-width: 640px)").addEventListener("change", function (event) {
      if (event.matches) {
        setNavOpen(false);
      }
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-dismiss]");
    if (!button) {
      return;
    }
    var alert = button.closest(".alert");
    if (alert) {
      alert.remove();
    }
  });
})();
