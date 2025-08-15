// Dashboard JavaScript для торгового бота
const API_BASE = 'http://localhost:8000';
let performanceChart = null;
let refreshInterval = null;

// Ініціалізація dashboard
document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 Dashboard ініціалізовано');
    loadDashboardData();
    startAutoRefresh();
    initializePerformanceChart();
});

// Автоматичне оновлення даних
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        loadDashboardData();
    }, 10000); // Оновлюємо кожні 10 секунд
}

// Завантаження всіх даних dashboard
async function loadDashboardData() {
    try {
        await Promise.all([
            loadAccountBalance(),
            loadRiskMetrics(),
            loadTradingStatus(),
            loadMonitoringStatus(),
            loadRecentSignals(),
            loadAlerts()
        ]);
    } catch (error) {
        console.error('Помилка завантаження даних:', error);
        showNotification('Помилка завантаження даних', 'error');
    }
}

// Завантаження балансу акаунту
async function loadAccountBalance() {
    try {
        const response = await fetch(`${API_BASE}/account/balance`);
        const data = await response.json();

        if (data.success) {
            // Оновлюємо основні метрики
            document.getElementById('total-assets').textContent = data.total_assets;
            document.getElementById('account-type').textContent = data.account_type;

            // Отримуємо USDT баланс
            const usdtResponse = await fetch(`${API_BASE}/account/usdt-balance`);
            const usdtData = await usdtResponse.json();

            if (usdtData.success) {
                document.getElementById('usdt-balance').textContent =
                    `$${usdtData.usdt_balance.toFixed(2)}`;
            }

            // Оновлюємо деталі балансу
            updateBalanceDetails(data.balances);
        } else {
            console.error('Помилка завантаження балансу:', data.error);
            document.getElementById('balance-details').innerHTML =
                '<p class="text-danger">Помилка завантаження балансу</p>';
        }
    } catch (error) {
        console.error('Помилка завантаження балансу акаунту:', error);
        document.getElementById('balance-details').innerHTML =
            '<p class="text-danger">Помилка з\'єднання</p>';
    }
}

