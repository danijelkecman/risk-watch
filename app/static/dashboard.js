const state = {
  history: [],
};

function colorForSeverity(sev) {
  return {
    green: '#29c46d',
    amber: '#f3b33d',
    red: '#ff5c5c',
    deep_red: '#7d0f18'
  }[sev] || '#9db0cb';
}

function fmtPct(v) { return `${Number(v).toFixed(1)}%`; }
function fmtBps(v) { return `${Math.round(v)} bps`; }
function fmtBn(v) { return `$${Number(v).toFixed(2)}bn`; }

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function renderAlerts(alerts) {
  const root = document.getElementById('alerts');
  root.innerHTML = '';
  alerts.forEach(a => {
    const div = document.createElement('div');
    div.className = 'alert';
    div.style.borderLeft = `5px solid ${colorForSeverity(a.severity)}`;
    div.innerHTML = `<h4>${a.title}</h4><p>${a.message}</p>`;
    root.appendChild(div);
  });
}

function linePath(points) {
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
}

function renderScoreChart() {
  const svg = document.getElementById('score-chart');
  const w = 520, h = 210, pad = 24;
  svg.innerHTML = '';
  const history = state.history.slice(-80);
  if (!history.length) return;

  [30, 55, 75].forEach(level => {
    const y = h - pad - (level / 100) * (h - pad * 2);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', pad); line.setAttribute('x2', w - pad);
    line.setAttribute('y1', y); line.setAttribute('y2', y);
    line.setAttribute('stroke', '#21344f'); line.setAttribute('stroke-dasharray', '4 4');
    svg.appendChild(line);
  });

  const pts = history.map((d, i) => ({
    x: pad + (i / Math.max(history.length - 1, 1)) * (w - pad * 2),
    y: h - pad - (d.overall_score / 100) * (h - pad * 2)
  }));

  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', linePath(pts));
  path.setAttribute('fill', 'none');
  path.setAttribute('stroke', '#91d0ff');
  path.setAttribute('stroke-width', '3');
  svg.appendChild(path);

  const latest = history[history.length - 1];
  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  circle.setAttribute('cx', pts[pts.length - 1].x);
  circle.setAttribute('cy', pts[pts.length - 1].y);
  circle.setAttribute('r', 5);
  circle.setAttribute('fill', colorForSeverity(latest.severity));
  svg.appendChild(circle);
}

function renderRadarChart(latest) {
  const svg = document.getElementById('radar-chart');
  const w = 280, h = 210, cx = 140, cy = 110, r = 74;
  svg.innerHTML = '';
  const axes = [
    ['Liquidity', latest.breakdown.liquidity_mismatch],
    ['Contagion', latest.breakdown.contagion],
    ['Sector', latest.breakdown.sector_damage],
    ['Market', latest.breakdown.market_stress],
    ['Oversight', latest.breakdown.oversight_heat],
  ];

  [20, 40, 60, 80, 100].forEach(level => {
    const rr = r * (level / 100);
    const pts = axes.map((_, i) => {
      const angle = (-Math.PI / 2) + (i * 2 * Math.PI / axes.length);
      return `${cx + Math.cos(angle) * rr},${cy + Math.sin(angle) * rr}`;
    }).join(' ');
    const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    poly.setAttribute('points', pts);
    poly.setAttribute('fill', 'none');
    poly.setAttribute('stroke', '#21344f');
    svg.appendChild(poly);
  });

  axes.forEach(([label], i) => {
    const angle = (-Math.PI / 2) + (i * 2 * Math.PI / axes.length);
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', cx); line.setAttribute('y1', cy);
    line.setAttribute('x2', x); line.setAttribute('y2', y);
    line.setAttribute('stroke', '#21344f');
    svg.appendChild(line);

    const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    txt.setAttribute('x', cx + Math.cos(angle) * (r + 18));
    txt.setAttribute('y', cy + Math.sin(angle) * (r + 18));
    txt.setAttribute('text-anchor', 'middle');
    txt.setAttribute('fill', '#dbe6f7');
    txt.setAttribute('font-size', '11');
    txt.textContent = label;
    svg.appendChild(txt);
  });

  const shape = axes.map(([, value], i) => {
    const angle = (-Math.PI / 2) + (i * 2 * Math.PI / axes.length);
    const rr = r * (value / 100);
    return `${cx + Math.cos(angle) * rr},${cy + Math.sin(angle) * rr}`;
  }).join(' ');
  const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
  poly.setAttribute('points', shape);
  poly.setAttribute('fill', 'rgba(255, 92, 92, 0.25)');
  poly.setAttribute('stroke', colorForSeverity(latest.severity));
  poly.setAttribute('stroke-width', '2.5');
  svg.appendChild(poly);
}

