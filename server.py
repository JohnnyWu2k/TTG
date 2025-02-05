# server.py
import socket
import threading
import json
import time

HOST = '0.0.0.0'
PORT = 12345

# Global game state maintained by the server.
# Players are stored as a dictionary mapping a client id (here, the connection address as string)
# to a dictionary with position, display character, and health.
players = {}        # {client_id: {"x": int, "y": int, "char": str, "hp": int}}
# Enemies are stored similarly.
enemies = {}        # {enemy_id: {"x": int, "y": int, "char": str, "hp": int}}
connections = []    # List of connected client sockets
state_lock = threading.Lock()

def spawn_enemies():
    """Spawn a couple of enemies at predetermined positions."""
    with state_lock:
        enemies["enemy_1"] = {"x": 10, "y": 10, "char": "E", "hp": 3}
        enemies["enemy_2"] = {"x": 20, "y": 15, "char": "E", "hp": 3}

def broadcast_state():
    """Broadcast the full game state (players and enemies) to all connected clients."""
    with state_lock:
        state = json.dumps({"players": players, "enemies": enemies}) + "\n"
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
            # Process each complete JSON message terminated by newline.
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                try:
                    message = json.loads(line)
                    # If this message is an attack command:
                    if message.get("attack", False):
                        dx = message.get("dx", 0)
                        dy = message.get("dy", 0)
                        with state_lock:
                            if client_id in players:
                                player = players[client_id]
                                target_x = player["x"] + dx
                                target_y = player["y"] + dy
                                target_enemy = None
                                # Check for an enemy in the target cell.
                                for eid, enemy in enemies.items():
                                    if enemy["x"] == target_x and enemy["y"] == target_y:
                                        target_enemy = eid
                                        break
                                if target_enemy:
                                    enemies[target_enemy]["hp"] -= 1
                                    print(f"[SERVER] {client_id} attacked enemy {target_enemy}; remaining hp: {enemies[target_enemy]['hp']}")
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
                                # Enforce simple boundaries (e.g., x between 1 and 40, y between 1 and 20).
                                new_x = max(1, min(40, player["x"] + dx))
                                new_y = max(1, min(20, player["y"] + dy))
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
    spawn_enemies()  # Spawn enemies when the server starts.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[SERVER] Listening on port {PORT}...")
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
    # Give the server a moment to start.
    import time
    time.sleep(0.5)
