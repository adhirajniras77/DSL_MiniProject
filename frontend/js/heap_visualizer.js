/**
 * Binary Heap and Queue Tree Visualizer for Canvas
 */
class HeapVisualizer {
  constructor(canvasId, arrayContainerId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
    this.arrayContainer = document.getElementById(arrayContainerId);
    this.resizeCanvas();

    window.addEventListener('resize', () => this.resizeCanvas());
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * (window.devicePixelRatio || 1);
    this.canvas.height = rect.height * (window.devicePixelRatio || 1);
    if (this.ctx) {
      this.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    }
  }

  render(treeData, arrayData, isPriorityHeap = true) {
    if (!this.ctx || !this.canvas) return;
    const width = this.canvas.width / (window.devicePixelRatio || 1);
    const height = this.canvas.height / (window.devicePixelRatio || 1);

    // Clear background
    this.ctx.clearRect(0, 0, width, height);

    if (!arrayData || arrayData.length === 0) {
      this.drawEmptyState(width, height, isPriorityHeap);
      this.renderArrayCells([]);
      return;
    }

    if (isPriorityHeap) {
      this.drawBinaryHeapTree(arrayData, width, height);
    } else {
      this.drawLinearFIFOQueue(arrayData, width, height);
    }

    this.renderArrayCells(arrayData);
  }

