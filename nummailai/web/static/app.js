// Known MWA Branches in Bangkok Metropolitan Area
const ALL_MWA_BRANCHES = [
  "บางกอกน้อย", "ตากสิน", "พญาไท", "นนทบุรี", "ทุ่งมหาเมฆ",
  "แม้นศรี", "สุขุมวิท", "ภาษีเจริญ", "ลาดพร้าว", "พระโขนง",
  "สุขสวัสดิ์", "ประชาชื่น", "บางเขน", "สมุทรปราการ", "มีนบุรี",
  "บางบัวทอง", "สุวรรณภูมิ", "มหาสวัสดิ์"
];

let map = null;
let homeMarker = null;
let radiusCircle = null;
let eventMarkersLayer = null;
let currentEvents = [];
let currentKeywords = [];
let selectedBranches = new Set();

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initBranchesList();
  initMap();
  loadConfiguration();
  bindEvents();
});

// Tab Switching
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add('active');
      if (map) map.invalidateSize();
    });
  });
}

// Generate Branch Checkboxes
function initBranchesList() {
  const container = document.getElementById('branches-checkboxes');
  if (!container) return;
  container.innerHTML = '';
  ALL_MWA_BRANCHES.forEach(branch => {
    const label = document.createElement('label');
    label.className = 'checkbox-label';
    label.innerHTML = `
      <input type="checkbox" value="${branch}" class="branch-chk">
      <span>สาขา${branch}</span>
    `;
    container.appendChild(label);
  });
}

// Initialize Leaflet Map
function initMap() {
  map = L.map('map', {
    center: [13.7563, 100.5018], // Bangkok Default
    zoom: 11
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors | MWA GIS'
  }).addTo(map);

  eventMarkersLayer = L.layerGroup().addTo(map);

  // Click on map moves home marker
  map.on('click', (e) => {
    updateHomeLocation(e.latlng.lat, e.latlng.lng);
  });
}

// Update Home Location Pin and Radius Circle
function updateHomeLocation(lat, lng, radiusKm = null) {
  if (radiusKm === null) {
    radiusKm = parseFloat(document.getElementById('loc-radius').value) || 5.0;
  }

  document.getElementById('loc-lat').value = lat.toFixed(6);
  document.getElementById('loc-lng').value = lng.toFixed(6);

  if (homeMarker) {
    homeMarker.setLatLng([lat, lng]);
  } else {
    const homeIcon = L.divIcon({
      className: 'custom-home-icon',
      html: '<div style="background:#06b6d4;width:18px;height:18px;border-radius:50%;border:3px solid #fff;box-shadow:0 0 8px rgba(0,0,0,0.6);"></div>',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
    homeMarker = L.marker([lat, lng], { draggable: true, icon: homeIcon }).addTo(map);
    homeMarker.bindPopup('<b>พิกัดบ้านของคุณ (Your Home / Office)</b><br>ลากหมุดเพื่อเปลี่ยนตำแหน่ง');
    homeMarker.on('dragend', (e) => {
      const pos = e.target.getLatLng();
      updateHomeLocation(pos.lat, pos.lng);
    });
  }

  const radiusMeters = radiusKm * 1000;
  if (radiusCircle) {
    radiusCircle.setLatLng([lat, lng]);
    radiusCircle.setRadius(radiusMeters);
  } else {
    radiusCircle = L.circle([lat, lng], {
      radius: radiusMeters,
      color: '#0284c7',
      fillColor: '#0284c7',
      fillOpacity: 0.12,
      weight: 2
    }).addTo(map);
  }

  renderEvents(currentEvents);
}

// Load App Configuration
async function loadConfiguration() {
  try {
    const res = await fetch('/api/config');
    const config = await res.json();
    populateForm(config);
    fetchEvents();
  } catch (err) {
    showToast('❌ ไม่สามารถโหลดการตั้งค่าได้: ' + err.message);
  }
}

// Populate UI Form Fields with Config
function populateForm(config) {
  const match = config.matching || {};
  const loc = match.location || {};
  const kw = match.keywords || {};
  const br = match.branches || {};
  const disc = config.notifications?.discord || {};
  const poll = config.polling || {};

  document.getElementById('matching-mode').value = match.mode || 'hybrid';
  document.getElementById('location-enabled').checked = loc.enabled !== false;
  document.getElementById('keywords-enabled').checked = kw.enabled !== false;
  document.getElementById('branches-enabled').checked = br.enabled === true;

  const lat = loc.latitude || 13.8240;
  const lng = loc.longitude || 100.4478;
  const radius = loc.radius_km || 5.0;

  document.getElementById('loc-lat').value = lat;
  document.getElementById('loc-lng').value = lng;
  document.getElementById('loc-radius').value = radius;
  document.getElementById('radius-val').innerText = radius.toFixed(1);

  updateHomeLocation(lat, lng, radius);
  map.setView([lat, lng], 12);

  // Keywords
  currentKeywords = kw.terms || [];
  renderKeywords();

  // Branches
  selectedBranches = new Set(br.names || []);
  document.querySelectorAll('.branch-chk').forEach(chk => {
    chk.checked = selectedBranches.has(chk.value);
  });

  // Discord
  document.getElementById('discord-enabled').checked = disc.enabled !== false;
  document.getElementById('discord-webhook-url').value = disc.webhook_url || '';
  document.getElementById('discord-username').value = disc.username || 'MWA Alert (น้ำไม่ไหล)';
  document.getElementById('polling-interval').value = poll.interval_minutes || 15;
}

// Render Keywords Tags
function renderKeywords() {
  const container = document.getElementById('keywords-tags');
  container.innerHTML = '';
  currentKeywords.forEach((term, index) => {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.innerHTML = `
      ${term}
      <span class="tag-remove" data-index="${index}">&times;</span>
    `;
    container.appendChild(tag);
  });

  container.querySelectorAll('.tag-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = parseInt(e.target.dataset.index);
      currentKeywords.splice(idx, 1);
      renderKeywords();
      renderEvents(currentEvents);
    });
  });
}

