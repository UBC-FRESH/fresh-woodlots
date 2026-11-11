const map = L.map("map", { scrollWheelZoom: false }).setView([54.5, -124.5], 5);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 12,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const pilots = new Set(["wl-w0026", "wl-w2023", "wl-w1548"]);
const pilotNames = {
  "wl-w0026": "Chinook",
  "wl-w2023": "Boomer",
  "wl-w1548": "Fibre Farms",
};
const pilotLabelDirection = {
  "wl-w0026": "bottom",
  "wl-w2023": "top",
  "wl-w1548": "top",
};
let ready = new Set();

Promise.all([
  fetch("/api/instances")
    .then((response) => response.json())
    .catch(() => ({ instances: [] })),
  fetch("/api/geojson/woodlots?v=2").then((response) => response.json()),
])
  .then(([instancePayload, geojson]) => {
    ready = new Set(
      instancePayload.instances
        .filter((instance) => instance.ready)
        .map((instance) => instance.slug)
    );
    const layer = L.geoJSON(geojson, {
      style: (feature) => {
        const live = ready.has(feature.properties.slug);
        const pilot = pilots.has(feature.properties.slug);
        return {
          color: pilot ? "#6b4f2a" : live ? "#2f7d5b" : "#8aa39a",
          weight: pilot ? 3 : live ? 2 : 1,
          fillOpacity: pilot ? 0.3 : live ? 0.12 : 0.04,
        };
      },
      onEachFeature: (feature, featureLayer) => {
        const name = feature.properties.display_name;
        if (ready.has(feature.properties.slug)) {
          featureLayer.bindPopup(
            "<strong>" + name + "</strong><br>" +
            '<a href="/instance/' + feature.properties.slug + '/">Open model</a>'
          );
        } else {
          featureLayer.bindTooltip(name + " (not built yet)");
        }
      },
    }).addTo(map);

    layer.eachLayer((candidate) => {
      const properties = candidate.feature.properties;
      if (!pilots.has(properties.slug)) {
        return;
      }
      const center = candidate.getBounds().getCenter();
      L.circleMarker(center, {
        radius: 7,
        color: "#6b4f2a",
        weight: 2,
        fillColor: "#6b4f2a",
        fillOpacity: 0.9,
      })
        .addTo(map)
        .bindPopup(
          "<strong>" + (pilotNames[properties.slug] || properties.display_name) +
          "</strong><br>" +
          '<a href="/instance/' + properties.slug + '/">Open model</a>'
        )
        .bindTooltip(pilotNames[properties.slug] || properties.display_name, {
          permanent: true,
          direction: pilotLabelDirection[properties.slug] || "top",
          className: "pilot-label",
          offset: [0, properties.slug === "wl-w0026" ? 8 : -8],
        });
    });

    map.fitBounds([[48.0, -139.0], [60.0, -114.0]], { padding: [20, 20] });
  })
  .catch(() => {
    document.getElementById("map").textContent = "Map data unavailable";
  });

const search = document.getElementById("woodlot-search");
if (search) {
  search.addEventListener("input", () => {
    const needle = search.value.toLowerCase();
    document.querySelectorAll(".card").forEach((card) => {
      const haystack = card.dataset.search || "";
      card.style.display = haystack.includes(needle) ? "" : "none";
    });
  });
}
