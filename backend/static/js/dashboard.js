/* LAND AI — dashboard logic
   Map: Leaflet + Esri World Imagery (free, no API key) as the satellite basemap.
   Drawing: Leaflet.draw for polygon / rectangle AOI selection.
   Data: talks to the Flask API in app.py (/api/location/search, /api/classify,
   /api/download/*).
*/

let map, drawnItems, drawControlPolygon, drawControlRect, resultLayer;
let currentAoiLatLngs = null;   // [[lat, lng], ...]
let currentLocationName = "Selected Area";

function initMap() {
  map = L.map('map', { zoomControl: true }).setView([14.4644, 75.9218], 12); // Davangere, Karnataka default

  L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { attribution: 'Tiles © Esri — World Imagery', maxZoom: 19 }
  ).addTo(map);

  drawnItems = new L.FeatureGroup();
  map.addLayer(drawnItems);

  resultLayer = L.layerGroup().addTo(map);

  map.on(L.Draw.Event.CREATED, (e) => {
    drawnItems.clearLayers();
    drawnItems.addLayer(e.layer);
    onAreaDrawn(e.layer);
  });
}

function setStep(n) {
  document.querySelectorAll('#stepTracker span').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.step) <= n);
  });
}

function onAreaDrawn(layer) {
  const latlngs = layer.getLatLngs()[0].map(p => [p.lat, p.lng]);
  currentAoiLatLngs = latlngs;

  const areaM2 = L.GeometryUtil ? null : null; // (kept simple — server computes the real area)
  document.getElementById('areaStatus').textContent = `Area drawn — ready to classify.`;
  document.getElementById('areaDot').classList.add('ok');

  document.getElementById('classifyBtn').disabled = false;
  document.getElementById('classifyStatus').textContent = 'Ready. Click "Fetch image & classify".';
  setStep(2);
}

/* ---------------- location search ---------------- */

function initSearch() {
  const input = document.getElementById('locationInput');
  const btn = document.getElementById('searchBtn');
  const wrap = document.getElementById('searchResults');

  async function runSearch() {
    const q = input.value.trim();
    if (!q) return;
    const res = await fetch(`/api/location/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();

    document.querySelectorAll('.search-suggestions').forEach(el => el.remove());
    if (!data.results || data.results.length === 0) return;

    const box = document.createElement('div');
    box.className = 'search-suggestions';
    data.results.forEach(r => {
      const item = document.createElement('div');
      item.textContent = r.name;
      item.onclick = () => {
        map.setView([r.lat, r.lng], 13);
        currentLocationName = r.name;
        input.value = r.name;
        box.remove();
        setStep(1);
      };
      box.appendChild(item);
    });
    wrap.appendChild(box);
  }

  btn.addEventListener('click', runSearch);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') runSearch(); });
  document.addEventListener('click', (e) => {
    if (!wrap.contains(e.target)) document.querySelectorAll('.search-suggestions').forEach(el => el.remove());
  });
}

/* ---------------- drawing toolbar buttons ---------------- */

function initDrawButtons() {
  document.getElementById('drawPolygonBtn').addEventListener('click', () => {
    new L.Draw.Polygon(map, { shapeOptions: { color: '#4fd1c5', weight: 2 } }).enable();
  });
  document.getElementById('drawRectBtn').addEventListener('click', () => {
    new L.Draw.Rectangle(map, { shapeOptions: { color: '#4fd1c5', weight: 2 } }).enable();
  });
  document.getElementById('clearBtn').addEventListener('click', () => {
    drawnItems.clearLayers();
    resultLayer.clearLayers();
    currentAoiLatLngs = null;
    document.getElementById('areaStatus').textContent = 'No area selected yet.';
    document.getElementById('areaDot').classList.remove('ok');
    document.getElementById('classifyBtn').disabled = true;
    document.getElementById('classifyStatus').textContent = 'Waiting for an area selection.';
    document.getElementById('resultsEmpty').style.display = 'block';
    document.getElementById('resultsContent').style.display = 'none';
    document.getElementById('polygonEmpty').style.display = 'block';
    document.getElementById('polygonContent').style.display = 'none';
    setStep(1);
  });
}

/* ---------------- classify ---------------- */

function initClassify() {
  document.getElementById('classifyBtn').addEventListener('click', async () => {
    if (!currentAoiLatLngs) return;

    const btn = document.getElementById('classifyBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Fetching image & classifying…';
    document.getElementById('classifyDot').classList.add('busy');
    document.getElementById('classifyStatus').textContent = 'Fetching satellite image for selected area…';
    setStep(4);

    try {
      const res = await fetch('/api/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          polygon: currentAoiLatLngs,
          location_name: currentLocationName,
        }),
      });
      const data = await res.json();

      if (data.error) {
        document.getElementById('classifyStatus').textContent = 'Error: ' + data.error;
        document.getElementById('classifyDot').classList.remove('busy');
        btn.disabled = false;
        btn.textContent = '🧠 Fetch image & classify';
        return;
      }

      renderResults(data);
      renderPolygons(data);
      wireDownloads();

      document.getElementById('classifyDot').classList.remove('busy');
      document.getElementById('classifyDot').classList.add('ok');
      document.getElementById('classifyStatus').textContent = 'Classification complete.';
      setStep(7);
    } catch (err) {
      document.getElementById('classifyStatus').textContent = 'Request failed: ' + err;
      document.getElementById('classifyDot').classList.remove('busy');
    } finally {
      btn.disabled = false;
      btn.textContent = '🧠 Fetch image & classify';
    }
  });
}

function renderResults(data) {
  document.getElementById('resultsEmpty').style.display = 'none';
  document.getElementById('resultsContent').style.display = 'block';

  document.getElementById('outLocation').textContent = data.location_name;
  document.getElementById('outArea').textContent = data.area_km2 + ' km²';

  const barsWrap = document.getElementById('classBars');
  barsWrap.innerHTML = '';

  const sorted = Object.entries(data.percentages).sort((a, b) => b[1] - a[1]);
  sorted.forEach(([cls, pct]) => {
    const color = data.class_colors[cls] || '#888';
    const row = document.createElement('div');
    row.className = 'class-bar-row';
    row.innerHTML = `
      <div class="swatch" style="background:${color}"></div>
      <div class="name">${cls}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%; background:${color}"></div></div>
      <div class="pct">${pct}%</div>
    `;
    barsWrap.appendChild(row);
  });
}

function renderPolygons(data) {
  resultLayer.clearLayers();

  const geoLayer = L.geoJSON(data.geojson, {
    style: (feature) => ({
      color: feature.properties.color,
      fillColor: feature.properties.color,
      fillOpacity: 0.55,
      weight: 1,
    }),
    onEachFeature: (feature, layer) => {
      layer.bindPopup(`<strong>${feature.properties.land_class}</strong>`);
    },
  });
  resultLayer.addLayer(geoLayer);

  document.getElementById('polygonEmpty').style.display = 'none';
  document.getElementById('polygonContent').style.display = 'block';
}

function wireDownloads() {
  document.getElementById('downloadGeojson').href = '/api/download/geojson';
  document.getElementById('downloadShapefile').href = '/api/download/shapefile';
  document.getElementById('downloadReport').href = '/api/download/report';
}

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initSearch();
  initDrawButtons();
  initClassify();
});
