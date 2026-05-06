const COLORS = {
    Firecrawl: '#c4410c',
    Apify: '#3a6ea5',
    Browserbase: '#4a8c5e',
    'Bright Data': '#8a4ea5',
    Zyte: '#a55a3a',
    ScrapingBee: '#666666',
};

function formatSegment(s) {
    return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function setHeadlineCompare(el, rank, total, topCompetitor, topScore) {
    el.textContent = '';
    const strong = document.createElement('strong');
    if (rank === 1) {
        strong.textContent = `#1 of ${total}.`;
        el.appendChild(strong);
        el.appendChild(document.createTextNode(' Leading the set.'));
    } else {
        strong.textContent = `#${rank} of ${total},`;
        el.appendChild(strong);
        el.appendChild(document.createTextNode(
            ` behind ${topCompetitor} (${topScore.toFixed(2)}).`
        ));
    }
}

async function main() {
    const data = await fetch('data.json').then(r => r.json());

    // ---- HEADLINE ----
    const fc = data.headline.find(h => h.competitor === 'Firecrawl');
    const top = data.headline[0];
    document.getElementById('firecrawl-score').textContent =
        fc.geo_score.toFixed(2);
    document.getElementById('headline-meta').textContent =
        `Across ${fc.n_obs} observations on ${fc.n_cells} segments`;
    const rank = data.headline.findIndex(h => h.competitor === 'Firecrawl') + 1;
    setHeadlineCompare(
        document.getElementById('headline-compare'),
        rank, data.headline.length, top.competitor, top.geo_score
    );

    // ---- RANKING CHART ----
    new Chart(document.getElementById('rankingChart'), {
        type: 'bar',
        data: {
            labels: data.headline.map(h => h.competitor),
            datasets: [{
                label: 'GEO Score',
                data: data.headline.map(h => h.geo_score),
                backgroundColor: data.headline.map(h => COLORS[h.competitor] || '#999'),
                borderColor: data.headline.map(h =>
                    h.competitor === 'Firecrawl' ? '#000' : 'transparent'
                ),
                borderWidth: 2,
            }]
        },
        options: {
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, max: 10, title: {
                    display: true, text: 'GEO Score (0-10)' } }
            }
        }
    });

    // ---- SEGMENT BREAKDOWN ----
    const segments = [...new Set(data.cells.map(c => c.segment))];
    const competitors = [...new Set(data.cells.map(c => c.competitor))];
    const segmentData = competitors.map(comp => {
        return {
            label: comp,
            data: segments.map(seg => {
                const matching = data.cells.filter(
                    c => c.competitor === comp && c.segment === seg
                );
                const avg = matching.length ?
                    matching.reduce((s, c) => s + c.geo_score, 0) / matching.length : 0;
                return avg;
            }),
            backgroundColor: COLORS[comp] || '#999',
            borderColor: comp === 'Firecrawl' ? '#000' : 'transparent',
            borderWidth: comp === 'Firecrawl' ? 2 : 0,
        };
    });
    new Chart(document.getElementById('segmentChart'), {
        type: 'bar',
        data: { labels: segments.map(formatSegment), datasets: segmentData },
        options: {
            plugins: { legend: { position: 'bottom' } },
            scales: {
                y: { beginAtZero: true, max: 10, title: {
                    display: true, text: 'GEO Score' } }
            }
        }
    });

    // ---- FOOTER ----
    const ts = new Date(data.generated_at);
    document.getElementById('footer').textContent =
        `Data as of ${ts.toLocaleString()} • ${data.cells.length} cells • ` +
        `Methodology disclosed in README`;
}

main().catch(err => {
    document.getElementById('footer').textContent =
        'Error loading data: ' + err.message;
});