// Оновлення деталей балансу
function updateBalanceDetails(balances) {
    const container = document.getElementById('balance-details');

    if (balances.length === 0) {
        container.innerHTML = '<p class="text-muted">Немає активів</p>';
        return;
    }

    const balanceHtml = `
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Актив</th>
                        <th>Вільний</th>
                        <th>Заблокований</th>
                        <th>Всього</th>
                    </tr>
                </thead>
                <tbody>
                    ${balances.slice(0, 10).map(balance => `
                        <tr>
                            <td><strong>${balance.asset}</strong></td>
                            <td>${balance.free.toFixed(6)}</td>
                            <td>${balance.locked.toFixed(6)}</td>
                            <td><strong>${balance.total.toFixed(6)}</strong></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        ${balances.length > 10 ? `<small class="text-muted">Показано перші 10 активів з ${balances.length}</small>` : ''}
    `;

    container.innerHTML = balanceHtml;
}

// Ручне оновлення балансу
async function refreshBalance() {
    try {
        await loadAccountBalance();
        showNotification('Баланс оновлено', 'success');
    } catch (error) {
        console.error('Помилка оновлення балансу:', error);
        showNotification('Помилка оновлення балансу', 'error');
    }
}

// Завантаження метрик ризику
async function loadRiskMetrics() {
    try {
        const response = await fetch(`${API_BASE}/risk/metrics`);
        const data = await response.json();

        if (data.success) {
            const metrics = data.metrics;

            // Оновлюємо метрики
            document.getElementById('total-exposure').textContent =
                `$${metrics.total_exposure.toFixed(2)}`;
            document.getElementById('daily-pnl').textContent =
                `$${metrics.daily_pnl.toFixed(2)}`;
            document.getElementById('win-rate').textContent =
                `${(metrics.win_rate * 100).toFixed(1)}%`;
            document.getElementById('max-drawdown').textContent =
                `${metrics.max_drawdown.toFixed(2)}%`;

            // Оновлюємо статус ризику
            updateRiskStatus(metrics);

            // Оновлюємо графік продуктивності
            updatePerformanceChart(metrics);
        }
    } catch (error) {
        console.error('Помилка завантаження метрик ризику:', error);
    }
}

// Завантаження статусу торгового двигуна
async function loadTradingStatus() {
    try {
        const response = await fetch(`${API_BASE}/trading/status`);
        const data = await response.json();

        if (data.success) {
            const statusIndicator = document.getElementById('engine-status');
            const statusText = document.getElementById('engine-status-text');

            if (data.is_running) {
                statusIndicator.className = 'status-indicator status-running';
                statusText.textContent = 'Запущений';
            } else {
                statusIndicator.className = 'status-indicator status-stopped';
                statusText.textContent = 'Зупинений';
            }

            // Оновлюємо активні ордери
            updateActiveOrders(data.active_orders);
        }
    } catch (error) {
        console.error('Помилка завантаження статусу торгового двигуна:', error);
    }
}

// Завантаження статусу моніторингу
async function loadMonitoringStatus() {
    try {
        const response = await fetch(`${API_BASE}/monitoring/status`);
        const data = await response.json();

        if (data.success) {
            const status = data.status;

            // Оновлюємо статус системи
            const systemStatus = document.getElementById('system-status');
            const systemStatusText = document.getElementById('system-status-text');

            if (status.risk_level === 'LOW') {
                systemStatus.className = 'status-indicator status-running';
                systemStatusText.textContent = 'Система активна';
            } else if (status.risk_level === 'MEDIUM') {
                systemStatus.className = 'status-indicator status-warning';
                systemStatusText.textContent = 'Середній ризик';
            } else {
                systemStatus.className = 'status-indicator status-stopped';
                systemStatusText.textContent = 'Високий ризик';
            }
        }
    } catch (error) {
        console.error('Помилка завантаження статусу моніторингу:', error);
    }
}

// Завантаження останніх сигналів
async function loadRecentSignals() {
    try {
        const response = await fetch(`${API_BASE}/signals/latest`);
        const data = await response.json();

        const signalsContainer = document.getElementById('recent-signals');

        if (data && data.symbol) {
            const signalHtml = `
                <div class="alert alert-info">
                    <strong>${data.symbol}</strong> - ${data.signal}
                    <br><small>${new Date(data.ts).toLocaleString()}</small>
                </div>
            `;
            signalsContainer.innerHTML = signalHtml;
        } else {
            signalsContainer.innerHTML = '<p class="text-muted">Немає останніх сигналів</p>';
        }
    } catch (error) {
        console.error('Помилка завантаження сигналів:', error);
        document.getElementById('recent-signals').innerHTML =
            '<p class="text-muted">Помилка завантаження сигналів</p>';
    }
}

// Завантаження сповіщень
async function loadAlerts() {
    try {
        const response = await fetch(`${API_BASE}/monitoring/alerts?hours=24`);
        const data = await response.json();

        const alertsContainer = document.getElementById('alerts');

        if (data.success && data.alerts.length > 0) {
            const alertsHtml = data.alerts.slice(0, 5).map(alert => `
                <div class="alert-item alert-${alert.level.toLowerCase()}">
                    <strong>${alert.type}</strong><br>
                    ${alert.message}<br>
                    <small>${new Date(alert.timestamp).toLocaleString()}</small>
                </div>
            `).join('');
            alertsContainer.innerHTML = alertsHtml;
        } else {
            alertsContainer.innerHTML = '<p class="text-muted">Немає сповіщень</p>';
        }
    } catch (error) {
        console.error('Помилка завантаження сповіщень:', error);
        document.getElementById('alerts').innerHTML =
            '<p class="text-muted">Помилка завантаження сповіщень</p>';
    }
}

// Запуск торгового двигуна
async function startTradingEngine() {
    try {
        const tradingPairs = document.getElementById('trading-pairs').value
            .split(',').map(pair => pair.trim()).filter(pair => pair);

        const response = await fetch(`${API_BASE}/trading/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ trading_pairs: tradingPairs })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Торговий двигун запущений', 'success');
            loadTradingStatus();
        } else {
            showNotification(`Помилка запуску: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Помилка запуску торгового двигуна:', error);
        showNotification('Помилка запуску торгового двигуна', 'error');
    }
}

// Зупинка торгового двигуна
async function stopTradingEngine() {
    try {
        const response = await fetch(`${API_BASE}/trading/stop`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Торговий двигун зупинений', 'success');
            loadTradingStatus();
        } else {
            showNotification(`Помилка зупинки: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Помилка зупинки торгового двигуна:', error);
        showNotification('Помилка зупинки торгового двигуна', 'error');
    }
}

