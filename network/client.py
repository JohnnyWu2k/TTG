# network/client.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import curses
import socket
import threading
import json
import time
from game.map import InfiniteGameMap
from game.combat import combat_minigame  # combat.py is now in the game folder

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
        self.quit_to_menu = False
        # Inventory: 5 slots; pre-populated for demo.
        self.inventory = ["#", "|_", "#", None, None]
        self.active_inventory_slot = 0
        self.scale = 1  # Zoom factor (1 = normal, etc.)
        # Track latest mouse raw coordinates.
        self.mouse_raw_x = None
        self.mouse_raw_y = None

    def wait_for_map_seed(self):
        while "map_seed" not in game_state:
            time.sleep(0.1)
        seed = game_state["map_seed"]
        max_y, max_x = self.stdscr.getmaxyx()
        # Create an infinite map using the full window width.
        self.game_map = InfiniteGameMap(max_x, chunk_height=20, seed=seed)
        self.stdscr.addstr(0, 0, f"Map seed: {seed}")
        self.stdscr.refresh()
        time.sleep(1)

    def shop_menu(self):
        options = [("Wall Block", "#", 10), ("Corner Block", "|_", 15)]
        selection = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(2, 2, "Shop: Buy building blocks", curses.A_BOLD)
            for idx, (name, block, price) in enumerate(options):
                prefix = "--> " if idx == selection else "    "
                line = f"{prefix}{name} ({block}) - {price} coins"
                self.stdscr.addstr(4 + idx, 4, line, curses.A_REVERSE if idx == selection else curses.A_NORMAL)
            self.stdscr.addstr(8, 4, "Press Enter to buy, ESC to exit.")
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key == 27:
                break
            elif key == curses.KEY_UP and selection > 0:
                selection -= 1
            elif key == curses.KEY_DOWN and selection < len(options) - 1:
                selection += 1
            elif key in [curses.KEY_ENTER, 10, 13]:
                chosen = options[selection]
                block = chosen[1]
                for i in range(len(self.inventory)):
                    if self.inventory[i] is None:
                        self.inventory[i] = block
                        break
                self.stdscr.addstr(10, 4, f"Purchased {chosen[0]}!")
                self.stdscr.refresh()
                time.sleep(1)
        # Return to game.

    def compute_camera_offset(self):
        """Compute camera offset so that the player is roughly centered vertically.
        The horizontal range is fixed to the full game area."""
        max_y, max_x = self.stdscr.getmaxyx()
        ui_width = max_x // 4  # Reserve 25% for the UI panel.
        game_area_width = max_x - ui_width
        camera_x = 0  # For horizontal, we display the entire game area.
        camera_y = 0
        if "players" in game_state and game_state["players"]:
            my_id = list(game_state["players"].keys())[0]
            my_player = game_state["players"][my_id]
            player_x = my_player.get("x", 0)
            player_y = my_player.get("y", 0)
            visible_rows = max_y // self.scale
            # Center vertically on the player.
            camera_y = max(0, player_y - visible_rows // 2)
        return camera_x, camera_y

    def draw_ui_panel(self):
        """Draw the UI panel on the right side."""
        max_y, max_x = self.stdscr.getmaxyx()
        ui_width = max_x // 4  # 25% of screen width.
        game_area_width = max_x - ui_width
        ui_win = self.stdscr.subwin(max_y, ui_width, 0, game_area_width)
        ui_win.clear()
        ui_win.box()
        # Health (assuming player's health from game_state).
        if "players" in game_state and game_state["players"]:
            my_id = list(game_state["players"].keys())[0]
            my_player = game_state["players"][my_id]
            health = my_player.get("hp", 5)
            ui_win.addstr(1, 2, f"Health: {health}")
        # Inventory listing.
        ui_win.addstr(3, 2, "Inventory:")
        for i in range(5):
            slot = self.inventory[i] if i < len(self.inventory) else None
            indicator = "->" if i == self.active_inventory_slot else "  "
            ui_win.addstr(5 + i, 2, f"{indicator}{i+1}: {slot if slot else 'Empty'}")
        ui_win.refresh()

    def render(self):
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        ui_width = max_x // 4
        game_area_width = max_x - ui_width
        camera_x, camera_y = self.compute_camera_offset()
        if self.game_map:
            # Draw only the game area.
            self.game_map.draw_scaled(self.stdscr, scale=self.scale, camera_x=camera_x, camera_y=camera_y, width_limit=game_area_width)
        # Draw a vertical separator.
        for row in range(max_y):
            try:
                self.stdscr.addch(row, game_area_width, '|')
            except curses.error:
                pass
        # Draw custom tiles.
        if "custom_tiles" in game_state:
            for tile in game_state["custom_tiles"].values():
                x = tile.get("x", 0)
                y = tile.get("y", 0)
                char = tile.get("char", tile.get("block", "?"))
                screen_x = (x - camera_x) * self.scale
                screen_y = (y - camera_y) * self.scale
                try:
                    self.stdscr.addch(screen_y, screen_x, char)
                except curses.error:
                    pass
        # Draw players.
        if "players" in game_state:
            for player in game_state["players"].values():
                x = player.get("x", 0)
                y = player.get("y", 0)
                char = player.get("char", "@")
                screen_x = (x - camera_x) * self.scale
                screen_y = (y - camera_y) * self.scale
                if 0 <= screen_x < game_area_width and 0 <= screen_y < max_y:
                    try:
                        self.stdscr.addch(screen_y, screen_x, char)
                    except curses.error:
                        pass
        # Draw enemies.
        if "enemies" in game_state:
            for enemy in game_state["enemies"].values():
                x = enemy.get("x", 0)
                y = enemy.get("y", 0)
                char = enemy.get("char", "E")
                screen_x = (x - camera_x) * self.scale
                screen_y = (y - camera_y) * self.scale
                if 0 <= screen_x < game_area_width and 0 <= screen_y < max_y:
                    try:
                        self.stdscr.addch(screen_y, screen_x, char)
                    except curses.error:
                        pass
        # Draw objects.
        if "objects" in game_state:
            for obj in game_state["objects"].values():
                x = obj.get("x", 0)
                y = obj.get("y", 0)
                char = obj.get("char", "O")
                screen_x = (x - camera_x) * self.scale
                screen_y = (y - camera_y) * self.scale
                if 0 <= screen_x < game_area_width and 0 <= screen_y < max_y:
                    try:
                        self.stdscr.addch(screen_y, screen_x, char)
                    except curses.error:
                        pass
        # Draw the mouse preview overlay.
        if self.mouse_raw_x is not None and self.mouse_raw_y is not None:
            # Convert raw mouse coordinates to world coordinates.
            world_mouse_x = camera_x + (self.mouse_raw_x // self.scale)
            world_mouse_y = camera_y + (self.mouse_raw_y // self.scale)
            # We'll cover a 3x3 area (in world tiles) with a border.
            preview_tiles = 3
            top_left_world_x = max(0, world_mouse_x - preview_tiles // 2)
            top_left_world_y = max(0, world_mouse_y - preview_tiles // 2)
            preview_pixel_width = preview_tiles * self.scale
            preview_pixel_height = preview_tiles * self.scale
            screen_preview_x = (top_left_world_x - camera_x) * self.scale
            screen_preview_y = (top_left_world_y - camera_y) * self.scale
            # Draw top and bottom borders.
            for i in range(preview_pixel_width):
                try:
                    self.stdscr.addch(screen_preview_y, screen_preview_x + i, '-')
                    self.stdscr.addch(screen_preview_y + preview_pixel_height - 1, screen_preview_x + i, '-')
                except curses.error:
                    pass
            # Draw left and right borders.
            for i in range(preview_pixel_height):
                try:
                    self.stdscr.addch(screen_preview_y + i, screen_preview_x, '|')
                    self.stdscr.addch(screen_preview_y + i, screen_preview_x + preview_pixel_width - 1, '|')
                except curses.error:
                    pass
            # Draw corners.
            try:
                self.stdscr.addch(screen_preview_y, screen_preview_x, '+')
                self.stdscr.addch(screen_preview_y, screen_preview_x + preview_pixel_width - 1, '+')
                self.stdscr.addch(screen_preview_y + preview_pixel_height - 1, screen_preview_x, '+')
                self.stdscr.addch(screen_preview_y + preview_pixel_height - 1, screen_preview_x + preview_pixel_width - 1, '+')
            except curses.error:
                pass
            # Optionally, fill the center row with preview text.
            preview_text = "|_|"
            center_y = screen_preview_y + preview_pixel_height // 2
            text_x = screen_preview_x + (preview_pixel_width - len(preview_text)) // 2
            try:
                self.stdscr.addstr(center_y, text_x, preview_text, curses.A_BOLD)
            except curses.error:
                pass

        # Draw the inventory UI in the game area (if desired) and the UI panel on the right.
        self.draw_inventory()
        self.draw_ui_panel()
        self.stdscr.refresh()

    def draw_inventory(self):
        # (Now removed from under the map; inventory is now shown in the UI panel.)
        pass

    def draw_ui_panel(self):
        """Draw the UI panel on the right side of the screen."""
        max_y, max_x = self.stdscr.getmaxyx()
        ui_width = max_x // 4  # 25% of the screen width.
        game_area_width = max_x - ui_width
        ui_win = self.stdscr.subwin(max_y, ui_width, 0, game_area_width)
        ui_win.clear()
        ui_win.box()
        # Health bar.
        if "players" in game_state and game_state["players"]:
            my_id = list(game_state["players"].keys())[0]
            my_player = game_state["players"][my_id]
            health = my_player.get("hp", 5)
            ui_win.addstr(1, 2, f"Health: {health}")
        # Inventory listing.
        ui_win.addstr(3, 2, "Inventory:")
        for i in range(5):
            slot = self.inventory[i] if i < len(self.inventory) else None
            indicator = "->" if i == self.active_inventory_slot else "  "
            ui_win.addstr(5 + i, 2, f"{indicator}{i+1}: {slot if slot else 'Empty'}")
        ui_win.refresh()

    def pause_menu(self):
        options = ["Resume", "Settings", "Quit"]
        selection = 0
        max_y, max_x = self.stdscr.getmaxyx()
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(2, max_x // 2 - len("Paused") // 2, "Paused", curses.A_BOLD)
            for idx, opt in enumerate(options):
                prefix = "--> " if idx == selection else "    "
                line = prefix + opt
                self.stdscr.addstr(4 + idx, max_x // 2 - len(line) // 2, line,
                                   curses.A_REVERSE if idx == selection else curses.A_NORMAL)
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
        self.stdscr.addstr(max_y // 2, max_x // 2 - len(text) // 2, text)
        self.stdscr.refresh()
        self.stdscr.getch()

    def process_input(self):
        key = self.stdscr.getch()
        if key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                self.mouse_raw_x = mx
                self.mouse_raw_y = my
                if bstate & curses.BUTTON4_PRESSED:
                    if self.scale < 3:
                        self.scale += 1
                elif bstate & curses.BUTTON5_PRESSED:
                    if self.scale > 1:
                        self.scale -= 1
            except Exception:
                pass
        if key == 27:
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
        if ch in ['1','2','3','4','5']:
            self.active_inventory_slot = int(ch) - 1
            return True
        if ch == 'p':
            self.shop_menu()
            return True

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
            state_data = game_state
            my_id = None
            if "players" in state_data and state_data["players"]:
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
        max_y, max_x = self.stdscr.getmaxyx()
        ui_width = max_x // 4
        game_area_width = max_x - ui_width
        camera_x, camera_y = self.compute_camera_offset()
        if self.game_map:
            self.game_map.draw_scaled(self.stdscr, scale=self.scale, camera_x=camera_x, camera_y=camera_y, width_limit=game_area_width)
        # Draw vertical separator.
        for row in range(max_y):
            try:
                self.stdscr.addch(row, game_area_width, '|')
            except curses.error:
                pass
        if "custom_tiles" in game_state:
            for tile in game_state["custom_tiles"].values():
                x = tile.get("x", 0)
                y = tile.get("y", 0)
                char = tile.get("char", tile.get("block", "?"))
                screen_x = (x - camera_x) * self.scale
                screen_y = (y - camera_y) * self.scale
                try:
                    self.stdscr.addch(screen_y, screen_x, char)
                except curses.error:
                    pass
        if "players" in game_state:
            for player in game_state["players"].values():
                x = player.get("x", 0)
                y = player.get("y", 0)
                char = player.get("char", "@")
                screen_x = (x - camera_x) * self.scale
                screen_y = (y - camera_y) * self.scale
                if 0 <= screen_x < game_area_width and 0 <= screen_y < max_y:
                    try:
                        self.stdscr.addch(screen_y, screen_x, char)
                    except curses.error:
                        pass
        if "enemies" in game_state:
            for enemy in game_state["enemies"].values():
                x = enemy.get("x", 0)
                y = enemy.get("y", 0)
                char = enemy.get("char", "E")
                screen_x = (x - camera_x) * self.scale
                screen_y = (y - camera_y) * self.scale
                if 0 <= screen_x < game_area_width and 0 <= screen_y < max_y:
                    try:
                        self.stdscr.addch(screen_y, screen_x, char)
                    except curses.error:
                        pass
        if "objects" in game_state:
            for obj in game_state["objects"].values():
                x = obj.get("x", 0)
                y = obj.get("y", 0)
                char = obj.get("char", "O")
                screen_x = (x - camera_x) * self.scale
                screen_y = (y - camera_y) * self.scale
                if 0 <= screen_x < game_area_width and 0 <= screen_y < max_y:
                    try:
                        self.stdscr.addch(screen_y, screen_x, char)
                    except curses.error:
                        pass
        # Draw the building preview overlay.
        # Draw the building preview overlay (5x5 area)
        if self.mouse_raw_x is not None and self.mouse_raw_y is not None:
            # Convert raw mouse coordinates to world coordinates.
            world_mouse_x = camera_x + (self.mouse_raw_x // self.scale)
            world_mouse_y = camera_y + (self.mouse_raw_y // self.scale)
            preview_tiles = 5  # 5x5 area for preview
            top_left_world_x = max(0, world_mouse_x - preview_tiles // 2)
            top_left_world_y = max(0, world_mouse_y - preview_tiles // 2)
            preview_pixel_width = preview_tiles * self.scale
            preview_pixel_height = preview_tiles * self.scale
            screen_preview_x = (top_left_world_x - camera_x) * self.scale
            screen_preview_y = (top_left_world_y - camera_y) * self.scale
            # Use color pair 1 if available; fallback to normal attributes.
            attr = curses.color_pair(1) if curses.has_colors() else curses.A_BOLD
            # Draw top and bottom borders.
            for i in range(preview_pixel_width):
                try:
                    self.stdscr.addch(screen_preview_y, screen_preview_x + i, '-', attr)
                    self.stdscr.addch(screen_preview_y + preview_pixel_height - 1, screen_preview_x + i, '-', attr)
                except curses.error:
                    pass
            # Draw left and right borders.
            for i in range(preview_pixel_height):
                try:
                    self.stdscr.addch(screen_preview_y + i, screen_preview_x, '|', attr)
                    self.stdscr.addch(screen_preview_y + i, screen_preview_x + preview_pixel_width - 1, '|', attr)
                except curses.error:
                    pass
            # Draw corners.
            try:
                self.stdscr.addch(screen_preview_y, screen_preview_x, '+', attr)
                self.stdscr.addch(screen_preview_y, screen_preview_x + preview_pixel_width - 1, '+', attr)
                self.stdscr.addch(screen_preview_y + preview_pixel_height - 1, screen_preview_x, '+', attr)
                self.stdscr.addch(screen_preview_y + preview_pixel_height - 1, screen_preview_x + preview_pixel_width - 1, '+', attr)
            except curses.error:
                pass
            # Draw preview text in the center.
            preview_text = "|_|"
            center_y = screen_preview_y + preview_pixel_height // 2
            text_x = screen_preview_x + (preview_pixel_width - len(preview_text)) // 2
            try:
                self.stdscr.addstr(center_y, text_x, preview_text, attr)
            except curses.error:
                pass
            
        # Draw the UI panel.
        self.draw_ui_panel()
        self.stdscr.refresh()

    def run(self):
        self.wait_for_map_seed()
        running = True
        while running:
            running = self.process_input()
            self.render()
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
