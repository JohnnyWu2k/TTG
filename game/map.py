# game/map.py
import random
import curses

class InfiniteGameMap:
    def __init__(self, width, chunk_height=20, seed=None):
        """
        width: fixed horizontal width in tiles.
        chunk_height: number of rows per vertical chunk.
        seed: global seed for procedural generation.
        """
        self.width = width
        self.chunk_height = chunk_height
        self.seed = seed if seed is not None else random.randint(0, 1000000)
        self.chunks = {}  # Dictionary: chunk_index -> 2D list of tiles

    def generate_chunk(self, chunk_index):
        local_seed = self.seed + chunk_index
        rng = random.Random(local_seed)
        chunk = []
        for row in range(self.chunk_height):
            row_data = []
            for x in range(self.width):
                if x == 0 or x == self.width - 1:
                    row_data.append('#')
                else:
                    if rng.random() < 0.1:
                        row_data.append('#')
                    else:
                        row_data.append('.')
            # Ensure center is open.
            center = self.width // 2
            row_data[center] = '.'
            chunk.append(row_data)
        self.chunks[chunk_index] = chunk
        return chunk

    def get_chunk(self, chunk_index):
        if chunk_index not in self.chunks:
            return self.generate_chunk(chunk_index)
        return self.chunks[chunk_index]

    def get_tile(self, x, y):
        if x < 0 or x >= self.width or y < 0:
            return ' '  # Out-of-bounds
        chunk_index = y // self.chunk_height
        local_y = y % self.chunk_height
        chunk = self.get_chunk(chunk_index)
        return chunk[local_y][x]

    def is_walkable(self, x, y):
        return self.get_tile(x, y) == '.'

    def draw_scaled(self, stdscr, scale=1, camera_x=0, camera_y=0, width_limit=None):
        """
        Draw the visible portion of the infinite map onto the screen.
          - scale: each tile is drawn as a square of size (scale x scale) characters.
          - camera_x, camera_y: global coordinates of the top-left tile visible.
          - width_limit: optional maximum horizontal pixel width to draw (if provided, only draw columns
            such that (col * scale) is less than width_limit).
        """
        max_y, max_x = stdscr.getmaxyx()
        # If width_limit is provided, use it; otherwise, use full width (self.width).
        if width_limit is None:
            visible_cols = self.width
        else:
            visible_cols = min(self.width, width_limit // scale)
        visible_rows = max_y // scale  # vertical number of tiles to draw

        for gy in range(camera_y, camera_y + visible_rows):
            for gx in range(camera_x, camera_x + visible_cols):
                tile = self.get_tile(gx, gy)
                screen_y = (gy - camera_y) * scale
                screen_x = (gx - camera_x) * scale
                for dy in range(scale):
                    for dx in range(scale):
                        try:
                            stdscr.addch(screen_y + dy, screen_x + dx, tile)
                        except curses.error:
                            pass

    def draw_pygame(self, surface, tile_size=32, camera_x=0, camera_y=0):
        """Draw the map onto a Pygame surface as colored squares."""
        import pygame

        width_pixels, height_pixels = surface.get_width(), surface.get_height()
        visible_cols = min(self.width, width_pixels // tile_size)
        visible_rows = height_pixels // tile_size

        colors = {
            '.': (50, 50, 50),
            '#': (100, 100, 100),
            ' ': (0, 0, 0),
        }

        for gy in range(camera_y, camera_y + visible_rows):
            for gx in range(camera_x, camera_x + visible_cols):
                tile = self.get_tile(gx, gy)
                color = colors.get(tile, (200, 200, 200))
                rect = pygame.Rect(
                    (gx - camera_x) * tile_size,
                    (gy - camera_y) * tile_size,
                    tile_size,
                    tile_size,
                )
                pygame.draw.rect(surface, color, rect)