// Fetch MWA Events from API
async function fetchEvents() {
  try {
    const res = await fetch('/api/events');
    const data = await res.json();
    if (data.status === 'ok') {
      currentEvents = data.events || [];
      document.getElementById('total-events-count').innerText = currentEvents.length;
      document.getElementById('tab-events-badge').innerText = currentEvents.length;
      renderEvents(currentEvents);
    }
  } catch (err) {
    console.error('Error loading events:', err);
  }
}

// Render Map Markers & Event Feed
function renderEvents(events) {
  if (!eventMarkersLayer) return;
  eventMarkersLayer.clearLayers();

  const listContainer = document.getElementById('events-list');
  listContainer.innerHTML = '';

  const filterType = document.getElementById('events-filter-type')?.value || 'all';
  const searchTerm = (document.getElementById('events-search')?.value || '').toLowerCase().trim();

  let matchedCount = 0;

  events.forEach(ev => {
    const isUrgent = ev.is_urgent;
    const isMatched = ev.matched;
    if (isMatched) matchedCount++;

    // Check filter criteria for list display
    let showInList = true;
    if (filterType === 'matched' && !isMatched) showInList = false;
    if (filterType === 'urgent' && !isUrgent) showInList = false;
    if (filterType === 'active' && !ev.active) showInList = false;

    if (searchTerm) {
      const corpus = `${ev.impact_area} ${ev.area_name} ${ev.impact_branch} ${ev.reason}`.toLowerCase();
      if (!corpus.includes(searchTerm)) showInList = false;
    }

    // Determine marker color
    let markerColor = '#94a3b8';
    if (ev.reason.includes('ท่อแตก') || ev.reason.includes('แตกรั่ว')) markerColor = '#ef4444';
    else if (ev.reason.includes('ปิดประตูน้ำ')) markerColor = '#f97316';
    else if (ev.reason.includes('ตัดบรรจบ')) markerColor = '#3b82f6';
    else if (ev.reason.includes('Step Test') || ev.reason.includes('DMA')) markerColor = '#eab308';

    // Add Marker on Leaflet Map
    if (ev.latitude && ev.longitude) {
      const circleMarker = L.circleMarker([ev.latitude, ev.longitude], {
        radius: isMatched ? 10 : 6,
        fillColor: markerColor,
        color: isMatched ? '#ffffff' : markerColor,
        weight: isMatched ? 3 : 1,
        opacity: 1,
        fillOpacity: 0.85
      });

      const popupHtml = `
        <div style="font-family:'Prompt',sans-serif;min-width:200px;">
          <h4 style="margin:0 0 4px 0;color:${markerColor};">${isUrgent ? '🚨' : '🔧'} ${ev.reason}</h4>
          <p style="margin:0 0 4px 0;font-size:12px;"><strong>สาขา:</strong> ${ev.impact_branch}</p>
          <p style="margin:0 0 4px 0;font-size:12px;"><strong>จุดงาน:</strong> ${ev.area_name}</p>
          <p style="margin:0 0 6px 0;font-size:12px;color:#475569;"><strong>พื้นที่ผลกระทบ:</strong> ${ev.impact_area}</p>
          <p style="margin:0 0 6px 0;font-size:11px;color:#64748b;">⏱️ ${ev.start_date_raw} - ${ev.finish_date_raw}</p>
          ${isMatched ? `<div style="background:#fee2e2;color:#dc2626;padding:3px 6px;border-radius:4px;font-size:11px;font-weight:600;">🎯 ${ev.match_reasons.join(' | ')}</div>` : ''}
        </div>
      `;
      circleMarker.bindPopup(popupHtml);
      eventMarkersLayer.addLayer(circleMarker);
    }

    // Add Event Card to List Feed
    if (showInList) {
      const card = document.createElement('div');
      card.className = `event-card ${isMatched ? 'matched' : ''}`;
      card.innerHTML = `
        <div class="event-header">
          <span class="event-title">${ev.reason} - สาขา${ev.impact_branch}</span>
          <span class="event-badge ${isUrgent ? 'badge-urgent' : 'badge-normal'}">
            ${ev.active ? 'กำลังดำเนินการ' : 'มีแผนงาน'}
          </span>
        </div>
        <div class="event-area">${ev.impact_area}</div>
        <div class="event-meta">
          <span>📍 ${ev.area_name || '-'}</span>
          <span>⏱️ ${ev.start_date_raw} ถึง ${ev.finish_date_raw}</span>
          ${ev.pipe_size ? `<span>🛠️ ${ev.pipe_size} มม.</span>` : ''}
          ${isMatched ? `<div class="meta-match-reason">🎯 ${ev.match_reasons.join(' | ')}</div>` : ''}
        </div>
      `;
      listContainer.appendChild(card);
    }
  });

  document.getElementById('matched-events-count').innerText = matchedCount;
}

