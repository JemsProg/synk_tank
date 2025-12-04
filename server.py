# server.py
import socket
import threading
import json
import time
import random
import math

from game_config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    TANK_SIZE, TANK_SPEED,
    BULLET_SPEED, BULLET_SIZE,
    TANK_HP,
    POWERUP_SIZE, POWERUP_RESPAWN_TIME, POWERUP_MAX, POWERUP_DURATION,
    TRAP_SIZE, TRAP_DAMAGE, TRAP_COOLDOWN, TRAP_MAX_ACTIVE,
    SERVER_TICK_RATE,
    SERVER_HOST, SERVER_PORT
)

players = {}      # player_id -> {x, y, dir, hp, weapon, weapon_expires, trap_ready_at, active_traps}
inputs = {}       # player_id -> latest input dict
bullets = []      # list of {x, y, dx, dy, owner, dmg}
shot_locks = {}   # player_id -> whether shoot is already handled (prevents autofire)
trap_locks = {}   # player_id -> prevents repeated trap placement while held down
traps = []        # list of {x, y, owner}
powerups = []     # list of {x, y, type}
last_powerup_spawn = 0.0

lock = threading.Lock()
next_player_id = 1

WEAPON_STATS = {
    "basic": {"speed": BULLET_SPEED, "damage": 1, "count": 1, "spread_deg": 0},
    "rapid": {"speed": BULLET_SPEED + 3, "damage": 1, "count": 1, "spread_deg": 0},
    "heavy": {"speed": BULLET_SPEED + 1, "damage": 2, "count": 1, "spread_deg": 0},
    "spread": {"speed": BULLET_SPEED, "damage": 1, "count": 3, "spread_deg": 14},
}

def get_weapon_stats(name: str):
    return WEAPON_STATS.get(name, WEAPON_STATS["basic"])

def create_new_player():
    x = random.randint(TANK_SIZE, SCREEN_WIDTH - TANK_SIZE)
    y = random.randint(TANK_SIZE, SCREEN_HEIGHT - TANK_SIZE)
    return {
        "x": x,
        "y": y,
        "dir": "up",
        "hp": TANK_HP,
        "weapon": "basic",
        "weapon_expires": 0.0,
        "trap_ready_at": 0.0,
        "active_traps": 0,
    }

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
            shot_locks.pop(player_id, None)
            trap_locks.pop(player_id, None)
        conn.close()

def _spawn_powerups(now: float):
    global last_powerup_spawn, powerups
    if len(powerups) >= POWERUP_MAX:
        return
    if now - last_powerup_spawn < POWERUP_RESPAWN_TIME:
        return
    px = random.randint(POWERUP_SIZE, SCREEN_WIDTH - POWERUP_SIZE)
    py = random.randint(POWERUP_SIZE, SCREEN_HEIGHT - POWERUP_SIZE)
    ptype = random.choice(["rapid", "heavy", "spread"])
    powerups.append({"x": px, "y": py, "type": ptype})
    last_powerup_spawn = now


def _rect_hit(x1, y1, size1, x2, y2, size2):
    return (x1 < x2 + size2 and x1 + size1 > x2 and
            y1 < y2 + size2 and y1 + size1 > y2)


def _clear_traps(owner_id: int):
    global traps
    traps = [t for t in traps if t["owner"] != owner_id]


