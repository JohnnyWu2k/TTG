# game/player.py
class Player:
    def __init__(self, x, y, char="@"):
        self.x = x
        self.y = y
        self.char = char
        self.hp = 5
