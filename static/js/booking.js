/* Randevu sayfası (PROJECT.md §13 Faz 5): boş saatleri API'den çeker, "Randevu fişi" özetini günceller.
   Form normal bir POST'tur; sunucu her şeyi yeniden doğrular. Kütüphane yok. */
(function () {
  "use strict";

  var form = document.querySelector("[data-booking-form]");
  if (!form) {
    return;
  }

  var api = form.getAttribute("data-api");
  var slotArea = document.getElementById("slot-area");
  var receiptService = form.querySelector("[data-receipt-service]");
  var receiptWhen = form.querySelector("[data-receipt-when]");
  var submit = form.querySelector("[data-submit]");
  var locked = submit && submit.hasAttribute("data-locked"); // sayım limiti dolu: buton pasif kalır
  var wantedTime = form.getAttribute("data-selected-time") || ""; // hata sonrası yeniden çizimde seçili saat
  var requestCounter = 0;

  var MESSAGES = {
    idle: "Saatleri görmek için hizmet ve gün seç.",
    loading: "Saatler yükleniyor…",
    closed: "Dükkan bu gün kapalı.",
    full: "Bu gün için boş saat kalmadı. Başka bir gün seç.",
    out_of_range: "Bu gün için randevu alınamaz. Başka bir gün seç.",
    failed: "Saatler yüklenemedi. Sayfayı yenileyip tekrar dene."
  };

  function checked(name) {
    return form.querySelector('input[name="' + name + '"]:checked');
  }

  function pad(number) {
    return (number < 10 ? "0" : "") + number;
  }

  function addMinutes(time, minutes) {
    var parts = time.split(":");
    var total = parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10) + minutes;
    return pad(Math.floor(total / 60) % 24) + ":" + pad(total % 60);
  }

  function setMessage(text) {
    slotArea.textContent = "";
    var paragraph = document.createElement("p");
    paragraph.className = "slot-area__message";
    paragraph.textContent = text;
    slotArea.appendChild(paragraph);
  }

  function renderSlots(slots) {
    var grid = document.createElement("div");
    grid.className = "slot-grid";
    grid.setAttribute("role", "radiogroup");
    grid.setAttribute("aria-label", "Boş saatler");
    slots.forEach(function (slot) {
      var label = document.createElement("label");
      label.className = "slot";
      var input = document.createElement("input");
      input.type = "radio";
      input.name = "time";
      input.value = slot;
      input.className = "slot__input";
      if (slot === wantedTime) {
        input.checked = true;
      }
      var text = document.createElement("span");
      text.className = "slot__label tabular";
      text.textContent = slot;
      label.appendChild(input);
      label.appendChild(text);
      grid.appendChild(label);
    });
    slotArea.textContent = "";
    slotArea.appendChild(grid);
  }

  function updateReceipt() {
    var service = checked("service");
    var day = checked("date");
    var time = checked("time");

    var duration = service ? parseInt(service.getAttribute("data-duration"), 10) : 0;
    receiptService.textContent = service ? service.getAttribute("data-name") + ", " + duration + " dk" : "Hizmet seç";

    if (day && time && service) {
      receiptWhen.textContent = day.getAttribute("data-label") + ", " + time.value + "–" + addMinutes(time.value, duration);
    } else if (day) {
      receiptWhen.textContent = day.getAttribute("data-label") + ", saat seç";
    } else {
      receiptWhen.textContent = "Gün ve saat seç";
    }

    if (submit && !locked) {
      var ready = !!(service && day && time);
      submit.disabled = !ready;
      submit.setAttribute("aria-disabled", ready ? "false" : "true");
    }
  }

  function loadSlots() {
    var service = checked("service");
    var day = checked("date");
    if (!service || !day) {
      setMessage(MESSAGES.idle);
      updateReceipt();
      return;
    }

    var current = ++requestCounter;
    setMessage(MESSAGES.loading);
    updateReceipt();

    var url = api + "?hizmet=" + encodeURIComponent(service.value) + "&tarih=" + encodeURIComponent(day.value);
    fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        if (current !== requestCounter) {
          return; // daha yeni bir seçim yapıldı; eski yanıtı yok say
        }
        if (!result.ok) {
          setMessage(result.data && result.data.error ? result.data.error : MESSAGES.failed);
        } else if (result.data.slots.length) {
          renderSlots(result.data.slots);
        } else {
          setMessage(MESSAGES[result.data.reason] || MESSAGES.full);
        }
        updateReceipt();
      })
      .catch(function () {
        if (current === requestCounter) {
          setMessage(MESSAGES.failed);
          updateReceipt();
        }
      });
  }

  form.addEventListener("change", function (event) {
    var name = event.target.name;
    if (name === "service" || name === "date") {
      wantedTime = ""; // yeni hizmet ya da gün: saati yeniden bilinçli seç
      loadSlots();
    } else if (name === "time") {
      updateReceipt();
    }
  });

  loadSlots();
})();
