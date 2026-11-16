// Cloud FinOps RAG dashboard. Renders data/finops_dataset.js (window.FINOPS_DATA).

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));
const usd = (n) => `$${n < 1 ? n.toFixed(3) : n.toFixed(2)}`;
// Models missing from the published-benchmark table get an estimated MMLU; the pipeline tags them with this category.
const isEstimate = (m) => m.category === 'API AI Model';

const state = { models: [], provider: '', query: '', sortKey: 'efficiency_score', sortDir: -1 };

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  let data = window.FINOPS_DATA;
  if (!data) {
    try { data = await (await fetch('data/finops_dataset.json')).json(); } catch (e) { data = null; }
  }
  if (data && data.models?.length) {
    state.models = data.models;
    renderHeader(data);
    renderPicks(data.models);
    renderScatter(data.models);
    initTable(data);
  } else {
    document.getElementById('tableBody').innerHTML = '<tr><td colspan="8" class="empty">The dataset could not be loaded.</td></tr>';
  }
  initBand();
  initReveal();
});

/* ---------- Theme ---------- */

function initTheme() {
  const root = document.documentElement;
  const dark = matchMedia('(prefers-color-scheme: dark)');
  document.getElementById('themeToggle').addEventListener('click', () => {
    const next = (root.dataset.theme || (dark.matches ? 'dark' : 'light')) === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
  });
}

/* ---------- Header facts ---------- */

function renderHeader(data) {
  if (data.generated_at) {
    const d = new Date(data.generated_at);
    document.getElementById('updated').textContent =
      `Updated ${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}`;
  }
  document.getElementById('modelCount').textContent = `the top ${data.models.length}`;
  document.getElementById('providerCount').textContent = String((data.providers || []).length);
}

/* ---------- Today's picks (band) ---------- */

function picksFrom(models) {
  const known = models.filter((m) => !isEstimate(m));
  const pool = known.length ? known : models;
  const bestValue = [...pool].sort((a, b) => b.efficiency_score - a.efficiency_score)[0];
  const topMmlu = Math.max(...pool.map((m) => m.mmlu_score));
  const top = pool.filter((m) => m.mmlu_score === topMmlu).sort((a, b) => a.blended_cost_per_1m - b.blended_cost_per_1m)[0];
  const nearTop = pool
    .filter((m) => m.mmlu_score >= topMmlu - 2 && m !== top)
    .sort((a, b) => a.blended_cost_per_1m - b.blended_cost_per_1m)[0];
  return { bestValue, top, nearTop };
}

function renderPicks(models) {
  const { bestValue, top, nearTop } = picksFrom(models);
  const cards = [
    {
      value: usd(bestValue.blended_cost_per_1m),
      label: `per million tokens for ${bestValue.model}, scoring ${bestValue.mmlu_score} on MMLU. The best value today.`,
      context: bestValue.provider,
    },
    {
      value: String(top.mmlu_score),
      label: `MMLU, the highest today: ${top.model} at ${usd(top.blended_cost_per_1m)} per million tokens.`,
      context: top.provider,
    },
  ];
  if (nearTop && nearTop.blended_cost_per_1m < top.blended_cost_per_1m) {
    const ratio = top.blended_cost_per_1m / nearTop.blended_cost_per_1m;
    cards.push({
      value: `${ratio >= 10 ? Math.round(ratio) : ratio.toFixed(1)}×`,
      label: `cheaper than the top model: ${nearTop.model} scores ${nearTop.mmlu_score}, within two points, at ${usd(nearTop.blended_cost_per_1m)} per million.`,
      context: nearTop.provider,
    });
  }
  document.getElementById('picks').innerHTML = cards.map((c) => `
    <div class="outcome">
      <dt class="outcome-label">${esc(c.label)}</dt>
      <dd class="outcome-value">${esc(c.value)}</dd>
      <dd class="outcome-context">${esc(c.context)}</dd>
    </div>`).join('');
  state.picks = new Set([bestValue, top, nearTop].filter(Boolean));
}

/* ---------- Scatter: blended price (log) vs MMLU ---------- */

