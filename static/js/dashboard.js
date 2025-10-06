// Dashboard JavaScript for Scholar Citation Tracker

let trendsChart, dailyChangesChart, paperTrendChart;
let papersData = [];
let currentSort = 'citations';

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadSummaryData();
    loadTrendsData();
    loadPapersData();
    loadStatus();
    
    // Set up auto-refresh every 5 minutes
    setInterval(loadSummaryData, 300000);
    setInterval(loadStatus, 60000); // Check status every minute
});

// Load summary statistics
async function loadSummaryData() {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading summary data:', data.error);
            return;
        }
        
        // Update summary cards
        document.getElementById('total-citations').textContent = data.current_total.toLocaleString();
        document.getElementById('daily-change').textContent = formatChange(data.daily_change);
        document.getElementById('weekly-change').textContent = formatChange(data.weekly_change);
        document.getElementById('total-papers').textContent = data.total_papers;
        document.getElementById('last-updated').textContent = `Last updated: ${data.last_updated}`;
        
        // Update top papers
        updateTopPapers(data.top_papers);
        
        // Add animation to changed numbers
        animateNumberChange('total-citations');
        animateNumberChange('daily-change');
        animateNumberChange('weekly-change');
        
    } catch (error) {
        console.error('Error loading summary data:', error);
    }
}

// Load trends data
async function loadTrendsData() {
    try {
        const response = await fetch('/api/trends');
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading trends data:', data.error);
            return;
        }
        
        createTrendsChart(data.overall_trend);
        createDailyChangesChart(data.daily_trend);
        
    } catch (error) {
        console.error('Error loading trends data:', error);
    }
}

// Load papers data
async function loadPapersData() {
    try {
        const response = await fetch('/api/papers');
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading papers data:', data.error);
            return;
        }
        
        papersData = data.papers;
        updatePapersTable();
        
    } catch (error) {
        console.error('Error loading papers data:', error);
    }
}

// Create trends chart
function createTrendsChart(data) {
    const ctx = document.getElementById('trendsChart').getContext('2d');
    
    if (trendsChart) {
        trendsChart.destroy();
    }
    
    trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.timestamp),
            datasets: [{
                label: 'Total Citations',
                data: data.map(d => d.total_citations),
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#007bff',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 8
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// Create daily changes chart
function createDailyChangesChart(data) {
    const ctx = document.getElementById('dailyChangesChart').getContext('2d');
    
    if (dailyChangesChart) {
        dailyChangesChart.destroy();
    }
    
    const colors = data.map(d => d.change >= 0 ? '#28a745' : '#dc3545');
    
    dailyChangesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.timestamp),
            datasets: [{
                label: 'Daily Change',
                data: data.map(d => d.change),
                backgroundColor: colors,
                borderColor: colors,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value > 0 ? '+' + value : value;
                        }
                    }
                }
            }
        }
    });
}

// Update top papers list
function updateTopPapers(topPapers) {
    const container = document.getElementById('top-papers-list');
    
    if (topPapers.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No data available</p>';
        return;
    }
    
    container.innerHTML = topPapers.map((paper, index) => `
        <div class="paper-item d-flex align-items-center">
            <div class="paper-rank">${index + 1}</div>
            <div class="flex-grow-1 ms-2">
                <div class="paper-title" title="${paper[0]}">${truncateText(paper[0], 50)}</div>
                <div class="paper-citations">${paper[1].toLocaleString()} citations</div>
            </div>
        </div>
    `).join('');
}

