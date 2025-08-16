// ML Dashboard JavaScript
const API_BASE = 'http://localhost:8000';

// Глобальні змінні для графіків
let performanceChart = null;
let weightsChart = null;
let priceCorrelationChart = null;

// Ініціалізація при завантаженні сторінки
document.addEventListener('DOMContentLoaded', function () {
    loadMLDashboardData();
    initializeCharts();
    startAutoRefresh();

    // Завантажуємо кореляції з ціною при завантаженні
    loadPriceCorrelations();
});

// Завантаження даних ML дашборду
async function loadMLDashboardData() {
    try {
        await Promise.all([
            loadModelOverview(),
            loadModelWeights(),
            loadModelPerformance(),
            loadFeatureImportance()
        ]);
    } catch (error) {
        console.error('Помилка завантаження ML даних:', error);
        showNotification('Помилка завантаження ML даних', 'error');
    }
}

// Завантаження кореляцій з ціною
async function loadPriceCorrelations() {
    try {
        const symbol = document.getElementById('correlation-symbol').value;
        const response = await fetch(`${API_BASE}/ml/price-correlations?symbol=${symbol}`);
        const data = await response.json();

        if (data.success) {
            updatePriceCorrelations(data.analysis);
        } else {
            console.error('Помилка завантаження кореляцій:', data.error);
            showNotification('Помилка завантаження кореляцій', 'error');
        }
    } catch (error) {
        console.error('Помилка завантаження кореляцій:', error);
        showNotification('Помилка завантаження кореляцій', 'error');
    }
}

// Оновлення кореляцій з ціною
function updatePriceCorrelations(analysis) {
    // Оновлюємо розподіл сигналів
    document.getElementById('buy-signals').textContent = `${analysis.signal_distribution.buy_pct}%`;
    document.getElementById('sell-signals').textContent = `${analysis.signal_distribution.sell_pct}%`;
    document.getElementById('hold-signals').textContent = `${analysis.signal_distribution.hold_pct}%`;
    document.getElementById('total-samples').textContent = analysis.total_samples.toLocaleString();

    // Оновлюємо графік кореляцій
    updatePriceCorrelationChart(analysis.correlations);

    // Оновлюємо таблицю ефективності
    updateEffectivenessTable(analysis.effectiveness);
}

// Оновлення графіка кореляцій
function updatePriceCorrelationChart(correlations) {
    if (priceCorrelationChart) {
        priceCorrelationChart.destroy();
    }

    const ctx = document.getElementById('priceCorrelationChart');
    if (ctx) {
        const labels = Object.keys(correlations);
        const data = Object.values(correlations);
        const colors = data.map(corr => {
            if (corr > 0.3) return '#4CAF50';
            if (corr > 0.1) return '#FF9800';
            if (corr > -0.1) return '#607D8B';
            if (corr > -0.3) return '#FF5722';
            return '#f44336';
        });

        priceCorrelationChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Кореляція з передбаченнями моделі',
                    data: data,
                    backgroundColor: colors,
                    borderColor: colors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Кореляція технічних індикаторів з передбаченнями логістичної регресії'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1,
                        min: -1
                    }
                }
            }
        });
    }
}

