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

async function main() {
  const data = await fetch('data.json').then(r => r.json());
  document.getElementById('subtitle').textContent =
    `Brand: ${data.brand} · generated ${new Date(data.generated_at)
      .toLocaleString()}`;

  const cities = [...new Set(data.presence.map(p => p.city))];
  const models = [...new Set(data.presence.map(p => p.model))];
  const lookup = {};
  data.presence.forEach(p => { lookup[`${p.city}|${p.model}`] = p; });

  // ---- Heatmap table ----
  let html = '<table><thead><tr><th>City \\ Engine</th>' +
    models.map(m => `<th>${esc(m)}</th>`).join('') + '</tr></thead><tbody>';
  for (const city of cities) {
    html += `<tr><th>${esc(city)}</th>`;
    for (const m of models) {
      const cell = lookup[`${city}|${m}`];
      if (!cell) { html += '<td>—</td>'; continue; }
      const pr = (cell.presence_rate * 100).toFixed(0);
      const cr = (cell.citation_rate * 100).toFixed(0);
      html += `<td class="heat" style="background:${heatColor(
        cell.presence_rate)}" title="n=${cell.n}">${pr}% <small>(${cr}%)</small> <small>n=${cell.n}</small></td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  document.getElementById('heatmap').innerHTML = html;

  // ---- Competitor leaderboard ----
  const board = document.getElementById('leaderboard');
  for (const city of Object.keys(data.leaderboard)) {
    const card = document.createElement('div');
    card.className = 'city-card';
    const top = data.leaderboard[city].slice(0, 8);
    const max = Math.max(...top.map(p => p.mentions), 1);
    card.innerHTML = `<h3>${esc(city)}</h3>` + top.map(p => {
      const isPinch = /pinch/i.test(p.name);
      const w = (p.mentions / max * 100).toFixed(0);
      return `<div class="bar ${isPinch ? 'pinch' : ''}">
        <i style="width:${w}%"></i>
        <span>${esc(p.name)} · ${p.mentions}</span></div>`;
    }).join('');
    board.appendChild(card);
  }
}

main();
