/* Harita (Leaflet 1.9, OpenStreetMap): dükkan detayında salt okunur görüntüleme, panelde konum seçme.
   Leaflet yüklenemezse ya da JS yoksa harita gizli kalır; adres ve "Yol tarifi al" ile "Ara" bağlantıları sayfada durur.
   Görüntüleme kancaları: #shop-map (data-lat, data-lng, data-name). Seçme kancaları: #location-map, #location-status,
   #id_latitude, #id_longitude, [data-location-help], [data-location-clear]. */
(function () {
  "use strict";

  if (typeof L === "undefined") {
    var missing = document.getElementById("location-status");
    if (missing && document.getElementById("location-map")) {
      missing.textContent = "Harita yüklenemedi. Konumu boş bırakabilirsin.";
    }
    return;
  }

  // Varsayılan merkez: Karamürsel.
  var DEFAULT_CENTER = [40.69, 29.61];

  // Özel işaretçi: 20 px limon daire, 3 px koyu kenarlık (FRONTEND-TASARIM.md §8.13)
  var pin = L.divIcon({ className: "map-pin", iconSize: [20, 20], iconAnchor: [10, 10] });

  function createMap(container, center, zoom) {
    var map = L.map(container, { scrollWheelZoom: false }).setView(center, zoom);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanlar',
      // Django'nun varsayılan "same-origin" politikası Referer'ı keser; OSM karo kullanım politikası ister.
      referrerPolicy: "strict-origin-when-cross-origin"
    }).addTo(map);
    return map;
  }

  // --- Dükkan detayı: salt okunur ---------------------------------------------------------------
  var view = document.getElementById("shop-map");
  if (view) {
    var lat = parseFloat(view.getAttribute("data-lat"));
    var lng = parseFloat(view.getAttribute("data-lng"));
    if (isFinite(lat) && isFinite(lng)) {
      view.hidden = false;
      var viewMap = createMap(view, [lat, lng], 17);
      L.marker([lat, lng], { icon: pin, title: view.getAttribute("data-name") || "", keyboard: false }).addTo(viewMap);
    }
  }

  // --- Panel: konum seçme -----------------------------------------------------------------------
  var container = document.getElementById("location-map");
  var status = document.getElementById("location-status");
  var latInput = document.getElementById("id_latitude");
  var lngInput = document.getElementById("id_longitude");
  if (!container || !status || !latInput || !lngInput) {
    return;
  }

  var help = document.querySelector("[data-location-help]");
  var clearButton = document.querySelector("[data-location-clear]");
  var marker = null;

  function readPoint() {
    var savedLat = parseFloat(latInput.value);
    var savedLng = parseFloat(lngInput.value);
    return isFinite(savedLat) && isFinite(savedLng) ? [savedLat, savedLng] : null;
  }

  var saved = readPoint();

  container.hidden = false;
  if (help) {
    help.hidden = false;
  }

  var map = createMap(container, saved || DEFAULT_CENTER, saved ? 17 : 14);

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
    latInput.value = latlng.lat.toFixed(6);
    lngInput.value = latlng.lng.toFixed(6);
    if (marker) {
      marker.setLatLng(latlng);
    } else {
      marker = L.marker(latlng, { icon: pin, draggable: true, keyboard: false }).addTo(map);
      marker.on("dragend", function () {
        setPoint(marker.getLatLng());
      });
    }
    announce([latlng.lat, latlng.lng]);
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
