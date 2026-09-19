/* Randevu düzenleme (PROJECT.md §13 Faz 6): hizmet ya da gün değişince boş saatleri sahibe özel uçtan çeker.
   JS yoksa "Saatleri göster" düğmesi sayfayı yeniler ve saatleri sunucu çizer; form normal bir POST'tur
   ve sunucu her şeyi yeniden doğrular. Kütüphane yok. */
(function () {
  "use strict";

  var picker = document.querySelector("[data-slot-picker]");
  var form = document.querySelector("[data-edit-form]");
  if (!picker || !form) {
    return;
  }

  var api = picker.getAttribute("data-api");
  var currentService = picker.getAttribute("data-current-service");
  var currentDate = picker.getAttribute("data-current-date");
  var currentTime = picker.getAttribute("data-current-time");
  var slotArea = document.getElementById("slot-area");
  var serviceSelect = picker.querySelector('select[name="hizmet"]');
  var dateInput = picker.querySelector('input[name="tarih"]');
  var showButton = picker.querySelector("[data-picker-submit]");
  var serviceMirror = form.querySelector('[data-mirror="service"]');
  var dateMirror = form.querySelector('[data-mirror="date"]');
  var requestCounter = 0;

  var MESSAGES = {
    idle: "Saatleri görmek için hizmet ve gün seç.",
    loading: "Saatler yükleniyor…",
    closed: "Dükkan bu gün kapalı.",
    full: "Bu gün için boş saat kalmadı. Başka bir gün seç.",
    out_of_range: "Bu gün için randevu alınamaz. Başka bir gün seç.",
    failed: "Saatler yüklenemedi. \"Saatleri göster\" düğmesine bas."
  };

  function setMessage(text) {
    slotArea.textContent = "";
    var paragraph = document.createElement("p");
    paragraph.className = "slot-area__message";
    paragraph.textContent = text;
    slotArea.appendChild(paragraph);
  }

  function renderSlots(slots, wantedTime) {
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

  function loadSlots() {
    var serviceId = serviceSelect.value;
    var day = dateInput.value;
    // Gönderilecek hizmet ve gün her zaman gösterilen saat listesine ait olur.
    serviceMirror.value = serviceId;
    dateMirror.value = day;
    if (!serviceId || !day) {
      setMessage(MESSAGES.idle);
      return;
    }

    var current = ++requestCounter;
    setMessage(MESSAGES.loading);
    var wantedTime = serviceId === currentService && day === currentDate ? currentTime : "";

    var url = api + "?hizmet=" + encodeURIComponent(serviceId) + "&tarih=" + encodeURIComponent(day);
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
          renderSlots(result.data.slots, wantedTime);
        } else {
          setMessage(MESSAGES[result.data.reason] || MESSAGES.full);
        }
      })
      .catch(function () {
        if (current === requestCounter) {
          setMessage(MESSAGES.failed);
          showButton.hidden = false; // otomatik yükleme çalışmadı: elle yenileme yolu açık kalsın
        }
      });
  }

  // JS varken saatler seçim değişince kendiliğinden gelir; düğme yalnızca JS yokken gerekir.
  showButton.hidden = true;
  picker.addEventListener("change", loadSlots);
  picker.addEventListener("submit", function (event) {
    event.preventDefault();
    loadSlots();
  });
})();
