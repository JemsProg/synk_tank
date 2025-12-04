# server.py
import socket
import threading
import json
import time
import random

from game_config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    TANK_SIZE, TANK_SPEED,
    BULLET_SPEED, BULLET_SIZE,
    TANK_HP,
    SERVER_TICK_RATE,
    SERVER_HOST, SERVER_PORT
)

players = {}      # player_id -> {x, y, dir, hp}
inputs = {}       # player_id -> latest input dict
bullets = []      # list of {x, y, dx, dy, owner}

lock = threading.Lock()
next_player_id = 1

def create_new_player():
    x = random.randint(TANK_SIZE, SCREEN_WIDTH - TANK_SIZE)
    y = random.randint(TANK_SIZE, SCREEN_HEIGHT - TANK_SIZE)
    return {"x": x, "y": y, "dir": "up", "hp": TANK_HP}

def handle_client(conn, addr, player_id):
    global inputs, players
    print(f"[SERVER] Player {player_id} connected from {addr}")

    init_msg = {"type": "init", "player_id": player_id}
    conn.sendall((json.dumps(init_msg) + "\n").encode())

    buffer = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if msg.get("type") == "input":
                    with lock:
                        inputs[player_id] = msg["keys"]
    except ConnectionResetError:
        pass
    finally:
        print(f"[SERVER] Player {player_id} disconnected.")
        with lock:
            if player_id in players:
                del players[player_id]
            if player_id in inputs:
                del inputs[player_id]
        conn.close()

def update_game(dt):
    global players, bullets

    with lock:
        for pid, player in players.items():
            keys = inputs.get(pid, {})

            dx = 0
            dy = 0
            if keys.get("up"):
                dy -= TANK_SPEED
                player["dir"] = "up"
            if keys.get("down"):
                dy += TANK_SPEED
                player["dir"] = "down"
            if keys.get("left"):
                dx -= TANK_SPEED
                player["dir"] = "left"
            if keys.get("right"):
                dx += TANK_SPEED
                player["dir"] = "right"

            player["x"] = max(0, min(SCREEN_WIDTH - TANK_SIZE, player["x"] + dx))
            player["y"] = max(0, min(SCREEN_HEIGHT - TANK_SIZE, player["y"] + dy))

            if keys.get("shoot") and not keys.get("shoot_handled", False):
                keys["shoot_handled"] = True
                bx = player["x"] + TANK_SIZE // 2
                by = player["y"] + TANK_SIZE // 2
                if player["dir"] == "up":
                    dx_b, dy_b = 0, -BULLET_SPEED
                elif player["dir"] == "down":
                    dx_b, dy_b = 0, BULLET_SPEED
                elif player["dir"] == "left":
                    dx_b, dy_b = -BULLET_SPEED, 0
                else:
                    dx_b, dy_b = BULLET_SPEED, 0
                bullets.append({"x": bx, "y": by, "dx": dx_b, "dy": dy_b, "owner": pid})

    with lock:
        new_bullets = []
        for b in bullets:
            b["x"] += b["dx"]
            b["y"] += b["dy"]

            if (b["x"] < 0 or b["x"] > SCREEN_WIDTH or
                b["y"] < 0 or b["y"] > SCREEN_HEIGHT):
                continue

            hit_any = False
            for pid, p in players.items():
                if pid == b["owner"]:
                    continue
                if (p["x"] < b["x"] < p["x"] + TANK_SIZE and
                    p["y"] < b["y"] < p["y"] + TANK_SIZE):
                    p["hp"] -= 1
                    print(f"[SERVER] Player {pid} hit! HP = {p['hp']}")
                    if p["hp"] <= 0:
                        print(f"[SERVER] Player {pid} died. Respawning.")
                        new_state = create_new_player()
                        players[pid].update(new_state)
                    hit_any = True
                    break
            if not hit_any:
                new_bullets.append(b)
        bullets = new_bullets

def broadcast_state(connections):
    with lock:
        state = {
            "type": "state",
            "players": players,
            "bullets": bullets,
        }
        data = (json.dumps(state) + "\n").encode()

    for conn in list(connections):
        try:
            conn.sendall(data)
        except:
            pass

def main():
    global next_player_id, players

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((SERVER_HOST, SERVER_PORT))
    server_sock.listen()

    print(f"[SERVER] Listening on {SERVER_HOST}:{SERVER_PORT}")

    connections = []

    def accept_thread():
        nonlocal connections
        global next_player_id, players

        while True:
            conn, addr = server_sock.accept()
            with lock:
                pid = next_player_id
                next_player_id += 1
                players[pid] = create_new_player()
                inputs[pid] = {}
            connections.append(conn)
            threading.Thread(target=handle_client, args=(conn, addr, pid), daemon=True).start()

    threading.Thread(target=accept_thread, daemon=True).start()

    tick_delay = 1.0 / SERVER_TICK_RATE
    last_time = time.time()

    try:
        while True:
            now = time.time()
            dt = now - last_time
            last_time = now

            update_game(dt)
            broadcast_state(connections)

            time.sleep(tick_delay)
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down.")
    finally:
        server_sock.close()

if __name__ == "__main__":
    main()
