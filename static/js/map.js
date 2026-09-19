/* Konum seçimi (PROJECT.md §13 Faz 3): haritaya tıklayınca işaretçi konur, gizli enlem/boylam alanları dolar.
   Leaflet yüklenemezse ya da JS yoksa form yine kaydedilir; mevcut konum gizli alanlarda korunur. */
(function () {
  "use strict";

  var container = document.getElementById("location-map");
  var status = document.getElementById("location-status");
  var latInput = document.getElementById("id_latitude");
  var lngInput = document.getElementById("id_longitude");
  if (!container || !status || !latInput || !lngInput) {
    return;
  }

  if (typeof L === "undefined") {
    status.textContent = "Harita yüklenemedi. Konumu boş bırakabilirsin.";
    return;
  }

  var help = document.querySelector("[data-location-help]");
  var clearButton = document.querySelector("[data-location-clear]");

  // Varsayılan merkez: Karamürsel.
  var DEFAULT_CENTER = [40.69, 29.61];
  var marker = null;

  function readPoint() {
    var lat = parseFloat(latInput.value);
    var lng = parseFloat(lngInput.value);
    return isFinite(lat) && isFinite(lng) ? [lat, lng] : null;
  }

  var saved = readPoint();

  container.hidden = false;
  if (help) {
    help.hidden = false;
  }

  var map = L.map(container, { scrollWheelZoom: false }).setView(saved || DEFAULT_CENTER, saved ? 17 : 14);

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanlar',
    // Django'nun varsayılan "same-origin" politikası Referer'ı keser; OSM karo kullanım politikası ister.
    referrerPolicy: "strict-origin-when-cross-origin"
  }).addTo(map);

  function announce(point) {
    if (point) {
      status.textContent = "Konum seçildi: " + point[0].toFixed(6) + ", " + point[1].toFixed(6) + ".";
    } else {
      status.textContent = "Konum seçilmedi. Haritaya dokunarak dükkanının yerini işaretle.";
    }
    if (clearButton) {
      clearButton.hidden = !point;
    }
  }

  function setPoint(latlng) {
    var lat = latlng.lat;
    var lng = latlng.lng;
    latInput.value = lat.toFixed(6);
    lngInput.value = lng.toFixed(6);
    if (marker) {
      marker.setLatLng(latlng);
    } else {
      marker = L.marker(latlng, { draggable: true, keyboard: false }).addTo(map);
      marker.on("dragend", function () {
        setPoint(marker.getLatLng());
      });
    }
    announce([lat, lng]);
  }

  function clearPoint() {
    latInput.value = "";
    lngInput.value = "";
    if (marker) {
      map.removeLayer(marker);
      marker = null;
    }
    announce(null);
  }

  map.on("click", function (event) {
    setPoint(event.latlng);
  });

  // Klavye: harita odaktayken Enter ortadaki noktayı seçer (ok tuşları ve +/- Leaflet'te hazır).
  container.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && event.target === container) {
      event.preventDefault();
      setPoint(map.getCenter());
    }
  });

  if (clearButton) {
    clearButton.addEventListener("click", clearPoint);
  }

  if (saved) {
    setPoint(L.latLng(saved[0], saved[1]));
  } else {
    announce(null);
  }
})();
