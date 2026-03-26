"""
Global reactive state shared across all Solara pages.
"""
import solara

# ── Navigation ──────────────────────────────────────────────────
current_page = solara.reactive("home")  # home, settings, simulation, results

# ── Simulation Parameters ───────────────────────────────────────
sim_params = solara.reactive({
    "num_patients": 10,
    "num_doctors": 3,
    "num_nurses": 5,
    "num_visitors": 4,
    "num_cleaners": 2,
    "num_volunteers": 2,
    "initially_infected": 2,
    "infection_rate": 0.3,
    "infection_radius": 15.0,
    "recovery_rate": 0.02,
    "sim_speed": 10,
    "max_steps": 500,
    "random_seed": 42,
    "floor_plan_name": "simple",
})

# ── Floor plan (JSON dict or None) ─────────────────────────────
custom_floor_plan = solara.reactive(None)

# ── Model instance ──────────────────────────────────────────────
model_instance = solara.reactive(None)

# ── Simulation control ──────────────────────────────────────────
sim_running = solara.reactive(False)
sim_paused = solara.reactive(False)
sim_tick = solara.reactive(0)

# ── Results data ────────────────────────────────────────────────
sim_results = solara.reactive(None)
