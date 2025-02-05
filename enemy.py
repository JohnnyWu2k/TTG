# enemy.py

class Enemy:
    def __init__(self, x, y, char="E", hp=3):
        self.x = x
        self.y = y
        self.char = char
        self.hp = hp

    def take_damage(self, damage=1):
        self.hp -= damage
