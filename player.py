# player.py

class Player:
    def __init__(self, x, y, char="@"):
        self.x = x
        self.y = y
        self.char = char
        self.hp = 5

    def move(self, dx, dy, game_map):
        new_x = self.x + dx
        new_y = self.y + dy
        if game_map.is_walkable(new_x, new_y):
            self.x = new_x
            self.y = new_y

    def attack(self, dx, dy):
        # This method returns the attack vector.
        return dx, dy
