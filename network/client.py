# network/client.py
import sys
import os
# Ensure the project root is in sys.path (for testing if needed).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import curses
import socket
import threading
import json
import time
from game.map import GameMap  # Import map generator from game package
from game.combat import combat_minigame  # Import the new combat minigame function

PORT = 12345  # Must match the server port.

# Global variable for shared game state received from the server.
game_state = {}

def network_listener(sock):
    """Continuously listen for game state updates from the server."""
    global game_state
    buffer = ""
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                try:
                    game_state = json.loads(line)
                except Exception as e:
                    print("[CLIENT] Error decoding state:", e)
    except Exception as e:
        print("[CLIENT] Network listener error:", e)
    finally:
        sock.close()

class Game:
    def __init__(self, stdscr, sock):
        self.stdscr = stdscr
        self.sock = sock
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)
        self.game_map = None  # Will be generated once we receive the map seed

    def wait_for_map_seed(self):
        """Wait until the network state includes a map_seed, then generate the map."""
        while "map_seed" not in game_state:
            time.sleep(0.1)
        seed = game_state["map_seed"]
        max_y, max_x = self.stdscr.getmaxyx()
        self.game_map = GameMap(max_x - 2, max_y - 2, open_world=True, seed=seed)
        self.stdscr.addstr(0, 0, f"Map seed: {seed}")
        self.stdscr.refresh()
        time.sleep(1)

    def process_input(self):
        key = self.stdscr.getch()
        if key == ord('q'):
            return False

        dx, dy = 0, 0
        if key == ord('w'):
            dy = -1
        elif key == ord('s'):
            dy = 1
        elif key == ord('a'):
            dx = -1
        elif key == ord('d'):
            dx = 1
        elif key == ord('x'):
            # Look up the shared state.
            state_data = game_state
            my_id = None
            # (For simplicity, assume the client uses the first player in the state as "self".)
            if "players" in state_data and len(state_data["players"]) > 0:
                my_id = list(state_data["players"].keys())[0]
            target_enemy = None
            if my_id:
                my_player = state_data["players"][my_id]
                player_x = my_player.get("x", 0)
                player_y = my_player.get("y", 0)
                # Check for an enemy in any of the four adjacent cells.
                if "enemies" in state_data:
                    for enemy in state_data["enemies"].values():
                        ex = enemy.get("x", 0)
                        ey = enemy.get("y", 0)
                        # Check if enemy is directly to the left, right, above, or below.
                        if (ex == player_x + 1 and ey == player_y) or \
                           (ex == player_x - 1 and ey == player_y) or \
                           (ex == player_x and ey == player_y + 1) or \
                           (ex == player_x and ey == player_y - 1):
                            target_enemy = enemy
                            break
            if target_enemy:
                # End curses so that Pygame can open its window.
                curses.endwin()
                try:
                    from game.combat import combat_minigame
                    # Launch the combat minigame. The enemy's HP is passed to it.
                    damage = combat_minigame(enemy_hp=target_enemy.get("hp", 3), attempts_allowed=5)
                except Exception as e:
                    print("Combat error:", e)
                    damage = 0
                # Reinitialize curses.
                self.stdscr = curses.initscr()
                curses.curs_set(0)
                self.stdscr.nodelay(True)
                self.stdscr.timeout(50)
                # Send an attack command including the computed damage.
                attack_command = {"attack": True, "dx": 0, "dy": 0, "damage": damage}
                try:
                    message = json.dumps(attack_command) + "\n"
                    self.sock.sendall(message.encode())
                except Exception as e:
                    self.stdscr.addstr(0, 0, f"Error sending attack: {e}")
                    self.stdscr.refresh()
                    time.sleep(1)
                    return False
                return True
            else:
                # If no enemy is adjacent (horizontally or vertically), ignore the attack.
                return True


        if dx != 0 or dy != 0:
            try:
                message = json.dumps({"dx": dx, "dy": dy}) + "\n"
                self.sock.sendall(message.encode())
            except Exception as e:
                self.stdscr.addstr(0, 0, f"Error sending movement: {e}")
                self.stdscr.refresh()
                time.sleep(1)
                return False
        return True

    def render(self):
        self.stdscr.clear()
        if self.game_map:
            self.game_map.draw(self.stdscr)
        max_y, max_x = self.stdscr.getmaxyx()
        state_data = game_state
        # Draw players.
        if "players" in state_data:
            for player in state_data["players"].values():
                x = player.get("x", 0)
                y = player.get("y", 0)
                char = player.get("char", "@")
                if 0 < x < max_x - 1 and 0 < y < max_y - 1:
                    try:
                        self.stdscr.addch(y, x, char)
                    except curses.error:
                        pass
        # Draw enemies.
        if "enemies" in state_data:
            for enemy in state_data["enemies"].values():
                x = enemy.get("x", 0)
                y = enemy.get("y", 0)
                char = enemy.get("char", "E")
                if 0 < x < max_x - 1 and 0 < y < max_y - 1:
                    try:
                        self.stdscr.addch(y, x, char)
                    except curses.error:
                        pass
        # Draw objects.
        if "objects" in state_data:
            for obj in state_data["objects"].values():
                x = obj.get("x", 0)
                y = obj.get("y", 0)
                char = obj.get("char", "O")
                if 0 < x < max_x - 1 and 0 < y < max_y - 1:
                    try:
                        self.stdscr.addch(y, x, char)
                    except curses.error:
                        pass
        self.stdscr.refresh()

    def run(self):
        self.wait_for_map_seed()
        running = True
        while running:
            running = self.process_input()
            self.render()

def run_client(stdscr, server_host, server_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((server_host, server_port))
    except Exception as e:
        stdscr.addstr(0, 0, f"Could not connect to server: {e}")
        stdscr.refresh()
        time.sleep(3)
        return
    threading.Thread(target=network_listener, args=(sock,), daemon=True).start()
    game = Game(stdscr, sock)
    game.run()
    sock.close()
