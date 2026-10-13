from typing import List, Dict, Any, Optional
import time
from ..structures.order import Order, PriorityTier, OrderStatus
from ..structures.fifo_queue import FIFOQueue
from ..structures.priority_heap import PriorityHeap
from .chef import Chef, CHEF_NAMES
from .generator import OrderGenerator
from ..analytics.metrics import MetricsCollector

class SimulationMode:
    PRIORITY_HEAP = "PRIORITY_HEAP"
    FIFO_BASELINE = "FIFO_BASELINE"

class SimulationEngine:
    """
    Central Discrete-Event Simulation Engine for Restaurant Order Management.
    Coordinates Order Arrival Generator, Data Structure Queues (FIFO vs Heap),
    Server/Chef Pools (1-N chefs), and Analytics Collectors.
    """

    def __init__(
        self,
        chef_count: int = 3,
        mode: str = SimulationMode.PRIORITY_HEAP,
        aging_factor: float = 0.5,
        traffic_mode: str = "NORMAL"
    ):
        self.mode: str = mode
        self.aging_factor: float = aging_factor
        self.is_running: bool = False
        self.speed_multiplier: float = 1.0
        self.sim_time: float = 0.0  # Simulation clock in seconds
        
        # Data Structures
        self.priority_heap: PriorityHeap = PriorityHeap(aging_factor=aging_factor)
        self.fifo_queue: FIFOQueue = FIFOQueue()
        
        # Servers / Chefs
        self.chefs: List[Chef] = []
        self._initialize_chefs(chef_count)
        
        # Order Generator
        self.generator: OrderGenerator = OrderGenerator(traffic_mode=traffic_mode)
        
        # Metrics
        self.metrics: MetricsCollector = MetricsCollector()
        
        # Event Activity Log for live frontend stream
        self.event_log: List[Dict[str, Any]] = []
        self._log_event("SYSTEM", "Simulator engine initialized. Ready to accept orders.", "info")

    def _initialize_chefs(self, count: int) -> None:
        """Configures the single or multi-server pool."""
        count = max(1, min(8, count))
        self.chefs.clear()
        for i in range(count):
            chef_id = f"CHEF-{i+1:02d}"
            name = CHEF_NAMES[i % len(CHEF_NAMES)]
            self.chefs.append(Chef(chef_id=chef_id, name=name))

    def set_chef_count(self, new_count: int) -> None:
        """Dynamically scales kitchen server capacity (1 to 8 chefs)."""
        new_count = max(1, min(8, new_count))
        curr_count = len(self.chefs)
        if new_count == curr_count:
            return

        if new_count > curr_count:
            # Add new idle chefs
            for i in range(curr_count, new_count):
                chef_id = f"CHEF-{i+1:02d}"
                name = CHEF_NAMES[i % len(CHEF_NAMES)]
                self.chefs.append(Chef(chef_id=chef_id, name=name))
            self._log_event("CHEF", f"Kitchen expanded: Added {new_count - curr_count} Chef(s).", "info")
        else:
            # Scale down: only remove idle chefs; busy ones finish and leave
            keep = []
            for chef in self.chefs:
                if len(keep) < new_count:
                    keep.append(chef)
                elif chef.is_available():
                    pass  # Safely removed
                else:
                    keep.append(chef)  # Keep until order finishes
            self.chefs = keep[:new_count]
            self._log_event("CHEF", f"Kitchen scaled to {len(self.chefs)} Chef(s).", "warning")

    def set_mode(self, new_mode: str) -> None:
        """Switches scheduling discipline between Priority Heap and Baseline FIFO."""
        if new_mode in [SimulationMode.PRIORITY_HEAP, SimulationMode.FIFO_BASELINE]:
            self.mode = new_mode
            self._log_event("STRATEGY", f"Queue strategy switched to: {new_mode}", "highlight")

    def set_aging_factor(self, factor: float) -> None:
        """Sets anti-starvation aging rate for priority heap."""
        self.aging_factor = max(0.0, float(factor))
        self.priority_heap.aging_factor = self.aging_factor
        if self.mode == SimulationMode.PRIORITY_HEAP:
            self.priority_heap.heapify(self.sim_time)
        self._log_event("CONFIG", f"Aging factor adjusted to {self.aging_factor}", "info")

    def add_order(self, order: Order) -> None:
        """Inserts an incoming order into the active data structure."""
        order.arrival_time = self.sim_time
        
        if self.mode == SimulationMode.PRIORITY_HEAP:
            self.priority_heap.push(order, self.sim_time)
        else:
            self.fifo_queue.enqueue(order)

        self._log_event(
            "ORDER_ARRIVED",
            f"[{order.tier.value}] {order.order_id} ({order.dish_name}) placed by {order.customer_name}.",
            order.tier.value.lower()
        )

    def intercept_and_escalate(self, order_id: str, new_tier: PriorityTier, reason: str = "Manual Escalation") -> bool:
        """
        Dynamically intercepts an order in queue and escalates it to higher tier.
        """
        if self.mode == SimulationMode.PRIORITY_HEAP:
            escalated = self.priority_heap.intercept_and_escalate(order_id, new_tier, reason, self.sim_time)
            if escalated:
                self._log_event(
                    "ESCALATED",
                    f"Order {order_id} escalated to {new_tier.value} in Priority Heap! ({reason})",
                    "escalated"
                )
                return True
        else:
            # Baseline FIFO escalation: find in FIFO and move to front
            order = self.fifo_queue.remove(order_id)
            if order:
                order.escalate(new_tier, reason, self.sim_time)
                # In FIFO, re-insert at front
                self.fifo_queue._items.appendleft(order)
                self._log_event(
                    "ESCALATED",
                    f"Order {order_id} escalated to {new_tier.value} in FIFO Queue!",
                    "escalated"
                )
                return True
        return False

    def cancel_order(self, order_id: str) -> bool:
        """Cancels and removes an order from the queue."""
        removed = None
        if self.mode == SimulationMode.PRIORITY_HEAP:
            removed = self.priority_heap.remove(order_id, self.sim_time)
        else:
            removed = self.fifo_queue.remove(order_id)

        if removed:
            removed.status = OrderStatus.CANCELLED
            self._log_event("CANCELLED", f"Order {order_id} cancelled and removed from queue.", "warning")
            return True
        return False

    def tick(self, delta_time: float) -> None:
        """
        Advances the simulation by delta_time (in seconds).
        Handles:
        1. Order generation from chaotic arrival model.
        2. Chef preparation ticks & dish completion.
        3. Dispatching waiting orders to available idle chefs.
        4. Metrics and time-series sampling.
        """
        scaled_delta = delta_time * self.speed_multiplier
        self.sim_time += scaled_delta

        # 1. Check for incoming orders
        new_order = self.generator.tick(scaled_delta, self.sim_time)
        if new_order:
            self.add_order(new_order)

        # 2. Advance all chefs
        for chef in self.chefs:
            finished = chef.tick(scaled_delta, self.sim_time)
            if finished:
                self.metrics.record_completed_order(finished)
                self._log_event(
                    "ORDER_SERVED",
                    f"{finished.order_id} ({finished.dish_name}) completed by {chef.name}! [Wait: {finished.waiting_time}s, Total: {finished.turnaround_time}s]",
                    "success"
                )

        # 3. Dispatch orders to idle chefs
        self._dispatch_to_idle_chefs()

        # 4. Record queue sample for metrics timeline
        current_queue_orders = (
            self.priority_heap.to_list()
            if self.mode == SimulationMode.PRIORITY_HEAP
            else self.fifo_queue.to_list()
        )
        self.metrics.record_queue_sample(self.sim_time, current_queue_orders)

    def _dispatch_to_idle_chefs(self) -> None:
        """Assigns highest priority orders to any free chefs."""
        for chef in self.chefs:
            if not chef.is_available():
                continue

            next_order: Optional[Order] = None
            if self.mode == SimulationMode.PRIORITY_HEAP:
                next_order = self.priority_heap.pop(self.sim_time)
            else:
                next_order = self.fifo_queue.dequeue()

            if next_order:
                chef.assign_order(next_order, self.sim_time)
                self._log_event(
                    "CHEF_COOKING",
                    f"{chef.name} started cooking {next_order.order_id} [{next_order.tier.value}] - {next_order.dish_name}.",
                    "info"
                )

    def _log_event(self, event_type: str, message: str, level: str = "info") -> None:
        """Appends to activity feed."""
        if len(self.event_log) > 60:
            self.event_log.pop(0)
        self.event_log.append({
            "timestamp": round(self.sim_time, 1),
            "type": event_type,
            "message": message,
            "level": level
        })

    def reset(self) -> None:
        """Resets the entire simulator to clean initial state."""
        self.sim_time = 0.0
        self.is_running = False
        self.priority_heap.clear()
        self.fifo_queue.clear()
        for chef in self.chefs:
            chef.reset()
        self.generator.reset()
        self.metrics.reset()
        self.event_log.clear()
        self._log_event("SYSTEM", "Simulator reset to time 0.0s.", "info")

    def get_state(self) -> Dict[str, Any]:
        """Returns comprehensive state for real-time frontend synchronization."""
        # Queue list
        if self.mode == SimulationMode.PRIORITY_HEAP:
            # Sorted in order of dispatch priority
            active_orders = [o.to_dict(self.sim_time, self.aging_factor) for o in self.priority_heap.to_sorted_list(self.sim_time)]
            tree_data = self.priority_heap.to_tree_dict(self.sim_time)
            array_data = self.priority_heap.to_array_representation(self.sim_time)
            q_size = self.priority_heap.size()
            peak_q = self.priority_heap.peak_size
        else:
            active_orders = [o.to_dict(self.sim_time) for o in self.fifo_queue.to_list()]
            tree_data = None
            array_data = [
                {
                    "index": i,
                    "parent_index": None,
                    "left_index": None,
                    "right_index": None,
                    "order_id": o.order_id,
                    "customer": o.customer_name,
                    "tier": o.tier.value,
                    "dish": o.dish_name,
                    "score": o.tier.value
                }
                for i, o in enumerate(self.fifo_queue.to_list())
            ]
            q_size = self.fifo_queue.size()
            peak_q = self.fifo_queue.peak_size

        chefs_data = [c.to_dict(self.sim_time, self.sim_time) for c in self.chefs]
        analytics_summary = self.metrics.get_summary(self.sim_time, q_size, chefs_data)

        return {
            "sim_time": round(self.sim_time, 1),
            "is_running": self.is_running,
            "speed_multiplier": self.speed_multiplier,
            "mode": self.mode,
            "aging_factor": self.aging_factor,
            "traffic_mode": self.generator.traffic_mode,
            "chef_count": len(self.chefs),
            "queue_size": q_size,
            "peak_queue_size": max(peak_q, self.metrics.max_queue_length),
            "queue_orders": active_orders,
            "heap_tree": tree_data,
            "heap_array": array_data,
            "chefs": chefs_data,
            "analytics": analytics_summary,
            "recent_events": list(reversed(self.event_log[-20:]))
        }
