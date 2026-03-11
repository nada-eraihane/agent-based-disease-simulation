from enum import Enum
import mesa

class State(Enum):
    SUSCEPTIBLE = "susceptible"
    INFECTED    = "infected"
    RECOVERED   = "recovered"

class HospitalAgent(mesa.Agent):


    def __init__(self, unique_id, model, agent_type: str, state: State):
        super().__init__(unique_id, model)

        self.agent_type = agent_type  
        self.state = state        
        self.infection_timer = 0           
    

    def move(self):
        
        neighbours = self.model.grid.get_neighborhood(
            self.pos,
            moore=True,         
            include_center=False 
        )
        new_pos = self.random.choice(neighbours)
        self.model.grid.move_agent(self, new_pos)

   
    def try_infect_others(self):
        
        if self.state != State.INFECTED:
            return  
        cellmates = self.model.grid.get_cell_list_contents([self.pos])

        for other in cellmates:
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