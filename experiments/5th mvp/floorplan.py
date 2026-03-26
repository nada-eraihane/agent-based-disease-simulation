from __future__ import annotations
import json, math, copy
from typing import List, Dict, Tuple, Optional, Any, Set


Point = Tuple[float, float]
Segment = Tuple[Point, Point]

def dist(a, b): #gets the distance between 2 points
    return math.hypot(a[0] - b[0], a[1] - b[1])

def _segments_intersect(p1, p2, p3, p4):#checks if two line sintersect
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = p4[0] - p3[0], p4[1] - p3[1]
    cross = d1x * d2y - d1y * d2x
    if abs(cross) < 1e-10:
        return False
    t = ((p3[0] - p1[0]) * d2y - (p3[1] - p1[1]) * d2x) / cross
    u = ((p3[0] - p1[0]) * d1y - (p3[1] - p1[1]) * d1x) / cross
    return 0 <= t <= 1 and 0 <= u <= 1

def point_in_polygon(point, polygon):#checks if a point is inside a shape
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def polygon_centroid(polygon):#finds the middle of the shape
    n = len(polygon)
    if n == 0:
        return (0.0, 0.0)
    return (sum(p[0] for p in polygon) / n, sum(p[1] for p in polygon) / n)

def has_line_of_sight(a, b, walls):#checks if there is a wall in the way
    for wall in walls:
        if _segments_intersect(a, b, wall[0], wall[1]):
            return False
    return True

class NavGraph:#dictionary of named points and their connections
    def __init__(self):
        self.nodes: Dict[str, Point] = {}
        self.edges: Dict[str, Set[str]] = {}
    def add_node(self, node_id, pos):
        self.nodes[node_id] = pos
        if node_id not in self.edges:
            self.edges[node_id] = set()
    def add_edge(self, a, b):
        if a in self.edges: self.edges[a].add(b)
        if b in self.edges: self.edges[b].add(a)


#room definition
class Room:
    __slots__ = ("name", "room_type", "polygon", "centroid", "contamination")
    def __init__(self, name, room_type, polygon):
        self.name = name
        self.room_type = room_type
        self.polygon = [tuple(p) for p in polygon]
        self.centroid = polygon_centroid(self.polygon)
        self.contamination = 0.0
    def contains(self, point):
        return point_in_polygon(point, self.polygon)
    def to_dict(self):
        return {"name": self.name, "room_type": self.room_type, "polygon": self.polygon}
#door definition
class Door:
    __slots__ = ("position", "connects")
    def __init__(self, position, connects):
        self.position = tuple(position)
        self.connects = connects
    def to_dict(self):
        return {"position": list(self.position), "connects": list(self.connects)}
#hygiene station definition
class HygieneStation:
    __slots__ = ("position",)
    def __init__(self, position):
        self.position = tuple(position)
    def to_dict(self):
        return {"position": list(self.position)}

#stores list of rooms, walls and doors... with width height and name
class FloorPlan:
    def __init__(self):
        self.rooms: List[Room] = []
        self.walls: List[Segment] = []
        self.doors: List[Door] = []
        self.hygiene_stations: List[HygieneStation] = []
        self.nav_graph: NavGraph = NavGraph()
        self.width: float = 800.0
        self.height: float = 600.0
        self.name: str = "Unnamed"

    def room_at(self, point):
        for room in self.rooms:
            if room.contains(point):
                return room
        return None

    def rooms_by_type(self, room_type):
        return [r for r in self.rooms if r.room_type == room_type]

    def to_dict(self):
        return {
            "name": self.name, "width": self.width, "height": self.height,
            "rooms": [r.to_dict() for r in self.rooms],
            "walls": [{"start": list(w[0]), "end": list(w[1])} for w in self.walls],
            "doors": [d.to_dict() for d in self.doors],
            "hygiene_stations": [hs.to_dict() for hs in self.hygiene_stations],
        }

    @classmethod
    def from_dict(cls, data):
        fp = cls()
        fp.name = data.get("name", "Imported")
        fp.width = float(data.get("width", 800))
        fp.height = float(data.get("height", 600))
        for rd in data.get("rooms", []):
            fp.rooms.append(Room(rd["name"], rd["room_type"], [tuple(p) for p in rd["polygon"]]))
        for wd in data.get("walls", []):
            fp.walls.append((tuple(wd["start"]), tuple(wd["end"])))
        for dd in data.get("doors", []):
            fp.doors.append(Door(tuple(dd["position"]), tuple(dd["connects"])))
        for hd in data.get("hygiene_stations", []):
            fp.hygiene_stations.append(HygieneStation(tuple(hd["position"])))
        fp.build_nav_graph()
        return fp

    def build_nav_graph(self):
        g = NavGraph()
        for room in self.rooms:
            g.add_node(f"room_{room.name}", room.centroid)
        for i, door in enumerate(self.doors):
            g.add_node(f"door_{i}", door.position)
        for i, hs in enumerate(self.hygiene_stations):
            g.add_node(f"hygiene_{i}", hs.position)
        node_ids = list(g.nodes.keys())
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                a_id, b_id = node_ids[i], node_ids[j]
                if has_line_of_sight(g.nodes[a_id], g.nodes[b_id], self.walls):
                    g.add_edge(a_id, b_id)
        for i, door in enumerate(self.doors):
            did = f"door_{i}"
            for rname in door.connects:
                rid = f"room_{rname}"
                if rid in g.nodes and did in g.nodes:
                    if rid not in g.edges.get(did, set()):
                        g.add_edge(did, rid)
        self.nav_graph = g


