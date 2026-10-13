from enum import Enum
import time
from typing import Optional, Dict, Any

class PriorityTier(str, Enum):
    VIP = "VIP"
    EXPRESS = "EXPRESS"
    STANDARD = "STANDARD"

# Base weights for priority tiers (Higher = Higher Priority in Max-Heap, or Lower Rank in Min-Heap)
# Using rank order: VIP (Rank 1), EXPRESS (Rank 2), STANDARD (Rank 3)
TIER_BASE_SCORES = {
    PriorityTier.VIP: 1000,
    PriorityTier.EXPRESS: 500,
    PriorityTier.STANDARD: 100
}

TIER_RANKS = {
    PriorityTier.VIP: 1,
    PriorityTier.EXPRESS: 2,
    PriorityTier.STANDARD: 3
}

class OrderStatus(str, Enum):
    WAITING = "WAITING"
    COOKING = "COOKING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Order:
    """
    Represents an order within the Restaurant Order Management Simulator.
    Implements comparison methods for heap operations, metric tracking,
    and dynamic escalation capabilities.
    """
    _counter = 100

    def __init__(
        self,
        customer_name: str,
        tier: PriorityTier,
        dish_name: str,
        prep_time: float,
        service_type: str = "Dine-In",
        arrival_time: Optional[float] = None,
        order_id: Optional[str] = None
    ):
        Order._counter += 1
        self.order_id: str = order_id or f"ORD-{Order._counter}"
        self.customer_name: str = customer_name
        self.tier: PriorityTier = tier
        self.original_tier: PriorityTier = tier
        self.dish_name: str = dish_name
        self.prep_time: float = round(float(prep_time), 1)
        self.service_type: str = service_type
        
        # Timestamps (in simulation seconds)
        self.arrival_time: float = arrival_time if arrival_time is not None else 0.0
        self.start_cooking_time: Optional[float] = None
        self.completion_time: Optional[float] = None
        
        # Status
        self.status: OrderStatus = OrderStatus.WAITING
        self.assigned_chef_id: Optional[str] = None
        self.assigned_chef_name: Optional[str] = None
        
        # Escalation tracking
        self.is_escalated: bool = False
        self.escalation_log: list = []
        
        # Unique sequence number for FIFO tie-breaking in heap
        self.sequence_num: int = Order._counter

    def calculate_priority_score(self, current_time: float, aging_factor: float = 0.5) -> float:
        """
        Calculates dynamic priority score.
        Score = Base_Tier_Weight + (Waiting_Time * Aging_Factor).
        This guarantees VIP > Express > Standard while preventing starvation
        under sustained heavy load if aging is active.
        """
        base = TIER_BASE_SCORES.get(self.tier, 100)
        wait_duration = max(0.0, current_time - self.arrival_time)
        return base + (wait_duration * aging_factor)

    def escalate(self, target_tier: PriorityTier, reason: str = "Manager Escalation", current_time: float = 0.0) -> bool:
        """
        Dynamically escalates the order priority (e.g. VIP escalation).
        Returns True if tier changed.
        """
        if TIER_RANKS[target_tier] < TIER_RANKS[self.tier]:
            old_tier = self.tier
            self.tier = target_tier
            self.is_escalated = True
            self.escalation_log.append({
                "from_tier": old_tier.value,
                "to_tier": target_tier.value,
                "reason": reason,
                "time": current_time
            })
            return True
        return False

    @property
    def waiting_time(self) -> float:
        """Time spent waiting in queue before cooking started."""
        if self.start_cooking_time is not None:
            return max(0.0, self.start_cooking_time - self.arrival_time)
        return 0.0

    @property
    def turnaround_time(self) -> float:
        """Total time from arrival to completion."""
        if self.completion_time is not None:
            return max(0.0, self.completion_time - self.arrival_time)
        return 0.0

    def to_dict(self, current_time: float = 0.0, aging_factor: float = 0.5) -> Dict[str, Any]:
        """Serializes order state to dictionary for API and frontend."""
        current_wait = (
            current_time - self.arrival_time
            if self.status == OrderStatus.WAITING
            else (self.waiting_time if self.start_cooking_time is not None else 0.0)
        )
        remaining_prep = 0.0
        if self.status == OrderStatus.COOKING and self.start_cooking_time is not None:
            elapsed = current_time - self.start_cooking_time
            remaining_prep = max(0.0, self.prep_time - elapsed)

        return {
            "order_id": self.order_id,
            "customer_name": self.customer_name,
            "tier": self.tier.value,
            "original_tier": self.original_tier.value,
            "dish_name": self.dish_name,
            "prep_time": self.prep_time,
            "remaining_prep": round(remaining_prep, 1),
            "service_type": self.service_type,
            "arrival_time": round(self.arrival_time, 1),
            "start_cooking_time": round(self.start_cooking_time, 1) if self.start_cooking_time is not None else None,
            "completion_time": round(self.completion_time, 1) if self.completion_time is not None else None,
            "status": self.status.value,
            "assigned_chef_id": self.assigned_chef_id,
            "assigned_chef_name": self.assigned_chef_name,
            "current_wait": round(max(0.0, current_wait), 1),
            "total_wait": round(self.waiting_time, 1),
            "turnaround_time": round(self.turnaround_time, 1),
            "priority_score": round(self.calculate_priority_score(current_time, aging_factor), 1),
            "is_escalated": self.is_escalated,
            "escalation_log": self.escalation_log,
            "sequence_num": self.sequence_num
        }

    def __repr__(self) -> str:
        return f"<Order {self.order_id} [{self.tier.value}] '{self.dish_name}' - {self.status.value}>"
