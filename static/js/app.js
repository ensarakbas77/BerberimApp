/* Berberim: ortak arayüz davranışı. Kütüphane yok; her bölüm kendi öğesi yoksa hiçbir şey yapmaz.
   Kancalar: [data-dismiss], [data-confirm], input[type=password], [data-js="segmented"], [data-js="autosubmit"], [data-loading-text]. */
(function () {
  "use strict";

  // Mesaj kapatma (Django messages)
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

  // Tehlikeli işlemler (iptal, silme): form `data-confirm` taşıyorsa onay penceresi açılır. JS yoksa onaysız gönderilir.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    var message = form.getAttribute && form.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
      return;
    }
    // Yükleniyor durumu: düğme adı taşımıyorsa pasifleşir ve metni değişir (gönderimden sonra, veri kaybolmasın)
    var submitter = event.submitter || form.querySelector("button[type=submit][data-loading-text]");
    if (submitter && submitter.hasAttribute("data-loading-text") && !submitter.name) {
      window.setTimeout(function () {
        submitter.textContent = submitter.getAttribute("data-loading-text");
        submitter.classList.add("is-loading");
        submitter.setAttribute("aria-disabled", "true");
      }, 0);
    }
  });

  // Şifre alanları: "Göster" düğmesi (JS yoksa normal şifre alanı)
  document.querySelectorAll("input[type=password]").forEach(function (input, index) {
    if (input.closest(".password")) {
      return;
    }
    if (!input.id) {
      input.id = "password-field-" + index;
    }
    var wrapper = document.createElement("div");
    wrapper.className = "password";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    var toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "password__toggle";
    toggle.textContent = "Göster";
    toggle.setAttribute("aria-controls", input.id);
    toggle.setAttribute("aria-pressed", "false");
    toggle.addEventListener("click", function () {
      var visible = input.type === "password";
      input.type = visible ? "text" : "password";
      toggle.textContent = visible ? "Gizle" : "Göster";
      toggle.setAttribute("aria-pressed", visible ? "true" : "false");
    });
    wrapper.appendChild(toggle);
  });

  // Bölümlü kontrol (Yaklaşan | Geçmiş): butonlar `data-segment`, bölümler `data-segment-panel`; JS yoksa bölümler alt alta
  document.querySelectorAll('[data-js="segmented"]').forEach(function (control) {
    var buttons = Array.prototype.slice.call(control.querySelectorAll("[data-segment]"));
    var panels = Array.prototype.slice.call(document.querySelectorAll("[data-segment-panel]"));
    if (!buttons.length || !panels.length) {
      return;
    }

    function select(name) {
      buttons.forEach(function (button) {
        button.setAttribute("aria-selected", button.getAttribute("data-segment") === name ? "true" : "false");
      });
      panels.forEach(function (panel) {
        panel.hidden = panel.getAttribute("data-segment-panel") !== name;
      });
    }

    buttons.forEach(function (button, index) {
      button.addEventListener("click", function () {
        select(button.getAttribute("data-segment"));
      });
      button.addEventListener("keydown", function (event) {
        var step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
        if (step) {
          var next = buttons[(index + step + buttons.length) % buttons.length];
          next.focus();
          select(next.getAttribute("data-segment"));
          event.preventDefault();
        }
      });
    });
    select(buttons[0].getAttribute("data-segment"));
  });

  // Filtre formu: seçim değişince kendiliğinden gönderilir; JS yoksa "Uygula" düğmesi görünür kalır
  document.querySelectorAll('form[data-js="autosubmit"]').forEach(function (form) {
    form.querySelectorAll("[data-js-hide]").forEach(function (element) {
      element.hidden = true;
    });
    form.addEventListener("change", function (event) {
      if (event.target.matches("select, input[type=checkbox], input[type=radio]")) {
        if (form.requestSubmit) {
          form.requestSubmit();
        } else {
          form.submit();
        }
      }
    });
  });

  // Yatay kaydırılan çip menülerinde seçili öğe görünür alana gelir
  document.querySelectorAll(".chip-row [aria-current]").forEach(function (item) {
    if (item.scrollIntoView) {
      item.scrollIntoView({ inline: "center", block: "nearest" });
    }
  });
})();
