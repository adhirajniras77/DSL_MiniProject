from typing import List, Dict, Any, Optional
from collections import defaultdict
from ..structures.order import Order, PriorityTier

class MetricsCollector:
    """
    Tracks real-time analytical metrics, historical queue time-series,
    throughput statistics, and comparative evaluations between FIFO and Priority Heap.
    """

    def __init__(self):
        self.completed_orders: List[Order] = []
        self.queue_length_history: List[Dict[str, Any]] = []  # [{time: t, queue_length: l, vip: v, ...}]
        self.max_queue_length: int = 0
        self.start_sim_time: float = 0.0
        
        # Summary caches
        self.wait_times_by_tier: Dict[str, List[float]] = {
            PriorityTier.VIP.value: [],
            PriorityTier.EXPRESS.value: [],
            PriorityTier.STANDARD.value: []
        }
        self.turnaround_times_by_tier: Dict[str, List[float]] = {
            PriorityTier.VIP.value: [],
            PriorityTier.EXPRESS.value: [],
            PriorityTier.STANDARD.value: []
        }

    def record_queue_sample(self, sim_time: float, queue_orders: List[Order]) -> None:
        """Records a point in the time-series for queue length tracking."""
        length = len(queue_orders)
        if length > self.max_queue_length:
            self.max_queue_length = length

        vip_count = sum(1 for o in queue_orders if o.tier == PriorityTier.VIP)
        express_count = sum(1 for o in queue_orders if o.tier == PriorityTier.EXPRESS)
        standard_count = sum(1 for o in queue_orders if o.tier == PriorityTier.STANDARD)

        # Keep last 150 points for smooth charts
        if len(self.queue_length_history) > 150:
            self.queue_length_history.pop(0)

        self.queue_length_history.append({
            "time": round(sim_time, 1),
            "total_queue": length,
            "vip_count": vip_count,
            "express_count": express_count,
            "standard_count": standard_count
        })

    def record_completed_order(self, order: Order) -> None:
        """Records order completion and aggregates statistics."""
        self.completed_orders.append(order)
        tier_val = order.tier.value
        if tier_val in self.wait_times_by_tier:
            self.wait_times_by_tier[tier_val].append(order.waiting_time)
            self.turnaround_times_by_tier[tier_val].append(order.turnaround_time)

    def get_average_wait_time(self, tier: Optional[PriorityTier] = None) -> float:
        """Returns average wait time overall or for a specific tier."""
        if tier is not None:
            times = self.wait_times_by_tier.get(tier.value, [])
            return round(sum(times) / len(times), 2) if times else 0.0
        
        all_times = [o.waiting_time for o in self.completed_orders]
        return round(sum(all_times) / len(all_times), 2) if all_times else 0.0

    def get_average_turnaround_time(self, tier: Optional[PriorityTier] = None) -> float:
        """Returns average turnaround time overall or for a specific tier."""
        if tier is not None:
            times = self.turnaround_times_by_tier.get(tier.value, [])
            return round(sum(times) / len(times), 2) if times else 0.0
            
        all_times = [o.turnaround_time for o in self.completed_orders]
        return round(sum(all_times) / len(all_times), 2) if all_times else 0.0

    def get_summary(
        self,
        current_sim_time: float,
        current_queue_length: int,
        chefs_utilization: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates comprehensive dashboard metrics package."""
        total_completed = len(self.completed_orders)
        
        # Calculate overall chef fleet utilization
        avg_chef_util = 0.0
        if chefs_utilization:
            avg_chef_util = round(
                sum(c["utilization_rate"] for c in chefs_utilization) / len(chefs_utilization),
                1
            )

        # Throughput (orders per 60 simulated seconds)
        throughput_rate = 0.0
        if current_sim_time > 5.0:
            throughput_rate = round((total_completed / current_sim_time) * 60.0, 2)

        return {
            "simulation_time_seconds": round(current_sim_time, 1),
            "total_orders_completed": total_completed,
            "current_queue_length": current_queue_length,
            "maximum_queue_length": self.max_queue_length,
            "average_waiting_time_overall": self.get_average_wait_time(),
            "average_waiting_time_vip": self.get_average_wait_time(PriorityTier.VIP),
            "average_waiting_time_express": self.get_average_wait_time(PriorityTier.EXPRESS),
            "average_waiting_time_standard": self.get_average_wait_time(PriorityTier.STANDARD),
            "average_turnaround_time_overall": self.get_average_turnaround_time(),
            "average_turnaround_time_vip": self.get_average_turnaround_time(PriorityTier.VIP),
            "average_turnaround_time_express": self.get_average_turnaround_time(PriorityTier.EXPRESS),
            "average_turnaround_time_standard": self.get_average_turnaround_time(PriorityTier.STANDARD),
            "chef_fleet_utilization_percent": avg_chef_util,
            "throughput_orders_per_minute": throughput_rate,
            "completed_by_tier": {
                "VIP": len(self.wait_times_by_tier[PriorityTier.VIP.value]),
                "EXPRESS": len(self.wait_times_by_tier[PriorityTier.EXPRESS.value]),
                "STANDARD": len(self.wait_times_by_tier[PriorityTier.STANDARD.value])
            },
            "recent_completed_orders": [
                o.to_dict(current_sim_time) for o in reversed(self.completed_orders[-15:])
            ],
            "queue_timeline": self.queue_length_history[-60:]
        }

    def reset(self) -> None:
        """Resets all metrics for fresh experiment."""
        self.completed_orders.clear()
        self.queue_length_history.clear()
        self.max_queue_length = 0
        for k in self.wait_times_by_tier:
            self.wait_times_by_tier[k].clear()
            self.turnaround_times_by_tier[k].clear()
