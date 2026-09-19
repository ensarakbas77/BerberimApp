/* Dükkan detayında salt okunur harita (PROJECT.md §13 Faz 4). Leaflet yüklenemezse ya da JS yoksa harita gizli kalır;
   adres ve "Yol tarifi al" bağlantısı sayfada durur. */
(function () {
  "use strict";

  var container = document.getElementById("shop-map");
  if (!container || typeof L === "undefined") {
    return;
  }

  var lat = parseFloat(container.getAttribute("data-lat"));
  var lng = parseFloat(container.getAttribute("data-lng"));
  if (!isFinite(lat) || !isFinite(lng)) {
    return;
  }

  container.hidden = false;

  var map = L.map(container, { scrollWheelZoom: false }).setView([lat, lng], 17);

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanlar',
    // Django'nun varsayılan "same-origin" politikası Referer'ı keser; OSM karo kullanım politikası ister.
    referrerPolicy: "strict-origin-when-cross-origin"
  }).addTo(map);

  L.marker([lat, lng], { title: container.getAttribute("data-name") || "", keyboard: false }).addTo(map);
})();