// Bind UI Events
function bindEvents() {
  // Radius slider
  const radiusSlider = document.getElementById('loc-radius');
  radiusSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    document.getElementById('radius-val').innerText = val.toFixed(1);
    const lat = parseFloat(document.getElementById('loc-lat').value) || 13.7563;
    const lng = parseFloat(document.getElementById('loc-lng').value) || 100.5018;
    updateHomeLocation(lat, lng, val);
  });

  // GPS Inputs change
  ['loc-lat', 'loc-lng'].forEach(id => {
    document.getElementById(id).addEventListener('change', () => {
      const lat = parseFloat(document.getElementById('loc-lat').value);
      const lng = parseFloat(document.getElementById('loc-lng').value);
      if (!isNaN(lat) && !isNaN(lng)) {
        updateHomeLocation(lat, lng);
        map.setView([lat, lng], 13);
      }
    });
  });

  // Browser Geolocation
  document.getElementById('btn-use-my-location').addEventListener('click', () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(pos => {
        updateHomeLocation(pos.coords.latitude, pos.coords.longitude);
        map.setView([pos.coords.latitude, pos.coords.longitude], 14);
        showToast('📍 อัปเดตพิกัดตาม GPS ปัจจุบันแล้ว');
      }, err => {
        showToast('⚠️ ไม่สามารถระบุตำแหน่งจากเบราว์เซอร์ได้: ' + err.message);
      });
    }
  });

  // Add Keyword
  const addKeywordBtn = document.getElementById('btn-add-keyword');
  const keywordInput = document.getElementById('keyword-input');
  const addKw = () => {
    const val = keywordInput.value.trim();
    if (val && !currentKeywords.includes(val)) {
      currentKeywords.push(val);
      renderKeywords();
      renderEvents(currentEvents);
      keywordInput.value = '';
    }
  };
  addKeywordBtn.addEventListener('click', addKw);
  keywordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addKw();
  });

  // Branch Checkboxes
  document.addEventListener('change', (e) => {
    if (e.target.classList.contains('branch-chk')) {
      if (e.target.checked) selectedBranches.add(e.target.value);
      else selectedBranches.delete(e.target.value);
    }
  });

  // Events Search & Filter
  document.getElementById('events-search').addEventListener('input', () => renderEvents(currentEvents));
  document.getElementById('events-filter-type').addEventListener('change', () => renderEvents(currentEvents));

  // Save Configuration Button
  document.getElementById('btn-save-config').addEventListener('click', async () => {
    const payload = buildConfigPayload();
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.status === 'ok') {
        showToast('💾 ' + data.message);
        fetchEvents();
      } else {
        showToast('❌ ' + data.message);
      }
    } catch (err) {
      showToast('❌ บันทึกไม่สำเร็จ: ' + err.message);
    }
  });

  // Test Discord Button
  document.getElementById('btn-test-discord').addEventListener('click', async () => {
    const webhookUrl = document.getElementById('discord-webhook-url').value.trim();
    const statusBox = document.getElementById('discord-test-status');
    statusBox.className = 'status-msg';
    statusBox.innerText = 'กำลังส่งข้อความทดสอบ...';
    statusBox.style.display = 'block';

    try {
      const res = await fetch('/api/test-discord', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: webhookUrl })
      });
      const data = await res.json();
      if (data.status === 'ok') {
        statusBox.className = 'status-msg success';
        statusBox.innerText = '✅ ' + data.message;
      } else {
        statusBox.className = 'status-msg error';
        statusBox.innerText = '❌ ' + data.message;
      }
    } catch (err) {
      statusBox.className = 'status-msg error';
      statusBox.innerText = '❌ ' + err.message;
    }
  });

  // Check Now Button
  document.getElementById('btn-check-now').addEventListener('click', async () => {
    showToast('🔄 กำลังตรวจสอบและดึงข้อมูลสดจาก MWA...');
    try {
      const res = await fetch('/api/check-now', { method: 'POST' });
      const data = await res.json();
      showToast('✅ ' + data.message);
      fetchEvents();
    } catch (err) {
      showToast('❌ ไม่สามารถตรวจสอบได้: ' + err.message);
    }
  });
}

// Build Config Object from Form
function buildConfigPayload() {
  return {
    matching: {
      mode: document.getElementById('matching-mode').value,
      location: {
        enabled: document.getElementById('location-enabled').checked,
        latitude: parseFloat(document.getElementById('loc-lat').value) || 0.0,
        longitude: parseFloat(document.getElementById('loc-lng').value) || 0.0,
        radius_km: parseFloat(document.getElementById('loc-radius').value) || 5.0
      },
      keywords: {
        enabled: document.getElementById('keywords-enabled').checked,
        terms: currentKeywords
      },
      branches: {
        enabled: document.getElementById('branches-enabled').checked,
        names: Array.from(selectedBranches)
      }
    },
    notifications: {
      discord: {
        enabled: document.getElementById('discord-enabled').checked,
        webhook_url: document.getElementById('discord-webhook-url').value.trim(),
        username: document.getElementById('discord-username').value.trim(),
        avatar_url: 'https://gisonline.mwa.co.th/GIS1125/SRC/resources/mwa-icon.png'
      }
    },
    polling: {
      interval_minutes: parseInt(document.getElementById('polling-interval').value) || 15,
      state_file: 'data/state.json'
    }
  };
}

// Show Toast Message
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3500);
}