function renderScatter(models) {
  const W = 1080, H = 460, m = { t: 20, r: 24, b: 56, l: 56 };
  const xs = models.map((d) => Math.log10(d.blended_cost_per_1m));
  const ys = models.map((d) => d.mmlu_score);
  const x0 = Math.floor(Math.min(...xs)), x1 = Math.ceil(Math.max(...xs));
  const y0 = Math.floor((Math.min(...ys) - 1) / 5) * 5, y1 = Math.min(100, Math.ceil((Math.max(...ys) + 1) / 5) * 5);
  const X = (v) => m.l + ((Math.log10(v) - x0) / (x1 - x0)) * (W - m.l - m.r);
  const Y = (v) => H - m.b - ((v - y0) / (y1 - y0)) * (H - m.t - m.b);

  const xTicks = [];
  for (let k = x0; k <= x1; k++) {
    xTicks.push(10 ** k);
    if (k < x1) xTicks.push(3 * 10 ** k);
  }
  const fmtTick = (v) => (v >= 1 ? `$${v}` : `$${Number(v.toPrecision(1))}`);
  const yTicks = [];
  for (let v = y0; v <= y1; v += 5) yTicks.push(v);

  const picks = state.picks || new Set();
  // Draw estimated and ordinary dots first, picks last so they sit on top.
  const order = [...models].sort((a, b) => (picks.has(a) ? 1 : 0) - (picks.has(b) ? 1 : 0));

  const svg = `
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
      <g class="grid">
        ${xTicks.map((v) => `<line x1="${X(v)}" x2="${X(v)}" y1="${m.t}" y2="${H - m.b}"/>`).join('')}
        ${yTicks.map((v) => `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}"/>`).join('')}
      </g>
      ${xTicks.map((v) => `<text class="axis-label" x="${X(v)}" y="${H - m.b + 20}" text-anchor="middle">${fmtTick(v)}</text>`).join('')}
      ${yTicks.map((v) => `<text class="axis-label" x="${m.l - 10}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`).join('')}
      <text class="axis-title" x="${(m.l + W - m.r) / 2}" y="${H - 10}" text-anchor="middle">Blended price per million tokens (log scale) →</text>
      <text class="axis-title" x="${-(m.t + H - m.b) / 2}" y="16" text-anchor="middle" transform="rotate(-90)">MMLU score →</text>
      ${order.map((d) => {
        const i = models.indexOf(d);
        const cls = ['dot', picks.has(d) ? 'is-pick' : '', isEstimate(d) ? 'is-est' : ''].join(' ');
        return `<circle class="${cls}" cx="${X(d.blended_cost_per_1m)}" cy="${Y(d.mmlu_score)}" r="${picks.has(d) ? 7 : 5}" tabindex="0" data-i="${i}"
          aria-label="${esc(`${d.model}, ${d.provider}: MMLU ${d.mmlu_score}${isEstimate(d) ? ' (estimate)' : ''}, ${usd(d.blended_cost_per_1m)} per million`)}"/>`;
      }).join('')}
      ${[...picks].map((d) => {
        const cx = X(d.blended_cost_per_1m), right = cx > W * 0.7;
        return `<text class="pick-label" x="${cx + (right ? -12 : 12)}" y="${Y(d.mmlu_score) - 10}" text-anchor="${right ? 'end' : 'start'}">${esc(d.model)}</text>`;
      }).join('')}
    </svg>
    <p class="legend" aria-hidden="true">
      <span><i class="l-pick"></i>Today’s picks</span>
      <span><i class="l-model"></i>Model with published MMLU</span>
      <span><i class="l-est"></i>Estimated MMLU</span>
    </p>`;
  const host = document.getElementById('scatter');
  host.innerHTML = svg;

  const tip = document.getElementById('tip');
  const show = (el) => {
    const d = models[Number(el.dataset.i)];
    tip.innerHTML = `<strong>${esc(d.model)}</strong><span>${esc(d.provider)}<br>MMLU ${d.mmlu_score}${isEstimate(d) ? ' (est.)' : ''} · ${usd(d.blended_cost_per_1m)} / 1M · value ${d.efficiency_score}</span>`;
    tip.hidden = false;
    const r = el.getBoundingClientRect();
    tip.style.left = `${Math.min(Math.max(8, r.left + r.width / 2 - tip.offsetWidth / 2), innerWidth - tip.offsetWidth - 8)}px`;
    tip.style.top = `${r.top - tip.offsetHeight - 10}px`;
  };
  const hide = () => { tip.hidden = true; };
  host.querySelectorAll('.dot').forEach((el) => {
    el.addEventListener('mouseenter', () => show(el));
    el.addEventListener('focus', () => show(el));
    el.addEventListener('mouseleave', hide);
    el.addEventListener('blur', hide);
  });
  addEventListener('scroll', hide, { passive: true });
}

/* ---------- Table ---------- */

function initTable(data) {
  const select = document.getElementById('providerSelect');
  [...(data.providers || [])].sort().forEach((p) => select.add(new Option(p, p)));
  select.addEventListener('change', () => { state.provider = select.value; renderTable(); });
  document.getElementById('searchInput').addEventListener('input', (e) => { state.query = e.target.value.trim().toLowerCase(); renderTable(); });

  document.querySelectorAll('.data th button').forEach((btn) => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.sort;
      const textCol = key === 'model' || key === 'provider';
      state.sortDir = state.sortKey === key ? -state.sortDir : (textCol || key.includes('cost') ? 1 : -1);
      state.sortKey = key;
      document.querySelectorAll('.data th button').forEach((b) => b.removeAttribute('aria-sort'));
      btn.setAttribute('aria-sort', state.sortDir === 1 ? 'ascending' : 'descending');
      renderTable();
    });
  });
  renderTable();
}

function renderTable() {
  const { sortKey: k, sortDir: dir } = state;
  const rows = state.models
    .filter((m) => !state.provider || m.provider === state.provider)
    .filter((m) => !state.query || `${m.model} ${m.provider} ${m.category}`.toLowerCase().includes(state.query))
    .sort((a, b) => (typeof a[k] === 'string' ? a[k].localeCompare(b[k]) : a[k] - b[k]) * dir);

  const maxLog = Math.log10(Math.max(...state.models.map((m) => m.efficiency_score)) + 1);
  document.getElementById('resultCount').textContent = `${rows.length} of ${state.models.length} models`;
  document.getElementById('tableBody').innerHTML = rows.length ? rows.map((m) => `
    <tr>
      <td><span class="model">${esc(m.model)}</span><span class="cat">${esc(isEstimate(m) ? 'Not in benchmark table' : m.category)}</span></td>
      <td class="prov">${esc(m.provider)}</td>
      <td class="num">${m.mmlu_score}${isEstimate(m) ? ' <span class="est">est.</span>' : ''}</td>
      <td class="num">${usd(m.input_cost_per_1m)}</td>
      <td class="num">${usd(m.output_cost_per_1m)}</td>
      <td class="num">${usd(m.blended_cost_per_1m)}</td>
      <td class="num">${Math.round(m.avg_throughput_tps)}</td>
      <td class="num"><span class="eff"><span class="eff-bar" aria-hidden="true"><i style="width:${(Math.log10(m.efficiency_score + 1) / maxLog) * 100}%"></i></span>${m.efficiency_score.toLocaleString('en-GB')}</span></td>
    </tr>`).join('') : '<tr><td colspan="8" class="empty">No models match.</td></tr>';
}

/* ---------- Band and reveal motion ---------- */

function initBand() {
  const band = document.querySelector('.outcomes');
  if (!document.documentElement.classList.contains('motion')) { band.classList.add('in'); return; }
  const open = () => { band.classList.add('in'); removeEventListener('scroll', check); };
  const check = () => { if (scrollY > 80 || band.getBoundingClientRect().top < innerHeight * 0.45) open(); };
  addEventListener('scroll', check, { passive: true });
  check();
}

function initReveal() {
  const els = document.querySelectorAll('.reveal');
  if (!document.documentElement.classList.contains('motion')) { els.forEach((el) => el.classList.add('in')); return; }
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
  }), { rootMargin: '0px 0px -8% 0px' });
  els.forEach((el) => io.observe(el));
}
