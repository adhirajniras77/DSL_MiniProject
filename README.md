# 🍽️ Queue-Based Simulator For Restaurant Order Management

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![Data Structures](https://img.shields.io/badge/Course-Data%20Structures%20Laboratory%20(DSL)-blueviolet.svg)](#)
[![Theme](https://img.shields.io/badge/Theme-Strict%20Dark%20%7C%20Blue%20Palette-0ea5e9.svg)](#)

A high-performance, full-stack Data Structures simulation and interactive web application modeling restaurant kitchen order management workflows. Designed specifically according to the specifications in **DS_GROUP NO-31.pptx**.

---

## 🏛️ Project Details

- **Institution:** Nutan Maharashtra Institute of Engineering and Technology (NMIET), Pune *(An Autonomous Institute)*
- **Department:** Department of Information & Technology
- **Course:** Data Structures Laboratory (DSL) Mini Project
- **Group ID:** DS_GROUP NO-31
- **Team Members:**
  - **NIRAS ADHIRAJ PANDURANG**
  - **MITHIL SHANTARAM PAGAR**

---

## 📌 Problem Statement

In high-traffic dining scenarios, traditional kitchen ticket systems treat incoming orders with equal urgency using standard linear First-Come, First-Served pipelines. This linear approach fails to accommodate dynamic business rules:
> *A single premium VIP order or a highly time-sensitive express pickup gets trapped behind massive, low-priority dine-in queues.*

**The Consequence:** Significant service delays, frustrated high-value customers, wasted resources, and lower kitchen throughput.

---

## 🎯 Objectives & Key Solutions

1. **Standard Queue (FIFO):** Implement a baseline First-In-First-Out queue to computationally model chronological arrival and processing.
2. **Priority Queue (Min/Max Heap):** Construct an algorithmic binary heap structure that dynamically intercepts, escalates, and expedites VIP and Express orders ahead of the standard processing line.
3. **Simulate Real-World Parameters:** Accurately model variable order arrival times (Poisson/exponential distribution) and kitchen processing durations reflecting chaotic kitchen dynamics.
4. **Multi-Server Configuration:** Model both single-server (1 chef) and multi-server (2–6 chefs) concurrency.
5. **Analytical Metrics & Statistical Throughput:** Measure and visualize real-time Average Waiting Times, Maximum Queue Depths, Server (Chef) Utilization Rates, and Throughput (orders/minute).

---

## 🚫 Project Scope (Inclusions & Exclusions)

### Inclusions (System Capabilities):
- Modeling single and multiple server (chef) service configurations (1 to 6 chefs).
- Handling 3 distinct priority tiers: **VIP**, **Express**, and **Standard**.
- Real-time graphical visualization of the binary heap tree and queue pipeline.
- Dynamic order interception and runtime escalation to VIP tier.
- Statistical throughput tracking and comparative benchmarking.

### Strict Exclusions (Out of Scope):
- ❌ No payment gateway integration or POS hardware interfacing.
- ❌ No physical inventory tracking or recipe ingredient management.
- ❌ No external delivery routing algorithms or driver tracking.

---

## 🏗️ Algorithmic Architecture & Data Structures

### 1. Baseline FIFO Queue (`backend/structures/fifo_queue.py`)
- Standard FIFO Queue with $O(1)$ `enqueue()` and $O(1)$ `dequeue()`.
- Preserves chronological arrival sequence.

### 2. Algorithmic Max-Heap Priority Queue (`backend/structures/priority_heap.py`)
- Array-based Binary Max-Heap satisfying:
  $$\text{Parent}(i) = \left\lfloor \frac{i - 1}{2} \right\rfloor$$
  $$\text{LeftChild}(i) = 2i + 1, \quad \text{RightChild}(i) = 2i + 2$$
  $$\text{Priority}(\text{Parent}) \ge \text{Priority}(\text{Children})$$
- **Priority Tiers & Weights:**
  - **VIP (Tier 1):** Base score 1000
  - **Express (Tier 2):** Base score 500
  - **Standard (Tier 3):** Base score 100
- **Anti-Starvation Aging Formula:**
  $$\text{Effective Priority} = \text{Base Weight} + (\text{Wait Time} \times \text{Aging Factor})$$
- **Dynamic Escalation:** $O(\log N)$ `intercept_and_escalate(order_id, new_tier)` modifying priority and restoring the heap property via `_bubble_up()`.

### 3. Server Utilization Formula (`backend/simulation/chef.py`)
$$\text{Utilization Rate} = \left( \frac{\text{Total Busy Cooking Time}}{\text{Total Elapsed Simulation Time}} \right) \times 100\%$$

---

## 🎨 UI/UX Design Specifications

- **Strict Dark Theme:** Deep slate/charcoal backgrounds (`#070b14`, `#0d1527`).
- **Curated Blue Palette:** Primary accents in electric blue (`#2563eb`), glowing blue borders (`#3b82f6`), and cyan highlights (`#38bdf8`).
- **Interactive Visualizations:**
  - **Live Canvas Binary Heap Visualizer:** Renders parent-child nodes and branches dynamically.
  - **Heap Array Inspector:** Displays underlying array indices `[0]`, `[1]`, `[2]` and parent pointers.
  - **Multi-Server Chef Stations:** Live circular/linear progress bars and cooking timers.
  - **Real-Time Performance Charts:** Time-series queue depth curves, waiting latency comparisons, and chef utilization gauges.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Pip package manager

### Installation

1. Navigate to the project directory:
   ```bash
   cd "C:\Users\adhir\.gemini\antigravity-ide\scratch\DSL_MiniProject"
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run automated data structure unit tests:
   ```bash
   python -m unittest tests/test_structures.py
   ```

4. Launch the application:
   ```bash
   python run.py
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

---

## 🧪 Testing

The repository includes a dedicated test suite verifying all core data structures:
- `test_fifo_queue_operations`: Verifies chronological dequeue order.
- `test_priority_heap_tiers_and_ordering`: Verifies VIP > Express > Standard priority heap invariant.
- `test_dynamic_interception_and_escalation`: Tests runtime escalation and bubble-up logic.
- `test_chef_cooking_and_utilization`: Verifies multi-server cooking ticks and utilization math.
- `test_simulation_engine_integration`: Validates end-to-end integration.

Run tests:
```bash
python -m unittest tests/test_structures.py
```
*(All 5 tests run in ~0.001s and pass 100%).*

---

## 📂 Repository Structure

```
DSL_MiniProject/
├── backend/
│   ├── structures/
│   │   ├── order.py               # Order entity, tiers, and escalation
│   │   ├── fifo_queue.py          # Pure FIFO Queue implementation
│   │   └── priority_heap.py       # Binary Max-Heap with tree serializer
│   ├── simulation/
│   │   ├── chef.py                # Chef / Server worker model & utilization
│   │   ├── generator.py           # Chaotic arrival & prep time generator
│   │   └── engine.py              # Discrete-event simulation coordinator
│   ├── analytics/
│   │   └── metrics.py             # Metrics collector & time-series sampler
│   └── app.py                     # FastAPI REST API & WebSocket server
├── frontend/
│   ├── index.html                 # Strict Dark Theme dashboard
│   ├── css/
│   │   └── styles.css             # Glassmorphism & Blue palette design
│   └── js/
│       ├── api.js                 # WebSocket & REST client
│       ├── heap_visualizer.js     # Canvas Binary Heap Tree visualizer
│       ├── charts.js              # Real-time Chart.js dashboards
│       └── app.js                 # Application state manager
├── tests/
│   └── test_structures.py         # Automated test suite
├── run.py                         # Application launcher
├── requirements.txt               # Dependencies
└── README.md                      # Academic documentation
```
