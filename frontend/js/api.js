/**
 * API and WebSocket client for Restaurant Order Management Simulator
 */
class SimulatorAPI {
  constructor(onStateUpdate, onConnectionChange) {
    this.onStateUpdate = onStateUpdate;
    this.onConnectionChange = onConnectionChange;
    this.ws = null;
    this.reconnectTimer = null;
    this.baseUrl = window.location.origin;
  }

  initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        if (this.onConnectionChange) this.onConnectionChange(true);
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const state = JSON.parse(event.data);
          if (this.onStateUpdate) this.onStateUpdate(state);
        } catch (e) {
          console.error("Failed to parse WS state message:", e);
        }
      };

      this.ws.onclose = () => {
        if (this.onConnectionChange) this.onConnectionChange(false);
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        if (this.onConnectionChange) this.onConnectionChange(false);
      };
    } catch (e) {
      console.error("WebSocket connection attempt failed:", e);
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        this.initWebSocket();
      }, 2500);
    }
  }

  async sendControl(action) {
    const res = await fetch(`${this.baseUrl}/api/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    return res.json();
  }

  async sendConfig(config) {
    const res = await fetch(`${this.baseUrl}/api/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return res.json();
  }

  async createOrder(orderData) {
    const res = await fetch(`${this.baseUrl}/api/order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData)
    });
    return res.json();
  }

  async escalateOrder(orderId, targetTier = 'VIP', reason = 'Manual Priority Escalation') {
    const res = await fetch(`${this.baseUrl}/api/order/escalate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: orderId, target_tier: targetTier, reason })
    });
    return res.json();
  }

  async cancelOrder(orderId) {
    const res = await fetch(`${this.baseUrl}/api/order/${orderId}`, {
      method: 'DELETE'
    });
    return res.json();
  }

  async getAcademicReport() {
    const res = await fetch(`${this.baseUrl}/api/metrics/report`);
    return res.json();
  }

  async runBenchmark(orderCount = 30, chefCount = 3) {
    const res = await fetch(`${this.baseUrl}/api/benchmark`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_count: orderCount, chef_count: chefCount })
    });
    return res.json();
  }

  async fetchInitialState() {
    const res = await fetch(`${this.baseUrl}/api/state`);
    return res.json();
  }
}
