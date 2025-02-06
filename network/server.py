# network/server.py
import socket
import threading
import json
import time
import random
from game.enemy import spawn_enemies, spawn_objects

HOST = '0.0.0.0'
PORT = 12345

# Global game state maintained by the server.
players = {}        # {client_id: {"x": int, "y": int, "char": str, "hp": int}}
enemies = {}        # Will be filled by spawn_enemies()
objects = {}        # Will be filled by spawn_objects()
connections = []    # List of connected client sockets
state_lock = threading.Lock()

# Generate a map seed once when the server starts.
map_seed = random.randint(0, 1000000)

def broadcast_state():
    """Broadcast the full game state (players, enemies, objects, and map_seed) to all clients."""
    with state_lock:
        state = json.dumps({
            "players": players,
            "enemies": enemies,
            "objects": objects,
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
        # Initialize the player's state.
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
                    if message.get("attack", False):
                        dx = message.get("dx", 0)
                        dy = message.get("dy", 0)
                        damage = message.get("damage", 1)  # Use damage from the combat minigame
                        with state_lock:
                            if client_id in players:
                                player = players[client_id]
                                # Here, since the combat system is triggered when the player is on the enemy                     
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
                                                # Process movement commands.
                        dx = message.get("dx", 0)
                        dy = message.get("dy", 0)
                        with state_lock:
                            if client_id in players:
                                player = players[client_id]
                                # Compute tentative new position.
                                new_x = max(1, min(40, player["x"] + dx))
                                new_y = max(1, min(20, player["y"] + dy))
                                # Check collision with enemies.
                                blocked = False
                                for enemy in enemies.values():
                                    if enemy["x"] == new_x and enemy["y"] == new_y:
                                        blocked = True
                                        break
                                # Check collision with objects if not already blocked.
                                if not blocked:
                                    for obj in objects.values():
                                        if obj["x"] == new_x and obj["y"] == new_y:
                                            blocked = True
                                            break
                                # Only update the player's position if not blocked.
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

def server_main():
    # Spawn enemies and objects using the same map seed.
    world_width = 80
    world_height = 24
    global enemies, objects
    enemies = spawn_enemies(world_width, world_height, seed=map_seed)
    objects = spawn_objects(world_width, world_height, seed=map_seed)
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

def start_server():
    """Start the server in a daemon thread."""
    threading.Thread(target=server_main, daemon=True).start()
    time.sleep(0.5)  # Allow time for server startup.
