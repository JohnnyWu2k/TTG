"""Pygame client providing a simple 2D interface."""

import json
import socket
import threading
import time

import pygame

from game.map import InfiniteGameMap

PORT = 12345

game_state = {}


def network_listener(sock):
    """Receive game state updates from the server."""
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
                except Exception:
                    pass
    finally:
        sock.close()


class Game:
    def __init__(self, sock):
        self.sock = sock
        self.running = True
        self.game_map = None
        self.tile_size = 32
        self.scale = 1
        self.inventory = ["#", "|_", None, None, None]
        self.active_slot = 0
        self.volume = 0.5
        self.show_settings = False

        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("TTG 2D")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)

    def wait_for_map_seed(self):
        while "map_seed" not in game_state:
            time.sleep(0.1)
        seed = game_state["map_seed"]
        width = 40
        self.game_map = InfiniteGameMap(width, chunk_height=20, seed=seed)

    def compute_camera(self):
        if "players" in game_state and game_state["players"]:
            pid = list(game_state["players"].keys())[0]
            p = game_state["players"][pid]
            visible_rows = self.screen.get_height() // (self.tile_size * self.scale)
            cam_y = max(0, p.get("y", 0) - visible_rows // 2)
            return 0, cam_y
        return 0, 0

    def send_move(self, dx, dy):
        message = json.dumps({"dx": dx, "dy": dy}) + "\n"
        try:
            self.sock.sendall(message.encode())
        except Exception:
            self.running = False

    def draw_ui(self):
        ui_width = 200
        panel = pygame.Surface((ui_width, self.screen.get_height()))
        panel.fill((30, 30, 30))
        if "players" in game_state and game_state["players"]:
            pid = list(game_state["players"].keys())[0]
            hp = game_state["players"][pid].get("hp", 5)
            txt = self.font.render(f"HP: {hp}", True, (255, 255, 255))
            panel.blit(txt, (10, 10))
        panel.blit(self.font.render("Inventory:", True, (255, 255, 255)), (10, 40))
        for i, item in enumerate(self.inventory):
            y = 60 + i * 20
            prefix = ">" if i == self.active_slot else " "
            text = f"{prefix}{i+1}: {item if item else 'Empty'}"
            panel.blit(self.font.render(text, True, (255, 255, 255)), (10, y))
        if self.show_settings:
            pygame.draw.rect(panel, (60, 60, 60), pygame.Rect(10, 200, ui_width-20, 80))
            panel.blit(self.font.render("Volume", True, (255, 255, 255)), (20, 210))
            bar_rect = pygame.Rect(20, 230, ui_width-40, 20)
            pygame.draw.rect(panel, (100, 100, 100), bar_rect)
            fill_rect = bar_rect.copy()
            fill_rect.width = int(bar_rect.width * self.volume)
            pygame.draw.rect(panel, (0, 150, 0), fill_rect)
        self.screen.blit(panel, (self.screen.get_width() - ui_width, 0))

    def render(self):
        self.screen.fill((0, 0, 0))
        cam_x, cam_y = self.compute_camera()
        if self.game_map:
            surface = pygame.Surface((self.screen.get_width() - 200, self.screen.get_height()))
            self.game_map.draw_pygame(surface, self.tile_size * self.scale, cam_x, cam_y)
            self.screen.blit(surface, (0, 0))

        if "players" in game_state:
            for p in game_state["players"].values():
                px = (p.get("x", 0) - cam_x) * self.tile_size * self.scale
                py = (p.get("y", 0) - cam_y) * self.tile_size * self.scale
                pygame.draw.rect(self.screen, (0, 200, 0), pygame.Rect(px, py, self.tile_size * self.scale, self.tile_size * self.scale))

        if "enemies" in game_state:
            for e in game_state["enemies"].values():
                ex = (e.get("x", 0) - cam_x) * self.tile_size * self.scale
                ey = (e.get("y", 0) - cam_y) * self.tile_size * self.scale
                pygame.draw.rect(self.screen, (200, 0, 0), pygame.Rect(ex, ey, self.tile_size * self.scale, self.tile_size * self.scale))

        self.draw_ui()
        pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.show_settings = not self.show_settings
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                    self.active_slot = event.key - pygame.K_1
                elif event.key == pygame.K_UP:
                    self.send_move(0, -1)
                elif event.key == pygame.K_DOWN:
                    self.send_move(0, 1)
                elif event.key == pygame.K_LEFT:
                    self.send_move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    self.send_move(1, 0)
            if event.type == pygame.MOUSEBUTTONDOWN and self.show_settings:
                x, y = event.pos
                ui_start = self.screen.get_width() - 200
                if 220 <= y <= 250 and ui_start + 20 <= x <= ui_start + 180:
                    rel = (x - (ui_start + 20)) / 160
                    self.volume = max(0.0, min(1.0, rel))

    def run(self):
        self.wait_for_map_seed()
        while self.running:
            self.handle_events()
            self.render()
            self.clock.tick(30)
        pygame.quit()


def run_client(server_host, server_port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_host, server_port))
    threading.Thread(target=network_listener, args=(sock,), daemon=True).start()
    game = Game(sock)
    game.run()


if __name__ == "__main__":
    run_client("127.0.0.1")

