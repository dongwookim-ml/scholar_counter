/* Scholar Citation Tracker dashboard.
   All user-supplied text goes through textContent, never innerHTML. */

(() => {
    'use strict';

    const SVG_NS = 'http://www.w3.org/2000/svg';
    const STATUS_POLL_MS = 60_000;

    const el = (id) => document.getElementById(id);
    const charts = new Map();

    const GRANULARITIES = ['daily', 'monthly', 'yearly'];
    const CHANGE_HEADING = { daily: 'Change per day', monthly: 'Change per month', yearly: 'Change per year' };

    let papers = [];
    let sortKey = 'citations';
    let filterText = '';
    let granularity = GRANULARITIES.includes(localStorage.getItem('sc-granularity'))
        ? localStorage.getItem('sc-granularity')
        : 'daily';

    // ---------- helpers ----------

    async function getJSON(url) {
        const response = await fetch(url, { headers: { Accept: 'application/json' } });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
        return body;
    }

    const int = (n) => Number(n ?? 0).toLocaleString();
    const signed = (n) => (n > 0 ? `+${int(n)}` : int(n));
    const changeClass = (n) => (n > 0 ? 'change-positive' : n < 0 ? 'change-negative' : 'change-neutral');

    function setText(id, text) {
        const node = el(id);
        if (!node) return;
        node.textContent = text;
    }

    function flash(id) {
        const node = el(id);
        if (!node) return;
        node.classList.remove('value-flash');
        void node.offsetWidth; // restart the animation
        node.classList.add('value-flash');
    }

    function toast(message, variant = 'primary') {
        const box = document.createElement('div');
        box.className = `alert alert-${variant} alert-dismissible shadow-sm mb-0`;
        box.role = 'alert';
        box.appendChild(document.createTextNode(message));

        const close = document.createElement('button');
        close.type = 'button';
        close.className = 'btn-close';
        close.setAttribute('aria-label', 'Close');
        close.addEventListener('click', () => box.remove());
        box.appendChild(close);

        el('toast-stack').appendChild(box);
        setTimeout(() => box.remove(), 6000);
    }

    // ---------- charts ----------

    function theme() {
        const styles = getComputedStyle(document.body);
        const read = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;
        return {
            accent: read('--bs-primary', '#0d6efd'),
            success: read('--bs-success', '#198754'),
            danger: read('--bs-danger', '#dc3545'),
            text: read('--bs-secondary-color', '#6c757d'),
            grid: read('--bs-border-color', 'rgba(0,0,0,.1)'),
        };
    }

    function render(id, config) {
        charts.get(id)?.destroy();
        const canvas = el(id);
        if (!canvas) return;
        const chart = new Chart(canvas, config);
        charts.set(id, chart);
        return chart;
    }

    function axes(colors, { beginAtZero = true } = {}) {
        return {
            x: { grid: { display: false }, ticks: { color: colors.text, maxTicksLimit: 8 } },
            y: {
                beginAtZero,
                grid: { color: colors.grid },
                ticks: { color: colors.text, callback: (v) => Number(v).toLocaleString() },
            },
        };
    }

    function lineChart(id, points, label) {
        const colors = theme();
        return render(id, {
            type: 'line',
            data: {
                labels: points.map((p) => p.timestamp),
                datasets: [{
                    label,
                    data: points.map((p) => p.total_citations ?? p.citations),
                    borderColor: colors.accent,
                    backgroundColor: `color-mix(in srgb, ${colors.accent} 14%, transparent)`,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.35,
                    // Sparse series (monthly, yearly) need visible markers.
                    pointRadius: points.length <= 24 ? 3 : 0,
                    pointHoverRadius: 5,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                interaction: { intersect: false, mode: 'index' },
                scales: axes(colors, { beginAtZero: false }),
            },
        });
    }

    function changesChart(points) {
        const colors = theme();
        return render('changes-chart', {
            type: 'bar',
            data: {
                labels: points.map((p) => p.timestamp),
                datasets: [{
                    label: 'Change',
                    data: points.map((p) => p.change),
                    backgroundColor: points.map((p) => (p.change >= 0 ? colors.success : colors.danger)),
                    borderRadius: 3,
                    // Without a cap, a two-bar yearly view renders as slabs.
                    maxBarThickness: 56,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: colors.text, maxTicksLimit: 12 } },
                    y: {
                        grid: { color: colors.grid },
                        ticks: { color: colors.text, callback: (v) => (v > 0 ? `+${v}` : v) },
                    },
                },
            },
        });
    }

    /* An inline SVG polyline: 75 of these cost far less than 75 Chart instances. */
    function sparkline(points, width = 100, height = 32) {
        const svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('aria-hidden', 'true');
        svg.classList.add('trend-mini');

        const values = points.map((p) => p.citations);
        if (values.length < 2) return svg;

        const min = Math.min(...values);
        const max = Math.max(...values);
        const span = max - min || 1;
        const step = width / (values.length - 1);
        const pad = 3;

        const coords = values.map((value, i) => {
            const x = i * step;
            const y = height - pad - ((value - min) / span) * (height - pad * 2);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        });

        const line = document.createElementNS(SVG_NS, 'polyline');
        line.setAttribute('points', coords.join(' '));
        line.setAttribute('fill', 'none');
        line.setAttribute('stroke', 'currentColor');
        line.setAttribute('stroke-width', '1.5');
        line.setAttribute('stroke-linejoin', 'round');
        line.setAttribute('stroke-linecap', 'round');
        svg.appendChild(line);
        svg.classList.add(values.at(-1) >= values[0] ? 'change-positive' : 'change-negative');
        return svg;
    }

    // ---------- rendering ----------

    function renderTopPapers(top) {
        const box = el('top-papers-list');
        box.replaceChildren();

        if (!top?.length) {
            box.appendChild(Object.assign(document.createElement('p'), {
                className: 'text-body-secondary text-center mb-0',
                textContent: 'No data yet.',
            }));
            return;
        }

        top.forEach((paper, index) => {
            const row = document.createElement('div');
            row.className = 'paper-item d-flex align-items-center gap-2';

            const rank = document.createElement('div');
            rank.className = 'paper-rank';
            rank.textContent = String(index + 1);

            const body = document.createElement('div');
            body.className = 'flex-grow-1 min-w-0';

            const title = document.createElement('div');
            title.className = 'paper-title';
            title.textContent = paper.title;
            title.title = paper.title;

            const count = document.createElement('div');
            count.className = 'paper-citations';
            count.textContent = `${int(paper.citations)} citations`;

            body.append(title, count);
            row.append(rank, body);
            box.appendChild(row);
        });
    }

    function visiblePapers() {
        const needle = filterText.toLowerCase();
        const rows = needle ? papers.filter((p) => p.title.toLowerCase().includes(needle)) : [...papers];

        rows.sort((a, b) => {
            if (sortKey === 'title') return a.title.localeCompare(b.title);
            if (sortKey === 'change') return b.recent_change - a.recent_change;
            return b.current_citations - a.current_citations;
        });
        return rows;
    }

    function renderPapersTable() {
        const body = el('papers-table-body');
        body.replaceChildren();
        const rows = visiblePapers();

        if (!rows.length) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 5;
            td.className = 'text-center text-body-secondary py-4';
            td.textContent = papers.length ? 'No papers match that filter.' : 'No data yet.';
            tr.appendChild(td);
            body.appendChild(tr);
            return;
        }

        for (const paper of rows) {
            const tr = document.createElement('tr');

            const title = document.createElement('td');
            title.className = 'paper-title';
            title.textContent = paper.title;

            const citations = document.createElement('td');
            citations.className = 'text-end citation-count';
            citations.textContent = int(paper.current_citations);

            const change = document.createElement('td');
            change.className = `text-end fw-semibold ${changeClass(paper.recent_change)}`;
            change.textContent = signed(paper.recent_change);

            const trend = document.createElement('td');
            trend.appendChild(sparkline(paper.trend));

            const actions = document.createElement('td');
            actions.className = 'text-end';
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-outline-secondary btn-sm';
            button.textContent = 'Details';
            button.addEventListener('click', () => showPaper(paper.title));
            actions.appendChild(button);

            tr.append(title, citations, change, trend, actions);
            body.appendChild(tr);
        }
    }

    function statTile(label, value, tone = '') {
        const col = document.createElement('div');
        col.className = 'col-6 col-md-4 col-lg-3';

        const card = document.createElement('div');
        card.className = 'card h-100';

        const inner = document.createElement('div');
        inner.className = 'card-body';

        const caption = document.createElement('div');
        caption.className = 'stat-label';
        caption.textContent = label;

        const figure = document.createElement('div');
        figure.className = `fs-4 fw-bold ${tone}`;
        figure.textContent = value;

        inner.append(caption, figure);
        card.appendChild(inner);
        col.appendChild(card);
        return col;
    }

    // ---------- data loading ----------

    async function loadSummary() {
        try {
            const data = await getJSON('/api/summary');
            setText('total-citations', int(data.current_total));
            setText('daily-change', signed(data.daily_change));
            setText('weekly-change', signed(data.weekly_change));
            setText('total-papers', int(data.total_papers));
            setText('last-updated', `Updated ${data.last_updated}`);

            el('daily-change').className = `stat-value ${changeClass(data.daily_change)}`;
            el('weekly-change').className = `stat-value ${changeClass(data.weekly_change)}`;
            ['total-citations', 'daily-change', 'weekly-change'].forEach(flash);

            renderTopPapers(data.top_papers);
        } catch (error) {
            setText('total-citations', '–');
            setText('last-updated', error.message);
        }
    }

    async function loadTrends() {
        setText('changes-heading', CHANGE_HEADING[granularity]);
        try {
            const data = await getJSON(`/api/trends?granularity=${granularity}`);
            lineChart('trends-chart', data.overall_trend, 'Total citations');
            changesChart(data.change_trend);
        } catch {
            /* charts stay empty; the summary tile already reports the problem */
        }
    }

    function setGranularity(next) {
        granularity = next;
        localStorage.setItem('sc-granularity', next);
        document.querySelectorAll('[data-granularity]').forEach((button) => {
            button.classList.toggle('active', button.dataset.granularity === next);
            button.setAttribute('aria-pressed', String(button.dataset.granularity === next));
        });
        loadTrends();
    }

    async function loadPapers() {
        try {
            const data = await getJSON('/api/papers');
            papers = data.papers;
        } catch {
            papers = [];
        }
        renderPapersTable();
    }

    async function loadStatus() {
        try {
            const data = await getJSON('/api/status');
            setText('snapshot-count', `${int(data.snapshots)} snapshots`);
            const next = el('next-update');
            if (data.updating) {
                next.textContent = 'Updating…';
            } else if (data.auto_update && data.next_update) {
                next.textContent = `Next auto-update ${data.next_update}`;
            } else {
                next.textContent = data.auto_update ? '' : 'Auto-update off';
            }
        } catch {
            /* transient; the next poll will retry */
        }
    }

    async function showPaper(title) {
        try {
            const data = await getJSON(`/api/paper?title=${encodeURIComponent(title)}`);
            setText('paper-modal-title', data.title);
            setText('modal-citations', int(data.current_citations));
            setText('modal-growth', signed(data.total_growth));
            setText('modal-per-day', data.avg_daily_growth.toFixed(2));
            setText('modal-points', String(data.trend.length));

            bootstrap.Modal.getOrCreateInstance(el('paper-modal')).show();
            lineChart('paper-chart', data.trend, 'Citations');
        } catch (error) {
            toast(error.message, 'danger');
        }
    }

    async function showAnalytics() {
        try {
            const d = await getJSON('/api/analytics');
            const grid = el('analytics-grid');
            grid.replaceChildren(
                statTile('Total growth', signed(d.total_growth), 'change-positive'),
                statTile('Growth per day', d.avg_daily_growth.toFixed(2)),
                statTile('Best jump', signed(d.best_day), 'change-positive'),
                statTile('Largest drop', signed(d.worst_day), d.worst_day < 0 ? 'change-negative' : ''),
                statTile('Mean change', d.avg_change.toFixed(2)),
                statTile('Median citations', d.median_citations.toFixed(1)),
                statTile('Mean per paper', d.avg_citations_per_paper.toFixed(1)),
                statTile('Last 30 days', signed(d.recent_growth_30_days)),
                statTile('Papers', int(d.total_papers)),
                statTile('Snapshots', int(d.data_points)),
                statTile('Tracking since', d.tracking_since),
                statTile('Most cited', int(d.most_cited_paper.citations)),
            );

            const note = document.createElement('div');
            note.className = 'col-12';
            const p = document.createElement('p');
            p.className = 'text-body-secondary small mb-0';
            p.textContent = `Most cited: ${d.most_cited_paper.title}`;
            note.appendChild(p);
            grid.appendChild(note);

            bootstrap.Modal.getOrCreateInstance(el('analytics-modal')).show();
        } catch (error) {
            toast(error.message, 'danger');
        }
    }

    async function runUpdate() {
        const button = el('update-btn');
        const icon = el('update-icon');
        button.disabled = true;
        icon.classList.add('fa-spin');
        setText('update-text', 'Updating…');

        try {
            const response = await fetch('/api/update', { method: 'POST' });
            const result = await response.json();
            toast(result.success ? `Updated: ${result.message}` : result.message,
                  result.success ? 'success' : 'danger');
            if (result.success) {
                await Promise.all([loadSummary(), loadTrends(), loadPapers(), loadStatus()]);
            }
        } catch (error) {
            toast(`Update failed: ${error.message}`, 'danger');
        } finally {
            button.disabled = false;
            icon.classList.remove('fa-spin');
            setText('update-text', 'Update now');
        }
    }

    // ---------- wiring ----------

    function applyTheme(next) {
        document.documentElement.dataset.bsTheme = next;
        localStorage.setItem('sc-theme', next);
        loadTrends();
    }

    function init() {
        el('update-btn').addEventListener('click', runUpdate);
        el('analytics-btn').addEventListener('click', showAnalytics);

        el('theme-toggle').addEventListener('click', () => {
            applyTheme(document.documentElement.dataset.bsTheme === 'dark' ? 'light' : 'dark');
        });

        el('paper-filter').addEventListener('input', (event) => {
            filterText = event.target.value.trim();
            renderPapersTable();
        });

        document.querySelectorAll('[data-granularity]').forEach((button) => {
            button.addEventListener('click', () => setGranularity(button.dataset.granularity));
        });

        document.querySelectorAll('[data-sort]').forEach((button) => {
            button.addEventListener('click', () => {
                sortKey = button.dataset.sort;
                document.querySelectorAll('[data-sort]').forEach((b) => b.classList.remove('active'));
                button.classList.add('active');
                renderPapersTable();
            });
        });

        loadSummary();
        setGranularity(granularity); // marks the active button and loads the charts
        loadPapers();
        loadStatus();
        setInterval(loadStatus, STATUS_POLL_MS);
    }

    document.addEventListener('DOMContentLoaded', init);
})();
