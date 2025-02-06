# game/enemy.py
import random

def spawn_enemies(world_width, world_height, seed=None):
    """
    Generate enemies for the world.
    For simplicity, we generate two enemies at fixed or random positions.
    """
    if seed is not None:
        random.seed(seed)
    enemies = {}
    # Here we use fixed positions as an example. You might choose to randomize these.
    enemies["enemy_1"] = {"x": min(world_width - 2, 10), "y": min(world_height - 2, 10), "char": "E", "hp": 3}
    enemies["enemy_2"] = {"x": min(world_width - 2, 20), "y": min(world_height - 2, 15), "char": "E", "hp": 3}
    return enemies

def spawn_objects(world_width, world_height, seed=None):
    """
    Generate objects (e.g., trees) for the world.
    Objects are placed with a fixed probability in walkable cells.
    """
    if seed is not None:
        random.seed(seed)
    objects = {}
    object_probability = 0.05  # 5% chance for an object in an open cell
    # We assume a coordinate system covering the interior of the world.
    for y in range(1, world_height - 1):
        for x in range(1, world_width - 1):
            if random.random() < object_probability:
                objects[f"obj_{x}_{y}"] = {"x": x, "y": y, "char": "T", "type": "tree"}
    return objects
