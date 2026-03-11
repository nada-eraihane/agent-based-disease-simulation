
import mesa
from agents import HospitalAgent, State


class HospitalModel(mesa.Model):


    def __init__(
        self,
        width = 20,
        height = 20, #grid dimensions
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
        self.recovery_steps = recovery_steps

        self.grid = mesa.space.MultiGrid(width, height, torus=True)

        self.schedule = mesa.time.RandomActivation(self)

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Susceptible": lambda m: self._count_state(m, State.SUSCEPTIBLE),
                "Infected": lambda m: self._count_state(m, State.INFECTED),
                "Recovered": lambda m: self._count_state(m, State.RECOVERED),
            }
        )

    
        agent_specs = [
            ("staff", n_staff, infected_staff),
            ("patient", n_patients, infected_patients),
            ("visitor", n_visitors, infected_visitors),
        ]

        agent_id = 0  #unique counter across all agents

        for agent_type, total, n_infected in agent_specs:
           
            n_infected = min(n_infected, total)

            for i in range(total):
                state = State.INFECTED if i < n_infected else State.SUSCEPTIBLE

                agent = HospitalAgent(agent_id, self, agent_type, state)
                agent_id += 1
                #place ageents randomly on the grid
                x = self.random.randrange(width)
                y = self.random.randrange(height)
                self.grid.place_agent(agent, (x, y))
                self.schedule.add(agent)

        self.datacollector.collect(self)

        self.running = True 

    def step(self):
       
        self.schedule.step()
        self.datacollector.collect(self)

    @staticmethod
    def _count_state(model, state: State) -> int:
        return sum(1 for a in model.schedule.agents if a.state == state)