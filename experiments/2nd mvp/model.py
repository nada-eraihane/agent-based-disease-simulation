"""
model.py
========
HospitalModel — the Mesa simulation model.

WHAT CHANGED FROM THE ORIGINAL:
────────────────────────────────
1. Accepts a `floor_plan` dict (already processed by floor_plan_loader)
   OR a `floor_plan_path` string to load from file.
   The Solara setup page passes a processed dict; standalone usage can
   pass a file path.

2. Grid dimensions come from the floor plan, not from user sliders.
   The floor plan IS the spatial definition — its size is fixed.

3. torus=False — a building has hard edges, not a wraparound space.

4. Agents are only placed on walkable cells at startup.
   Before, they were placed anywhere on the grid.

5. self.floor_plan and self.walkable are stored as attributes so:
     • agents.move() can check `if cell in self.model.walkable`
     • app.py's visualisation can read room/wall data for drawing

MODEL PARAMETERS (adjustable via Solara sliders in app.py):
    n_staff / n_patients / n_visitors    → agent counts
    infected_*                           → initial infected counts
    transmission_prob                    → P(infection per shared step)
    recovery_steps                       → ticks until recovery
"""

import mesa
from agents import HospitalAgent, State
from floor_plan_loader import load as fp_load


class HospitalModel(mesa.Model):

    def __init__(
        self,
        floor_plan        = None,              # already-processed dict (from app.py)
        floor_plan_path   = "floor_plan.json", # used if floor_plan is None
        n_staff           = 10,
        n_patients        = 15,
        n_visitors        = 10,
        infected_staff    = 1,
        infected_patients = 2,
        infected_visitors = 0,
        transmission_prob = 0.3,
        recovery_steps    = 50,
    ):
        super().__init__()

        # Store SIR parameters on self so agents can read them
        self.transmission_prob = transmission_prob
        self.recovery_steps    = recovery_steps

        # ── Load floor plan ──────────────────────────────────────────────────
        # Priority: passed-in dict > file path.
        # The Solara setup page always passes a processed dict so the model
        # never needs to hit the filesystem during simulation.
        if floor_plan is not None:
            fp = floor_plan
        else:
            fp = fp_load(floor_plan_path)

        # Expose on self so agents and visualisation can access them
        self.floor_plan = fp                  # full dict (rooms, walls, objects)
        self.walkable   = fp["walkable"]      # set of (x,y) tuples — O(1) lookup

        width  = fp["width"]
        height = fp["height"]

        # ── Mesa grid ────────────────────────────────────────────────────────
        # MultiGrid: multiple agents may share a cell (needed for infection).
        # torus=False: the building has physical edges.
        self.grid = mesa.space.MultiGrid(width, height, torus=False)

        # ── Data collector ───────────────────────────────────────────────────
        # Records S/I/R counts each step so SIRChart can plot them.
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Susceptible": lambda m: sum(
                    1 for a in m.agents if a.state == State.SUSCEPTIBLE
                ),
                "Infected":    lambda m: sum(
                    1 for a in m.agents if a.state == State.INFECTED
                ),
                "Recovered":   lambda m: sum(
                    1 for a in m.agents if a.state == State.RECOVERED
                ),
            }
        )

        # ── Place agents on walkable cells ───────────────────────────────────
        # Convert walkable set to list for random.choice (sets aren't indexable)
        walkable_cells = list(self.walkable)

        if not walkable_cells:
            raise ValueError(
                "Floor plan has no walkable cells. "
                "Make sure at least one room is defined."
            )

        agent_specs = [
            ("staff",   n_staff,    min(infected_staff,    n_staff)),
            ("patient", n_patients, min(infected_patients, n_patients)),
            ("visitor", n_visitors, min(infected_visitors, n_visitors)),
        ]

        for agent_type, total, n_infected in agent_specs:
            for i in range(total):
                # First n_infected agents of this type start INFECTED
                state = State.INFECTED if i < n_infected else State.SUSCEPTIBLE
                agent = HospitalAgent(self, agent_type, state)
                # Place on a randomly chosen walkable cell (not just any grid cell)
                self.grid.place_agent(agent, self.random.choice(walkable_cells))

        # Collect step-0 data before any movement
        self.datacollector.collect(self)
        self.running = True


    def step(self):
        """
        Advance simulation by one tick.
        shuffle_do randomises agent activation order each step to avoid
        any one agent always having "first mover" advantage.
        """
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)