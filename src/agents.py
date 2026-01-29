# agent definitions for the simulation
# has the different types of agents
# agents simulated RN: staff, patients

from mesa import Agent
import random

class MedicalAgent(Agent):

    def __init(self, unique_id, model, agent_type):
        super().__init__(unique_id, model)
        self.agent_type = agent_type
    
    def move(self):
        #overriden by subclassese
        pass

    def step(self):
        #this is called at each simulation step
        #it currently just handles movement
        self.move()

class StaffAgent(MedicalAgent):
    # general and represent doctors, nurses and cleaners
    # abale to roam around the entire building

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model, agent_type="staff")

    def move(self):
        # staff is able to walk to adjacent cells
        # staff is allowed to roam continuouslt around the building

        possible_moves = self.model.grid.get_neighborhood( self.pos, moore=True, include_center=False) #can move diagonaly and adjacent cells doesnt include the current one
        valid_moves =[]
        for pos in possible_moves:
            if not self.model.is_wall(pos):
                cell_contents = self.model.grid.get_cell_list_contents(pos)
                if len(cell_contents) <3:
                    valid_moves.append(pos)

        if valid_moves:
            new_position = random.choice(valid_moves)
            self.model.grid.move_agent(self, new_position)

class PatientAgent(MedicalAgent):
    def __init__(self, unique_id, model, movement_probablity=0.1):
        super().__init__(unique_id, model, agent_type="patient")
        self.movement_probability = movement_probablity
        
    def move(self):

        if random.random() < self.movement_probability:
            possible_moves = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=True) #no diagonal movement, and agent can sty in the same place

            valid_moves = []
            for pos in possible_moves:
                if not self.model.is_wall(pos):
                    valid_moves.append(pos)
            
            if valid_moves:
                new_position = random.choice(valid_moves)
                self.model.grid.move_agent(self, new_position)
                
        
