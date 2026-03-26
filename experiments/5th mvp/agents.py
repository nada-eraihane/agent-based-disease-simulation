from __future__ import annotations
import math, random
from typing import List, Optional, Tuple, TYPE_CHECKING
from mesa import Agent

if TYPE_CHECKING:
    from .model import HospitalModel


#geometry helpers 
def _dist(a, b): #calculate the distance between two points
    return math.hypot(a[0] - b[0], a[1] - b[1])

def _segments_intersect(p1, p2, p3, p4):#check if two line segments intersect
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = p4[0] - p3[0], p4[1] - p3[1]
    cross = d1x * d2y - d1y * d2x
    if abs(cross) < 1e-10:
        return False
    t = ((p3[0] - p1[0]) * d2y - (p3[1] - p1[1]) * d2x) / cross
    u = ((p3[0] - p1[0]) * d1y - (p3[1] - p1[1]) * d1x) / cross
    return 0 <= t <= 1 and 0 <= u <= 1

def _point_seg_dist(p, a, b):#calculate the distance from a point to a line segment
    dx, dy = b[0] - a[0], b[1] - a[1]
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return _dist(p, a)
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len_sq))
    cp = (a[0] + t * dx, a[1] + t * dy)
    return _dist(p, cp)



class Status:
    SUSCEPTIBLE = "S"
    EXPOSED = "E"
    INFECTED = "I"
    RECOVERED = "R"

AGENT_TYPES = ["patient", "doctor", "nurse", "visitor", "cleaner", "volunteer"]

AGENT_SPEEDS = {
    "patient": 1.0,
    "doctor": 2.5,
    "nurse": 2.0,
    "visitor": 1.8,
    "cleaner": 1.8,
    "volunteer": 1.8,
}

AGENT_SHAPES = {
    "patient": "circle",
    "doctor": "diamond",
    "nurse": "square",
    "visitor": "triangle_up",
    "cleaner": "triangle_down",
    "volunteer": "hexagon",
}

STATUS_COLOURS = {
    Status.SUSCEPTIBLE: "#22C55E",
    Status.EXPOSED: "#FBBF24",
    Status.INFECTED: "#EF4444",
    Status.RECOVERED: "#9CA3AF",
}

WALL_BUFFER = 4.0
SEPARATION_RADIUS = 15.0

#basic agent settings
class HospitalAgent(Agent):

    def __init__(self, model: "HospitalModel", agent_type: str, **kwargs):
        super().__init__(model)
        self.agent_type = agent_type
        self.status: str = Status.SUSCEPTIBLE
        self.removed: bool = False

        speed_base = AGENT_SPEEDS.get(agent_type, 2.0)
        self.max_speed = speed_base * (0.9 + random.random() * 0.2)
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * self.max_speed
        self.vy = math.sin(angle) * self.max_speed

        self.assigned_room: Optional[str] = None
        self.ticks_in_room: int = 0
        

    #movement
    def _move(self):
        if self.pos is None:
            return

        #change direction randomely 20% of the time
        if random.random() < 0.20:
            angle = random.uniform(0, 2 * math.pi)
            self.vx = math.cos(angle) * self.max_speed
            self.vy = math.sin(angle) * self.max_speed

        #if wall hit try up to 8 new directions
        for _ in range(20):
            new_x = self.pos[0] + self.vx
            new_y = self.pos[1] + self.vy
            if not self._hits_wall(self.pos[0], self.pos[1], new_x, new_y):
                break
            angle = random.uniform(0, 2 * math.pi)
            self.vx = math.cos(angle) * self.max_speed
            self.vy = math.sin(angle) * self.max_speed
        else:
            return

        #to avoid agent overlap
        new_x, new_y = self._separate(new_x, new_y)

        #agents cannot leave the florplan
        fp = self.model.floor_plan
        m = 5.0
        new_x = max(m, min(fp.width - m, new_x))
        new_y = max(m, min(fp.height - m, new_y))
        if new_x <= m or new_x >= fp.width - m:
            self.vx *= -1
        if new_y <= m or new_y >= fp.height - m:
            self.vy *= -1

        self.model.space.move_agent(self, (new_x, new_y))

    def _hits_wall(self, ox, oy, nx, ny):
        for wall in self.model.floor_plan.walls:
            if _segments_intersect((ox, oy), (nx, ny), wall[0], wall[1]):
                return True
            if _point_seg_dist((nx, ny), wall[0], wall[1]) < WALL_BUFFER:
                return True
        return False

    def _separate(self, new_x, new_y):
        neighbors = self.model.space.get_neighbors(
            (new_x, new_y), radius=SEPARATION_RADIUS, include_center=False
        )
        push_x, push_y = 0.0, 0.0
        for other in neighbors:
            if other.pos is None or getattr(other, 'removed', False):
                continue
            d = _dist((new_x, new_y), other.pos)
            if 0 < d < SEPARATION_RADIUS:
                strength = (SEPARATION_RADIUS - d) / SEPARATION_RADIUS
                push_x += ((new_x - other.pos[0]) / d) * strength * 4.0
                push_y += ((new_y - other.pos[1]) / d) * strength * 4.0
        return new_x + push_x, new_y + push_y

    
    def _hand_hygiene(self):
        ...

    def _navigate_to(self, room_name: str):
       ...

    def _surface_cleaning(self):
        ...

    def _role_behaviour(self):
        ...

    def step(self):
        if self.removed or self.pos is None:
            return
        self._role_behaviour()
        self._move()


#detailed agents
class PatientAgent(HospitalAgent):
    def __init__(self, model, **kwargs):
        super().__init__(model, "patient", **kwargs)
    def _role_behaviour(self):
        self.ticks_in_room += 1

class DoctorAgent(HospitalAgent):
    def __init__(self, model, **kwargs):
        super().__init__(model, "doctor", **kwargs)
    def _role_behaviour(self):
        self.ticks_in_room += 1

class NurseAgent(HospitalAgent):
    def __init__(self, model, **kwargs):
        super().__init__(model, "nurse", **kwargs)
    def _role_behaviour(self):
        self.ticks_in_room += 1

class VisitorAgent(HospitalAgent):
    def __init__(self, model, **kwargs):
        super().__init__(model, "visitor", **kwargs)
    def _role_behaviour(self):
        self.ticks_in_room += 1

class CleanerAgent(HospitalAgent):
    def __init__(self, model, **kwargs):
        super().__init__(model, "cleaner", **kwargs)
    def _role_behaviour(self):
        self.ticks_in_room += 1

class VolunteerAgent(HospitalAgent):
    def __init__(self, model, **kwargs):
        super().__init__(model, "volunteer", **kwargs)
    def _role_behaviour(self):
        self.ticks_in_room += 1

AGENT_CLASSES = {
    "patient": PatientAgent,
    "doctor": DoctorAgent,
    "nurse": NurseAgent,
    "visitor": VisitorAgent,
    "cleaner": CleanerAgent,
    "volunteer": VolunteerAgent,
}