// Оновлення таблиці ефективності
function updateEffectivenessTable(effectiveness) {
    const tbody = document.getElementById('effectiveness-table');

    const rows = Object.entries(effectiveness).map(([indicator, data]) => {
        const correlationClass = data.separation > 0.1 ? 'text-success' :
            data.separation > 0.05 ? 'text-warning' : 'text-muted';

        return `
            <tr>
                <td><strong>${indicator}</strong></td>
                <td class="${correlationClass}">${data.separation.toFixed(3)}</td>
                <td class="text-success">${data.buy_avg.toFixed(3)}</td>
                <td class="text-danger">${data.sell_avg.toFixed(3)}</td>
                <td class="text-warning">${data.hold_avg.toFixed(3)}</td>
                <td class="${correlationClass}"><strong>${data.separation.toFixed(3)}</strong></td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = rows;
}

// Завантаження загального огляду моделі
async function loadModelOverview() {
    try {
        const response = await fetch(`${API_BASE}/ml/overview`);
        const data = await response.json();

        if (data.success) {
            updateModelOverview(data.overview);
        } else {
            // Використовуємо демо дані
            updateModelOverview(getDemoModelOverview());
        }
    } catch (error) {
        console.error('Помилка завантаження огляду моделі:', error);
        updateModelOverview(getDemoModelOverview());
    }
}

// Оновлення загального огляду моделі
function updateModelOverview(overview) {
    document.getElementById('model-accuracy').textContent = `${(overview.accuracy * 100).toFixed(1)}%`;
    document.getElementById('total-predictions').textContent = overview.total_predictions.toLocaleString();
    document.getElementById('model-version').textContent = overview.version;
    document.getElementById('last-update').textContent = formatTimestamp(overview.last_update);

    // Оновлюємо статус моделі
    updateModelStatus(overview.status);

    // Оновлюємо останній сигнал
    document.getElementById('last-signal').textContent = overview.last_signal;
    document.getElementById('processing-time').textContent = `${overview.processing_time} сек`;
}

// Оновлення статусу моделі
function updateModelStatus(status) {
    const statusElement = document.getElementById('model-status');
    statusElement.className = 'model-status';

    switch (status) {
        case 'active':
            statusElement.classList.add('status-active');
            statusElement.innerHTML = '<i class="fas fa-check-circle"></i> Модель активна та працює';
            break;
        case 'training':
            statusElement.classList.add('status-training');
            statusElement.innerHTML = '<i class="fas fa-cog fa-spin"></i> Модель навчається';
            break;
        case 'error':
            statusElement.classList.add('status-error');
            statusElement.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Помилка моделі';
            break;
        default:
            statusElement.classList.add('status-active');
            statusElement.innerHTML = '<i class="fas fa-check-circle"></i> Модель активна';
    }
}

// Завантаження ваг моделі
async function loadModelWeights() {
    try {
        const response = await fetch(`${API_BASE}/ml/weights`);
        const data = await response.json();

        if (data.success) {
            updateModelWeights(data.weights);
        } else {
            // Використовуємо демо дані
            updateModelWeights(getDemoWeights());
        }
    } catch (error) {
        console.error('Помилка завантаження ваг:', error);
        updateModelWeights(getDemoWeights());
    }
}

// Оновлення ваг моделі
function updateModelWeights(weights) {
    // Оновлюємо ваги сигналів
    updateWeightBar('tech-weight', weights.signal_weights.technical_analysis, 'bg-primary');
    updateWeightBar('smart-weight', weights.signal_weights.smart_money, 'bg-success');
    updateWeightBar('gpt-weight', weights.signal_weights.gpt_sentiment, 'bg-warning');

    // Оновлюємо часові ваги
    updateWeightBar('5m-weight', weights.timeframe_weights['5m'], 'bg-info');
    updateWeightBar('15m-weight', weights.timeframe_weights['15m'], 'bg-info');
    updateWeightBar('1h-weight', weights.timeframe_weights['1h'], 'bg-info');
}

// Оновлення панелі ваги
function updateWeightBar(elementId, weight, colorClass) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = weight.toFixed(2);

        // Оновлюємо відповідну панель
        const weightBar = element.closest('.mb-3').querySelector('.weight-fill');
        if (weightBar) {
            weightBar.style.width = `${weight * 100}%`;
            weightBar.className = `weight-fill ${colorClass}`;
            weightBar.querySelector('.weight-text').textContent = `${(weight * 100).toFixed(0)}%`;
        }
    }
}

// Завантаження продуктивності моделі
async function loadModelPerformance() {
    try {
        const response = await fetch(`${API_BASE}/ml/performance`);
        const data = await response.json();

        if (data.success) {
            updateModelPerformance(data.performance);
        } else {
            // Використовуємо демо дані
            updateModelPerformance(getDemoPerformance());
        }
    } catch (error) {
        console.error('Помилка завантаження продуктивності:', error);
        updateModelPerformance(getDemoPerformance());
    }
}

// Оновлення продуктивності моделі
function updateModelPerformance(performance) {
    // Оновлюємо метрики
    document.getElementById('precision').textContent = performance.precision.toFixed(2);
    document.getElementById('recall').textContent = performance.recall.toFixed(2);
    document.getElementById('f1-score').textContent = performance.f1_score.toFixed(2);
    document.getElementById('confidence').textContent = performance.confidence.toFixed(2);

    // Оновлюємо графік продуктивності
    updatePerformanceChart(performance.history);
}

// Завантаження важливості ознак
async function loadFeatureImportance() {
    try {
        const response = await fetch(`${API_BASE}/ml/features`);
        const data = await response.json();

        if (data.success) {
            updateFeatureImportance(data.features);
        } else {
            // Використовуємо демо дані
            updateFeatureImportance(getDemoFeatures());
        }
    } catch (error) {
        console.error('Помилка завантаження ознак:', error);
        updateFeatureImportance(getDemoFeatures());
    }
}

// Оновлення важливості ознак
function updateFeatureImportance(features) {
    const container = document.getElementById('feature-importance-list');

    const featuresHtml = features.map((feature, index) => {
        const colors = [
            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'linear-gradient(135deg, #4CAF50, #45a049)',
            'linear-gradient(135deg, #FF9800, #F57C00)',
            'linear-gradient(135deg, #2196F3, #1976D2)',
            'linear-gradient(135deg, #9C27B0, #7B1FA2)',
            'linear-gradient(135deg, #607D8B, #455A64)'
        ];

        return `
            <div class="feature-importance" style="background: ${colors[index % colors.length]};">
                <div class="d-flex justify-content-between">
                    <span>${feature.name}</span>
                    <span>${feature.importance.toFixed(3)}</span>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = featuresHtml;

    // Оновлюємо кругову діаграму
    updateWeightsChart(features);
}

// Ініціалізація графіків
function initializeCharts() {
    // Графік продуктивності
    const performanceCtx = document.getElementById('performanceChart');
    if (performanceCtx) {
        performanceChart = new Chart(performanceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Точність',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                }, {
                    label: 'F1-Score',
                    data: [],
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Продуктивність моделі в часі'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1
                    }
                }
            }
        });
    }

    // Кругова діаграма ваг
    const weightsCtx = document.getElementById('weightsChart');
    if (weightsCtx) {
        weightsChart = new Chart(weightsCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#667eea',
                        '#4CAF50',
                        '#FF9800',
                        '#2196F3',
                        '#9C27B0',
                        '#607D8B'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    title: {
                        display: true,
                        text: 'Розподіл важливості ознак'
                    }
                }
            }
        });
    }
}

