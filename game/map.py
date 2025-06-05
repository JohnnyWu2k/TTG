# game/map.py
import random
import curses

class GameMap:
    def __init__(self, width, height, open_world=True, seed=None):
        """
        Initialize the map.
          - width, height: dimensions of the map.
          - open_world: if True, generate an open-world map.
          - seed: an optional seed for deterministic generation.
        """
        self.width = width
        self.height = height
        if seed is not None:
            random.seed(seed)
        if open_world:
            self.tiles = self.generate_open_world()
        else:
            self.tiles = [['.' for _ in range(width)] for _ in range(height)]
            self.create_walls()

    def create_walls(self):
        """Create a simple border around the map."""
        for x in range(self.width):
            self.tiles[0][x] = '#'
            self.tiles[self.height - 1][x] = '#'
        for y in range(self.height):
            self.tiles[y][0] = '#'
            self.tiles[y][self.width - 1] = '#'

    def generate_open_world(self):
        """
        Generate an open-world map:
         - Mostly open floor ('.') with scattered obstacles ('#').
         - Border walls are always present.
         - A flood fill from (1,1) is used to improve connectivity.
        """
        # Initialize grid with floor.
        grid = [['.' for _ in range(self.width)] for _ in range(self.height)]
        # Create border walls.
        for x in range(self.width):
            grid[0][x] = '#'
            grid[self.height - 1][x] = '#'
        for y in range(self.height):
            grid[y][0] = '#'
            grid[y][self.width - 1] = '#'
        
        # Place obstacles randomly in the interior.
        obstacle_probability = 0.1  # 10% chance
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if random.random() < obstacle_probability:
                    grid[y][x] = '#'
        
        # Flood fill from the starting cell (1,1).
        reachable = set()
        stack = [(1, 1)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in reachable:
                continue
            reachable.add((cx, cy))
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height and grid[ny][nx] == '.':
                    stack.append((nx, ny))
        
        # Remove obstacles adjacent to reachable cells to improve connectivity.
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if grid[y][x] == '#':
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        if (x + dx, y + dy) in reachable:
                            grid[y][x] = '.'
                            break
        return grid

    def is_walkable(self, x, y):
        """Return True if tile (x, y) is floor ('.')."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x] == '.'
        return False

    def draw(self, stdscr):
        """Draw the map on the provided curses window."""
        max_y, max_x = stdscr.getmaxyx()
        for y, row in enumerate(self.tiles):
            if y >= max_y:
                break
            for x, tile in enumerate(row):
                if x >= max_x:
                    break
                try:
                    stdscr.addch(y, x, tile)
                except curses.error:
                    pass
