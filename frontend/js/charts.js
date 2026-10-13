/**
 * Interactive Performance Charts for Restaurant Queue Simulator
 * Uses Chart.js with dark-mode styling and blue color palette.
 */
class PerformanceCharts {
  constructor() {
    this.queueChart = null;
    this.waitTimeChart = null;
    this.chefUtilChart = null;
    this.initCharts();
  }

  initCharts() {
    if (typeof Chart === 'undefined') {
      console.warn("Chart.js not loaded yet. Will retry when ready.");
      return;
    }

    // Global Chart.js defaults for strict dark theme
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
    Chart.defaults.plugins.tooltip.titleColor = '#38bdf8';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(59, 130, 246, 0.4)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;

    // 1. Queue Length Timeline Chart
    const ctxQueue = document.getElementById('chartQueueTimeline');
    if (ctxQueue) {
      this.queueChart = new Chart(ctxQueue, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Total Queue Depth',
              data: [],
              borderColor: '#38bdf8',
              backgroundColor: 'rgba(56, 189, 248, 0.12)',
              fill: true,
              tension: 0.35,
              borderWidth: 2,
              pointRadius: 1
            },
            {
              label: 'VIP Orders',
              data: [],
              borderColor: '#fbbf24',
              backgroundColor: 'rgba(251, 191, 36, 0.2)',
              borderWidth: 1.5,
              borderDash: [4, 4],
              pointRadius: 0
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 300 },
          scales: {
            x: {
              grid: { color: 'rgba(59, 130, 246, 0.08)' },
              ticks: { maxTicksLimit: 8, font: { size: 10 } }
            },
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(59, 130, 246, 0.08)' },
              ticks: { precision: 0, font: { size: 10 } }
            }
          },
          plugins: {
            legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } }
          }
        }
      });
    }

    // 2. Average Wait Time by Tier Bar Chart
    const ctxWait = document.getElementById('chartWaitTimes');
    if (ctxWait) {
      this.waitTimeChart = new Chart(ctxWait, {
        type: 'bar',
        data: {
          labels: ['VIP', 'Express', 'Standard', 'Overall'],
          datasets: [{
            label: 'Avg Wait Time (s)',
            data: [0, 0, 0, 0],
            backgroundColor: [
              'rgba(251, 191, 36, 0.85)',
              'rgba(56, 189, 248, 0.85)',
              'rgba(148, 163, 184, 0.65)',
              'rgba(37, 99, 235, 0.85)'
            ],
            borderColor: ['#fbbf24', '#38bdf8', '#94a3b8', '#2563eb'],
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 11, weight: 'bold' } } },
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(59, 130, 246, 0.08)' },
              title: { display: true, text: 'Seconds', color: '#64748b', font: { size: 10 } }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    // 3. Chef Utilization Horizontal Bar Chart
    const ctxUtil = document.getElementById('chartChefUtil');
    if (ctxUtil) {
      this.chefUtilChart = new Chart(ctxUtil, {
        type: 'bar',
        data: {
          labels: [],
          datasets: [{
            label: 'Utilization %',
            data: [],
            backgroundColor: 'rgba(59, 130, 246, 0.75)',
            borderColor: '#38bdf8',
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              beginAtZero: true,
              max: 100,
              grid: { color: 'rgba(59, 130, 246, 0.08)' },
              ticks: { callback: (val) => `${val}%`, font: { size: 10 } }
            },
            y: { grid: { display: false }, ticks: { font: { size: 10 } } }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }
  }

  updateCharts(analytics, timeline, chefs) {
    if (!this.queueChart && typeof Chart !== 'undefined') {
      this.initCharts();
    }

    // 1. Update Queue Timeline
    if (this.queueChart && timeline && timeline.length > 0) {
      const labels = timeline.map(p => `${Math.round(p.time)}s`);
      const depths = timeline.map(p => p.total_queue);
      const vips = timeline.map(p => p.vip_count);

      this.queueChart.data.labels = labels;
      this.queueChart.data.datasets[0].data = depths;
      this.queueChart.data.datasets[1].data = vips;
      this.queueChart.update('none');
    }

    // 2. Update Wait Times
    if (this.waitTimeChart && analytics) {
      this.waitTimeChart.data.datasets[0].data = [
        analytics.average_waiting_time_vip || 0,
        analytics.average_waiting_time_express || 0,
        analytics.average_waiting_time_standard || 0,
        analytics.average_waiting_time_overall || 0
      ];
      this.waitTimeChart.update('none');
    }

    // 3. Update Chef Utilization
    if (this.chefUtilChart && chefs && chefs.length > 0) {
      this.chefUtilChart.data.labels = chefs.map(c => c.name.split(' (')[0]);
      this.chefUtilChart.data.datasets[0].data = chefs.map(c => c.utilization_rate || 0);
      this.chefUtilChart.update('none');
    }
  }
}
