# map.py
import curses

class GameMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [['.' for _ in range(width)] for _ in range(height)]
        self.create_walls()

    def create_walls(self):
        for x in range(self.width):
            self.tiles[0][x] = '#'
            self.tiles[self.height - 1][x] = '#'
        for y in range(self.height):
            self.tiles[y][0] = '#'
            self.tiles[y][self.width - 1] = '#'
        mid = self.width // 2
        for y in range(2, self.height - 2):
            self.tiles[y][mid] = '#'

    def is_walkable(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x] != '#'
        return False

    def draw(self, stdscr):
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
