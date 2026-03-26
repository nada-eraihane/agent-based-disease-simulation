from __future__ import annotations
import random, math, time
from typing import List, Optional
from mesa import Model
from mesa.space import ContinuousSpace
from mesa.datacollection import DataCollector

from .floorplan import FloorPlan, load_predefined
from .agents import (
    HospitalAgent, PatientAgent, DoctorAgent, NurseAgent,
    VisitorAgent, CleanerAgent, VolunteerAgent,
    Status, AGENT_CLASSES,
)

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

class HospitalModel(Model):
    def __init__(self, params: dict, floor_plan: Optional[FloorPlan] = None):
        super().__init__()

        self.p = {
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
            "max_steps": 1000,

            "random_seed": 42, #to make all runs the same, for testing and debugging
            "floor_plan_name": "simple",
        }
        self.p.update(params)

        random.seed(self.p["random_seed"])

        if floor_plan:
            self.floor_plan = floor_plan
        else:
            self.floor_plan = load_predefined(self.p["floor_plan_name"])

        self.space = ContinuousSpace(
            x_max=self.floor_plan.width,
            y_max=self.floor_plan.height,
            torus=False,
        )

        self.tick_count: int = 0
        self.running: bool = True
        self.transmission_events: List[dict] = []
        self.sir_history: List[dict] = []
        self.new_infections_per_tick: List[int] = []
        self._removed_agents: set = set()

        self._create_agents()

        self.datacollector = DataCollector(
            model_reporters={
                "Susceptible": lambda m: sum(1 for a in m._living_agents() if a.status == Status.SUSCEPTIBLE),
                "Infected": lambda m: sum(1 for a in m._living_agents() if a.status == Status.INFECTED),
                "Recovered": lambda m: sum(1 for a in m._living_agents() if a.status == Status.RECOVERED),
                "Tick": lambda m: m.tick_count,
            }
        )

    def _living_agents(self) -> List[HospitalAgent]: #agents that are not removed
        return [
            a for a in self.agents
            if isinstance(a, HospitalAgent)
            and not a.removed
            and a.pos is not None
        ]

    def _create_agents(self):
        #finds all rooms and ICUs
        patient_rooms = self.floor_plan.rooms_by_type("patient_room")
        icu_rooms = self.floor_plan.rooms_by_type("icu")
        all_patient_rooms = patient_rooms + icu_rooms
        all_rooms = self.floor_plan.rooms

        def _place_in_room(room):
            cx, cy = room.centroid
            x = cx + random.uniform(-15, 15)
            y = cy + random.uniform(-15, 15)
            x = max(5, min(self.floor_plan.width - 5, x))
            y = max(5, min(self.floor_plan.height - 5, y))
            return (x, y)

        def _place_random():
            if all_rooms:
                room = random.choice(all_rooms)
                return _place_in_room(room)
            return (random.uniform(50, self.floor_plan.width - 50),
                    random.uniform(50, self.floor_plan.height - 50))

        #patients are placed in offices and randomly if not enough space
        for i in range(self.p["num_patients"]):
            a = PatientAgent(self)
            if all_patient_rooms:
                room = all_patient_rooms[i % len(all_patient_rooms)]
                pos = _place_in_room(room)
                a.assigned_room = room.name
            else:
                pos = _place_random()
            self.space.place_agent(a, pos)

        #other agents are placed randomely
        for i in range(self.p["num_doctors"]):
            a = DoctorAgent(self)
            self.space.place_agent(a, _place_random())

        for i in range(self.p["num_nurses"]):
            a = NurseAgent(self)
            self.space.place_agent(a, _place_random())

        for i in range(self.p["num_visitors"]):
            a = VisitorAgent(self)
            self.space.place_agent(a, _place_random())

        for i in range(self.p["num_cleaners"]):
            a = CleanerAgent(self)
            self.space.place_agent(a, _place_random())

        for i in range(self.p["num_volunteers"]):
            a = VolunteerAgent(self)
            self.space.place_agent(a, _place_random())

        #pick patients randomely and makes them infected
        hospital_agents = self._living_agents()
        patients = [a for a in hospital_agents if a.agent_type == "patient"]
        if not patients:
            patients = hospital_agents
        num_infect = min(self.p["initially_infected"], len(patients))
        for a in random.sample(patients, num_infect):
            a.status = Status.INFECTED

    def remove_agent(self, agent: HospitalAgent):
        agent.removed = True
        self._removed_agents.add(agent.unique_id)
        try:
            self.space.remove_agent(agent)
        except Exception:
            pass

    def _disease_step(self):
        #infection transmission logic
        living = self._living_agents()
        new_infections = 0

        infected = [a for a in living if a.status == Status.INFECTED]
        susceptible = [a for a in living if a.status == Status.SUSCEPTIBLE]

        # for each infected agent:
        #     for each susceptble agent:
        #         measure distance between them
        #         if distance < infection_radius:
        #             roll a random number
        #             if random < infection_rate:
        #                 mark susceptible agent as INFECTED
        #                 log which room it happened in

        for inf_agent in infected:
            if inf_agent.pos is None:
                continue
            for sus_agent in susceptible:
                if sus_agent.pos is None or sus_agent.status != Status.SUSCEPTIBLE:
                    continue
                d = dist(inf_agent.pos, sus_agent.pos)
                if d < self.p["infection_radius"]:
                    if random.random() < self.p["infection_rate"]:
                        sus_agent.status = Status.INFECTED
                        new_infections += 1
                        room = self.floor_plan.room_at(sus_agent.pos)
                        self.transmission_events.append({
                            "tick": self.tick_count,
                            "from": inf_agent.unique_id,
                            "to": sus_agent.unique_id,
                            "room": room.name if room else "unknown",
                        })
#to change, inaccurate, should also use time 
        for a in infected:
            if random.random() < self.p["recovery_rate"]:
                a.status = Status.RECOVERED

        self.new_infections_per_tick.append(new_infections)

    def step(self):
        self.tick_count += 1

        living = self._living_agents()
        random.shuffle(living)
        for agent in living:
            agent.step()

        self._disease_step()
#count SIR
        living = self._living_agents()
        s_count = sum(1 for a in living if a.status == Status.SUSCEPTIBLE)
        i_count = sum(1 for a in living if a.status == Status.INFECTED)
        r_count = sum(1 for a in living if a.status == Status.RECOVERED)

        self.sir_history.append({
            "tick": self.tick_count,
            "S": s_count, "I": i_count, "R": r_count,
        })

        
        self.datacollector.collect(self)

        #to stop sim when all infected agents are recovered

        # if i_count == 0:
        #     self.running = False
        if self.tick_count >= self.p["max_steps"]:
            self.running = False

    def get_results(self) -> dict:
        living = self._living_agents()
        return {
            "params": self.p,
            "floor_plan_name": self.floor_plan.name,
            "tick_count": self.tick_count,
            "sir_history": self.sir_history,
            "new_infections_per_tick": self.new_infections_per_tick,
            "transmission_events": self.transmission_events,
            "agent_summary": [
                {
                    "id": a.unique_id,
                    "type": a.agent_type,
                    "final_status": a.status,
                    "state_history": a.state_history,
                }
                for a in living
            ],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
