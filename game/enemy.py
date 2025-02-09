# game/enemy.py
import random

def spawn_enemies(world_width, world_height, seed=None):
    """
    Generate enemies for the world.
    For simplicity, here we generate two enemies at fixed positions,
    but you can randomize their placement if desired.
    """
    if seed is not None:
        random.seed(seed)
    enemies = {}
    enemies["enemy_1"] = {"x": min(world_width - 2, 10), "y": min(world_height - 2, 10), "char": "E", "hp": 3}
    enemies["enemy_2"] = {"x": min(world_width - 2, 20), "y": min(world_height - 2, 15), "char": "E", "hp": 3}
    return enemies

def spawn_objects(world_width, world_height, seed=None, game_map=None):
    """
    Generate objects (e.g., trees) for the world.
    If a game_map is provided, use a flood fill from the starting cell to get the reachable cells.
    Only place an object in a cell if it is reachable.
    The object_probability is lowered to avoid blocking the map.
    """
    if seed is not None:
        random.seed(seed)
    objects = {}
    object_probability = 0.02  # 2% chance per cell
    reachable = set()
    if game_map is not None:
        # Flood fill from (1,1) to determine reachable cells.
        stack = [(1, 1)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in reachable:
                continue
            reachable.add((cx, cy))
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < world_width and 0 <= ny < world_height and game_map.tiles[ny][nx] == '.':
                    stack.append((nx, ny))
    # Loop over interior cells.
    for y in range(1, world_height - 1):
        for x in range(1, world_width - 1):
            # If a game_map was given, only consider placing an object in a reachable cell.
            if game_map is None or (x, y) in reachable:
                if random.random() < object_probability:
                    objects[f"obj_{x}_{y}"] = {"x": x, "y": y, "char": "T", "type": "tree"}
    return objects
