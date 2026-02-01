from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from agents import StaffAgent, PatientAgent
import random

class MedicalBuildingModel(Model):
    def __init__(
            self, width=50,height=50,num_staff=10, num_patients=20, patient_movement_prob=0.1
    ):
        super().__init__()
        #the model parameters

        self.width = width
        self.height = height
        self.num_staff = num_staff
        self.num_patients = num_patients
        self.patient_movement_prob = patient_movement_prob

        #create a gridthat allows multiple agents in one cell
        self.grid = MultiGrid(width, height, torus= False)
        
        #create scheduler (with random activation order each step)
        self.schedule = RandomActivation(self)

        #track walls as sets of (x,y) tuples
        self.wall = set()

        # create environment with roomes and walls
        self._create_environment()

        #create and places agents
        self._create_agents()

        #data collector for later analysis
        self.datacollector = DataCollector(
            model_reporters={
                "Staff": lambda m: sum(1 for a in m.schedule.agents if a.agent_type == "staff"),
                "Patients": lambda m: sum(1 for a in m.schedule.agents if a.agent_type == "patient")
            }
        )

        self.running = True

    def _create_environment(self):
        for x in range(self.width):
            self.walls.add((x,0))
            self.walls.add((x,self.height - 1))

        for y in range(self.height):
            self.walls.add((0,y))
            self.walls.add((self.width - 1, y))

        for x in range(5,20):
            self.walls.add((x,35))

        for y in range(35, self.height -1):
            self.walls.add((5, y))
            self.walls.add((20,y))

        for x in range(25,40):
            self.walls.add((x,25))
            self.walls.add((x, 35))

        for y in range(25,35):
            self.walls.add((25,y))
            self.walls.add((40,y))
        
        if (30,25) in self.walls:
            self.walls.remove((30,25))

        if (42,15) in self.walls:
            self.walls.remove((42,15))
    
    def _create_agents(self):

        agent_id = 0

        for _ in range(self.num_staff):
            agent=StaffAgent(agent_id, self)
            self.shedule.add(agent)

            pos= self._get_random_empty_position()
            self.grid.place_agent(agent, pos)

            agent_id += 1
        for _ in range(self.num_patients):
            agent = PatientAgent(agent_id, self, self.patient_movement_prob)
            self.schedule.add(agent)
            # here is where patients are placed randomly in areas
            # it is made for the patients to be able to be added to specific locations
            pos = self._get_random_empty_position()
            self.grid.place_agent(agent, pos)

            agent_id += 1
    
    def _get_random_empty_position(self):
        while True:
            x = random.randrange(self.width)
            y = random.randrange(self.height)
            pos = (x,y)

            if not self.is_wall(pos):
                return pos
            
    def is_wall(self, pos):
        
