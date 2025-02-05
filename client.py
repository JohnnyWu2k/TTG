# client.py
import curses
import socket
import threading
import json
import time
from map import GameMap

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
        max_y, max_x = self.stdscr.getmaxyx()
        self.game_map = GameMap(max_x - 2, max_y - 2)

    def process_input(self):
        key = self.stdscr.getch()
        if key == ord('q'):
            return False

        dx, dy = 0, 0
        # Movement: WASD
        if key == ord('w'):
            dy = -1
        elif key == ord('s'):
            dy = 1
        elif key == ord('a'):
            dx = -1
        elif key == ord('d'):
            dx = 1
        # Attack: press X then a direction key.
        elif key == ord('x'):
            self.stdscr.addstr(0, 0, "Attack direction (WASD): ")
            self.stdscr.refresh()
            dir_key = self.stdscr.getch()
            if dir_key == ord('w'):
                dx, dy = 0, -1
            elif dir_key == ord('s'):
                dx, dy = 0, 1
            elif dir_key == ord('a'):
                dx, dy = -1, 0
            elif dir_key == ord('d'):
                dx, dy = 1, 0
            attack_command = {"attack": True, "dx": dx, "dy": dy}
            try:
                message = json.dumps(attack_command) + "\n"
                self.sock.sendall(message.encode())
            except Exception as e:
                self.stdscr.addstr(0, 0, f"Error sending attack: {e}")
                self.stdscr.refresh()
                time.sleep(1)
                return False
            return True  # Skip movement after an attack.

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
        self.stdscr.refresh()

    def run(self):
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
