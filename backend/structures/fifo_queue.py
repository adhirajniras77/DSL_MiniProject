from collections import deque
from typing import List, Optional, Any
from .order import Order

class FIFOQueue:
    """
    Standard First-In-First-Out (FIFO) Queue Data Structure.
    Represents the baseline linear queue model described in the problem statement
    and project objectives (DS_GROUP NO-31).
    """

    def __init__(self, name: str = "Standard FIFO Queue"):
        self.name: str = name
        self._items: deque[Order] = deque()
        self.total_enqueued: int = 0
        self.total_dequeued: int = 0
        self.peak_size: int = 0

    def enqueue(self, order: Order) -> None:
        """
        Inserts an order at the rear (tail) of the FIFO queue.
        Time Complexity: O(1).
        """
        self._items.append(order)
        self.total_enqueued += 1
        if len(self._items) > self.peak_size:
            self.peak_size = len(self._items)

    def dequeue(self) -> Optional[Order]:
        """
        Removes and returns the order at the front (head) of the FIFO queue.
        Time Complexity: O(1).
        """
        if self.is_empty():
            return None
        self.total_dequeued += 1
        return self._items.popleft()

    def peek(self) -> Optional[Order]:
        """
        Returns the order at the front without removing it.
        Time Complexity: O(1).
        """
        if self.is_empty():
            return None
        return self._items[0]

    def is_empty(self) -> bool:
        """Checks whether the queue contains zero elements."""
        return len(self._items) == 0

    def size(self) -> int:
        """Returns the current number of orders in the queue."""
        return len(self._items)

    def to_list(self) -> List[Order]:
        """Returns a snapshot list of current orders in FIFO sequence."""
        return list(self._items)

    def find(self, order_id: str) -> Optional[Order]:
        """Searches for an order by ID."""
        for order in self._items:
            if order.order_id == order_id:
                return order
        return None

    def remove(self, order_id: str) -> Optional[Order]:
        """
        Removes a specific order by ID (e.g., when intercepted and escalated to Priority Queue).
        """
        target = None
        new_deque = deque()
        while self._items:
            item = self._items.popleft()
            if item.order_id == order_id:
                target = item
            else:
                new_deque.append(item)
        self._items = new_deque
        return target

    def clear(self) -> None:
        """Resets the queue to empty state."""
        self._items.clear()
        self.peak_size = 0

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"<FIFOQueue '{self.name}' - Size: {len(self._items)}, Peak: {self.peak_size}>"
