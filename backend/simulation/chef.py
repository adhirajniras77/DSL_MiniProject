from typing import Optional, Dict, Any
from enum import Enum
from ..structures.order import Order, OrderStatus

class ChefStatus(str, Enum):
    IDLE = "IDLE"
    COOKING = "COOKING"
    EXPEDITING = "EXPEDITING"

CHEF_NAMES = [
    "Chef Gordon (Head Chef)",
    "Chef Julia (Sous Chef)",
    "Chef Marco (Pastry & Grill)",
    "Chef Auguste (Saucier)",
    "Chef Elena (Line Cook)",
    "Chef Antoine (Expediter)",
    "Chef Priya (Wok Master)",
    "Chef Kenji (Prep & Fry)"
]

class Chef:
    """
    Represents a kitchen server (chef).
    Tracks active dish preparation, idle vs. busy duration, and calculates
    real-time chef utilization rates.
    """

    def __init__(self, chef_id: str, name: Optional[str] = None):
        self.chef_id: str = chef_id
        self.name: str = name or f"Chef {chef_id}"
        self.status: ChefStatus = ChefStatus.IDLE
        self.current_order: Optional[Order] = None
        self.cooking_time_remaining: float = 0.0
        
        # Statistics
        self.total_busy_time: float = 0.0
        self.orders_completed_count: int = 0
        self.last_order_completed: Optional[Dict[str, Any]] = None

    def is_available(self) -> bool:
        """Checks if chef is idle and ready to take the next order."""
        return self.status == ChefStatus.IDLE and self.current_order is None

    def assign_order(self, order: Order, current_time: float) -> None:
        """Assigns an order to this chef and starts preparation."""
        self.current_order = order
        self.status = ChefStatus.COOKING
        self.cooking_time_remaining = order.prep_time
        
        # Update order timestamps and assignments
        order.status = OrderStatus.COOKING
        order.start_cooking_time = current_time
        order.assigned_chef_id = self.chef_id
        order.assigned_chef_name = self.name

    def tick(self, delta_time: float, current_time: float) -> Optional[Order]:
        """
        Advances the chef's timer by delta_time.
        Returns the completed order if preparation finished on this tick, else None.
        """
        if self.status == ChefStatus.COOKING and self.current_order is not None:
            time_worked = min(delta_time, self.cooking_time_remaining)
            self.total_busy_time += time_worked
            self.cooking_time_remaining -= delta_time

            if self.cooking_time_remaining <= 0.001:
                # Order complete!
                finished_order = self.current_order
                finished_order.status = OrderStatus.COMPLETED
                finished_order.completion_time = current_time
                self.orders_completed_count += 1
                self.last_order_completed = {
                    "order_id": finished_order.order_id,
                    "dish_name": finished_order.dish_name,
                    "customer_name": finished_order.customer_name,
                    "tier": finished_order.tier.value,
                    "turnaround": finished_order.turnaround_time,
                    "wait": finished_order.waiting_time
                }
                
                # Reset chef to idle
                self.current_order = None
                self.status = ChefStatus.IDLE
                self.cooking_time_remaining = 0.0
                return finished_order

        return None

    def get_utilization_rate(self, total_simulation_time: float) -> float:
        """
        Calculates Chef Utilization Rate:
        Utilization = (Total Busy Time / Total Elapsed Time) * 100%.
        """
        if total_simulation_time <= 0.001:
            return 0.0
        rate = (self.total_busy_time / total_simulation_time) * 100.0
        return round(min(100.0, rate), 1)

    def to_dict(self, total_simulation_time: float = 0.0, current_time: float = 0.0) -> Dict[str, Any]:
        """Serializes chef state for frontend display."""
        order_dict = self.current_order.to_dict(current_time) if self.current_order else None
        progress_pct = 0.0
        if self.current_order and self.current_order.prep_time > 0:
            elapsed = self.current_order.prep_time - max(0.0, self.cooking_time_remaining)
            progress_pct = round(min(100.0, (elapsed / self.current_order.prep_time) * 100.0), 1)

        return {
            "chef_id": self.chef_id,
            "name": self.name,
            "status": self.status.value,
            "cooking_time_remaining": round(max(0.0, self.cooking_time_remaining), 1),
            "progress_percent": progress_pct,
            "orders_completed_count": self.orders_completed_count,
            "total_busy_time": round(self.total_busy_time, 1),
            "utilization_rate": self.get_utilization_rate(total_simulation_time),
            "current_order": order_dict,
            "last_order_completed": self.last_order_completed
        }

    def reset(self) -> None:
        """Resets chef state for a fresh simulation run."""
        self.status = ChefStatus.IDLE
        self.current_order = None
        self.cooking_time_remaining = 0.0
        self.total_busy_time = 0.0
        self.orders_completed_count = 0
        self.last_order_completed = None
