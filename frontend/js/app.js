/* ══════════════════════════════════════════════════════════════
   TRAFFIC INTELLIGENCE SYSTEM v2 — Main Application JS
   CCTV Canvas • Smart Alerts • Pulsing Hotspots • Cause Badges
   ══════════════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────
let ws = null, map = null, markers = {}, edgeLines = [], labelMarkers = {};
let hotspotCircles = [];
let detailChart = null, currentData = null, selectedNode = null;
let showPredictions = true, showEdges = false, showLabels = false, showHotspots = true;
let cctvAnimFrame = null;

// ── Colors ────────────────────────────────────────────────────
function ciColor(ci) {
    if (ci < 0.25) return '#22c55e';
    if (ci < 0.5)  return '#eab308';
    if (ci < 0.75) return '#f97316';
    return '#ef4444';
}
function ciClass(ci) {
    if (ci < 0.25) return 'low';
    if (ci < 0.5)  return 'moderate';
    if (ci < 0.75) return 'high';
    return 'critical';
}
function trendIcon(t) { return t === 'rising' ? '📈' : t === 'falling' ? '📉' : '➡️'; }

// ── Map Init ──────────────────────────────────────────────────
function initMap() {
    map = L.map('map', { center: [19.05, 72.88], zoom: 12, zoomControl: false, attributionControl: false });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 18 }).addTo(map);
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    L.control.attribution({ position: 'bottomleft', prefix: '© CartoDB © OSM' }).addTo(map);
}

// ── Marker Creation ───────────────────────────────────────────
function createMarker(node, explanation) {
    const ci = node.congestion_index || 0;
    const color = ciColor(ci);
    const isCrit = ci >= 0.75;
    const size = 11 + Math.round(ci * 13);
    const cause = explanation?.cause || {};
    const causeIcon = cause.icon || '';

    let extras = '';
    if (showPredictions && node.predicted_ci > 0.5)
        extras += '<div class="predicted-ring"></div>';
    if (showHotspots && ci >= 0.6)
        extras += '<div class="hotspot-ring active"></div>';

    const icon = L.divIcon({
        className: 'custom-marker',
        html: `
            <div class="marker-dot ${isCrit ? 'critical' : ''}"
                 style="width:${size}px;height:${size}px;background:${color};color:${color}"></div>
            ${extras}
            <div class="marker-label">${node.id} ${ci.toFixed(2)}</div>
            ${causeIcon ? `<div class="marker-cause">${causeIcon}</div>` : ''}
        `,
        iconSize: [size + 20, size + 34],
        iconAnchor: [(size + 20) / 2, (size + 34) / 2],
    });

    const marker = L.marker([node.lat, node.lon], { icon });

    const causeLabel = cause.label || '';
    const causeColor = cause.color || '#64748b';
    const validationType = explanation?.validation_type || 'consistent';
    let crossTag = '';
    if (validationType === 'false_positive') crossTag = '<div style="color:#eab308;font-size:10px;margin-top:3px">⚠️ API-only signal</div>';
    else if (validationType === 'early_warning') crossTag = '<div style="color:#06d6a0;font-size:10px;margin-top:3px">🔔 Visual early warning</div>';

    marker.bindTooltip(`
        <div class="tt-name">${node.name}</div>
        <div class="tt-row"><span class="lbl">CI</span><span class="val" style="color:${color}">${ci.toFixed(3)}</span></div>
        <div class="tt-row"><span class="lbl">Speed</span><span class="val">${(node.speed_norm * 60).toFixed(0)} kph</span></div>
        <div class="tt-row"><span class="lbl">Vehicles</span><span class="val">${node.vehicle_count}</span></div>
        <div class="tt-row"><span class="lbl">Predicted</span><span class="val" style="color:${ciColor(node.predicted_ci)}">${node.predicted_ci.toFixed(3)}</span></div>
        ${causeLabel ? `<div class="tt-cause" style="background:${causeColor}20;color:${causeColor}">${cause.icon||''} ${causeLabel}</div>` : ''}
        ${crossTag}
    `, { direction: 'top', offset: [0, -16] });

    marker.on('click', () => openDetail(node.id));
    return marker;
}

// ── Map Update ────────────────────────────────────────────────
function updateMap(data) {
    if (!map || !data?.network) return;
    const nodes = data.network.nodes;
    const explanations = data.explanations || {};

    nodes.forEach(n => {
        if (markers[n.id]) map.removeLayer(markers[n.id]);
        const m = createMarker(n, explanations[n.id]);
        m.addTo(map);
        markers[n.id] = m;
    });

    if (showEdges) drawEdges(data.network.edges, nodes);
    if (showLabels) drawLabels(nodes);
}

function drawEdges(edges, nodes) {
    edgeLines.forEach(l => map.removeLayer(l));
    edgeLines = [];
    const nm = {}; nodes.forEach(n => nm[n.id] = n);
    edges.forEach(e => {
        const s = nm[e.source], t = nm[e.target];
        if (!s || !t) return;
        const avg = ((s.congestion_index || 0) + (t.congestion_index || 0)) / 2;
        const l = L.polyline([[s.lat, s.lon], [t.lat, t.lon]], {
            color: ciColor(avg), weight: 2 + avg * 3, opacity: 0.35 + avg * 0.3,
            dashArray: avg > 0.6 ? '8,6' : null,
        });
        l.addTo(map); edgeLines.push(l);
    });
}

function drawLabels(nodes) {
    Object.values(labelMarkers).forEach(m => map.removeLayer(m));
    labelMarkers = {};
    nodes.forEach(n => {
        const l = L.marker([n.lat, n.lon], {
            icon: L.divIcon({
                className: '',
                html: `<span style="font-size:9px;font-weight:500;color:#94a3b8;background:rgba(13,19,33,.8);padding:2px 5px;border-radius:3px;white-space:nowrap;pointer-events:none">${n.name}</span>`,
                iconSize: [150, 18], iconAnchor: [75, -8],
            }), interactive: false,
        });
        l.addTo(map); labelMarkers[n.id] = l;
    });
}

// ── Side Panel Updates ────────────────────────────────────────
function updatePanel(data) {
    if (!data) return;
    const sys = data.system || {};
    const nodes = data.network?.nodes || [];
    const avgCi = nodes.length ? nodes.reduce((s, n) => s + (n.congestion_index || 0), 0) / nodes.length : 0;

    document.getElementById('statNodes').textContent = sys.total_nodes || 20;
    document.getElementById('statCongested').textContent = sys.congested_nodes || 0;
    const avgEl = document.getElementById('statAvgCi');
    avgEl.textContent = avgCi.toFixed(2);
    avgEl.style.color = ciColor(avgCi);
    document.getElementById('statIncidents').textContent = (data.active_incidents || []).length;
    document.getElementById('statWarnings').textContent = sys.early_warnings || 0;
    document.getElementById('statAlerts').textContent = sys.active_alert_count || 0;

    document.getElementById('tickValue').textContent = data.tick || 0;
    document.getElementById('cycleTime').textContent = (data.cycle_time_ms || 0).toFixed(0) + 'ms';
    document.getElementById('deviceText').textContent = data.mode || 'CPU';
    document.getElementById('horizonText').textContent = sys.prediction_horizon || '45min';

    updateSmartAlerts(data.smart_alerts || []);
    updateIncidents(data.active_incidents || []);
    updateNodeList(nodes, data.explanations || {});
}

function updateSmartAlerts(alerts) {
    const el = document.getElementById('smartAlertList');
    const badge = document.getElementById('alertBadge');
    badge.textContent = alerts.length;
    if (!alerts.length) {
        el.innerHTML = '<div class="empty-state"><span class="empty-icon">🔔</span>No predictive alerts</div>';
        return;
    }
    el.innerHTML = alerts.map(a => `
        <div class="alert-card smart">
            <div class="alert-type">⚡ ${a.type} — in ${a.minutes_ahead}min</div>
            <div class="alert-loc">${a.cause_icon} ${a.node_name}</div>
            <div class="alert-meta">Predicted CI: ${a.predicted_ci} · Confidence: ${(a.confidence * 100).toFixed(0)}%</div>
        </div>
    `).join('');
}

function updateIncidents(incidents) {
    const el = document.getElementById('incidentList');
    const badge = document.getElementById('incidentBadge');
    badge.textContent = incidents.length;
    if (!incidents.length) {
        el.innerHTML = '<div class="empty-state"><span class="empty-icon">✅</span>No active incidents</div>';
        return;
    }
    el.innerHTML = incidents.map(i => `
        <div class="alert-card incident">
            <div class="alert-type">🚨 ${(i.type || '').replace(/_/g, ' ')}</div>
            <div class="alert-loc">${i.node_name || i.node_id}</div>
            <div class="alert-meta">Conf: ${(i.confidence * 100).toFixed(0)}% · ${i.severity || ''}</div>
        </div>
    `).join('');
}

function updateNodeList(nodes, explanations) {
    const el = document.getElementById('nodeList');
    const sorted = [...nodes].sort((a, b) => (b.congestion_index || 0) - (a.congestion_index || 0));
    el.innerHTML = sorted.map(n => {
        const ci = n.congestion_index || 0;
        const exp = explanations[n.id] || {};
        const cause = exp.cause || {};
        return `
            <div class="node-item ${selectedNode === n.id ? 'active' : ''}" onclick="openDetail('${n.id}')" id="ni_${n.id}">
                <div class="node-dot" style="background:${ciColor(ci)};color:${ciColor(ci)}"></div>
                <div class="node-info">
                    <div class="node-name">${n.name}</div>
                    <div class="node-id">${n.id}</div>
                </div>
                <div class="node-ci" style="color:${ciColor(ci)}">${ci.toFixed(2)}</div>
                <div class="node-cause">${cause.icon || ''}</div>
                <div class="node-trend">${trendIcon(exp.prediction_trend)}</div>
            </div>
        `;
    }).join('');
}

// ── CCTV Canvas ───────────────────────────────────────────────
function drawCCTV(frameData) {
    if (!frameData) return;
    const canvas = document.getElementById('cctvCanvas');
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.clientWidth;
    const h = canvas.height = canvas.clientHeight;
    const sx = w / 640, sy = h / 400;

    // Background
    ctx.fillStyle = '#0a0f18';
    ctx.fillRect(0, 0, w, h);

    // Road surface
    ctx.fillStyle = '#181f2e';
    ctx.fillRect(0, h * 0.18, w, h * 0.7);

    // Lane markings
    ctx.setLineDash([16 * sx, 12 * sx]);
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    for (let i = 1; i <= 3; i++) {
        ctx.beginPath();
        ctx.moveTo(0, h * (0.18 + 0.175 * i));
        ctx.lineTo(w, h * (0.18 + 0.175 * i));
        ctx.stroke();
    }
    ctx.setLineDash([]);

    // Vehicles with bounding boxes
    const vehicles = frameData.vehicles || [];
    vehicles.forEach(v => {
        const x = v.x * sx, y = v.y * sy, vw = v.w * sx, vh = v.h * sy;

        // Vehicle body
        ctx.fillStyle = v.color;
        ctx.globalAlpha = v.stopped ? 0.6 : 0.85;
        ctx.fillRect(x, y, vw, vh);
        ctx.globalAlpha = 1;

        // Bounding box
        ctx.strokeStyle = v.stopped ? '#ef4444' : '#06d6a0';
        ctx.lineWidth = v.stopped ? 2 : 1;
        ctx.strokeRect(x - 2, y - 2, vw + 4, vh + 4);

        // Class label
        ctx.fillStyle = v.stopped ? '#ef4444' : '#06d6a0';
        ctx.font = `${9 * Math.min(sx, 1)}px JetBrains Mono, monospace`;
        ctx.fillText(v.cls, x, y - 4);

        // Stopped indicator
        if (v.stopped) {
            ctx.fillStyle = '#ef4444';
            ctx.font = `bold ${11 * Math.min(sx, 1)}px Inter, sans-serif`;
            ctx.fillText('⚠ STOPPED', x, y + vh + 12);
        }
    });

    // Anomaly overlays
    (frameData.anomalies || []).forEach(a => {
        if (a.type === 'sudden_clustering') {
            ctx.strokeStyle = 'rgba(234,179,8,0.5)';
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.arc(a.center_x * sx, a.center_y * sy, 80 * sx, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = '#eab308';
            ctx.font = `bold ${11 * Math.min(sx, 1)}px Inter`;
            ctx.fillText('⚠ CLUSTER DETECTED', (a.center_x - 60) * sx, (a.center_y - 90) * sy);
        }
    });

    // HUD overlay
    ctx.fillStyle = 'rgba(6,214,160,0.8)';
    ctx.font = `bold ${10 * Math.min(sx, 1)}px JetBrains Mono`;
    ctx.fillText(`VEHICLES: ${frameData.vehicle_count}`, 8, 14);
    ctx.fillText(`CI: ${frameData.congestion_index?.toFixed(3) || '—'}`, 8, 26);

    const ts = new Date(frameData.timestamp * 1000);
    ctx.fillStyle = 'rgba(148,163,184,0.5)';
    ctx.fillText(ts.toLocaleTimeString(), w - 80, 14);

    // Update CCTV header
    document.getElementById('cctvNodeName').textContent = frameData.node_name || '—';
    document.getElementById('cctvVehicleCount').textContent = frameData.vehicle_count || 0;
    document.getElementById('cctvCi').textContent = frameData.congestion_index?.toFixed(3) || '—';

    // Anomaly text
    const anomEl = document.getElementById('cctvAnomalies');
    const anomalies = frameData.anomalies || [];
    if (anomalies.length) {
        anomEl.textContent = anomalies.map(a => a.type === 'stopped_vehicle' ? '⚠ Stopped vehicle' : '⚠ Cluster').join(' · ');
    } else {
        anomEl.textContent = '';
    }
}

// ── Detail Modal ──────────────────────────────────────────────
function openDetail(nodeId) {
    selectedNode = nodeId;
    if (!currentData?.network) return;
    const node = currentData.network.nodes.find(n => n.id === nodeId);
    if (!node) return;
    const exp = currentData.explanations?.[nodeId] || {};
    const pred = currentData.predictions?.[nodeId] || [];
    const cause = exp.cause || {};

    document.getElementById('detailName').textContent = node.name;
    document.getElementById('detailSubtitle').textContent = `${nodeId} · ${exp.severity || '?'} severity · Confidence: ${((exp.prediction_confidence || 0) * 100).toFixed(0)}%`;

    // Cause badge
    document.getElementById('detailCauseIcon').textContent = cause.icon || '🚗';
    document.getElementById('detailCauseLabel').textContent = cause.label || 'Unknown';
    document.getElementById('detailCauseConf').textContent = `${((cause.confidence || 0) * 100).toFixed(0)}%`;
    const causeBadge = document.getElementById('detailCauseBadge');
    causeBadge.style.borderColor = (cause.color || '#64748b') + '40';
    causeBadge.style.color = cause.color || '#64748b';

    // Cross-modal flag
    const cmEl = document.getElementById('detailCrossModal');
    if (exp.cross_modal_flag) {
        cmEl.textContent = exp.cross_modal_flag;
        cmEl.className = `crossmodal-flag ${exp.validation_type || ''}`;
    } else {
        cmEl.className = 'crossmodal-flag hidden';
    }

    // Metrics
    const ci = node.congestion_index || 0;
    document.getElementById('detailCi').textContent = ci.toFixed(3);
    document.getElementById('detailCi').style.color = ciColor(ci);
    document.getElementById('detailSpeed').textContent = (node.speed_norm * 60).toFixed(0);
    document.getElementById('detailDensity').textContent = node.vehicle_count || 0;

    // Contribution
    const bd = exp.contribution_breakdown || {};
    document.getElementById('detailSpeedBar').style.width = (bd.speed_pct || 50) + '%';
    document.getElementById('detailDensityBar').style.width = (bd.density_pct || 50) + '%';
    document.getElementById('dSpeedPct').textContent = (bd.speed_pct || 50).toFixed(0);
    document.getElementById('dDensityPct').textContent = (bd.density_pct || 50).toFixed(0);

    document.getElementById('detailNarrative').textContent = exp.narrative || 'Analysis unavailable.';

    drawDetailChart(node.history || [], pred);
    document.getElementById('detailOverlay').classList.add('visible');

    if (map) map.panTo([node.lat, node.lon], { animate: true, duration: 0.5 });
    document.querySelectorAll('.node-item').forEach(e => e.classList.remove('active'));
    const li = document.getElementById(`ni_${nodeId}`);
    if (li) { li.classList.add('active'); li.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
}

function closeDetail(e) {
    if (e && e.target !== document.getElementById('detailOverlay')) return;
    document.getElementById('detailOverlay').classList.remove('visible');
    selectedNode = null;
}

function drawDetailChart(history, predictions) {
    const ctx = document.getElementById('detailChart').getContext('2d');
    if (detailChart) detailChart.destroy();

    const labels = [], hData = [], pData = [];
    for (let i = 0; i < history.length; i++) {
        labels.push(`-${(history.length - i) * 5}m`);
        hData.push(history[i]); pData.push(null);
    }
    for (let i = 0; i < predictions.length; i++) {
        labels.push(`+${(i + 1) * 5}m`);
        hData.push(null); pData.push(predictions[i]);
    }
    if (history.length && predictions.length) pData[history.length - 1] = history[history.length - 1];

    detailChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: 'Historical CI', data: hData, borderColor: '#06d6a0', backgroundColor: 'rgba(6,214,160,.08)', fill: true, tension: .4, pointRadius: 1.5, borderWidth: 2 },
                { label: 'Predicted CI', data: pData, borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,.08)', fill: true, tension: .4, pointRadius: 2.5, borderWidth: 2, borderDash: [6, 4] },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { display: true, position: 'top', labels: { color: '#94a3b8', font: { size: 9, family: 'Inter' }, usePointStyle: true, pointStyleWidth: 7 } } },
            scales: {
                x: { ticks: { color: '#64748b', font: { size: 8, family: 'JetBrains Mono' } }, grid: { color: 'rgba(148,163,184,.05)' } },
                y: { min: 0, max: 1, ticks: { color: '#64748b', font: { size: 8, family: 'JetBrains Mono' }, stepSize: .25 }, grid: { color: 'rgba(148,163,184,.05)' } },
            },
        },
    });
}

// ── Toggles ───────────────────────────────────────────────────
function togglePredictions() { showPredictions = !showPredictions; document.getElementById('btnPredictions').classList.toggle('active', showPredictions); if (currentData) updateMap(currentData); }
function toggleEdges() {
    showEdges = !showEdges; document.getElementById('btnEdges').classList.toggle('active', showEdges);
    if (showEdges && currentData) drawEdges(currentData.network.edges, currentData.network.nodes);
    else { edgeLines.forEach(l => map.removeLayer(l)); edgeLines = []; }
}
function toggleLabels() {
    showLabels = !showLabels; document.getElementById('btnLabels').classList.toggle('active', showLabels);
    if (showLabels && currentData) drawLabels(currentData.network.nodes);
    else { Object.values(labelMarkers).forEach(m => map.removeLayer(m)); labelMarkers = {}; }
}
function toggleHotspots() { showHotspots = !showHotspots; document.getElementById('btnHotspots').classList.toggle('active', showHotspots); if (currentData) updateMap(currentData); }

// ── Mode & Simulation ─────────────────────────────────────────
function setMode(m) {
    if (ws?.readyState === 1) ws.send(JSON.stringify({ action: 'set_mode', mode: m }));
    document.getElementById('modeBtnGpu').classList.toggle('active', m === 'GPU');
    document.getElementById('modeBtnLite').classList.toggle('active', m === 'LITE');
}
function simulateBlockage(nid) {
    if (ws?.readyState === 1) ws.send(JSON.stringify({ action: 'simulate_blockage', node_id: nid, duration: 12 }));
}
function switchCCTV(nid) {
    if (ws?.readyState === 1) ws.send(JSON.stringify({ action: 'switch_cctv', node_id: nid }));
}

// ── WebSocket ─────────────────────────────────────────────────
function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    setConn('connecting');
    ws = new WebSocket(`${proto}://${location.host}/ws/traffic`);
    ws.onopen = () => { setConn('connected'); hideLoading(); };
    ws.onmessage = (e) => {
        try {
            const d = JSON.parse(e.data);
            if (d.type === 'command_response') return;
            currentData = d;
            updateMap(d);
            updatePanel(d);
            drawCCTV(d.cctv_frame);
            if (selectedNode) openDetail(selectedNode);
        } catch (err) { console.error('Parse error:', err); }
    };
    ws.onclose = () => { setConn('disconnected'); setTimeout(connectWS, 3000); };
    ws.onerror = () => setConn('disconnected');
}

function setConn(s) {
    const d = document.getElementById('wsDot'), l = document.getElementById('wsLabel');
    const sd = document.getElementById('statusDot'), st = document.getElementById('statusText');
    d.className = `conn-dot ${s}`;
    if (s === 'connected') { l.textContent = 'Live'; sd.className = 'dot green'; st.textContent = 'System Active'; }
    else if (s === 'connecting') { l.textContent = '...'; sd.className = 'dot yellow'; st.textContent = 'Connecting...'; }
    else { l.textContent = 'Off'; sd.className = 'dot red'; st.textContent = 'Disconnected'; }
}

function hideLoading() { setTimeout(() => document.getElementById('loadingOverlay').classList.add('hidden'), 600); }

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    connectWS();
    setTimeout(hideLoading, 5000);
});
