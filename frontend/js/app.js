/**
 * Main Application Orchestrator for Restaurant Order Management Simulator
 */

document.addEventListener('DOMContentLoaded', () => {
  // Instances
  let api = null;
  let heapVis = null;
  let charts = null;
  let currentState = null;
  let activeTab = 'heap'; // 'heap' or 'pipeline'

  // Initialize Canvas Visualizer & Charts
  heapVis = new HeapVisualizer('heapCanvas', 'heapArrayCells');
  charts = new PerformanceCharts();

  // Initialize API and WebSockets
  api = new SimulatorAPI(
    (state) => handleStateUpdate(state),
    (isConnected) => handleConnectionChange(isConnected)
  );
  api.initWebSocket();

  // Initial REST fetch in case WS takes a moment
  api.fetchInitialState().then(state => {
    if (state) handleStateUpdate(state);
  }).catch(err => console.log("Initial state fetch:", err));

  // --- UI Elements ---
  const elSimClock = document.getElementById('simClock');
  const elClockPulse = document.getElementById('clockPulse');
  const btnPlay = document.getElementById('btnPlay');
  const btnPause = document.getElementById('btnPause');
  const btnStep = document.getElementById('btnStep');
  const btnReset = document.getElementById('btnReset');

  const togglePriority = document.getElementById('togglePriority');
  const toggleFifo = document.getElementById('toggleFifo');

  const selectChefCount = document.getElementById('selectChefCount');
  const selectTraffic = document.getElementById('selectTraffic');
  const sliderAging = document.getElementById('sliderAging');
  const valAging = document.getElementById('valAging');

  // Metrics DOM
  const valAvgWait = document.getElementById('valAvgWait');
  const valWaitVip = document.getElementById('valWaitVip');
  const valWaitExpress = document.getElementById('valWaitExpress');
  const valWaitStandard = document.getElementById('valWaitStandard');

  const valQueueLength = document.getElementById('valQueueLength');
  const valMaxQueue = document.getElementById('valMaxQueue');
  const valChefFleetUtil = document.getElementById('valChefFleetUtil');
  const valThroughput = document.getElementById('valThroughput');
  const valTotalCompleted = document.getElementById('valTotalCompleted');

  // Containers
  const queueCardsList = document.getElementById('queueCardsList');
  const chefsContainer = document.getElementById('chefsContainer');
  const eventFeed = document.getElementById('eventFeed');
  const activeQueueCountBadge = document.getElementById('activeQueueCountBadge');

  // Tab buttons
  const tabBtnHeap = document.getElementById('tabBtnHeap');
  const tabBtnPipeline = document.getElementById('tabBtnPipeline');
  const heapViewSection = document.getElementById('heapViewSection');
  const pipelineViewSection = document.getElementById('pipelineViewSection');

  // Order Form
  const orderForm = document.getElementById('orderForm');
  const inputCustomer = document.getElementById('inputCustomer');
  const selectTier = document.getElementById('selectTier');
  const selectDish = document.getElementById('selectDish');
  const inputPrepTime = document.getElementById('inputPrepTime');
  const valPrepTime = document.getElementById('valPrepTime');

  // Modals
  const btnOpenReport = document.getElementById('btnOpenReport');
  const btnOpenBenchmark = document.getElementById('btnOpenBenchmark');
  const modalReport = document.getElementById('modalReport');
  const modalBenchmark = document.getElementById('modalBenchmark');
  const reportContent = document.getElementById('reportContent');
  const benchmarkContent = document.getElementById('benchmarkContent');
  const btnRunBenchmarkAction = document.getElementById('btnRunBenchmarkAction');

  // Lab Mock Dataset & JSON Batch Importer
  const btnLoadMockData = document.getElementById('btnLoadMockData');
  const btnOpenJsonImport = document.getElementById('btnOpenJsonImport');
  const modalJsonImport = document.getElementById('modalJsonImport');
  const jsonBatchInput = document.getElementById('jsonBatchInput');
  const jsonImportFeedback = document.getElementById('jsonImportFeedback');
  const btnPreloadLabMock = document.getElementById('btnPreloadLabMock');
  const btnVerifyMockDispatch = document.getElementById('btnVerifyMockDispatch');
  const btnSubmitJsonBatch = document.getElementById('btnSubmitJsonBatch');

  // --- Event Listeners ---

  // Control Buttons
  btnPlay.addEventListener('click', async () => {
    await api.sendControl('play');
    updatePlayPauseUI(true);
  });

  btnPause.addEventListener('click', async () => {
    await api.sendControl('pause');
    updatePlayPauseUI(false);
  });

  btnStep.addEventListener('click', async () => {
    await api.sendControl('step');
    updatePlayPauseUI(false);
  });

  btnReset.addEventListener('click', async () => {
    if (confirm('Reset entire simulation state to 0.0s?')) {
      await api.sendControl('reset');
      updatePlayPauseUI(false);
    }
  });

  // Strategy Toggle
  togglePriority.addEventListener('click', async () => {
    if (togglePriority.classList.contains('active')) return;
    togglePriority.classList.add('active');
    toggleFifo.classList.remove('active');
    await api.sendConfig({ mode: 'PRIORITY_HEAP' });
  });

  toggleFifo.addEventListener('click', async () => {
    if (toggleFifo.classList.contains('active')) return;
    toggleFifo.classList.add('active');
    togglePriority.classList.remove('active');
    await api.sendConfig({ mode: 'FIFO_BASELINE' });
  });

  // Config Selectors
  selectChefCount.addEventListener('change', async (e) => {
    await api.sendConfig({ chef_count: parseInt(e.target.value) });
  });

  selectTraffic.addEventListener('change', async (e) => {
    await api.sendConfig({ traffic_mode: e.target.value });
  });

  sliderAging.addEventListener('input', (e) => {
    valAging.textContent = `${parseFloat(e.target.value).toFixed(1)}x`;
  });

  sliderAging.addEventListener('change', async (e) => {
    await api.sendConfig({ aging_factor: parseFloat(e.target.value) });
  });

  inputPrepTime.addEventListener('input', (e) => {
    valPrepTime.textContent = `${e.target.value}s`;
  });

  // Tab switching
  tabBtnHeap.addEventListener('click', () => {
    activeTab = 'heap';
    tabBtnHeap.classList.add('active');
    tabBtnPipeline.classList.remove('active');
    heapViewSection.style.display = 'flex';
    pipelineViewSection.style.display = 'none';
    if (heapVis && currentState) {
      heapVis.resizeCanvas();
      heapVis.render(currentState.heap_tree, currentState.heap_array, currentState.mode === 'PRIORITY_HEAP');
    }
  });

  tabBtnPipeline.addEventListener('click', () => {
    activeTab = 'pipeline';
    tabBtnPipeline.classList.add('active');
    tabBtnHeap.classList.remove('active');
    heapViewSection.style.display = 'none';
    pipelineViewSection.style.display = 'flex';
  });

  // Order Placement Form
  orderForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const orderData = {
      customer_name: inputCustomer.value || 'Patron',
      tier: selectTier.value,
      dish_name: selectDish.value,
      prep_time: parseFloat(inputPrepTime.value) || 10.0,
      service_type: selectTier.value === 'VIP' ? 'Premium VIP Delivery' : 'Dine-In'
    };

    await api.createOrder(orderData);
    // Randomize next customer name
    const sampleNames = ["Adhiraj N.", "Mithil P.", "Aarav Sharma", "Priya Verma", "Rohan D.", "Ananya I."];
    inputCustomer.value = sampleNames[Math.floor(Math.random() * sampleNames.length)];
  });

  // Preset Buttons
  document.querySelectorAll('.btn-preset').forEach(btn => {
    btn.addEventListener('click', async () => {
      const tier = btn.dataset.tier;
      const dish = btn.dataset.dish;
      const prep = parseFloat(btn.dataset.prep);
      const burst = parseInt(btn.dataset.burst || 1);

      for (let i = 0; i < burst; i++) {
        const orderData = {
          customer_name: `Guest ${Math.floor(Math.random() * 899 + 100)}`,
          tier: tier || (Math.random() < 0.2 ? 'VIP' : (Math.random() < 0.4 ? 'EXPRESS' : 'STANDARD')),
          dish_name: dish || 'Chef Special Pizza',
          prep_time: prep || (Math.floor(Math.random() * 8) + 6),
          service_type: 'Dine-In'
        };
        await api.createOrder(orderData);
      }
    });
  });

  // Modal Handlers
  btnOpenReport.addEventListener('click', async () => {
    modalReport.classList.add('open');
    reportContent.innerHTML = '<div style="text-align: center; padding: 2rem;">Generating formal report...</div>';
    try {
      const data = await api.getAcademicReport();
      renderAcademicReport(data);
    } catch (e) {
      reportContent.innerHTML = `<div style="color: #ef4444;">Failed to load report: ${e.message}</div>`;
    }
  });

  btnOpenBenchmark.addEventListener('click', () => {
    modalBenchmark.classList.add('open');
  });

  document.querySelectorAll('.modal-close, .btn-modal-close').forEach(btn => {
    btn.addEventListener('click', () => {
      modalReport.classList.remove('open');
      modalBenchmark.classList.remove('open');
      if (modalJsonImport) modalJsonImport.classList.remove('open');
    });
  });

  // Direct Lab Mock Dataset Loader
  if (btnLoadMockData) {
    btnLoadMockData.addEventListener('click', async () => {
      btnLoadMockData.disabled = true;
      btnLoadMockData.textContent = 'Loading...';
      try {
        await api.loadMockData();
        // Switch to pipeline view to inspect the 4 loaded tickets
        tabBtnPipeline.click();
      } catch (err) {
        alert('Failed to load mock data: ' + err.message);
      } finally {
        btnLoadMockData.disabled = false;
        btnLoadMockData.textContent = '📥 Load Mock Dataset';
      }
    });
  }

  // JSON Import Modal Handlers
  if (btnOpenJsonImport) {
    btnOpenJsonImport.addEventListener('click', async () => {
      modalJsonImport.classList.add('open');
      if (jsonImportFeedback) jsonImportFeedback.style.display = 'none';
      if (jsonBatchInput && !jsonBatchInput.value.trim()) {
        try {
          const data = await api.fetchMockData();
          jsonBatchInput.value = JSON.stringify(data, null, 2);
        } catch (e) {
          console.error(e);
        }
      }
    });
  }

  if (btnPreloadLabMock) {
    btnPreloadLabMock.addEventListener('click', async () => {
      try {
        const data = await api.fetchMockData();
        jsonBatchInput.value = JSON.stringify(data, null, 2);
        if (jsonImportFeedback) {
          jsonImportFeedback.style.display = 'block';
          jsonImportFeedback.innerHTML = '<span style="color: var(--blue-cyan);">Reset to official 4-order DS_GROUP NO-31 dataset.</span>';
        }
      } catch (e) {
        console.error(e);
      }
    });
  }

  if (btnSubmitJsonBatch) {
    btnSubmitJsonBatch.addEventListener('click', async () => {
      try {
        const parsed = JSON.parse(jsonBatchInput.value);
        if (!Array.isArray(parsed)) {
          throw new Error('Payload must be a JSON array of order objects.');
        }
        btnSubmitJsonBatch.disabled = true;
        btnSubmitJsonBatch.textContent = 'Importing...';
        const res = await api.importBatch(parsed);
        if (jsonImportFeedback) {
          jsonImportFeedback.style.display = 'block';
          jsonImportFeedback.innerHTML = `<span style="color: var(--status-success);">Successfully enqueued ${res.count} orders into the active queue!</span>`;
        }
        tabBtnPipeline.click();
      } catch (err) {
        if (jsonImportFeedback) {
          jsonImportFeedback.style.display = 'block';
          jsonImportFeedback.innerHTML = `<span style="color: var(--status-danger);">JSON Parse Error: ${err.message}</span>`;
        }
      } finally {
        btnSubmitJsonBatch.disabled = false;
        btnSubmitJsonBatch.textContent = 'Import & Enqueue';
      }
    });
  }

  if (btnVerifyMockDispatch) {
    btnVerifyMockDispatch.addEventListener('click', async () => {
      btnVerifyMockDispatch.disabled = true;
      btnVerifyMockDispatch.textContent = 'Verifying...';
      try {
        const res = await api.verifyMockSimulation();
        if (jsonImportFeedback) {
          jsonImportFeedback.style.display = 'block';
          const heapOrder = res.priority_heap_dispatch_order.map(o => `<strong>#${o.order_id} (${o.order_type} P${o.priority_level})</strong>`).join(' → ');
          const fifoOrder = res.baseline_fifo_dispatch_order.map(o => `<strong>#${o.order_id} (${o.order_type})</strong>`).join(' → ');
          jsonImportFeedback.innerHTML = `
            <div style="background: rgba(37, 99, 235, 0.15); border: 1px solid var(--blue-border); padding: 0.75rem; border-radius: var(--radius-sm); margin-top: 0.5rem;">
              <div style="color: #10b981; font-weight: 700; margin-bottom: 0.3rem;">✓ Algorithm Verification: PASSED</div>
              <div style="font-size: 0.75rem; color: #f8fafc; margin-bottom: 0.2rem;">⚡ Priority Heap Order: ${heapOrder}</div>
              <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.4rem;">⏱️ Baseline FIFO Order: ${fifoOrder}</div>
              <div style="font-size: 0.72rem; color: #38bdf8; font-style: italic;">${res.algorithmic_analysis}</div>
            </div>
          `;
        }
      } catch (err) {
        if (jsonImportFeedback) {
          jsonImportFeedback.style.display = 'block';
          jsonImportFeedback.innerHTML = `<span style="color: var(--status-danger);">Verification Error: ${err.message}</span>`;
        }
      } finally {
        btnVerifyMockDispatch.disabled = false;
        btnVerifyMockDispatch.textContent = 'Verify Bypass Test';
      }
    });
  }

  btnRunBenchmarkAction.addEventListener('click', async () => {
    btnRunBenchmarkAction.disabled = true;
    btnRunBenchmarkAction.textContent = 'Simulating 30 Batches...';
    benchmarkContent.innerHTML = '<div style="text-align: center; padding: 2rem; color: #38bdf8;">Running parallel FIFO vs Heap benchmark (30 chaotic tickets)...</div>';
    try {
      const results = await api.runBenchmark(30, currentState ? currentState.chef_count : 3);
      renderBenchmarkResults(results);
    } catch (e) {
      benchmarkContent.innerHTML = `<div style="color: #ef4444;">Benchmark error: ${e.message}</div>`;
    } finally {
      btnRunBenchmarkAction.disabled = false;
      btnRunBenchmarkAction.textContent = 'Run Benchmark';
    }
  });

  // --- State Synchronization ---
  function handleStateUpdate(state) {
    currentState = state;

    // 1. Clock & Controls
    elSimClock.textContent = `${state.sim_time.toFixed(1)}s`;
    updatePlayPauseUI(state.is_running);

    // 2. Strategy Toggle state sync
    if (state.mode === 'PRIORITY_HEAP') {
      togglePriority.classList.add('active');
      toggleFifo.classList.remove('active');
    } else {
      toggleFifo.classList.add('active');
      togglePriority.classList.remove('active');
    }

    // 3. Sliders / Selects
    if (document.activeElement !== selectChefCount) {
      selectChefCount.value = state.chef_count;
    }
    if (document.activeElement !== selectTraffic) {
      selectTraffic.value = state.traffic_mode;
    }
    if (document.activeElement !== sliderAging) {
      sliderAging.value = state.aging_factor;
      valAging.textContent = `${state.aging_factor.toFixed(1)}x`;
    }

    // 4. Metrics Cards
    const an = state.analytics;
    valAvgWait.textContent = an.average_waiting_time_overall.toFixed(1);
    valWaitVip.textContent = `VIP: ${an.average_waiting_time_vip.toFixed(1)}s`;
    valWaitExpress.textContent = `Exp: ${an.average_waiting_time_express.toFixed(1)}s`;
    valWaitStandard.textContent = `Std: ${an.average_waiting_time_standard.toFixed(1)}s`;

    valQueueLength.textContent = state.queue_size;
    valMaxQueue.textContent = `Peak: ${state.peak_queue_size}`;
    valChefFleetUtil.textContent = `${an.chef_fleet_utilization_percent.toFixed(1)}%`;
    valThroughput.textContent = `${an.throughput_orders_per_minute.toFixed(1)}`;
    valTotalCompleted.textContent = `Total: ${an.total_orders_completed}`;

    activeQueueCountBadge.textContent = `${state.queue_size} Orders`;

    // 5. Visualizer Render
    if (activeTab === 'heap') {
      heapVis.render(state.heap_tree, state.heap_array, state.mode === 'PRIORITY_HEAP');
    }

    // 6. Queue Pipeline List Render
    renderQueueCards(state.queue_orders, state.mode);

    // 7. Kitchen Stations (Chefs)
    renderChefs(state.chefs);

    // 8. Event Activity Stream
    renderEvents(state.recent_events);

    // 9. Update Charts
    charts.updateCharts(an, an.queue_timeline, state.chefs);
  }

  function handleConnectionChange(isConnected) {
    if (isConnected) {
      elClockPulse.classList.remove('paused');
    } else {
      elClockPulse.classList.add('paused');
    }
  }

  function updatePlayPauseUI(isRunning) {
    if (isRunning) {
      btnPlay.classList.add('btn-success');
      btnPlay.classList.remove('btn-outline');
      btnPause.classList.add('btn-outline');
      btnPause.classList.remove('btn-warning');
      elClockPulse.classList.remove('paused');
    } else {
      btnPause.classList.add('btn-warning');
      btnPause.classList.remove('btn-outline');
      btnPlay.classList.add('btn-outline');
      btnPlay.classList.remove('btn-success');
      elClockPulse.classList.add('paused');
    }
  }

  // --- DOM Renderers ---

  function renderQueueCards(orders, mode) {
    if (!queueCardsList) return;
    if (!orders || orders.length === 0) {
      queueCardsList.innerHTML = `
        <div style="text-align: center; color: #64748b; padding: 2.5rem; font-size: 0.85rem;">
          No pending orders in queue. The kitchen is ready!
        </div>
      `;
      return;
    }

    queueCardsList.innerHTML = orders.map((order, idx) => {
      const tierClass = order.tier.toLowerCase();
      const badgeClass = `badge-${tierClass}`;
      const canEscalate = order.tier !== 'VIP';
      const itemsHtml = (order.items && order.items.length > 0)
        ? `<div style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px;">
            ${order.items.map(it => `<span style="background: rgba(37, 99, 235, 0.18); border: 1px solid var(--blue-border); font-size: 0.7rem; padding: 2px 7px; border-radius: 4px; color: #93c5fd;">🍽️ ${it}</span>`).join('')}
           </div>`
        : '';

      return `
        <div class="order-card order-${tierClass}">
          <div class="order-main-info">
            <div class="order-id-row">
              <span class="order-id">#${order.order_id}</span>
              <span class="${badgeClass}">#${idx + 1} ${order.tier} (Priority ${order.priority_level})</span>
              ${order.is_escalated ? '<span style="font-size: 0.7rem; color: #ec4899; font-weight: 700;">⚡ ESCALATED</span>' : ''}
            </div>
            <div class="order-dish">${order.dish_name}</div>
            ${itemsHtml}
            <div class="order-customer-row" style="margin-top: 4px;">
              <span>👤 ${order.customer_name}</span>
              <span>•</span>
              <span>🕒 ${order.arrival_timestamp || '18:00:00'}</span>
              <span>•</span>
              <span>⏱️ Est: ${order.prep_time}m</span>
              <span>•</span>
              <span>⏳ Waiting: ${order.current_wait}s</span>
            </div>
          </div>
          <div class="order-metrics-col">
            <span class="order-score-badge" title="Dynamic Priority Score">Score: ${order.priority_score}</span>
            <div class="order-actions">
              ${canEscalate ? `
                <button class="btn btn-outline btn-sm btn-escalate" data-id="${order.order_id}" title="Dynamically Escalate to VIP Tier">
                  ⚡ VIP
                </button>
              ` : ''}
              <button class="btn btn-outline btn-sm btn-cancel" data-id="${order.order_id}" style="color: #ef4444;" title="Cancel Order">
                ✕
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Attach actions
    queueCardsList.querySelectorAll('.btn-escalate').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await api.escalateOrder(btn.dataset.id, 'VIP', 'Front-Desk Expedited');
      });
    });

    queueCardsList.querySelectorAll('.btn-cancel').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await api.cancelOrder(btn.dataset.id);
      });
    });
  }

  function renderChefs(chefs) {
    if (!chefsContainer) return;
    chefsContainer.innerHTML = chefs.map(chef => {
      const isCooking = chef.status === 'COOKING';
      const statusClass = isCooking ? 'status-cooking' : 'status-idle';
      const order = chef.current_order;

      return `
        <div class="chef-card ${isCooking ? 'cooking' : ''}">
          <div class="chef-header-row">
            <span class="chef-name">👨‍🍳 ${chef.name.split(' (')[0]}</span>
            <span class="chef-status-badge ${statusClass}">${chef.status}</span>
          </div>

          <div class="chef-active-dish">
            ${order ? `
              <div class="active-dish-title">${order.dish_name} (${order.order_id})</div>
              <div class="active-dish-timer">
                <span>[${order.tier}] ${order.customer_name}</span>
                <span>⏱️ ${chef.cooking_time_remaining}s</span>
              </div>
            ` : `
              <div style="font-size: 0.78rem; color: #64748b; text-align: center;">Ready for Next Ticket</div>
            `}
          </div>

          <div class="progress-track">
            <div class="progress-fill" style="width: ${chef.progress_percent}%;"></div>
          </div>

          <div class="chef-stats-row">
            <span>Util: <strong style="color: #38bdf8;">${chef.utilization_rate}%</strong></span>
            <span>Completed: <strong style="color: #f8fafc;">${chef.orders_completed_count}</strong></span>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderEvents(events) {
    if (!eventFeed) return;
    if (!events || events.length === 0) {
      eventFeed.innerHTML = '<div style="color: #64748b; font-size: 0.75rem; padding: 1rem; text-align: center;">Awaiting kitchen activity...</div>';
      return;
    }

    eventFeed.innerHTML = events.map(ev => `
      <div class="event-row level-${ev.level || 'info'}">
        <span class="event-time">${ev.timestamp.toFixed(1)}s</span>
        <span class="event-msg">${ev.message}</span>
      </div>
    `).join('');
  }

  function renderAcademicReport(report) {
    const meta = report.project_metadata;
    const core = report.core_metrics;
    const params = report.simulation_parameters;

    reportContent.innerHTML = `
      <div class="report-section">
        <h3>🏛️ Academic Metadata & Team Details</h3>
        <p><strong>Project:</strong> ${meta.title}</p>
        <p><strong>Institute:</strong> ${meta.institution}</p>
        <p><strong>Department:</strong> ${meta.department}</p>
        <p><strong>Group:</strong> ${meta.group_id} | <strong>Subject:</strong> ${meta.subject}</p>
        <p><strong>Team Members:</strong> ${meta.team_members.join(', ')}</p>
      </div>

      <div class="report-section">
        <h3>⚙️ Simulation Parameters</h3>
        <p><strong>Algorithm Discipline:</strong> ${params.active_mode}</p>
        <p><strong>Chef Servers Configured:</strong> ${params.chef_servers_count}</p>
        <p><strong>Elapsed Simulation Time:</strong> ${params.simulated_time_seconds} seconds</p>
        <p><strong>Aging Anti-Starvation Factor:</strong> ${params.aging_anti_starvation_factor}</p>
      </div>

      <div class="report-section">
        <h3>📊 Statistical Performance Metrics</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 0.5rem;">
          <div>
            <p><strong>Total Completed:</strong> ${core.total_orders_completed} tickets</p>
            <p><strong>Maximum Queue Length:</strong> ${core.maximum_peak_queue_depth}</p>
            <p><strong>Throughput:</strong> ${core.throughput_orders_per_minute} orders/min</p>
            <p><strong>Chef Utilization:</strong> ${core.chef_fleet_utilization_rate_pct}%</p>
          </div>
          <div>
            <p><strong>Avg Wait (Overall):</strong> ${core.average_waiting_times.overall_seconds}s</p>
            <p><strong>Avg Wait (VIP Tier):</strong> <span style="color: #fbbf24; font-weight: 700;">${core.average_waiting_times.vip_tier_seconds}s</span></p>
            <p><strong>Avg Wait (Express):</strong> ${core.average_waiting_times.express_tier_seconds}s</p>
            <p><strong>Avg Wait (Standard):</strong> ${core.average_waiting_times.standard_tier_seconds}s</p>
          </div>
        </div>
      </div>

      <div class="report-section">
        <h3>💡 Algorithmic Conclusion</h3>
        <p style="font-style: italic; color: #38bdf8;">${report.algorithmic_conclusion}</p>
      </div>
    `;
  }

  function renderBenchmarkResults(data) {
    const f = data.fifo_baseline;
    const h = data.priority_heap;
    const comp = data.comparison_summary;

    benchmarkContent.innerHTML = `
      <div class="benchmark-compare-grid">
        <div class="benchmark-box">
          <h4 style="color: #94a3b8; margin-bottom: 0.5rem;">Baseline FIFO Queue</h4>
          <p>Orders Completed: <strong>${f.total_completed}</strong></p>
          <p>Peak Queue: <strong>${f.max_queue}</strong></p>
          <p>Avg Wait (Overall): <strong>${f.avg_wait_overall}s</strong></p>
          <p style="color: #ef4444; font-size: 0.95rem;">VIP Wait Time: <strong>${f.avg_wait_vip}s</strong></p>
          <p>Standard Wait: <strong>${f.avg_wait_standard}s</strong></p>
          <p>Chef Utilization: <strong>${f.avg_chef_utilization}%</strong></p>
        </div>

        <div class="benchmark-box highlight">
          <h4 style="color: #38bdf8; margin-bottom: 0.5rem;">Priority Queue (Heap)</h4>
          <p>Orders Completed: <strong>${h.total_completed}</strong></p>
          <p>Peak Queue: <strong>${h.max_queue}</strong></p>
          <p>Avg Wait (Overall): <strong>${h.avg_wait_overall}s</strong></p>
          <p style="color: #fbbf24; font-size: 0.95rem;">VIP Wait Time: <strong>${h.avg_wait_vip}s</strong></p>
          <p>Standard Wait: <strong>${h.avg_wait_standard}s</strong></p>
          <p>Chef Utilization: <strong>${h.avg_chef_utilization}%</strong></p>
        </div>
      </div>

      <div style="background: rgba(37, 99, 235, 0.15); border: 1px solid var(--blue-border); padding: 1rem; border-radius: var(--radius-md); text-align: center;">
        <div style="font-size: 1.1rem; font-weight: 700; color: #38bdf8;">
          VIP Latency Reduction: ${comp.vip_latency_improvement_pct} (${comp.vip_wait_time_reduction_seconds}s saved)
        </div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.3rem;">
          ${comp.verdict}
        </div>
      </div>
    `;
  }
});