  drawEmptyState(width, height, isPriorityHeap) {
    this.ctx.fillStyle = '#64748b';
    this.ctx.font = '14px Inter, sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText(
      isPriorityHeap ? 'Priority Max-Heap is currently empty' : 'FIFO Queue is currently empty',
      width / 2,
      height / 2 - 10
    );
    this.ctx.font = '12px Inter, sans-serif';
    this.ctx.fillStyle = '#475569';
    this.ctx.fillText('Add orders above or start the simulation', width / 2, height / 2 + 15);
  }

  drawBinaryHeapTree(arrayData, width, height) {
    const n = Math.min(arrayData.length, 15); // Show up to 4 levels (15 nodes) on canvas
    const nodeCoords = [];

    // Calculate node coordinates: level 0 to 3
    for (let i = 0; i < n; i++) {
      const level = Math.floor(Math.log2(i + 1));
      const posInLevel = i - (Math.pow(2, level) - 1);
      const totalInLevel = Math.pow(2, level);

      const spacingX = width / (totalInLevel + 1);
      const x = spacingX * (posInLevel + 1);
      const y = 45 + level * 70;

      nodeCoords.push({ x, y, data: arrayData[i] });
    }

    // 1. Draw connecting branches (parent to children)
    for (let i = 0; i < n; i++) {
      const leftIdx = 2 * i + 1;
      const rightIdx = 2 * i + 2;

      if (leftIdx < n) {
        this.drawBranch(nodeCoords[i], nodeCoords[leftIdx]);
      }
      if (rightIdx < n) {
        this.drawBranch(nodeCoords[i], nodeCoords[rightIdx]);
      }
    }

    // 2. Draw nodes
    for (let i = 0; i < n; i++) {
      const node = nodeCoords[i];
      this.drawHeapNode(node.x, node.y, node.data, i);
    }
  }

  drawBranch(parent, child) {
    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.moveTo(parent.x, parent.y);
    this.ctx.lineTo(child.x, child.y);
    this.ctx.strokeStyle = 'rgba(59, 130, 246, 0.4)';
    this.ctx.lineWidth = 2;
    this.ctx.stroke();
    this.ctx.restore();
  }

  drawHeapNode(x, y, item, index) {
    const tier = item.tier;
    let borderColor = '#94a3b8';
    let bgColor = 'rgba(148, 163, 184, 0.2)';
    let textColor = '#f8fafc';

    if (tier === 'VIP') {
      borderColor = '#fbbf24';
      bgColor = 'rgba(251, 191, 36, 0.25)';
      textColor = '#fbbf24';
    } else if (tier === 'EXPRESS') {
      borderColor = '#38bdf8';
      bgColor = 'rgba(56, 189, 248, 0.25)';
      textColor = '#38bdf8';
    }

    this.ctx.save();
    // Node circle
    this.ctx.beginPath();
    this.ctx.arc(x, y, 22, 0, Math.PI * 2);
    this.ctx.fillStyle = bgColor;
    this.ctx.fill();
    this.ctx.lineWidth = 2.5;
    this.ctx.strokeStyle = borderColor;
    this.ctx.stroke();

    // Node Index badge (small circle top-left)
    this.ctx.beginPath();
    this.ctx.arc(x - 16, y - 16, 9, 0, Math.PI * 2);
    this.ctx.fillStyle = '#0f172a';
    this.ctx.fill();
    this.ctx.strokeStyle = '#38bdf8';
    this.ctx.lineWidth = 1.5;
    this.ctx.stroke();

    this.ctx.font = 'bold 9px JetBrains Mono, monospace';
    this.ctx.fillStyle = '#38bdf8';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText(index.toString(), x - 16, y - 16);

    // Node label (Order ID snippet)
    this.ctx.font = 'bold 10px JetBrains Mono, monospace';
    this.ctx.fillStyle = textColor;
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    const idShort = item.order_id ? (String(item.order_id).startsWith('#') ? String(item.order_id) : `#${String(item.order_id).replace('ORD-', '')}`) : `#${index}`;
    this.ctx.fillText(idShort, x, y - 4);

    // Score and Priority Rank badge below center
    this.ctx.font = '9px JetBrains Mono, monospace';
    const pRank = item.priority_level ? `P${item.priority_level}` : (tier === 'VIP' ? 'P1' : (tier === 'EXPRESS' ? 'P2' : 'P3'));
    this.ctx.fillText(`${pRank} [${Math.round(item.score || 0)}]`, x, y + 8);

    this.ctx.restore();
  }

  drawLinearFIFOQueue(arrayData, width, height) {
    const n = Math.min(arrayData.length, 8);
    const startX = 60;
    const gap = (width - 120) / Math.max(1, n);
    const y = height / 2;

    this.ctx.save();
    // Front and Rear labels
    this.ctx.font = 'bold 11px Inter, sans-serif';
    this.ctx.fillStyle = '#38bdf8';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('FRONT (Next Served)', startX, y - 45);
    this.ctx.fillStyle = '#64748b';
    this.ctx.fillText('REAR (Tail)', startX + (n - 1) * gap, y - 45);

    for (let i = 0; i < n; i++) {
      const x = startX + i * gap;
      const item = arrayData[i];

      // Draw box
      this.ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
      this.ctx.strokeStyle = i === 0 ? '#38bdf8' : 'rgba(59, 130, 246, 0.4)';
      this.ctx.lineWidth = i === 0 ? 2 : 1;
      this.ctx.strokeRect(x - 26, y - 26, 52, 52);
      this.ctx.fillRect(x - 26, y - 26, 52, 52);

      // Order ID
      this.ctx.font = 'bold 10px JetBrains Mono, monospace';
      this.ctx.fillStyle = '#f8fafc';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(item.order_id ? item.order_id.replace('ORD-', '#') : `#${i}`, x, y - 6);

      // Tier badge
      this.ctx.font = '9px Inter, sans-serif';
      this.ctx.fillStyle = item.tier === 'VIP' ? '#fbbf24' : (item.tier === 'EXPRESS' ? '#38bdf8' : '#94a3b8');
      this.ctx.fillText(item.tier, x, y + 10);

      // Connecting arrow
      if (i < n - 1) {
        const nextX = startX + (i + 1) * gap;
        this.ctx.beginPath();
        this.ctx.moveTo(x + 28, y);
        this.ctx.lineTo(nextX - 28, y);
        this.ctx.strokeStyle = '#3b82f6';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
      }
    }
    this.ctx.restore();
  }

  renderArrayCells(arrayData) {
    if (!this.arrayContainer) return;
    this.arrayContainer.innerHTML = '';

    if (!arrayData || arrayData.length === 0) {
      this.arrayContainer.innerHTML = '<div style="color: #64748b; font-size: 0.75rem; padding: 0.4rem;">Heap array representation empty</div>';
      return;
    }

    arrayData.slice(0, 14).forEach((cell, idx) => {
      const div = document.createElement('div');
      div.className = 'heap-cell';
      const tierClass = cell.tier ? cell.tier.toLowerCase() : 'standard';
      div.innerHTML = `
        <div class="cell-index">[${idx}]</div>
        <div class="cell-id">${cell.order_id ? cell.order_id.replace('ORD-', '#') : idx}</div>
        <div class="cell-score">${cell.tier} (${Math.round(cell.score || 0)})</div>
      `;
      this.arrayContainer.appendChild(div);
    });
  }
}
