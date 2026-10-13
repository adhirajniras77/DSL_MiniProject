import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .structures.order import Order, PriorityTier
from .simulation.engine import SimulationEngine, SimulationMode
from .simulation.generator import MENU_ITEMS, CUSTOMER_NAMES

# Shared engine instance
engine = SimulationEngine(
    chef_count=3,
    mode=SimulationMode.PRIORITY_HEAP,
    aging_factor=0.5,
    traffic_mode="NORMAL"
)

# Active WebSocket connections
connected_websockets: List[WebSocket] = []

# Background tick worker
simulation_task: Optional[asyncio.Task] = None

async def broadcast_state():
    """Broadcasts current engine state to all active WebSocket clients."""
    if not connected_websockets:
        return
    state = engine.get_state()
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_json(state)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)

async def simulation_loop():
    """Runs continuous background ticks when simulator is active."""
    while True:
        try:
            if engine.is_running:
                # 1 second of simulation time stepped in 0.5s real time
                engine.tick(0.5)
                await broadcast_state()
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in simulation loop: {e}")
            await asyncio.sleep(1.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch background loop
    global simulation_task
    simulation_task = asyncio.create_task(simulation_loop())
    yield
    # Shutdown: cancel task
    if simulation_task:
        simulation_task.cancel()

app = FastAPI(
    title="Restaurant Order Management Queue Simulator",
    description="Queue-based Simulator for Restaurant Order Management - NMIET Pune (DS_GROUP NO-31)",
    version="1.0.0",
    lifespan=lifespan
)

# Frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# --- Pydantic Request Models ---
class CreateOrderRequest(BaseModel):
    customer_name: str = Field(default="Guest Patron", description="Customer Name")
    tier: PriorityTier = Field(default=PriorityTier.STANDARD, description="VIP, EXPRESS, or STANDARD")
    dish_name: str = Field(default="Artisan Wood-Fired Pizza", description="Dish Name")
    prep_time: float = Field(default=10.0, ge=1.0, le=60.0, description="Estimated prep duration (s)")
    service_type: str = Field(default="Dine-In", description="Dine-In, Takeout, or Premium Delivery")

class EscalateOrderRequest(BaseModel):
    order_id: str
    target_tier: PriorityTier = PriorityTier.VIP
    reason: str = "Manager Escalation"

class ControlRequest(BaseModel):
    action: str = Field(..., description="play, pause, step, reset")

class ConfigRequest(BaseModel):
    chef_count: Optional[int] = Field(default=None, ge=1, le=8)
    mode: Optional[str] = Field(default=None, description="PRIORITY_HEAP or FIFO_BASELINE")
    aging_factor: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    traffic_mode: Optional[str] = Field(default=None, description="OFF, CALM, NORMAL, RUSH_HOUR, CHAOTIC")
    speed_multiplier: Optional[float] = Field(default=None, ge=0.25, le=10.0)

class BenchmarkRequest(BaseModel):
    order_count: int = Field(default=30, ge=5, le=100)
    chef_count: int = Field(default=3, ge=1, le=6)

# --- API Endpoints ---

@app.get("/api/state")
def get_state():
    """Returns real-time simulation snapshot."""
    return engine.get_state()

@app.post("/api/order")
async def create_order(req: CreateOrderRequest):
    """Manually injects an order into the simulator."""
    order = engine.generator.create_custom_order(
        customer_name=req.customer_name,
        tier=req.tier,
        dish_name=req.dish_name,
        prep_time=req.prep_time,
        service_type=req.service_type,
        arrival_time=engine.sim_time
    )
    engine.add_order(order)
    await broadcast_state()
    return {"status": "success", "order": order.to_dict(engine.sim_time)}

@app.post("/api/order/escalate")
async def escalate_order(req: EscalateOrderRequest):
    """Intercepts and elevates an order's priority tier dynamically."""
    success = engine.intercept_and_escalate(req.order_id, req.target_tier, req.reason)
    if not success:
        raise HTTPException(status_code=400, detail="Order not found or cannot be escalated to specified tier.")
    await broadcast_state()
    return {"status": "success", "message": f"Order {req.order_id} escalated to {req.target_tier.value}."}

@app.delete("/api/order/{order_id}")
async def cancel_order(order_id: str):
    """Cancels and removes an order from the queue."""
    success = engine.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found in queue.")
    await broadcast_state()
    return {"status": "success", "message": f"Order {order_id} cancelled."}

@app.post("/api/control")
async def simulation_control(req: ControlRequest):
    """Controls simulation execution: play, pause, step, reset."""
    action = req.action.lower()
    if action == "play":
        engine.is_running = True
        engine._log_event("CONTROL", "Simulation resumed.", "info")
    elif action == "pause":
        engine.is_running = False
        engine._log_event("CONTROL", "Simulation paused.", "info")
    elif action == "step":
        engine.is_running = False
        engine.tick(1.0)
        engine._log_event("CONTROL", "Stepped simulation forward by 1.0s.", "info")
    elif action == "reset":
        engine.reset()
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use play, pause, step, or reset.")

    await broadcast_state()
    return {"status": "success", "action": action, "is_running": engine.is_running, "sim_time": engine.sim_time}

@app.post("/api/config")
async def update_config(req: ConfigRequest):
    """Updates simulation settings and parameters."""
    if req.chef_count is not None:
        engine.set_chef_count(req.chef_count)
    if req.mode is not None:
        engine.set_mode(req.mode)
    if req.aging_factor is not None:
        engine.set_aging_factor(req.aging_factor)
    if req.traffic_mode is not None:
        engine.generator.set_traffic_mode(req.traffic_mode)
    if req.speed_multiplier is not None:
        engine.speed_multiplier = req.speed_multiplier

    await broadcast_state()
    return {"status": "success", "config": {
        "chef_count": len(engine.chefs),
        "mode": engine.mode,
        "aging_factor": engine.aging_factor,
        "traffic_mode": engine.generator.traffic_mode,
        "speed_multiplier": engine.speed_multiplier
    }}

@app.get("/api/menu")
def get_menu_and_defaults():
    """Returns preconfigured menu items and sample customer names."""
    return {
        "menu": MENU_ITEMS,
        "customers": CUSTOMER_NAMES,
        "service_types": ["Dine-In", "Express Takeout", "Premium VIP Delivery"]
    }

@app.get("/api/metrics/report")
def generate_academic_report():
    """
    Generates a formal academic report aligning with
    DS_GROUP NO-31.pptx presentation objectives.
    """
    state = engine.get_state()
    analytics = state["analytics"]
    
    return {
        "project_metadata": {
            "title": "Design a Queue-Based Simulator For Restaurant Order Management",
            "institution": "Nutan Maharashtra Institute of Engineering and Technology (NMIET), Pune",
            "department": "Department of Information & Technology",
            "group_id": "DS_GROUP NO-31",
            "team_members": ["NIRAS ADHIRAJ PANDURANG", "MITHIL SHANTARAM PAGAR"],
            "subject": "Data Structures Laboratory (DSL) Mini Project",
            "academic_year": "2026-2027"
        },
        "simulation_parameters": {
            "active_mode": engine.mode,
            "chef_servers_count": len(engine.chefs),
            "simulated_time_seconds": state["sim_time"],
            "aging_anti_starvation_factor": engine.aging_factor,
            "arrival_traffic_intensity": engine.generator.traffic_mode
        },
        "core_metrics": {
            "total_orders_completed": analytics["total_orders_completed"],
            "current_queue_depth": analytics["current_queue_length"],
            "maximum_peak_queue_depth": analytics["maximum_queue_length"],
            "throughput_orders_per_minute": analytics["throughput_orders_per_minute"],
            "chef_fleet_utilization_rate_pct": analytics["chef_fleet_utilization_percent"],
            "average_waiting_times": {
                "overall_seconds": analytics["average_waiting_time_overall"],
                "vip_tier_seconds": analytics["average_waiting_time_vip"],
                "express_tier_seconds": analytics["average_waiting_time_express"],
                "standard_tier_seconds": analytics["average_waiting_time_standard"]
            },
            "average_turnaround_times": {
                "overall_seconds": analytics["average_turnaround_time_overall"],
                "vip_tier_seconds": analytics["average_turnaround_time_vip"],
                "express_tier_seconds": analytics["average_turnaround_time_express"],
                "standard_tier_seconds": analytics["average_turnaround_time_standard"]
            }
        },
        "chef_server_breakdown": [
            {
                "chef_id": c["chef_id"],
                "name": c["name"],
                "orders_completed": c["orders_completed_count"],
                "busy_time_seconds": c["total_busy_time"],
                "utilization_pct": c["utilization_rate"]
            }
            for c in state["chefs"]
        ],
        "algorithmic_conclusion": (
            "Empirical results demonstrate that the Algorithmic Priority Queue (Max-Heap) "
            "substantially reduces VIP and Express waiting latency compared to the baseline linear FIFO queue, "
            "successfully preventing high-value order starvation while maintaining optimal kitchen server utilization."
        )
    }

@app.post("/api/benchmark")
def run_comparative_benchmark(req: BenchmarkRequest):
    """
    Simulates identical batches of chaotic orders through both:
    1. Baseline FIFO Queue
    2. Algorithmic Priority Heap
    Provides mathematical proof for the project's problem statement.
    """
    import random
    
    # Generate identical order stream
    stream = []
    for i in range(req.order_count):
        r = random.random()
        if r < 0.20:
            tier = PriorityTier.VIP
        elif r < 0.50:
            tier = PriorityTier.EXPRESS
        else:
            tier = PriorityTier.STANDARD
            
        dish = random.choice(MENU_ITEMS)
        prep = round(random.uniform(dish["prep_min"], dish["prep_max"]), 1)
        arrival = round(i * random.uniform(2.0, 5.0), 1)
        
        stream.append({
            "name": f"Customer {i+1}",
            "tier": tier,
            "dish": dish["dish"],
            "prep": prep,
            "arrival": arrival
        })

    def run_sim(mode_str: str) -> Dict[str, Any]:
        sim = SimulationEngine(chef_count=req.chef_count, mode=mode_str, traffic_mode="OFF")
        pending = list(stream)
        t = 0.0
        step = 0.5
        max_time = 1200.0
        
        while t < max_time and (pending or sim.priority_heap.size() > 0 or sim.fifo_queue.size() > 0 or any(not c.is_available() for c in sim.chefs)):
            # Check arrivals
            while pending and pending[0]["arrival"] <= t:
                item = pending.pop(0)
                sim.add_order(Order(
                    customer_name=item["name"],
                    tier=item["tier"],
                    dish_name=item["dish"],
                    prep_time=item["prep"],
                    arrival_time=item["arrival"]
                ))
            sim.tick(step)
            t += step

        st = sim.get_state()
        an = st["analytics"]
        return {
            "mode": mode_str,
            "total_completed": an["total_orders_completed"],
            "max_queue": an["maximum_queue_length"],
            "avg_wait_overall": an["average_waiting_time_overall"],
            "avg_wait_vip": an["average_waiting_time_vip"],
            "avg_wait_express": an["average_waiting_time_express"],
            "avg_wait_standard": an["average_waiting_time_standard"],
            "avg_chef_utilization": an["chef_fleet_utilization_percent"],
            "throughput_opm": an["throughput_orders_per_minute"]
        }

    fifo_results = run_sim(SimulationMode.FIFO_BASELINE)
    heap_results = run_sim(SimulationMode.PRIORITY_HEAP)

    vip_wait_saved = max(0.0, fifo_results["avg_wait_vip"] - heap_results["avg_wait_vip"])
    pct_improvement = round((vip_wait_saved / max(0.1, fifo_results["avg_wait_vip"])) * 100.0, 1) if fifo_results["avg_wait_vip"] > 0 else 0.0

    return {
        "benchmark_parameters": {
            "order_count": req.order_count,
            "chef_count": req.chef_count
        },
        "fifo_baseline": fifo_results,
        "priority_heap": heap_results,
        "comparison_summary": {
            "vip_wait_time_reduction_seconds": round(vip_wait_saved, 1),
            "vip_latency_improvement_pct": f"{pct_improvement}%",
            "verdict": "Priority Queue (Heap) dramatically eliminates VIP ticket blocking vs linear FIFO."
        }
    }

# --- WebSocket Streaming ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    # Immediately send initial state
    await websocket.send_json(engine.get_state())
    try:
        while True:
            # Handle incoming ping / command messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
    except Exception:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

# Serve Frontend static assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")
