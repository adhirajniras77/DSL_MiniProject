import unittest
from backend.structures.order import Order, PriorityTier, OrderStatus
from backend.structures.fifo_queue import FIFOQueue
from backend.structures.priority_heap import PriorityHeap
from backend.simulation.chef import Chef
from backend.simulation.engine import SimulationEngine, SimulationMode

class TestRestaurantSimulatorDataStructures(unittest.TestCase):

    def test_fifo_queue_operations(self):
        q = FIFOQueue()
        self.assertTrue(q.is_empty())
        self.assertEqual(q.size(), 0)

        o1 = Order("Adhiraj", PriorityTier.STANDARD, "Burger", 10.0, arrival_time=1.0)
        o2 = Order("Mithil", PriorityTier.VIP, "Steak", 15.0, arrival_time=2.0)
        o3 = Order("Aarav", PriorityTier.EXPRESS, "Ramen", 8.0, arrival_time=3.0)

        q.enqueue(o1)
        q.enqueue(o2)
        q.enqueue(o3)

        self.assertEqual(q.size(), 3)
        self.assertEqual(q.peak_size, 3)
        self.assertEqual(q.peek().customer_name, "Adhiraj")

        # In FIFO, o1 must come out first regardless of VIP tier of o2
        popped1 = q.dequeue()
        self.assertEqual(popped1.customer_name, "Adhiraj")
        popped2 = q.dequeue()
        self.assertEqual(popped2.customer_name, "Mithil")
        popped3 = q.dequeue()
        self.assertEqual(popped3.customer_name, "Aarav")
        self.assertTrue(q.is_empty())

    def test_priority_heap_tiers_and_ordering(self):
        heap = PriorityHeap(aging_factor=0.0)
        
        # Insert Standard first, then Express, then VIP
        std_order = Order("Customer 1", PriorityTier.STANDARD, "Salad", 5.0, arrival_time=1.0)
        exp_order = Order("Customer 2", PriorityTier.EXPRESS, "Pizza", 10.0, arrival_time=2.0)
        vip_order = Order("Customer 3", PriorityTier.VIP, "Wagyu", 18.0, arrival_time=3.0)

        heap.push(std_order)
        heap.push(exp_order)
        heap.push(vip_order)

        self.assertEqual(heap.size(), 3)
        # Root must be VIP
        self.assertEqual(heap.peek().tier, PriorityTier.VIP)

        # Dequeue sequence must be VIP -> EXPRESS -> STANDARD
        p1 = heap.pop()
        self.assertEqual(p1.tier, PriorityTier.VIP)
        self.assertEqual(p1.customer_name, "Customer 3")

        p2 = heap.pop()
        self.assertEqual(p2.tier, PriorityTier.EXPRESS)
        self.assertEqual(p2.customer_name, "Customer 2")

        p3 = heap.pop()
        self.assertEqual(p3.tier, PriorityTier.STANDARD)
        self.assertEqual(p3.customer_name, "Customer 1")
        self.assertTrue(heap.is_empty())

    def test_dynamic_interception_and_escalation(self):
        heap = PriorityHeap(aging_factor=0.0)

        std1 = Order("Std One", PriorityTier.STANDARD, "Soup", 5.0, arrival_time=1.0)
        std2 = Order("Std Two", PriorityTier.STANDARD, "Fries", 4.0, arrival_time=2.0)
        exp = Order("Exp One", PriorityTier.EXPRESS, "Wings", 8.0, arrival_time=3.0)

        heap.push(std1)
        heap.push(std2)
        heap.push(exp)

        # Before escalation, Exp One is root
        self.assertEqual(heap.peek().order_id, exp.order_id)

        # Now dynamically escalate std2 ("Std Two") to VIP!
        escalated = heap.intercept_and_escalate(std2.order_id, PriorityTier.VIP, "Customer upgraded to VIP")
        self.assertIsNotNone(escalated)
        self.assertEqual(escalated.tier, PriorityTier.VIP)
        self.assertTrue(escalated.is_escalated)

        # Now root MUST be std2 (it bubbled up to index 0)!
        self.assertEqual(heap.peek().order_id, std2.order_id)
        popped = heap.pop()
        self.assertEqual(popped.order_id, std2.order_id)

    def test_chef_cooking_and_utilization(self):
        chef = Chef("CHEF-01", "Chef Gordon")
        self.assertTrue(chef.is_available())

        order = Order("Adhiraj", PriorityTier.VIP, "Steak", 10.0, arrival_time=0.0)
        chef.assign_order(order, current_time=2.0)

        self.assertFalse(chef.is_available())
        self.assertEqual(order.status, OrderStatus.COOKING)

        # Advance 4 seconds
        finished = chef.tick(4.0, current_time=6.0)
        self.assertIsNone(finished)
        self.assertAlmostEqual(chef.cooking_time_remaining, 6.0)

        # Advance 6 seconds -> Order should finish!
        finished = chef.tick(6.0, current_time=12.0)
        self.assertIsNotNone(finished)
        self.assertEqual(finished.status, OrderStatus.COMPLETED)
        self.assertEqual(finished.completion_time, 12.0)
        self.assertEqual(finished.waiting_time, 2.0)
        self.assertEqual(finished.turnaround_time, 12.0)
        self.assertTrue(chef.is_available())

        # Check utilization after 20 simulation seconds
        util = chef.get_utilization_rate(20.0)
        # 10s busy out of 20s = 50%
        self.assertAlmostEqual(util, 50.0)

    def test_simulation_engine_integration(self):
        engine = SimulationEngine(chef_count=2, mode=SimulationMode.PRIORITY_HEAP, traffic_mode="OFF")
        
        # Inject standard order, then VIP order
        o_std = Order("Regular Diner", PriorityTier.STANDARD, "Salad", 6.0, arrival_time=0.0)
        o_vip = Order("VIP Patron", PriorityTier.VIP, "Lobster", 8.0, arrival_time=0.0)
        
        engine.add_order(o_std)
        engine.add_order(o_vip)

        # Engine tick: dispatches orders to the 2 chefs
        engine.tick(1.0)
        self.assertEqual(len([c for c in engine.chefs if not c.is_available()]), 2)

        # Add another VIP and standard while chefs are busy
        o_vip2 = Order("VIP 2", PriorityTier.VIP, "Wagyu", 10.0, arrival_time=1.0)
        o_std2 = Order("Std 2", PriorityTier.STANDARD, "Pasta", 5.0, arrival_time=1.0)
        engine.add_order(o_std2)
        engine.add_order(o_vip2)

        state = engine.get_state()
        self.assertEqual(state["queue_size"], 2)
        # In priority heap, VIP 2 must be ahead of Std 2
        self.assertEqual(state["queue_orders"][0]["tier"], "VIP")

    def test_mock_data_priority_dispatch(self):
        """
        Tests the exact JSON mock payload specified for lab evaluation:
        1001: Standard (P3), 18:00:00
        1002: VIP (P1), 18:02:00
        1003: Express (P2), 18:03:00
        1004: Standard (P3), 18:05:00
        """
        mock_payload = [
            {
                "order_id": 1001,
                "customer_name": "Adhiraj Niras",
                "order_type": "Standard",
                "priority_level": 3,
                "items": ["Margherita Pizza", "Garlic Bread"],
                "arrival_timestamp": "18:00:00",
                "estimated_prep_time_mins": 12
            },
            {
                "order_id": 1002,
                "customer_name": "Mithil Pagar",
                "order_type": "VIP",
                "priority_level": 1,
                "items": ["Truffle Pasta", "Red Wine"],
                "arrival_timestamp": "18:02:00",
                "estimated_prep_time_mins": 15
            },
            {
                "order_id": 1003,
                "customer_name": "Alex",
                "order_type": "Express",
                "priority_level": 2,
                "items": ["Iced Latte"],
                "arrival_timestamp": "18:03:00",
                "estimated_prep_time_mins": 3
            },
            {
                "order_id": 1004,
                "customer_name": "Sam",
                "order_type": "Standard",
                "priority_level": 3,
                "items": ["Veggie Burger", "Fries"],
                "arrival_timestamp": "18:05:00",
                "estimated_prep_time_mins": 10
            }
        ]

        # 1. Test in Priority Heap (Aging factor 0 to test pure priority tiers)
        heap = PriorityHeap(aging_factor=0.0)
        for item in mock_payload:
            order = Order.from_dict(item)
            heap.push(order)

        self.assertEqual(heap.size(), 4)

        # Dequeue must return: 1002 (VIP) -> 1003 (Express) -> 1001 (Standard) -> 1004 (Standard)
        d1 = heap.pop()
        self.assertEqual(d1.order_id, "1002")
        self.assertEqual(d1.customer_name, "Mithil Pagar")
        self.assertEqual(d1.tier, PriorityTier.VIP)
        self.assertEqual(d1.priority_level, 1)

        d2 = heap.pop()
        self.assertEqual(d2.order_id, "1003")
        self.assertEqual(d2.customer_name, "Alex")
        self.assertEqual(d2.tier, PriorityTier.EXPRESS)
        self.assertEqual(d2.priority_level, 2)

        d3 = heap.pop()
        self.assertEqual(d3.order_id, "1001")
        self.assertEqual(d3.customer_name, "Adhiraj Niras")
        self.assertEqual(d3.tier, PriorityTier.STANDARD)
        self.assertEqual(d3.priority_level, 3)

        d4 = heap.pop()
        self.assertEqual(d4.order_id, "1004")
        self.assertEqual(d4.customer_name, "Sam")
        self.assertEqual(d4.tier, PriorityTier.STANDARD)
        self.assertEqual(d4.priority_level, 3)

        # 2. Test in Baseline FIFO Queue
        fifo = FIFOQueue()
        for item in mock_payload:
            order = Order.from_dict(item)
            fifo.enqueue(order)

        # Chronological order: 1001 -> 1002 -> 1003 -> 1004
        f1 = fifo.dequeue()
        self.assertEqual(f1.order_id, "1001")
        f2 = fifo.dequeue()
        self.assertEqual(f2.order_id, "1002")
        f3 = fifo.dequeue()
        self.assertEqual(f3.order_id, "1003")
        f4 = fifo.dequeue()
        self.assertEqual(f4.order_id, "1004")

if __name__ == "__main__":
    unittest.main()