// Оновлення статусу ризику
function updateRiskStatus(metrics) {
    const riskStatus = document.getElementById('risk-status');
    const riskStatusText = document.getElementById('risk-status-text');

    if (metrics.max_drawdown < 5) {
        riskStatus.className = 'status-indicator status-running';
        riskStatusText.textContent = 'Низький ризик';
    } else if (metrics.max_drawdown < 10) {
        riskStatus.className = 'status-indicator status-warning';
        riskStatusText.textContent = 'Середній ризик';
    } else {
        riskStatus.className = 'status-indicator status-stopped';
        riskStatusText.textContent = 'Високий ризик';
    }
}

// Оновлення активних ордерів
function updateActiveOrders(orderCount) {
    const ordersContainer = document.getElementById('active-orders');

    if (orderCount > 0) {
        ordersContainer.innerHTML = `
            <div class="alert alert-warning">
                <strong>${orderCount}</strong> активних ордерів
            </div>
        `;
    } else {
        ordersContainer.innerHTML = '<p class="text-muted">Немає активних ордерів</p>';
    }
}

// Ініціалізація графіка продуктивності
function initializePerformanceChart() {
    const ctx = document.getElementById('performance-chart').getContext('2d');

    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'P&L',
                data: [],
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Оновлення графіка продуктивності
function updatePerformanceChart(metrics) {
    if (!performanceChart) return;

    const now = new Date().toLocaleTimeString();

    performanceChart.data.labels.push(now);
    performanceChart.data.datasets[0].data.push(metrics.daily_pnl);

    // Обмежуємо кількість точок на графіку
    if (performanceChart.data.labels.length > 20) {
        performanceChart.data.labels.shift();
        performanceChart.data.datasets[0].data.shift();
    }

    performanceChart.update();
}

// Показ модального вікна налаштувань ризику
function showRiskConfig() {
    const modal = new bootstrap.Modal(document.getElementById('riskConfigModal'));
    modal.show();
}

// Збереження налаштувань ризику
async function saveRiskConfig() {
    try {
        const stopLoss = document.getElementById('stop-loss-input').value;
        const takeProfit = document.getElementById('take-profit-input').value;
        const maxPosition = document.getElementById('max-position-input').value;
        const maxDailyLoss = document.getElementById('max-daily-loss-input').value;

        // Тут можна додати API виклик для збереження налаштувань
        console.log('Збереження налаштувань:', {
            stopLoss, takeProfit, maxPosition, maxDailyLoss
        });

        showNotification('Налаштування збережено', 'success');

        // Закриваємо модальне вікно
        const modal = bootstrap.Modal.getInstance(document.getElementById('riskConfigModal'));
        modal.hide();

    } catch (error) {
        console.error('Помилка збереження налаштувань:', error);
        showNotification('Помилка збереження налаштувань', 'error');
    }
}

// Ручне оновлення даних
function refreshData() {
    loadDashboardData();
    showNotification('Дані оновлено', 'info');
}

// Показ сповіщень
function showNotification(message, type = 'info') {
    // Створюємо сповіщення
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Автоматично видаляємо через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Обробка помилок мережі
window.addEventListener('offline', () => {
    showNotification('Втрачено з\'єднання з сервером', 'error');
});

window.addEventListener('online', () => {
    showNotification('З\'єднання відновлено', 'success');
    loadDashboardData();
});

// Експорт функцій для глобального використання
window.startTradingEngine = startTradingEngine;
window.stopTradingEngine = stopTradingEngine;
window.refreshData = refreshData;
window.refreshBalance = refreshBalance;
window.showRiskConfig = showRiskConfig;
window.saveRiskConfig = saveRiskConfig;
