import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mesa
from enum import Enum
from mesa.visualization import SolaraViz, make_space_component, make_plot_component

class State(Enum):
    SUSCEPTIBLE = "susceptible"
    INFECTED = "infected"
    RECOVERED = "recovered"

class HospitalAgent(mesa.Agent):

    def __init__(self, model, agent_type: str, state: State):
        super().__init__(model)
        self.agent_type = agent_type
        self.state = state
        self.infection_timer = 0

    def move(self):
        neighbours = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        self.model.grid.move_agent(self, self.random.choice(neighbours))

    def try_infect_others(self):
        
        if self.state != State.INFECTED:
            return
        for other in self.model.grid.get_cell_list_contents([self.pos]):
            if other is self:
                continue
            if other.state == State.SUSCEPTIBLE:
                if self.random.random() < self.model.transmission_prob:
                    other.state = State.INFECTED
                    other.infection_timer = 0

    def progress_infection(self):
        
        if self.state != State.INFECTED:
            return
        self.infection_timer += 1
        if self.infection_timer >= self.model.recovery_steps:
            self.state = State.RECOVERED

    def step(self):
        
        self.move()
        self.try_infect_others()
        self.progress_infection()

class HospitalModel(mesa.Model):

    def __init__(
        self,
        width = 20,
        height = 20,
        n_staff = 10,
        n_patients = 15,
        n_visitors = 10,
        infected_staff = 1,
        infected_patients = 2,
        infected_visitors = 0,
        transmission_prob = 0.3,
        recovery_steps = 50,
    ):
        super().__init__()

        self.transmission_prob = transmission_prob
        self.recovery_steps    = recovery_steps

        self.grid = mesa.space.MultiGrid(width, height, torus=True)

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Susceptible": lambda m: sum(1 for a in m.agents if a.state == State.SUSCEPTIBLE),
                "Infected": lambda m: sum(1 for a in m.agents if a.state == State.INFECTED),
                "Recovered": lambda m: sum(1 for a in m.agents if a.state == State.RECOVERED),
            }
        )

        agent_specs = [
            ("staff", n_staff, infected_staff),
            ("patient", n_patients, infected_patients),
            ("visitor", n_visitors, infected_visitors),
        ]

        for agent_type, total, n_infected in agent_specs:
            n_infected = min(n_infected, total)
            for i in range(total):
                state = State.INFECTED if i < n_infected else State.SUSCEPTIBLE
                agent = HospitalAgent(self, agent_type, state)
                x = self.random.randrange(width)
                y = self.random.randrange(height)
                self.grid.place_agent(agent, (x, y))

        self.datacollector.collect(self)
        self.running = True

    def step(self):
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)

COLOUR_MAP = {
    # (agent_type,  state)          : CSS colour
    ("staff",   State.SUSCEPTIBLE): "#013F69",   # blue
    ("staff",   State.INFECTED): "#5F0D04",   # red
    ("staff",   State.RECOVERED): "#107C3D",   # green

    ("patient", State.SUSCEPTIBLE): "#865200",   # amber/orange
    ("patient", State.INFECTED): "#5F0D04",   # red
    ("patient", State.RECOVERED): "#107C3D",   # green

    ("visitor", State.SUSCEPTIBLE): "#8B2EAF",   # purple
    ("visitor", State.INFECTED): "#5F0D04",   # red
    ("visitor", State.RECOVERED): "#107C3D",   # green
}

def agent_portrayal(agent):
    colour = COLOUR_MAP.get((agent.agent_type, agent.state), "#CCCCCC")
    return {"color": colour, "size": 8 if agent.state == State.INFECTED else 5}

model_params = {
    "width": {"type": "SliderInt", "label": "Grid width", "value": 20, "min": 10, "max": 40, "step": 5},
    "height": {"type": "SliderInt", "label": "Grid height", "value": 20, "min": 10, "max": 40, "step": 5},

    "n_staff": {"type": "SliderInt", "label":  "Staff count", "value": 10, "min": 0, "max": 50, "step": 1},
    "n_patients": {"type": "SliderInt", "label": "Patient count", "value": 15, "min": 0, "max": 50, "step": 1},
    "n_visitors": {"type": "SliderInt", "label": "Visitor count", "value": 10, "min": 0, "max": 50, "step": 1},

    "infected_staff": {"type": "SliderInt", "label": "Infected staff", "value": 1, "min": 0, "max": 50, "step": 1},
    "infected_patients": {"type": "SliderInt", "label": "Infected patients", "value": 2, "min": 0, "max": 50, "step": 1},
    "infected_visitors": {"type": "SliderInt", "label": "Infected visitors", "value": 0, "min": 0, "max": 50, "step": 1},

    "transmission_prob": {"type": "SliderFloat", "label": "Transmission probability", "value": 0.3, "min": 0.0, "max": 1.0,  "step": 0.05},
    "recovery_steps": {"type": "SliderInt", "label": "Recovery steps", "value": 50,  "min": 5,   "max": 200, "step": 5},
}


#
# ASSEMBLE THE SOLARA PAGE
#
#
import solara
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg") # Use a non-interactive backend for matplotlib


SpaceView = make_space_component(agent_portrayal)


def SIRChart(model):
    df = model.datacollector.get_model_vars_dataframe()

    fig, ax = plt.subplots(figsize=(4, 2.2))  

    if not df.empty:
        ax.plot(df.index, df["Susceptible"], color="#013F69", label="S", linewidth=1.5)
        ax.plot(df.index, df["Infected"],    color="#5F0D04", label="I", linewidth=1.5)
        ax.plot(df.index, df["Recovered"],   color="#107C3D", label="R", linewidth=1.5)

    ax.set_xlabel("Step", fontsize=7)
    ax.set_ylabel("Agents", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.legend(fontsize=6, loc="upper right")
    ax.set_title("S / I / R over time", fontsize=8)
    fig.tight_layout()

    solara.FigureMatplotlib(fig)
    plt.close(fig)  # free memory after rendering


page = SolaraViz(
    model        = HospitalModel(),
    components   = [SpaceView, SIRChart],
    model_params = model_params,
    name         = " Hospital Disease Spread Simulation",
)

page