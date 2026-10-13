from typing import List, Optional, Dict, Any, Tuple
from .order import Order, PriorityTier, TIER_BASE_SCORES, TIER_RANKS

class PriorityHeap:
    """
    Algorithmic Priority Queue implemented using a Max-Heap data structure.
    Expedites VIP and Express orders ahead of the Standard processing line.
    
    Heap Property:
    For any node i at index i:
        Parent: (i - 1) // 2
        Left Child: 2 * i + 1
        Right Child: 2 * i + 2
        Priority(Parent) >= Priority(Children)
        
    Tie-Breaking:
    If priority scores are identical, earlier arrival (lower sequence number)
    takes precedence, preserving FIFO fairness within identical tiers.
    """

    def __init__(self, aging_factor: float = 0.5, name: str = "Kitchen Priority Max-Heap"):
        self.name: str = name
        self._heap: List[Order] = []
        self.aging_factor: float = aging_factor
        self.total_enqueued: int = 0
        self.total_dequeued: int = 0
        self.peak_size: int = 0
        self.last_operations_log: List[Dict[str, Any]] = []

    def _compare(self, order_a: Order, order_b: Order, current_time: float = 0.0) -> bool:
        """
        Returns True if order_a has HIGHER priority than order_b.
        1. Compare priority score (Tier base + wait time * aging).
           Equivalently in Min-Heap representation: Lower Priority Level (1 < 2 < 3).
        2. Tie-break: order arrived earlier (lower arrival_time, then sequence_num).
        """
        score_a = order_a.calculate_priority_score(current_time, self.aging_factor)
        score_b = order_b.calculate_priority_score(current_time, self.aging_factor)
        
        if abs(score_a - score_b) > 0.001:
            return score_a > score_b
            
        # Tie breaker 1: earlier arrival timestamp
        if abs(order_a.arrival_time - order_b.arrival_time) > 0.001:
            return order_a.arrival_time < order_b.arrival_time
            
        # Tie breaker 2: sequence number
        return order_a.sequence_num < order_b.sequence_num

    def _parent(self, i: int) -> int:
        return (i - 1) // 2

    def _left_child(self, i: int) -> int:
        return 2 * i + 1

    def _right_child(self, i: int) -> int:
        return 2 * i + 2

    def _bubble_up(self, index: int, current_time: float = 0.0) -> None:
        """
        Restores max-heap property upwards from given index to root.
        Time Complexity: O(log N).
        """
        curr = index
        while curr > 0:
            parent_idx = self._parent(curr)
            if self._compare(self._heap[curr], self._heap[parent_idx], current_time):
                # Swap current with parent
                self._heap[curr], self._heap[parent_idx] = self._heap[parent_idx], self._heap[curr]
                self.last_operations_log.append({
                    "action": "SWAP_BUBBLE_UP",
                    "from_idx": curr,
                    "to_idx": parent_idx,
                    "order_id": self._heap[parent_idx].order_id
                })
                curr = parent_idx
            else:
                break

    def _sift_down(self, index: int, current_time: float = 0.0) -> None:
        """
        Restores max-heap property downwards from given index to leaf.
        Time Complexity: O(log N).
        """
        n = len(self._heap)
        curr = index
        while True:
            largest = curr
            left = self._left_child(curr)
            right = self._right_child(curr)

            if left < n and self._compare(self._heap[left], self._heap[largest], current_time):
                largest = left

            if right < n and self._compare(self._heap[right], self._heap[largest], current_time):
                largest = right

            if largest != curr:
                self._heap[curr], self._heap[largest] = self._heap[largest], self._heap[curr]
                self.last_operations_log.append({
                    "action": "SWAP_SIFT_DOWN",
                    "from_idx": curr,
                    "to_idx": largest,
                    "order_id": self._heap[curr].order_id
                })
                curr = largest
            else:
                break

    def push(self, order: Order, current_time: float = 0.0) -> None:
        """
        Inserts an order into the Priority Queue and reorganizes the heap.
        Time Complexity: O(log N).
        """
        self.last_operations_log.clear()
        self._heap.append(order)
        self.total_enqueued += 1
        if len(self._heap) > self.peak_size:
            self.peak_size = len(self._heap)
            
        self._bubble_up(len(self._heap) - 1, current_time)

    def pop(self, current_time: float = 0.0) -> Optional[Order]:
        """
        Extracts and returns the highest priority order (Root).
        Time Complexity: O(log N).
        """
        if self.is_empty():
            return None
        self.last_operations_log.clear()
        self.total_dequeued += 1
        
        root = self._heap[0]
        last_item = self._heap.pop()
        
        if len(self._heap) > 0:
            self._heap[0] = last_item
            self._sift_down(0, current_time)
            
        return root

    def peek(self) -> Optional[Order]:
        """Returns highest priority order without removal. Time Complexity: O(1)."""
        if self.is_empty():
            return None
        return self._heap[0]

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def size(self) -> int:
        return len(self._heap)

    def heapify(self, current_time: float = 0.0) -> None:
        """Re-heapifies entire heap in O(N) time (e.g. after aging recalculation)."""
        n = len(self._heap)
        for i in range((n // 2) - 1, -1, -1):
            self._sift_down(i, current_time)

    def intercept_and_escalate(
        self,
        order_id: str,
        new_tier: PriorityTier,
        reason: str = "VIP Expedited Escalation",
        current_time: float = 0.0
    ) -> Optional[Order]:
        """
        Dynamically intercepts an order inside the priority heap, escalates its tier,
        and bubbles it up to its new expedited position.
        """
        target_idx = -1
        for idx, item in enumerate(self._heap):
            if item.order_id == order_id:
                target_idx = idx
                break

        if target_idx == -1:
            return None

        target_order = self._heap[target_idx]
        escalated = target_order.escalate(new_tier, reason, current_time)
        if escalated:
            # Re-establish heap property from target_idx upward
            self._bubble_up(target_idx, current_time)
            return target_order
        return None

    def remove(self, order_id: str, current_time: float = 0.0) -> Optional[Order]:
        """Removes a specific order by ID and restores heap invariant."""
        target_idx = -1
        for idx, item in enumerate(self._heap):
            if item.order_id == order_id:
                target_idx = idx
                break

        if target_idx == -1:
            return None

        removed = self._heap[target_idx]
        last_item = self._heap.pop()
        if target_idx < len(self._heap):
            self._heap[target_idx] = last_item
            # Restore heap upwards or downwards
            parent_idx = self._parent(target_idx)
            if target_idx > 0 and self._compare(self._heap[target_idx], self._heap[parent_idx], current_time):
                self._bubble_up(target_idx, current_time)
            else:
                self._sift_down(target_idx, current_time)
        return removed

    def clear(self) -> None:
        self._heap.clear()
        self.peak_size = 0
        self.last_operations_log.clear()

    def to_list(self) -> List[Order]:
        """Returns heap elements in raw array order."""
        return list(self._heap)

    def to_sorted_list(self, current_time: float = 0.0) -> List[Order]:
        """Returns elements in descending priority order without mutating heap."""
        snapshot = list(self._heap)
        sorted_items = []
        # Temporary copy heap
        temp_heap = PriorityHeap(aging_factor=self.aging_factor)
        temp_heap._heap = list(snapshot)
        while not temp_heap.is_empty():
            sorted_items.append(temp_heap.pop(current_time))
        return sorted_items

    def to_tree_dict(self, current_time: float = 0.0) -> Optional[Dict[str, Any]]:
        """
        Serializes binary heap into hierarchical tree structure for interactive
        frontend binary tree visualizer.
        """
        if self.is_empty():
            return None

        def build_node(i: int) -> Optional[Dict[str, Any]]:
            if i >= len(self._heap):
                return None
            order = self._heap[i]
            score = order.calculate_priority_score(current_time, self.aging_factor)
            left_node = build_node(self._left_child(i))
            right_node = build_node(self._right_child(i))
            children = []
            if left_node:
                children.append(left_node)
            if right_node:
                children.append(right_node)
                
            return {
                "heap_index": i,
                "order_id": order.order_id,
                "customer_name": order.customer_name,
                "tier": order.tier.value,
                "priority_level": order.priority_level,
                "dish_name": order.dish_name,
                "items": order.items,
                "prep_time": order.prep_time,
                "priority_score": round(score, 1),
                "is_escalated": order.is_escalated,
                "children": children
            }

        return build_node(0)

    def to_array_representation(self, current_time: float = 0.0) -> List[Dict[str, Any]]:
        """
        Returns indexed array representation showing parent/child index relationships
        for education and transparency in data structure lab evaluation.
        """
        result = []
        for i, order in enumerate(self._heap):
            parent_idx = self._parent(i) if i > 0 else None
            left_idx = self._left_child(i) if self._left_child(i) < len(self._heap) else None
            right_idx = self._right_child(i) if self._right_child(i) < len(self._heap) else None
            result.append({
                "index": i,
                "parent_index": parent_idx,
                "left_index": left_idx,
                "right_index": right_idx,
                "order_id": order.order_id,
                "customer": order.customer_name,
                "tier": order.tier.value,
                "priority_level": order.priority_level,
                "dish": order.dish_name,
                "items": order.items,
                "score": round(order.calculate_priority_score(current_time, self.aging_factor), 1)
            })
        return result

    def __len__(self) -> int:
        return len(self._heap)

    def __repr__(self) -> str:
        return f"<PriorityHeap '{self.name}' - Size: {len(self._heap)}, Peak: {self.peak_size}>"
