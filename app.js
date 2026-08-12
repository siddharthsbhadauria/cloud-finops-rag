// ==========================================================================
// Cloud FinOps & AI Tokenomics Evaluator - Frontend Engine
// ==========================================================================

let appState = {
  models: [],
  filtered: [],
  selectedProvider: 'ALL',
  searchQuery: '',
  sortBy: 'eff-desc'
};

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initApp();
});

function initTheme() {
  const savedTheme = localStorage.getItem('theme');
  const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
  const initialTheme = savedTheme || (prefersLight ? 'light' : 'dark');

  document.documentElement.setAttribute('data-theme', initialTheme);

  const themeToggleBtn = document.getElementById('themeToggle');
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      showToast(newTheme === 'dark' ? '🌙 Dark Mode Activated' : '☀️ Light Mode Activated');
    });
  }
}

function showToast(message) {
  const toast = document.getElementById('toast');
  const toastMsg = document.getElementById('toastMessage');
  if (!toast || !toastMsg) return;

  toastMsg.textContent = message;
  toast.classList.add('show');

  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

async function initApp() {
  setupEventListeners();

  let data = window.FINOPS_DATA;

  if (!data) {
    try {
      const response = await fetch('data/finops_dataset.json');
      if (response.ok) {
        data = await response.json();
      }
    } catch (err) {
      console.warn('Could not fetch json file:', err);
    }
  }

  if (data) {
    appState.models = data.models || [];
    renderStats(data);
    renderRagSummary(data.summary);
    renderProviderPills(data.providers || []);
    applyFiltersAndSort();
  }
}

function renderStats(data) {
  document.getElementById('statModels').textContent = data.total_models_tracked || 0;
  document.getElementById('statProviders').textContent = (data.providers || []).length;

  if (data.models && data.models.length > 0) {
    const topEff = Math.max(...data.models.map(m => m.efficiency_score));
    document.getElementById('statTopEfficiency').textContent = topEff.toFixed(1);
  }

  if (data.generated_at) {
    const dateObj = new Date(data.generated_at);
    document.getElementById('lastUpdatedTag').textContent = `Last updated: ${dateObj.toLocaleDateString()} ${dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }
}

function renderRagSummary(summary) {
  if (!summary || !summary.markdown_brief) return;
  const rawMarkdown = summary.markdown_brief;
  // Convert markdown bullet highlights to clean HTML
  const formattedHtml = rawMarkdown
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\* (.*$)/gim, '<li>$1</li>')
    .replace(/^- (.*$)/gim, '<li>$1</li>')
    .replace(/\n\n/g, '<br>');

  document.getElementById('ragBriefContent').innerHTML = formattedHtml;
}

function renderProviderPills(providers) {
  const container = document.getElementById('providerContainer');
  container.querySelectorAll('.cat-pill:not([data-provider="ALL"])').forEach(el => el.remove());

  providers.sort().forEach(prov => {
    const btn = document.createElement('button');
    btn.className = 'cat-pill';
    btn.dataset.provider = prov;
    btn.textContent = prov;
    btn.addEventListener('click', () => {
      container.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      appState.selectedProvider = prov;
      applyFiltersAndSort();
    });
    container.appendChild(btn);
  });
}

function setupEventListeners() {
  const searchInput = document.getElementById('searchInput');
  const clearBtn = document.getElementById('clearSearch');
  const sortSelect = document.getElementById('sortSelect');
  const allCatBtn = document.querySelector('.cat-pill[data-provider="ALL"]');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      appState.searchQuery = e.target.value.toLowerCase().trim();
      if (clearBtn) clearBtn.classList.toggle('show', appState.searchQuery.length > 0);
      applyFiltersAndSort();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      appState.searchQuery = '';
      clearBtn.classList.remove('show');
      applyFiltersAndSort();
    });
  }

  if (allCatBtn) {
    allCatBtn.addEventListener('click', () => {
      document.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active'));
      allCatBtn.classList.add('active');
      appState.selectedProvider = 'ALL';
      applyFiltersAndSort();
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      appState.sortBy = e.target.value;
      applyFiltersAndSort();
    });
  }
}

function applyFiltersAndSort() {
  let list = [...appState.models];

  if (appState.selectedProvider !== 'ALL') {
    list = list.filter(item => item.provider === appState.selectedProvider);
  }

  if (appState.searchQuery) {
    const q = appState.searchQuery;
    list = list.filter(item =>
      item.model.toLowerCase().includes(q) ||
      item.provider.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q)
    );
  }

  switch (appState.sortBy) {
    case 'eff-desc':
      list.sort((a, b) => b.efficiency_score - a.efficiency_score);
      break;
    case 'cost-asc':
      list.sort((a, b) => a.blended_cost_per_1m - b.blended_cost_per_1m);
      break;
    case 'mmlu-desc':
      list.sort((a, b) => b.mmlu_score - a.mmlu_score);
      break;
    case 'tps-desc':
      list.sort((a, b) => b.avg_throughput_tps - a.avg_throughput_tps);
      break;
  }

  appState.filtered = list;
  document.getElementById('resultsCount').textContent = `Showing ${list.length} of ${appState.models.length} tracked models`;

  renderTable(list);
}

function renderTable(items) {
  const tbody = document.getElementById('tableBody');
  tbody.innerHTML = items.map(item => `
    <tr>
      <td style="font-weight: 700; color: var(--text-main);">${item.model}</td>
      <td><span class="pill-provider">${item.provider}</span></td>
      <td style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-cyan);">${item.mmlu_score}</td>
      <td style="font-family: var(--font-mono); font-weight: 700; color: var(--text-main);">${item.tokens_per_dollar_formatted}</td>
      <td style="font-family: var(--font-mono);">$${item.input_cost_per_1m.toFixed(3)}</td>
      <td style="font-family: var(--font-mono);">$${item.output_cost_per_1m.toFixed(3)}</td>
      <td style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-amber);">$${item.blended_cost_per_1m.toFixed(3)}</td>
      <td><span class="score-badge">⚡ ${item.efficiency_score}</span></td>
    </tr>
  `).join('');
}
