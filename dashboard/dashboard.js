function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function heatColor(rate) {
  // 0 -> light grey, 1 -> Pinch orange
  const r = Math.round(0xf0 + (0xc4 - 0xf0) * rate);
  const g = Math.round(0xf0 + (0x41 - 0xf0) * rate);
  const b = Math.round(0xf0 + (0x0c - 0xf0) * rate);
  return `rgb(${r},${g},${b})`;
}

const pct = x => (x * 100).toFixed(0) + '%';
const isPinch = name => /pinch/i.test(name);

// ---- Presence heatmap (city x engine) ----
function renderHeatmap(data) {
  const cities = [...new Set(data.presence.map(p => p.city))];
  const models = [...new Set(data.presence.map(p => p.model))];
  const lookup = {};
  data.presence.forEach(p => { lookup[`${p.city}|${p.model}`] = p; });

  let html = '<table><thead><tr><th>City \\ Engine</th>' +
    models.map(m => `<th>${esc(m)}</th>`).join('') + '</tr></thead><tbody>';
  for (const city of cities) {
    html += `<tr><th>${esc(city)}</th>`;
    for (const m of models) {
      const cell = lookup[`${city}|${m}`];
      if (!cell) { html += '<td>—</td>'; continue; }
      html += `<td class="heat" style="background:${heatColor(cell.presence_rate)}"
        title="n=${cell.n}">${pct(cell.presence_rate)}
        <small>(${pct(cell.citation_rate)})</small>
        <small>n=${cell.n}</small></td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  document.getElementById('heatmap').innerHTML = html;
}

// ---- Presence by engine (all cities) ----
function renderEngineTable(data) {
  const rows = data.presence_by_engine || [];
  let html = '<table><thead><tr><th>Engine</th><th>Presence</th>' +
    '<th>Citation</th><th>n</th></tr></thead><tbody>';
  for (const r of rows) {
    html += `<tr><td>${esc(r.model)}</td>
      <td style="background:${heatColor(r.presence_rate)};color:#fff;font-weight:600">
      ${pct(r.presence_rate)}</td>
      <td>${pct(r.citation_rate)}</td><td>${r.n}</td></tr>`;
  }
  html += '</tbody></table>';
  document.getElementById('engine-table').innerHTML = html;
}

// ---- Competitor leaderboard ----
function lbRow(p, max) {
  const w = (p.mentions / max * 100).toFixed(0);
  const cls = isPinch(p.name) ? 'lb-row pinch' : 'lb-row';
  return `<div class="${cls}">
    <span class="lb-name" title="${esc(p.name)}">${esc(p.name)}</span>
    <span class="lb-bar"><i style="width:${w}%"></i></span>
    <span class="lb-val">${p.mentions} · ${pct(p.share_of_voice)}</span></div>`;
}

function renderLeaderboard(data) {
  const board = document.getElementById('leaderboard');
  board.innerHTML = '';
  for (const city of Object.keys(data.leaderboard)) {
    const all = data.leaderboard[city];
    const max = Math.max(...all.map(p => p.mentions), 1);
    const top = all.slice(0, 15);
    const rest = all.slice(15);
    const card = document.createElement('div');
    card.className = 'city-card';
    let html = `<h3>${esc(city)}</h3>
      <div class="count">${all.length} providers named</div>` +
      top.map(p => lbRow(p, max)).join('');
    if (rest.length) {
      html += `<details class="more"><summary>show ${rest.length} more</summary>` +
        rest.map(p => lbRow(p, max)).join('') + '</details>';
    }
    card.innerHTML = html;
    board.appendChild(card);
  }
}

// ---- Queries reference ----
function renderQueries(data) {
  const bySeg = {};
  (data.queries || []).forEach(q => {
    (bySeg[q.segment] = bySeg[q.segment] || []).push(q);
  });
  let html = '';
  for (const seg of Object.keys(bySeg)) {
    html += `<div class="qseg"><b>${esc(seg.replace(/_/g, ' '))}</b></div>
      <ul class="qlist">` +
      bySeg[seg].map(q =>
        `<li><code>${esc(q.id)}</code> — ${esc(q.template)}</li>`).join('') +
      '</ul>';
  }
  document.getElementById('queries').innerHTML = html;
}

// ---- Answer drill-down ----
function optionList(values) {
  return ['<option value="">all</option>']
    .concat(values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`))
    .join('');
}