// Update papers table
function updatePapersTable() {
    const tbody = document.getElementById('papers-table-body');
    
    if (papersData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = papersData.map(paper => `
        <tr>
            <td>
                <div class="paper-title" title="${paper.title}">${paper.title}</div>
            </td>
            <td>
                <span class="citation-count">${paper.current_citations.toLocaleString()}</span>
            </td>
            <td>
                <span class="${getChangeClass(paper.recent_change)}">
                    ${formatChange(paper.recent_change)}
                </span>
            </td>
            <td>
                <canvas class="trend-mini" data-trend='${JSON.stringify(paper.trend)}'></canvas>
            </td>
            <td>
                <button class="btn btn-outline-primary btn-sm" onclick="showPaperDetail('${paper.title.replace(/'/g, "\\'")}')">
                    <i class="fas fa-chart-line me-1"></i>Details
                </button>
            </td>
        </tr>
    `).join('');
    
    // Create mini trend charts
    createMiniTrendCharts();
}

// Create mini trend charts for table
function createMiniTrendCharts() {
    const canvases = document.querySelectorAll('.trend-mini');
    canvases.forEach(canvas => {
        const trendData = JSON.parse(canvas.dataset.trend);
        if (trendData.length > 1) {
            new Chart(canvas, {
                type: 'line',
                data: {
                    labels: trendData.map(d => d.timestamp),
                    datasets: [{
                        data: trendData.map(d => d.citations),
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        borderWidth: 1,
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { display: false },
                        y: { display: false }
                    },
                    interaction: {
                        intersect: false
                    }
                }
            });
        }
    });
}

// Show paper detail modal
async function showPaperDetail(paperTitle) {
    try {
        const response = await fetch(`/api/paper/${encodeURIComponent(paperTitle)}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading paper details:', data.error);
            return;
        }
        
        // Update modal content
        document.getElementById('paperModalTitle').textContent = data.title;
        document.getElementById('modal-current-citations').textContent = data.current_citations.toLocaleString();
        document.getElementById('modal-total-growth').textContent = data.total_growth.toLocaleString();
        document.getElementById('modal-avg-growth').textContent = data.avg_daily_growth.toFixed(2);
        document.getElementById('modal-data-points').textContent = data.trend.length;
        
        // Create paper trend chart
        createPaperTrendChart(data.trend);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('paperModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading paper details:', error);
    }
}

// Create paper trend chart in modal
function createPaperTrendChart(data) {
    const ctx = document.getElementById('paperTrendChart').getContext('2d');
    
    if (paperTrendChart) {
        paperTrendChart.destroy();
    }
    
    paperTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.timestamp),
            datasets: [{
                label: 'Citations',
                data: data.map(d => d.citations),
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#007bff',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Sort papers
function sortPapers(sortBy) {
    currentSort = sortBy;
    
    papersData.sort((a, b) => {
        switch (sortBy) {
            case 'citations':
                return b.current_citations - a.current_citations;
            case 'change':
                return b.recent_change - a.recent_change;
            case 'title':
                return a.title.localeCompare(b.title);
            default:
                return 0;
        }
    });
    
    updatePapersTable();
}

// Utility functions
function formatChange(change) {
    if (change > 0) {
        return `+${change}`;
    } else if (change < 0) {
        return change.toString();
    } else {
        return '0';
    }
}

function getChangeClass(change) {
    if (change > 0) return 'change-positive';
    if (change < 0) return 'change-negative';
    return 'change-neutral';
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function animateNumberChange(elementId) {
    const element = document.getElementById(elementId);
    element.classList.add('number-change');
    setTimeout(() => {
        element.classList.remove('number-change');
    }, 500);
}

// Export data functions
function exportData(type) {
    const url = type === 'csv' ? '/api/export/csv' : '/api/export/papers';
    const filename = type === 'csv' ? 'citation_data.csv' : 'papers_data.csv';
    
    fetch(url)
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('Error exporting data:', error);
            alert('Error exporting data. Please try again.');
        });
}

// Show analytics modal
async function showAnalytics() {
    try {
        const response = await fetch('/api/analytics');
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading analytics:', data.error);
            return;
        }
        
        // Update analytics modal content
        document.getElementById('analytics-total-growth').textContent = data.total_growth.toLocaleString();
        document.getElementById('analytics-best-day').textContent = `+${data.best_day}`;
        document.getElementById('analytics-worst-day').textContent = data.worst_day.toString();
        document.getElementById('analytics-avg-daily').textContent = data.avg_daily_change.toFixed(2);
        
        document.getElementById('analytics-most-cited-title').textContent = truncateText(data.most_cited_paper.title, 50);
        document.getElementById('analytics-most-cited-count').textContent = `${data.most_cited_paper.citations.toLocaleString()} citations`;
        
        document.getElementById('analytics-least-cited-title').textContent = truncateText(data.least_cited_paper.title, 50);
        document.getElementById('analytics-least-cited-count').textContent = `${data.least_cited_paper.citations.toLocaleString()} citations`;
        
        document.getElementById('analytics-avg-per-paper').textContent = data.avg_citations_per_paper.toFixed(1);
        document.getElementById('analytics-median-citations').textContent = data.median_citations.toFixed(1);
        document.getElementById('analytics-recent-growth').textContent = data.recent_growth_30_days.toLocaleString();
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('analyticsModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading analytics:', error);
        alert('Error loading analytics. Please try again.');
    }
}

// Update data from Google Scholar
async function updateData() {
    const updateBtn = document.getElementById('update-btn');
    const updateText = document.getElementById('update-text');
    const statusBadge = document.getElementById('status-badge');
    
    // Disable button and show loading state
    updateBtn.disabled = true;
    updateText.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Updating...';
    statusBadge.className = 'badge bg-warning';
    statusBadge.textContent = 'Updating...';
    
    try {
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show success message
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'Updated';
            
            // Reload all data
            await Promise.all([
                loadSummaryData(),
                loadTrendsData(),
                loadPapersData(),
                loadStatus()
            ]);
            
            // Show success notification
            showNotification('Data updated successfully!', 'success');
            
        } else {
            // Show error message
            statusBadge.className = 'badge bg-danger';
            statusBadge.textContent = 'Error';
            showNotification(`Update failed: ${result.message}`, 'error');
        }
        
    } catch (error) {
        console.error('Error updating data:', error);
        statusBadge.className = 'badge bg-danger';
        statusBadge.textContent = 'Error';
        showNotification('Error updating data. Please try again.', 'error');
    } finally {
        // Re-enable button
        updateBtn.disabled = false;
        updateText.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Update Data';
        
        // Reset status after 3 seconds
        setTimeout(() => {
            if (statusBadge.textContent === 'Updated') {
                statusBadge.className = 'badge bg-success';
                statusBadge.textContent = 'Ready';
            }
        }, 3000);
    }
}

// Load current status
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.has_data) {
            document.getElementById('last-updated').textContent = `Last updated: ${data.last_update}`;
        } else {
            document.getElementById('last-updated').textContent = 'No data available';
        }
        
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}