# network/client.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import curses
import socket
import threading
import json
import time
from game.map import GameMap

PORT = 12345
game_state = {}

def network_listener(sock):
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
        self.game_map = None
        self.quit_to_menu = False  # Flag to indicate quitting back to main menu

    def wait_for_map_seed(self):
        while "map_seed" not in game_state:
            time.sleep(0.1)
        seed = game_state["map_seed"]
        max_y, max_x = self.stdscr.getmaxyx()
        # Generate the map using the full window dimensions.
        self.game_map = GameMap(max_x, max_y, open_world=True, seed=seed)
        self.stdscr.addstr(0, 0, f"Map seed: {seed}")
        self.stdscr.refresh()
        time.sleep(1)

    def pause_menu(self):
        options = ["Resume", "Settings", "Quit"]
        selection = 0
        max_y, max_x = self.stdscr.getmaxyx()
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(2, max_x//2 - len("Paused")//2, "Paused", curses.A_BOLD)
            for idx, opt in enumerate(options):
                line = ("--> " if idx == selection else "    ") + opt
                attr = curses.A_REVERSE if idx == selection else curses.A_NORMAL
                self.stdscr.addstr(4 + idx, max_x//2 - len(line)//2, line, attr)
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key == curses.KEY_UP and selection > 0:
                selection -= 1
            elif key == curses.KEY_DOWN and selection < len(options) - 1:
                selection += 1
            elif key in [curses.KEY_ENTER, 10, 13]:
                return options[selection].lower()

    def settings_menu(self):
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        text = "Settings not implemented. Press any key to return."
        self.stdscr.addstr(max_y//2, max_x//2 - len(text)//2, text)
        self.stdscr.refresh()
        self.stdscr.getch()

    def process_input(self):
        key = self.stdscr.getch()
        if key == 27:  # ESC key
            choice = self.pause_menu()
            if choice == "resume":
                return True
            elif choice == "settings":
                self.settings_menu()
                return True
            elif choice == "quit":
                self.quit_to_menu = True
                return False

        try:
            ch = chr(key).lower()
        except Exception:
            ch = ""
        if ch == 'q':
            return False

        dx, dy = 0, 0
        if ch == 'w':
            dy = -1
        elif ch == 's':
            dy = 1
        elif ch == 'a':
            dx = -1
        elif ch == 'd':
            dx = 1
        elif ch == 'x':
            # Attack trigger: check if an enemy is adjacent (not diagonal)
            state_data = game_state
            my_id = None
            if "players" in state_data and len(state_data["players"]) > 0:
                my_id = list(state_data["players"].keys())[0]
            target_enemy = None
            enemy_offset = (0, 0)
            if my_id:
                my_player = state_data["players"][my_id]
                player_x = my_player.get("x", 0)
                player_y = my_player.get("y", 0)
                if "enemies" in state_data:
                    for enemy in state_data["enemies"].values():
                        ex = enemy.get("x", 0)
                        ey = enemy.get("y", 0)
                        if (ex == player_x + 1 and ey == player_y) or \
                           (ex == player_x - 1 and ey == player_y) or \
                           (ex == player_x and ey == player_y + 1) or \
                           (ex == player_x and ey == player_y - 1):
                            target_enemy = enemy
                            enemy_offset = (ex - player_x, ey - player_y)
                            break
            if target_enemy:
                curses.endwin()
                try:
                    from game.combat import combat_minigame
                    damage = combat_minigame(enemy_hp=target_enemy.get("hp", 3), attempts_allowed=5)
                except Exception as e:
                    print("Combat error:", e)
                    damage = 0
                self.stdscr = curses.initscr()
                curses.curs_set(0)
                self.stdscr.nodelay(True)
                self.stdscr.timeout(50)
                attack_command = {"attack": True,
                                  "dx": enemy_offset[0],
                                  "dy": enemy_offset[1],
                                  "damage": damage}
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
        if "players" in state_data:
            for player in state_data["players"].values():
                x = player.get("x", 0)
                y = player.get("y", 0)
                char = player.get("char", "@")
                if 0 <= x < max_x and 0 <= y < max_y:
                    try:
                        self.stdscr.addch(y, x, char)
                    except curses.error:
                        pass
        if "enemies" in state_data:
            for enemy in state_data["enemies"].values():
                x = enemy.get("x", 0)
                y = enemy.get("y", 0)
                char = enemy.get("char", "E")
                if 0 <= x < max_x and 0 <= y < max_y:
                    try:
                        self.stdscr.addch(y, x, char)
                    except curses.error:
                        pass
        if "objects" in state_data:
            for obj in state_data["objects"].values():
                x = obj.get("x", 0)
                y = obj.get("y", 0)
                char = obj.get("char", "O")
                if 0 <= x < max_x and 0 <= y < max_y:
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
        # Return a value to indicate if we quit to main menu.
        if self.quit_to_menu:
            return "quit_to_menu"
        return "exit"

def run_client(stdscr, server_host, server_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((server_host, server_port))
    except Exception as e:
        stdscr.addstr(0, 0, f"Could not connect to server: {e}")
        stdscr.refresh()
        time.sleep(3)
        return "exit"
    threading.Thread(target=network_listener, args=(sock,), daemon=True).start()
    game = Game(stdscr, sock)
    result = game.run()
    sock.close()
    return result
