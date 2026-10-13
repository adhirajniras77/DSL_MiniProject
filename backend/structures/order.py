from enum import Enum
import time
from typing import Optional, Dict, Any, List

class PriorityTier(str, Enum):
    VIP = "VIP"
    EXPRESS = "EXPRESS"
    STANDARD = "STANDARD"

# Base weights for priority tiers (Higher = Higher Priority in Max-Heap)
# VIP (Rank 1): 1000, EXPRESS (Rank 2): 500, STANDARD (Rank 3): 100
TIER_BASE_SCORES = {
    PriorityTier.VIP: 1000,
    PriorityTier.EXPRESS: 500,
    PriorityTier.STANDARD: 100
}

# Explicit numerical priority rank (1 = Highest Priority in Min-Heap, 3 = Standard)
TIER_RANKS = {
    PriorityTier.VIP: 1,
    PriorityTier.EXPRESS: 2,
    PriorityTier.STANDARD: 3
}

RANK_TO_TIER = {
    1: PriorityTier.VIP,
    2: PriorityTier.EXPRESS,
    3: PriorityTier.STANDARD
}

STRING_TO_TIER = {
    "vip": PriorityTier.VIP,
    "express": PriorityTier.EXPRESS,
    "standard": PriorityTier.STANDARD
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
    items management, and dynamic escalation capabilities.
    """
    _counter = 1000

    def __init__(
        self,
        customer_name: str,
        tier: PriorityTier = PriorityTier.STANDARD,
        dish_name: Optional[str] = None,
        items: Optional[List[str]] = None,
        prep_time: float = 10.0,
        service_type: str = "Dine-In",
        arrival_time: Optional[float] = None,
        arrival_timestamp: Optional[str] = None,
        order_id: Optional[Any] = None,
        priority_level: Optional[int] = None
    ):
        Order._counter += 1
        self.order_id: str = str(order_id) if order_id is not None else f"{Order._counter}"
        self.customer_name: str = customer_name
        
        # Priority mapping
        if priority_level in RANK_TO_TIER:
            self.tier: PriorityTier = RANK_TO_TIER[priority_level]
        else:
            self.tier: PriorityTier = tier
            
        self.original_tier: PriorityTier = self.tier
        self.priority_level: int = TIER_RANKS[self.tier]
        
        # Items and dish representation
        self.items: List[str] = items if items is not None else []
        if dish_name:
            self.dish_name: str = dish_name
            if not self.items:
                self.items = [dish_name]
        elif self.items:
            self.dish_name: str = ", ".join(self.items)
        else:
            self.dish_name: str = "Chef Special"
            self.items = ["Chef Special"]

        self.prep_time: float = round(float(prep_time), 1)
        self.service_type: str = service_type
        
        # Timestamps
        self.arrival_time: float = arrival_time if arrival_time is not None else 0.0
        self.arrival_timestamp: str = arrival_timestamp or self._format_timestamp(self.arrival_time)
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

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Formats simulation seconds into HH:MM:SS format starting at 18:00:00."""
        total_sec = int(18 * 3600 + seconds)
        h = (total_sec // 3600) % 24
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any], current_sim_time: float = 0.0) -> "Order":
        """
        Creates an Order instance from dictionary payload, accepting both standard
        fields and lab mock data format.
        """
        # Determine priority tier
        tier = PriorityTier.STANDARD
        priority_lvl = data.get("priority_level")
        
        if priority_lvl in RANK_TO_TIER:
            tier = RANK_TO_TIER[priority_lvl]
        elif "order_type" in data:
            otype = str(data["order_type"]).strip().lower()
            tier = STRING_TO_TIER.get(otype, PriorityTier.STANDARD)
        elif "tier" in data:
            tier_val = str(data["tier"]).strip().lower()
            tier = STRING_TO_TIER.get(tier_val, PriorityTier.STANDARD)

        # Determine items / dish name
        items = data.get("items")
        dish_name = data.get("dish_name")
        if not dish_name and items:
            dish_name = ", ".join(items)

        # Determine prep time (handling estimated_prep_time_mins)
        prep_time = data.get("prep_time")
        if prep_time is None:
            prep_time = data.get("estimated_prep_time_mins", 10.0)

        # Parse arrival timestamp if provided
        arr_timestamp = data.get("arrival_timestamp")
        arr_time = data.get("arrival_time")
        if arr_time is None:
            if arr_timestamp:
                try:
                    parts = [int(p) for p in arr_timestamp.split(":")]
                    if len(parts) == 3:
                        # Seconds offset relative to 18:00:00
                        base_sec = 18 * 3600
                        given_sec = parts[0] * 3600 + parts[1] * 60 + parts[2]
                        arr_time = max(0.0, float(given_sec - base_sec))
                    else:
                        arr_time = current_sim_time
                except Exception:
                    arr_time = current_sim_time
            else:
                arr_time = current_sim_time

        return cls(
            customer_name=data.get("customer_name", "Guest Patron"),
            tier=tier,
            dish_name=dish_name,
            items=items,
            prep_time=prep_time,
            service_type=data.get("service_type", "Dine-In" if tier != PriorityTier.VIP else "Premium VIP Delivery"),
            arrival_time=arr_time,
            arrival_timestamp=arr_timestamp,
            order_id=data.get("order_id"),
            priority_level=priority_lvl
        )

    def calculate_priority_score(self, current_time: float, aging_factor: float = 0.5) -> float:
        """
        Calculates dynamic priority score.
        Score = Base_Tier_Weight + (Waiting_Time * Aging_Factor).
        This guarantees VIP (1000) > Express (500) > Standard (100) while preventing starvation.
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
            self.priority_level = TIER_RANKS[target_tier]
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
        """Serializes order state to dictionary for API, frontend, and tests."""
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
            "order_type": self.tier.value.capitalize(),
            "tier": self.tier.value,
            "original_tier": self.original_tier.value,
            "priority_level": self.priority_level,
            "dish_name": self.dish_name,
            "items": self.items,
            "prep_time": self.prep_time,
            "estimated_prep_time_mins": self.prep_time,
            "remaining_prep": round(remaining_prep, 1),
            "service_type": self.service_type,
            "arrival_time": round(self.arrival_time, 1),
            "arrival_timestamp": self.arrival_timestamp,
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
        return f"<Order {self.order_id} [{self.tier.value} | P{self.priority_level}] '{self.dish_name}' - {self.status.value}>"