#simple floorplan
#python dictionary with floor plan data, in simulation it is rendered to svg shapes
def make_simple_hospital():
    rooms = [
        {"name": "Office1", "room_type": "patient_room",
         "polygon": [[100, 40], [280, 40], [280, 200], [100, 200]]},
        {"name": "Reception", "room_type": "waiting",
         "polygon": [[280, 40], [560, 40], [560, 200], [280, 200]]},
        {"name": "WaitingRoom", "room_type": "waiting",
         "polygon": [[560, 40], [940, 40], [940, 200], [560, 200]]},
        {"name": "DarkRoom", "room_type": "icu",
         "polygon": [[100, 200], [200, 200], [200, 260], [100, 260]]},
        {"name": "Corridor", "room_type": "corridor",
         "polygon": [[200, 200], [900, 200], [900, 260], [200, 260]]},
        {"name": "Entrance", "room_type": "entrance",
         "polygon": [[900, 200], [940, 200], [940, 260], [900, 260]]},
        {"name": "Office2", "room_type": "patient_room",
         "polygon": [[100, 260], [280, 260], [280, 400], [100, 400]]},
        {"name": "Xray", "room_type": "icu",
         "polygon": [[280, 260], [460, 260], [460, 400], [280, 400]]},
        {"name": "Office3", "room_type": "patient_room",
         "polygon": [[460, 260], [660, 260], [660, 400], [460, 400]]},
        {"name": "Office4", "room_type": "patient_room",
         "polygon": [[660, 260], [840, 260], [840, 400], [660, 400]]},
        {"name": "WC", "room_type": "bathroom",
         "polygon": [[840, 260], [940, 260], [940, 400], [840, 400]]},
    ]
    walls = [
        {"start": [100, 40], "end": [940, 40]},
        {"start": [100, 400], "end": [940, 400]},
        {"start": [100, 40], "end": [100, 400]},
        {"start": [940, 40], "end": [940, 205]},
        {"start": [940, 255], "end": [940, 400]},
        {"start": [100, 200], "end": [240, 200]},
        {"start": [320, 200], "end": [520, 200]},
        {"start": [560, 200], "end": [590, 200]},
        {"start": [630, 200], "end": [900, 200]},
        {"start": [100, 260], "end": [200, 260]},
        {"start": [200, 260], "end": [240, 260]},
        {"start": [320, 260], "end": [620, 260]},
        {"start": [700, 260], "end": [840, 260]},
        {"start": [880, 260], "end": [940, 260]},
        {"start": [200, 200], "end": [200, 220]},
        {"start": [280, 40], "end": [280, 200]},
        {"start": [560, 40], "end": [560, 200]},
        {"start": [280, 260], "end": [280, 400]},
        {"start": [460, 260], "end": [460, 400]},
        {"start": [660, 260], "end": [660, 400]},
        {"start": [840, 260], "end": [840, 400]},
    ]
    doors = [
        {"position": [260, 200], "connects": ["Office1", "Corridor"]},
        {"position": [300, 200], "connects": ["Reception", "Corridor"]},
        {"position": [540, 200], "connects": ["Reception", "Corridor"]},
        {"position": [610, 200], "connects": ["WaitingRoom", "Corridor"]},
        {"position": [200, 240], "connects": ["DarkRoom", "Corridor"]},
        {"position": [260, 260], "connects": ["Office2", "Corridor"]},
        {"position": [300, 260], "connects": ["Xray", "Corridor"]},
        {"position": [640, 260], "connects": ["Office3", "Corridor"]},
        {"position": [680, 260], "connects": ["Office4", "Corridor"]},
        {"position": [860, 260], "connects": ["WC", "Corridor"]},
        {"position": [940, 230], "connects": ["Entrance", "Corridor"]},
    ]
    hygiene_stations = [
        {"position": [420, 195]},
        {"position": [300, 265]},
        {"position": [680, 265]},
        {"position": [895, 230]},
    ]
    return {
        "name": "Simple Hospital", "width": 1040, "height": 440,
        "rooms": rooms, "walls": walls,
        "doors": doors, "hygiene_stations": hygiene_stations,
    }

