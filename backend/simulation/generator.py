import random
from typing import Optional, Dict, Any, List
from ..structures.order import Order, PriorityTier

MENU_ITEMS = [
    {"dish": "Prime Wagyu Steak", "prep_min": 14, "prep_max": 20, "category": "Grill", "default_tier": PriorityTier.VIP},
    {"dish": "Truffle Mushroom Risotto", "prep_min": 12, "prep_max": 16, "category": "Saute", "default_tier": PriorityTier.VIP},
    {"dish": "Artisan Wood-Fired Pizza", "prep_min": 10, "prep_max": 15, "category": "Oven", "default_tier": PriorityTier.STANDARD},
    {"dish": "Smoked Angus Burger & Fries", "prep_min": 8, "prep_max": 12, "category": "Grill", "default_tier": PriorityTier.STANDARD},
    {"dish": "Spicy Tonkotsu Ramen", "prep_min": 9, "prep_max": 13, "category": "Noodles", "default_tier": PriorityTier.EXPRESS},
    {"dish": "Classic Caesar Salad", "prep_min": 4, "prep_max": 7, "category": "Pantry", "default_tier": PriorityTier.EXPRESS},
    {"dish": "Crispy Calamari & Dip", "prep_min": 5, "prep_max": 8, "category": "Fry", "default_tier": PriorityTier.EXPRESS},
    {"dish": "Garlic Butter Prawns", "prep_min": 7, "prep_max": 11, "category": "Saute", "default_tier": PriorityTier.VIP},
    {"dish": "Creamy Penne Alfredo", "prep_min": 8, "prep_max": 12, "category": "Pasta", "default_tier": PriorityTier.STANDARD},
    {"dish": "Espresso Affogato & Pastry", "prep_min": 3, "prep_max": 5, "category": "Dessert", "default_tier": PriorityTier.EXPRESS}
]

CUSTOMER_NAMES = [
    "Adhiraj N.", "Mithil P.", "Aarav Sharma", "Priya Verma",
    "Rohan Deshmukh", "Ananya Iyer", "Vikram Patel", "Sneha Kulkarni",
    "Dev Malhotra", "Neha Joshi", "Arjun Nair", "Diya Kapoor",
    "Kabir Sen", "Meera Rao", "Karan Singhania", "Ishita Gupta",
    "Aditya Shinde", "Tanvi Bhatia", "Rishi Mehta", "Pooja Hegde"
]

SERVICE_TYPES = ["Dine-In", "Takeout", "Premium VIP Delivery"]

class OrderGenerator:
    """
    Generates realistic, variable customer orders simulating peak hours,
    chaotic arrivals, and diverse preparation complexities.
    """

    def __init__(
        self,
        traffic_mode: str = "NORMAL",
        vip_probability: float = 0.15,
        express_probability: float = 0.25,
        standard_probability: float = 0.60
    ):
        self.traffic_mode: str = traffic_mode  # CALM, NORMAL, RUSH_HOUR, CHAOTIC
        self.vip_prob: float = vip_probability
        self.express_prob: float = express_probability
        self.standard_prob: float = standard_probability
        
        # Countdown timer until next random order arrival (in simulation seconds)
        self.time_to_next_arrival: float = self._sample_inter_arrival_time()
        self.total_generated: int = 0

    def _sample_inter_arrival_time(self) -> float:
        """
        Samples variable order inter-arrival time according to traffic dynamics.
        Uses exponential/uniform distributions to mimic Poisson arrival processes.
        """
        if self.traffic_mode == "CALM":
            return random.uniform(8.0, 16.0)
        elif self.traffic_mode == "NORMAL":
            return random.uniform(4.0, 9.0)
        elif self.traffic_mode == "RUSH_HOUR":
            return random.uniform(1.5, 4.0)
        elif self.traffic_mode == "CHAOTIC":
            # Chaotic kitchen: bursts alternating with quick tickets
            return random.expovariate(1.0 / 2.5)
        else:
            return random.uniform(5.0, 10.0)

    def set_traffic_mode(self, mode: str) -> None:
        """Updates traffic intensity mode."""
        self.traffic_mode = mode.upper()
        self.time_to_next_arrival = min(self.time_to_next_arrival, self._sample_inter_arrival_time())

    def create_custom_order(
        self,
        customer_name: str,
        tier: PriorityTier,
        dish_name: str,
        prep_time: float,
        service_type: str = "Dine-In",
        arrival_time: float = 0.0
    ) -> Order:
        """Creates a deterministic or user-injected custom order."""
        self.total_generated += 1
        return Order(
            customer_name=customer_name,
            tier=tier,
            dish_name=dish_name,
            prep_time=prep_time,
            service_type=service_type,
            arrival_time=arrival_time
        )

    def tick(self, delta_time: float, current_time: float) -> Optional[Order]:
        """
        Advances the arrival generator clock.
        If arrival threshold is reached, creates and returns a newly arrived order.
        """
        if self.traffic_mode == "OFF":
            return None

        self.time_to_next_arrival -= delta_time
        if self.time_to_next_arrival <= 0.0:
            # Generate new random order
            order = self._generate_random_order(current_time)
            self.time_to_next_arrival = self._sample_inter_arrival_time()
            return order

        return None

    def _generate_random_order(self, current_time: float) -> Order:
        """Samples customer, tier, dish, and prep time."""
        # Tier selection
        r = random.random()
        if r < self.vip_prob:
            tier = PriorityTier.VIP
            service = "Premium VIP Delivery" if random.random() < 0.5 else "Dine-In"
        elif r < (self.vip_prob + self.express_prob):
            tier = PriorityTier.EXPRESS
            service = "Express Takeout"
        else:
            tier = PriorityTier.STANDARD
            service = random.choice(["Dine-In", "Takeout"])

        # Dish selection
        dish_info = random.choice(MENU_ITEMS)
        prep_time = round(random.uniform(dish_info["prep_min"], dish_info["prep_max"]), 1)
        customer = random.choice(CUSTOMER_NAMES)

        self.total_generated += 1
        return Order(
            customer_name=customer,
            tier=tier,
            dish_name=dish_info["dish"],
            prep_time=prep_time,
            service_type=service,
            arrival_time=current_time
        )

    def reset(self) -> None:
        self.time_to_next_arrival = self._sample_inter_arrival_time()
        self.total_generated = 0