// Оновлення графіка продуктивності
function updatePerformanceChart(history) {
    if (performanceChart && history) {
        performanceChart.data.labels = history.map(h => h.date);
        performanceChart.data.datasets[0].data = history.map(h => h.accuracy);
        performanceChart.data.datasets[1].data = history.map(h => h.f1_score);
        performanceChart.update();
    }
}

// Оновлення кругової діаграми ваг
function updateWeightsChart(features) {
    if (weightsChart && features) {
        weightsChart.data.labels = features.map(f => f.name);
        weightsChart.data.datasets[0].data = features.map(f => f.importance);
        weightsChart.update();
    }
}

// Автоматичне оновлення даних
function startAutoRefresh() {
    setInterval(() => {
        loadMLDashboardData();
    }, 30000); // Оновлюємо кожні 30 секунд
}

// Демо дані
function getDemoModelOverview() {
    return {
        accuracy: 0.78,
        total_predictions: 15420,
        version: 'v1.2.3',
        last_update: new Date().toISOString(),
        status: 'active',
        last_signal: 'BTCUSDT - BUY (0.85)',
        processing_time: 0.023
    };
}

function getDemoWeights() {
    return {
        signal_weights: {
            technical_analysis: 0.40,
            smart_money: 0.35,
            gpt_sentiment: 0.25
        },
        timeframe_weights: {
            '5m': 0.50,
            '15m': 0.30,
            '1h': 0.20
        }
    };
}

function getDemoPerformance() {
    return {
        precision: 0.78,
        recall: 0.72,
        f1_score: 0.75,
        confidence: 0.85,
        history: [
            { date: '2024-01-01', accuracy: 0.65, f1_score: 0.62 },
            { date: '2024-01-02', accuracy: 0.68, f1_score: 0.65 },
            { date: '2024-01-03', accuracy: 0.71, f1_score: 0.68 },
            { date: '2024-01-04', accuracy: 0.74, f1_score: 0.71 },
            { date: '2024-01-05', accuracy: 0.76, f1_score: 0.73 },
            { date: '2024-01-06', accuracy: 0.78, f1_score: 0.75 }
        ]
    };
}

function getDemoFeatures() {
    return [
        { name: 'RSI (14)', importance: 0.245 },
        { name: 'MACD (12,26,9)', importance: 0.198 },
        { name: 'Bollinger Bands', importance: 0.167 },
        { name: 'Volume SMA', importance: 0.134 },
        { name: 'Smart Money Flow', importance: 0.123 },
        // GPT Sentiment вимкнено
    ];
}

// Допоміжні функції
function formatTimestamp(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('uk-UA');
}

function showNotification(message, type = 'info') {
    // Проста реалізація повідомлень
    console.log(`${type.toUpperCase()}: ${message}`);
}

// Експорт функцій для глобального використання
window.loadMLDashboardData = loadMLDashboardData;
window.refreshMLData = loadMLDashboardData;
window.loadPriceCorrelations = loadPriceCorrelations;