def make_medium_hospital():
    rooms = [
        {"name": "MainCorridor", "room_type": "corridor", "polygon": [[50, 250], [750, 250], [750, 330], [50, 330]]},
        {"name": "Entrance", "room_type": "entrance", "polygon": [[10, 250], [50, 250], [50, 330], [10, 330]]},
        {"name": "Reception", "room_type": "waiting", "polygon": [[10, 10], [200, 10], [200, 230], [10, 230]]},
        {"name": "PR1", "room_type": "patient_room", "polygon": [[220, 10], [370, 10], [370, 230], [220, 230]]},
        {"name": "PR2", "room_type": "patient_room", "polygon": [[390, 10], [540, 10], [540, 230], [390, 230]]},
        {"name": "OperatingTheatre", "room_type": "icu", "polygon": [[560, 10], [790, 10], [790, 230], [560, 230]]},
        {"name": "PR3", "room_type": "patient_room", "polygon": [[50, 350], [220, 350], [220, 530], [50, 530]]},
        {"name": "PR4", "room_type": "patient_room", "polygon": [[240, 350], [410, 350], [410, 530], [240, 530]]},
        {"name": "ICU", "room_type": "icu", "polygon": [[430, 350], [620, 350], [620, 530], [430, 530]]},
        {"name": "StaffRoom", "room_type": "staff_room", "polygon": [[640, 350], [790, 350], [790, 530], [640, 530]]},
        {"name": "Bathroom", "room_type": "bathroom", "polygon": [[10, 350], [50, 350], [50, 430], [10, 430]]},
    ]
    walls = [
        {"start": [10, 10], "end": [790, 10]}, {"start": [10, 530], "end": [790, 530]},
        {"start": [10, 10], "end": [10, 530]}, {"start": [790, 10], "end": [790, 530]},
        {"start": [50, 250], "end": [120, 250]}, {"start": [140, 250], "end": [270, 250]},
        {"start": [290, 250], "end": [440, 250]}, {"start": [460, 250], "end": [620, 250]},
        {"start": [640, 250], "end": [750, 250]},
        {"start": [50, 330], "end": [100, 330]}, {"start": [120, 330], "end": [290, 330]},
        {"start": [310, 330], "end": [480, 330]}, {"start": [500, 330], "end": [690, 330]},
        {"start": [710, 330], "end": [750, 330]},
        {"start": [200, 10], "end": [200, 230]}, {"start": [220, 10], "end": [220, 230]},
        {"start": [370, 10], "end": [370, 230]}, {"start": [390, 10], "end": [390, 230]},
        {"start": [540, 10], "end": [540, 230]}, {"start": [560, 10], "end": [560, 230]},
        {"start": [220, 350], "end": [220, 530]}, {"start": [240, 350], "end": [240, 530]},
        {"start": [410, 350], "end": [410, 530]}, {"start": [430, 350], "end": [430, 530]},
        {"start": [620, 350], "end": [620, 530]}, {"start": [640, 350], "end": [640, 530]},
        {"start": [50, 350], "end": [50, 530]},
    ]
    doors = [
        {"position": [130, 250], "connects": ["Reception", "MainCorridor"]},
        {"position": [280, 250], "connects": ["PR1", "MainCorridor"]},
        {"position": [450, 250], "connects": ["PR2", "MainCorridor"]},
        {"position": [630, 250], "connects": ["OperatingTheatre", "MainCorridor"]},
        {"position": [110, 330], "connects": ["MainCorridor", "PR3"]},
        {"position": [300, 330], "connects": ["MainCorridor", "PR4"]},
        {"position": [490, 330], "connects": ["MainCorridor", "ICU"]},
        {"position": [700, 330], "connects": ["MainCorridor", "StaffRoom"]},
        {"position": [30, 290], "connects": ["Entrance", "MainCorridor"]},
    ]
    hygiene_stations = [{"position": [130, 245]}, {"position": [280, 245]}, {"position": [450, 245]}, {"position": [490, 335]}, {"position": [700, 335]}]
    return {"name": "Medium Hospital", "width": 800, "height": 550, "rooms": rooms, "walls": walls, "doors": doors, "hygiene_stations": hygiene_stations}

