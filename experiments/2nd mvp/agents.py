"""
agents.py
=========
HospitalAgent — the only agent class in the simulation.

WHAT CHANGED FROM THE ORIGINAL (plain grid version):
────────────────────────────────────────────────────
The only meaningful change is in move().

    BEFORE  (no floor plan):
        Agent picked any of the 8 Moore neighbours at random.
        Agents could walk through anything — no walls.

    AFTER   (floor-plan aware):
        Agent filters the 8 neighbours to only cells in model.walkable
        before choosing a destination.

        model.walkable is the set built by floor_plan_loader — it contains
        only cells inside a room/corridor, minus wall cells, plus door cells.

        The result is that agents are physically constrained by the building:
          • They cannot enter wall cells or empty space outside rooms
          • They can only move between rooms via corridors or doors
          • Placing a door in a wall creates the only legal crossing point

        If all neighbours are non-walkable (agent somehow ends up in a
        dead-end with no exits), the agent stays put for that step. This
        is a safe fallback that should never occur in a well-connected plan.

INFECTION MODEL (unchanged):
─────────────────────────────
SUSCEPTIBLE → INFECTED  (via try_infect_others, probability-based)
INFECTED    → RECOVERED (via progress_infection, after recovery_steps ticks)

Each step: move → try_infect_others → progress_infection
"""

from enum import Enum
import mesa


class State(Enum):
    SUSCEPTIBLE = "susceptible"
    INFECTED    = "infected"
    RECOVERED   = "recovered"


class HospitalAgent(mesa.Agent):

    def __init__(self, model, agent_type: str, state: State):
        super().__init__(model)
        self.agent_type      = agent_type   # "staff" | "patient" | "visitor"
        self.state           = state
        self.infection_timer = 0            # steps since infection began


    # ── Movement ──────────────────────────────────────────────────────────────

    def move(self):
        """
        Move to a random walkable neighbouring cell.

        HOW WALL AVOIDANCE WORKS:
            1. Ask Mesa for the Moore neighbourhood (8 surrounding cells).
            2. Filter that list to only cells present in model.walkable.
               model.walkable is a Python set → membership check is O(1).
            3. Pick one of the valid cells at random and move there.

        WHY MOORE (8-directional)?
            Diagonal movement matters in hospital layouts because rooms
            often meet at corners. Without diagonals, agents can get
            stuck if the only connection between two areas is a corner cell.

        WHY STAY PUT IF NO WALKABLE NEIGHBOURS?
            Shouldn't happen in a well-connected floor plan, but if an
            agent is placed on an isolated cell (rare edge case), it
            simply waits rather than crashing.
        """
        all_neighbours = self.model.grid.get_neighborhood(
            self.pos,
            moore          = True,
            include_center = False,
        )

        # Filter to only cells the floor plan marks as walkable
        walkable_neighbours = [
            cell for cell in all_neighbours
            if cell in self.model.walkable   # O(1) set lookup
        ]

        if walkable_neighbours:
            self.model.grid.move_agent(self, self.random.choice(walkable_neighbours))
        # else: stay put (safe fallback)


    # ── Infection ─────────────────────────────────────────────────────────────

    def try_infect_others(self):
        """
        If INFECTED, attempt to infect each SUSCEPTIBLE agent sharing
        this cell. Each target is independently rolled against
        model.transmission_prob.
        """
        if self.state != State.INFECTED:
            return

        for other in self.model.grid.get_cell_list_contents([self.pos]):
            if other is self:
                continue
            if other.state == State.SUSCEPTIBLE:
                if self.random.random() < self.model.transmission_prob:
                    other.state           = State.INFECTED
                    other.infection_timer = 0


    def progress_infection(self):
        """Increment infection timer; recover when it reaches recovery_steps."""
        if self.state != State.INFECTED:
            return
        self.infection_timer += 1
        if self.infection_timer >= self.model.recovery_steps:
            self.state = State.RECOVERED


    # ── Step ──────────────────────────────────────────────────────────────────

    def step(self):
        """Called once per simulation tick by Mesa's scheduler."""
        self.move()
        self.try_infect_others()
        self.progress_infection()