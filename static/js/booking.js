/* Randevu sayfası (FRONTEND-TASARIM.md §10.4, §11): boş saatleri API'den çeker, randevu fişini ve alt çubuğu günceller.
   Sözleşme değişmez: GET <data-api>?hizmet=<id>&tarih=YYYY-MM-DD → {"date", "slots": ["HH:MM"], "reason": null|"closed"|"full"|"out_of_range"};
   form normal bir POST'tur (service, date, time, note) ve sunucu her şeyi yeniden doğrular. Kütüphane yok. */
(function () {
  "use strict";

  var form = document.querySelector("[data-booking-form]");
  if (!form) {
    return;
  }

  var api = form.getAttribute("data-api");
  var slotArea = document.getElementById("slot-area");
  var receiptService = document.querySelector("[data-receipt-service]");
  var receiptDate = document.querySelector("[data-receipt-date]");
  var receiptTime = document.querySelector("[data-receipt-time]");
  var submits = Array.prototype.slice.call(document.querySelectorAll("[data-submit]"));
  var bar = document.querySelector("[data-booking-bar]");
  var barTime = document.querySelector("[data-bar-time]");
  var locked = submits.some(function (button) {
    return button.hasAttribute("data-locked"); // sayım limiti dolu ya da kısıt var: düğmeler pasif kalır
  });
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

  // Yüklenirken hap boyutunda iskelet kutular; ekran okuyucuya "Saatler yükleniyor…" söylenir
  function setLoading() {
    slotArea.textContent = "";
    var status = document.createElement("p");
    status.className = "visually-hidden";
    status.textContent = MESSAGES.loading;
    var grid = document.createElement("div");
    grid.className = "slot-grid";
    grid.setAttribute("aria-hidden", "true");
    for (var i = 0; i < 8; i += 1) {
      var box = document.createElement("div");
      box.className = "slot-skeleton";
      grid.appendChild(box);
    }
    slotArea.appendChild(status);
    slotArea.appendChild(grid);
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

  var lastTimeText = "";

  function updateReceipt() {
    var service = checked("service");
    var day = checked("date");
    var time = checked("time");

    var duration = service ? parseInt(service.getAttribute("data-duration"), 10) : 0;
    if (service) {
      var parts = [service.getAttribute("data-name"), duration + " dk"];
      if (service.getAttribute("data-price")) {
        parts.push(service.getAttribute("data-price"));
      }
      receiptService.textContent = parts.join(", ");
    } else {
      receiptService.textContent = "Hizmet seç";
    }

    receiptDate.textContent = day ? day.getAttribute("data-label") : "Gün seç";

    var timeText = time && service ? time.value + "–" + addMinutes(time.value, duration) : "";
    receiptTime.textContent = timeText || "Saat seç";
    receiptTime.classList.toggle("receipt__time--empty", !timeText);
    if (timeText && timeText !== lastTimeText) {
      // Tek özel an: fişteki saat 180 ms'de hafifçe büyüyerek belirir (prefers-reduced-motion'da CSS kapatır)
      receiptTime.classList.remove("is-updated");
      void receiptTime.offsetWidth;
      receiptTime.classList.add("is-updated");
    }
    lastTimeText = timeText;

    var ready = !!(service && day && time);
    submits.forEach(function (button) {
      if (!locked) {
        button.disabled = !ready;
        button.setAttribute("aria-disabled", ready ? "false" : "true");
      }
    });
    if (bar) {
      bar.hidden = !(ready && !locked);
      if (barTime) {
        barTime.textContent = time ? time.value : "";
      }
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
    setLoading();
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
      if (name === "date") {
        var chip = event.target.closest(".day-chip");
        if (chip && chip.scrollIntoView) {
          chip.scrollIntoView({ inline: "center", block: "nearest" });
        }
      }
      loadSlots();
    } else if (name === "time") {
      updateReceipt();
    }
  });

  // Seçili gün çipi görünür alana gelsin (sayfa yenilenince ya da hata sonrası)
  var selectedChip = form.querySelector(".day-chip input:checked");
  if (selectedChip && selectedChip.closest(".day-chip").scrollIntoView) {
    selectedChip.closest(".day-chip").scrollIntoView({ inline: "center", block: "nearest" });
  }

  loadSlots();
})();