function renderDrilldown(data) {
  const details = data.details || [];
  const cities = [...new Set(details.map(d => d.city))].sort();
  const models = [...new Set(details.map(d => d.model))].sort();
  const queries = [...new Set(details.map(d => d.query_id))].sort();

  const filters = document.getElementById('filters');
  filters.innerHTML = `
    <label>City <select id="f-city">${optionList(cities)}</select></label>
    <label>Engine <select id="f-model">${optionList(models)}</select></label>
    <label>Query <select id="f-query">${optionList(queries)}</select></label>
    <label><input type="checkbox" id="f-pinch"> Pinch present only</label>
    <input type="search" id="f-text" placeholder="search answer / provider text" size="28">`;

  ['f-city', 'f-model', 'f-query', 'f-pinch', 'f-text']
    .forEach(id => document.getElementById(id).addEventListener('input', draw));

  function draw() {
    const [city, model, query] = ['f-city', 'f-model', 'f-query']
      .map(id => document.getElementById(id).value);
    const pinchOnly = document.getElementById('f-pinch').checked;
    const q = document.getElementById('f-text').value.trim().toLowerCase();

    const rows = details.filter(d =>
      (!city || d.city === city) &&
      (!model || d.model === model) &&
      (!query || d.query_id === query) &&
      (!pinchOnly || d.pinch_present) &&
      (!q || (d.answer || '').toLowerCase().includes(q) ||
             d.providers.some(p => p.toLowerCase().includes(q))));

    document.getElementById('drill-count').textContent =
      `${rows.length} of ${details.length} answers` +
      (rows.length ? ` · ${rows.filter(r => r.pinch_present).length} name Pinch` : '');

    document.getElementById('drilldown').innerHTML = rows.map(ansCard).join('');
  }
  draw();
}

function ansCard(d) {
  const badge = d.pinch_present
    ? `<span class="badge yes">Pinch: yes${d.pinch_position ?
        ' · #' + d.pinch_position : ''}</span>`
    : `<span class="badge no">Pinch: no</span>`;
  const chips = d.providers.map(p =>
    `<span class="chip ${isPinch(p) ? 'pinch' : ''}">${esc(p)}</span>`).join('');
  const cites = (d.citations || []).length
    ? `<details><summary>${d.citations.length} citations</summary>` +
      d.citations.map(c => `<div class="cite">${esc(c)}</div>`).join('') +
      '</details>'
    : '';
  return `<div class="ans">
    <div class="ans-head">
      <span class="tag city">${esc(d.city)}</span>
      <span class="tag">${esc(d.model)}</span>
      <span class="tag">${esc(d.query_id)}</span>
      ${badge}
      ${d.pinch_cited ? '<span class="tag">bookpinch.com cited</span>' : ''}
    </div>
    <div class="q">${esc(d.query)}</div>
    ${d.evidence_quote ? `<div class="ev">${esc(d.evidence_quote)}</div>` : ''}
    <div class="chips">${chips || '<span class="tag">no providers parsed</span>'}</div>
    <details><summary>full answer</summary><pre>${esc(d.answer || '')}</pre>${cites}</details>
  </div>`;
}

async function main() {
  const data = await fetch('data.json').then(r => r.json());
  document.getElementById('subtitle').textContent =
    `Brand: ${data.brand} · generated ${new Date(data.generated_at).toLocaleString()}`;
  renderHeatmap(data);
  renderEngineTable(data);
  renderLeaderboard(data);
  renderQueries(data);
  renderDrilldown(data);
}

main();
