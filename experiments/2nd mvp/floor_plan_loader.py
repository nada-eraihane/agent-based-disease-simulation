"""
floor_plan_loader.py
====================
Converts floor_plan.json → Python structures the Mesa model uses.

THE THREE-STEP WALKABILITY ALGORITHM
─────────────────────────────────────
Step 1 — ROOMS  → Add cells
    Every (x,y) cell inside any room rectangle is walkable.

Step 2 — WALLS  → Remove cells  (Bresenham rasterisation)
    Explicit wall lines cut through walkable space.
    Each wall segment is converted to a list of cells using Bresenham's
    line algorithm, and those cells are removed from the walkable set.
    Result: a wall drawn across a room/corridor blocks agent crossing.

Step 3 — DOORS  → Re-add cells
    Door objects punch holes in walls.
    The cell where a door sits is re-added to walkable even if a wall
    occupies it. This is how you create passages: draw a wall, place a
    door along it to make an opening agents can walk through.

WHY A SET?
    Agents check `if (x,y) in model.walkable` once per step per agent.
    Python set membership is O(1), so even 500 agents checking 8
    neighbours each tick is negligible.
"""

import json
import pathlib


# ─── Bresenham's line → cells ────────────────────────────────────────────────

def _bresenham(x0: float, y0: float, x1: float, y1: float) -> list:
    """
    Return all integer grid cells the line from (x0,y0)→(x1,y1) passes
    through using Bresenham's classic rasterisation.

    The algorithm steps along the longer axis one integer at a time and
    uses an accumulating error term to decide when to also step on the
    shorter axis — producing the closest integer approximation to the
    true geometric line with no gaps.
    """
    x0, y0 = int(round(x0)), int(round(y0))
    x1, y1 = int(round(x1)), int(round(y1))
    cells = []
    dx = abs(x1 - x0);  dy = abs(y1 - y0)
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    x, y = x0, y0

    if dx >= dy:
        err = dx // 2
        while x != x1:
            cells.append((x, y))
            err -= dy
            if err < 0:
                y += sy;  err += dx
            x += sx
    else:
        err = dy // 2
        while y != y1:
            cells.append((x, y))
            err -= dx
            if err < 0:
                x += sx;  err += dy
            y += sy

    cells.append((x1, y1))
    return cells


# ─── Core processor ──────────────────────────────────────────────────────────

def process(data: dict) -> dict:
    """
    Turn a raw floor-plan dict into simulation-ready structures.

    Returns dict with:
        width, height  — grid dimensions (int)
        walkable       — set of (x,y) tuples agents may occupy
        rooms          — original room list  (for visualisation)
        walls          — original wall list  (for visualisation)
        objects        — original object list
    """
    rooms   = data.get("rooms",   [])
    walls   = data.get("walls",   [])
    objects = data.get("objects", [])
    width   = int(data["width"])
    height  = int(data["height"])

    # Step 1 — rooms → walkable
    walkable: set = set()
    for r in rooms:
        for dx in range(int(r["w"])):
            for dy in range(int(r["h"])):
                walkable.add((int(r["x"]) + dx, int(r["y"]) + dy))

    # Step 2 — walls → remove cells
    for w in walls:
        for cell in _bresenham(w["x1"], w["y1"], w["x2"], w["y2"]):
            walkable.discard(cell)

    # Step 3 — doors → re-add cells
    for obj in objects:
        if obj.get("type") == "door":
            cx, cy = int(round(obj["x"])), int(round(obj["y"]))
            if 0 <= cx < width and 0 <= cy < height:
                walkable.add((cx, cy))

    return {
        "width":    width,
        "height":   height,
        "walkable": walkable,
        "rooms":    rooms,
        "walls":    walls,
        "objects":  objects,
    }


# ─── Public loaders ───────────────────────────────────────────────────────────

def load(path: str = "floor_plan.json") -> dict:
    """Load and process a floor plan from a JSON file path."""
    return process(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))

def load_from_string(s: str) -> dict:
    """Load and process a floor plan from a raw JSON string."""
    return process(json.loads(s))

def load_from_dict(d: dict) -> dict:
    """Load and process an already-parsed floor plan dict."""
    return process(d)