def update_game(dt):
    global players, bullets, traps, powerups
    now = time.time()

    with lock:
        _spawn_powerups(now)

        # expire temporary weapons
        for player in players.values():
            if player.get("weapon") != "basic" and now > player.get("weapon_expires", 0):
                player["weapon"] = "basic"
                player["weapon_expires"] = 0.0

        # movement + actions
        for pid, player in players.items():
            keys = inputs.get(pid, {})
            mouse_pos = keys.get("mouse_pos")

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

            # update facing based on cursor to keep turret following aim
            aim_angle = None
            center_x = player["x"] + TANK_SIZE // 2
            center_y = player["y"] + TANK_SIZE // 2
            if isinstance(mouse_pos, (list, tuple)) and len(mouse_pos) == 2:
                mx, my = mouse_pos
                aim_dx = mx - center_x
                aim_dy = my - center_y
                if aim_dx != 0 or aim_dy != 0:
                    aim_angle = math.degrees(math.atan2(aim_dy, aim_dx))
                    if abs(aim_dx) > abs(aim_dy):
                        player["dir"] = "right" if aim_dx > 0 else "left"
                    else:
                        player["dir"] = "down" if aim_dy > 0 else "up"

            # traps
            is_trap = keys.get("trap", False)
            if not trap_locks.get(pid, False):
                trap_locks[pid] = False
            if is_trap and not trap_locks[pid]:
                if player["active_traps"] < TRAP_MAX_ACTIVE and now >= player["trap_ready_at"]:
                    tx = player["x"] + TANK_SIZE // 2 - TRAP_SIZE // 2
                    ty = player["y"] + TANK_SIZE // 2 - TRAP_SIZE // 2
                    traps.append({"x": tx, "y": ty, "owner": pid})
                    player["active_traps"] += 1
                    player["trap_ready_at"] = now + TRAP_COOLDOWN
                trap_locks[pid] = True
            elif not is_trap:
                trap_locks[pid] = False

            # shooting
            is_shooting = keys.get("shoot", False)
            if not shot_locks.get(pid, False):
                shot_locks[pid] = False

            if is_shooting and not shot_locks[pid]:
                shot_locks[pid] = True
                stats = get_weapon_stats(player.get("weapon", "basic"))
                bx = center_x
                by = center_y
                base_angle = aim_angle if aim_angle is not None else {"right": 0, "down": 90, "left": 180, "up": -90}.get(player["dir"], -90)
                count = max(1, stats.get("count", 1))
                spread = stats.get("spread_deg", 0)
                for i in range(count):
                    angle = base_angle
                    if count > 1:
                        offset = i - (count - 1) / 2
                        angle += spread * offset
                    rad = math.radians(angle)
                    speed = stats.get("speed", BULLET_SPEED)
                    dx_b = math.cos(rad) * speed
                    dy_b = math.sin(rad) * speed
                    bullets.append({
                        "x": bx,
                        "y": by,
                        "dx": dx_b,
                        "dy": dy_b,
                        "owner": pid,
                        "dmg": stats.get("damage", 1),
                    })
            elif not is_shooting:
                shot_locks[pid] = False

        # update bullets + hits
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
                    p["hp"] -= b.get("dmg", 1)
                    print(f"[SERVER] Player {pid} hit! HP = {p['hp']}")
                    if p["hp"] <= 0:
                        print(f"[SERVER] Player {pid} died. Respawning.")
                        new_state = create_new_player()
                        players[pid].update(new_state)
                        _clear_traps(pid)
                    hit_any = True
                    break
            if not hit_any:
                new_bullets.append(b)
        bullets = new_bullets

        # powerup pickups
        kept_powerups = []
        for p in powerups:
            claimed = False
            for pid, player in players.items():
                if _rect_hit(player["x"], player["y"], TANK_SIZE, p["x"], p["y"], POWERUP_SIZE):
                    player["weapon"] = p["type"]
                    player["weapon_expires"] = now + POWERUP_DURATION
                    claimed = True
                    break
            if not claimed:
                kept_powerups.append(p)
        powerups = kept_powerups

        # trap hits
        kept_traps = []
        for t in traps:
            triggered = False
            for pid, player in players.items():
                if pid == t["owner"]:
                    continue
                if _rect_hit(player["x"], player["y"], TANK_SIZE, t["x"], t["y"], TRAP_SIZE):
                    player["hp"] -= TRAP_DAMAGE
                    print(f"[SERVER] Player {pid} hit a trap! HP = {player['hp']}")
                    if player["hp"] <= 0:
                        print(f"[SERVER] Player {pid} died from trap. Respawning.")
                        new_state = create_new_player()
                        players[pid].update(new_state)
                        _clear_traps(pid)
                    owner = players.get(t["owner"])
                    if owner:
                        owner["active_traps"] = max(0, owner.get("active_traps", 0) - 1)
                    triggered = True
                    break
            if not triggered:
                kept_traps.append(t)
        traps = kept_traps

def broadcast_state(connections):
    with lock:
        now = time.time()
        export_players = {}
        for pid, p in players.items():
            export_players[pid] = {
                "x": p["x"],
                "y": p["y"],
                "dir": p["dir"],
                "hp": p["hp"],
                "weapon": p.get("weapon", "basic"),
                "weapon_timer": max(0.0, p.get("weapon_expires", 0) - now),
                "trap_cooldown": max(0.0, p.get("trap_ready_at", 0) - now),
                "active_traps": p.get("active_traps", 0),
            }

        state = {
            "type": "state",
            "players": export_players,
            "bullets": [dict(b) for b in bullets],
            "powerups": list(powerups),
            "traps": list(traps),
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
                shot_locks[pid] = False
                trap_locks[pid] = False
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