def make_large_hospital():
    rooms = [
        {"name": "MainHall", "room_type": "corridor", "polygon": [[50, 280], [950, 280], [950, 360], [50, 360]]},
        {"name": "Entrance", "room_type": "entrance", "polygon": [[10, 280], [50, 280], [50, 360], [10, 360]]},
        {"name": "WaitingArea", "room_type": "waiting", "polygon": [[10, 10], [200, 10], [200, 260], [10, 260]]},
        {"name": "PR1", "room_type": "patient_room", "polygon": [[220, 10], [380, 10], [380, 260], [220, 260]]},
        {"name": "PR2", "room_type": "patient_room", "polygon": [[400, 10], [560, 10], [560, 260], [400, 260]]},
        {"name": "PR3", "room_type": "patient_room", "polygon": [[580, 10], [740, 10], [740, 260], [580, 260]]},
        {"name": "OT", "room_type": "icu", "polygon": [[760, 10], [990, 10], [990, 260], [760, 260]]},
        {"name": "PR4", "room_type": "patient_room", "polygon": [[50, 380], [230, 380], [230, 580], [50, 580]]},
        {"name": "PR5", "room_type": "patient_room", "polygon": [[250, 380], [430, 380], [430, 580], [250, 580]]},
        {"name": "ICU", "room_type": "icu", "polygon": [[450, 380], [680, 380], [680, 580], [450, 580]]},
        {"name": "StaffRoom", "room_type": "staff_room", "polygon": [[700, 380], [870, 380], [870, 580], [700, 580]]},
        {"name": "Pharmacy", "room_type": "staff_room", "polygon": [[890, 380], [990, 380], [990, 580], [890, 580]]},
        {"name": "Bathroom", "room_type": "bathroom", "polygon": [[10, 380], [50, 380], [50, 470], [10, 470]]},
    ]
    walls = [
        {"start": [10, 10], "end": [990, 10]}, {"start": [10, 580], "end": [990, 580]},
        {"start": [10, 10], "end": [10, 580]}, {"start": [990, 10], "end": [990, 580]},
        {"start": [50, 280], "end": [120, 280]}, {"start": [140, 280], "end": [270, 280]},
        {"start": [290, 280], "end": [450, 280]}, {"start": [470, 280], "end": [630, 280]},
        {"start": [650, 280], "end": [810, 280]}, {"start": [830, 280], "end": [950, 280]},
        {"start": [50, 360], "end": [100, 360]}, {"start": [120, 360], "end": [300, 360]},
        {"start": [320, 360], "end": [500, 360]}, {"start": [520, 360], "end": [750, 360]},
        {"start": [770, 360], "end": [940, 360]}, {"start": [960, 360], "end": [950, 360]},
        {"start": [200, 10], "end": [200, 260]}, {"start": [220, 10], "end": [220, 260]},
        {"start": [380, 10], "end": [380, 260]}, {"start": [400, 10], "end": [400, 260]},
        {"start": [560, 10], "end": [560, 260]}, {"start": [580, 10], "end": [580, 260]},
        {"start": [740, 10], "end": [740, 260]}, {"start": [760, 10], "end": [760, 260]},
        {"start": [230, 380], "end": [230, 580]}, {"start": [250, 380], "end": [250, 580]},
        {"start": [430, 380], "end": [430, 580]}, {"start": [450, 380], "end": [450, 580]},
        {"start": [680, 380], "end": [680, 580]}, {"start": [700, 380], "end": [700, 580]},
        {"start": [870, 380], "end": [870, 580]}, {"start": [890, 380], "end": [890, 580]},
    ]
    doors = [
        {"position": [130, 280], "connects": ["WaitingArea", "MainHall"]},
        {"position": [280, 280], "connects": ["PR1", "MainHall"]},
        {"position": [460, 280], "connects": ["PR2", "MainHall"]},
        {"position": [640, 280], "connects": ["PR3", "MainHall"]},
        {"position": [820, 280], "connects": ["OT", "MainHall"]},
        {"position": [110, 360], "connects": ["MainHall", "PR4"]},
        {"position": [310, 360], "connects": ["MainHall", "PR5"]},
        {"position": [510, 360], "connects": ["MainHall", "ICU"]},
        {"position": [760, 360], "connects": ["MainHall", "StaffRoom"]},
        {"position": [950, 360], "connects": ["MainHall", "Pharmacy"]},
        {"position": [30, 320], "connects": ["Entrance", "MainHall"]},
    ]
    hygiene_stations = [{"position": [130, 275]}, {"position": [280, 275]}, {"position": [460, 275]}, {"position": [640, 275]}, {"position": [510, 365]}, {"position": [760, 365]}]
    return {"name": "Large Hospital", "width": 1000, "height": 600, "rooms": rooms, "walls": walls, "doors": doors, "hygiene_stations": hygiene_stations}

PREDEFINED_LAYOUTS = {
    "simple": make_simple_hospital,
    "medium": make_medium_hospital,
    "large": make_large_hospital,
}

def load_predefined(name):
    factory = PREDEFINED_LAYOUTS.get(name)
    if factory is None:
        raise ValueError(f"Unknown layout: {name}")
    return FloorPlan.from_dict(factory())