# network/server.py
import socket
import threading
import json
import time
import random
from game.map import InfiniteGameMap
from game.enemy import spawn_enemies, spawn_objects

HOST = '0.0.0.0'
PORT = 12345

players = {}     # {client_id: {"x": int, "y": int, "char": str, "hp": int}}
enemies = {}     # {enemy_id: {...}}
objects = {}     # {object_id: {...}}
custom_tiles = {}  # {(x,y): {"x": x, "y": y, "block": str, "char": str}}
connections = []  # List of connected client sockets
state_lock = threading.Lock()

map_seed = random.randint(0, 1000000)
world_map = None

def broadcast_state():
    with state_lock:
        state = json.dumps({
            "players": players,
            "enemies": enemies,
            "objects": objects,
            "custom_tiles": custom_tiles,
            "map_seed": map_seed
        }) + "\n"
        for conn in connections.copy():
            try:
                conn.sendall(state.encode())
            except Exception:
                if conn in connections:
                    connections.remove(conn)

def handle_client(conn, addr):
    client_id = str(addr)
    print(f"[SERVER] New connection from {client_id}")
    with state_lock:
        players[client_id] = {"x": 5, "y": 5, "char": "@", "hp": 5}
        connections.append(conn)
    broadcast_state()

    buffer = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                try:
                    message = json.loads(line)
                    if message.get("build", False):
                        # Build command: x, y, and block type.
                        x = message.get("x", 0)
                        y = message.get("y", 0)
                        block = message.get("block", "")
                        # Check that the target cell is walkable (terrain) and not occupied.
                        can_build = True
                        if not world_map.is_walkable(x, y):
                            can_build = False
                        for p in players.values():
                            if p["x"] == x and p["y"] == y:
                                can_build = False
                                break
                        if can_build:
                            # Save or update the custom tile.
                            custom_tiles[(x, y)] = {"x": x, "y": y, "block": block, "char": block}
                    elif message.get("attack", False):
                        dx = message.get("dx", 0)
                        dy = message.get("dy", 0)
                        damage = message.get("damage", 1)
                        with state_lock:
                            if client_id in players:
                                player = players[client_id]
                                target_x = player["x"] + dx
                                target_y = player["y"] + dy
                                target_enemy = None
                                for eid, enemy in list(enemies.items()):
                                    if enemy["x"] == target_x and enemy["y"] == target_y:
                                        target_enemy = eid
                                        break
                                if target_enemy:
                                    enemies[target_enemy]["hp"] -= damage
                                    print(f"[SERVER] {client_id} attacked enemy {target_enemy} for {damage} damage; remaining hp: {enemies[target_enemy]['hp']}")
                                    if enemies[target_enemy]["hp"] <= 0:
                                        print(f"[SERVER] Enemy {target_enemy} defeated.")
                                        del enemies[target_enemy]
                    else:
                        dx = message.get("dx", 0)
                        dy = message.get("dy", 0)
                        with state_lock:
                            if client_id in players:
                                player = players[client_id]
                                new_x = player["x"] + dx
                                new_y = player["y"] + dy
                                blocked = False
                                if not world_map.is_walkable(new_x, new_y):
                                    blocked = True
                                if not blocked:
                                    for enemy in enemies.values():
                                        if enemy["x"] == new_x and enemy["y"] == new_y:
                                            blocked = True
                                            break
                                if not blocked:
                                    for obj in objects.values():
                                        if obj["x"] == new_x and obj["y"] == new_y:
                                            blocked = True
                                            break
                                if not blocked:
                                    player["x"] = new_x
                                    player["y"] = new_y
                except Exception as e:
                    print(f"[SERVER] Error processing message from {client_id}: {e}")
            broadcast_state()
    finally:
        with state_lock:
            print(f"[SERVER] Connection closed: {client_id}")
            if conn in connections:
                connections.remove(conn)
            if client_id in players:
                del players[client_id]
        broadcast_state()
        conn.close()

def server_main(world_width, world_height):
    global world_map, enemies, objects
    world_map = InfiniteGameMap(world_width, chunk_height=20, seed=map_seed)
    enemies = spawn_enemies(world_width, world_height, seed=map_seed)
    objects = spawn_objects(world_width, world_height, seed=map_seed, game_map=world_map)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[SERVER] Listening on port {PORT} with map seed: {map_seed}")
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except Exception as e:
        print(f"[SERVER] Error: {e}")
    finally:
        server.close()

def start_server(world_width, world_height):
    threading.Thread(target=server_main, args=(world_width, world_height), daemon=True).start()
    time.sleep(0.5)