function renderLadderChart(latest) {
  const svg = document.getElementById('ladder-chart');
  svg.innerHTML = '';
  const items = [
    ['Redemptions', latest.snapshot.redemption_rate_pct, 25],
    ['Peer spread', latest.snapshot.peer_redemption_avg_pct, 15],
    ['Sector damage', latest.snapshot.software_sector_stress, 70],
    ['Discounts', latest.snapshot.secondary_discount_pct, 12],
    ['Oversight', latest.snapshot.regulator_attention, 60],
  ];

  items.forEach(([label, value, danger], i) => {
    const y = 24 + i * 34;
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('x', 110); bg.setAttribute('y', y); bg.setAttribute('width', 170); bg.setAttribute('height', 18);
    bg.setAttribute('rx', 9); bg.setAttribute('fill', '#15304d');
    svg.appendChild(bg);

    const dangerX = 110 + Math.min(danger, 100) / 100 * 170;
    const dline = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    dline.setAttribute('x1', dangerX); dline.setAttribute('x2', dangerX);
    dline.setAttribute('y1', y - 3); dline.setAttribute('y2', y + 21);
    dline.setAttribute('stroke', '#ffb0b0'); dline.setAttribute('stroke-width', '2');
    svg.appendChild(dline);

    const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bar.setAttribute('x', 110); bar.setAttribute('y', y); bar.setAttribute('width', (Math.min(Number(value), 100) / 100) * 170); bar.setAttribute('height', 18);
    bar.setAttribute('rx', 9); bar.setAttribute('fill', colorForSeverity(latest.severity));
    svg.appendChild(bar);

    const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    txt.setAttribute('x', 14); txt.setAttribute('y', y + 13);
    txt.setAttribute('fill', '#dbe6f7'); txt.setAttribute('font-size', '12');
    txt.textContent = label;
    svg.appendChild(txt);

    const val = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    val.setAttribute('x', 292); val.setAttribute('y', y + 13);
    val.setAttribute('text-anchor', 'end'); val.setAttribute('fill', '#dbe6f7'); val.setAttribute('font-size', '12');
    val.textContent = Number(value).toFixed(1);
    svg.appendChild(val);
  });
}

function render(latest) {
  setText('timestamp', `UTC ${new Date(latest.timestamp).toLocaleString()}`);
  setText('overall-score', latest.overall_score.toFixed(1));
  const pill = document.getElementById('severity-pill');
  pill.textContent = latest.severity.replace('_', ' ').toUpperCase();
  pill.style.background = colorForSeverity(latest.severity);
  pill.style.color = latest.severity === 'amber' ? '#111' : '#fff';

  setText('m-redemptions', fmtPct(latest.snapshot.redemption_rate_pct));
  setText('m-peer', fmtPct(latest.snapshot.peer_redemption_avg_pct));
  setText('m-secondary', fmtPct(latest.snapshot.secondary_discount_pct));
  setText('m-spread', fmtBps(latest.snapshot.funding_spread_bps));
  setText('notes-text', latest.annotations.join(' '));

  renderAlerts(latest.alerts);
  renderScoreChart();
  renderRadarChart(latest);
  renderLadderChart(latest);
}

async function boot() {
  const resp = await fetch('/api/state');
  const data = await resp.json();
  state.history = data.history || [];
  if (data.latest) render(data.latest);

  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${wsProto}://${location.host}/ws`);
  ws.onmessage = (event) => {
    const latest = JSON.parse(event.data);
    state.history.push(latest);
    state.history = state.history.slice(-120);
    render(latest);
  };
}

boot();


async function startReplay() {
  const token = document.getElementById("token").value.trim();
  const limit = Number(document.getElementById("replay-limit").value || 120);
  const speed_multiplier = Number(document.getElementById("replay-speed").value || 8);
  const resp = await fetch("/api/replay", {
    method: "POST",
    headers: {"Content-Type": "application/json", "Authorization": `Bearer ${token}`},
    body: JSON.stringify({limit, speed_multiplier})
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.detail || "Replay failed"); return; }
  setText("mode-label", `Mode: ${data.mode}`);
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("replay-btn");
  if (btn) btn.addEventListener("click", startReplay);
});
