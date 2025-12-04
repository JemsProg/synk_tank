# client.py
import socket
import threading
import json
import pygame
import sys
import os

from game_config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    TANK_SIZE,
    BULLET_SIZE,
    POWERUP_SIZE, TRAP_SIZE, TRAP_MAX_ACTIVE,
    COLOR_BG,
    COLOR_TANK_1, COLOR_TANK_2, COLOR_TANK_OTHER,
    COLOR_BULLET, COLOR_TEXT, COLOR_POWERUP, COLOR_TRAP,
    SERVER_PORT
)

from weapons import (
    get_primary_weapon_for_player,
    get_secondary_weapon_for_player,
)

# Allow overriding the server IP via CLI arg or env var for easy LAN setup.
DEFAULT_SERVER_IP = "127.0.0.1"

player_id = None
players = {}
bullets = []
powerups = []
traps = []
state_lock = threading.Lock()

keys_state = {
    "up": False,
    "down": False,
    "left": False,
    "right": False,
    "shoot": False,
    "trap": False,
}

running = True

def network_thread(sock):
    global player_id, players, bullets, powerups, traps, running

    buffer = ""
    try:
        while running:
            data = sock.recv(4096)
            if not data:
                print("[CLIENT] Disconnected from server.")
                running = False
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

                if msg.get("type") == "init":
                    player_id = msg["player_id"]
                    print(f"[CLIENT] My player_id = {player_id}")
                elif msg.get("type") == "state":
                    with state_lock:
                        players = msg.get("players", {})
                        bullets = msg.get("bullets", [])
                        powerups[:] = msg.get("powerups", [])
                        traps[:] = msg.get("traps", [])
    except ConnectionResetError:
        print("[CLIENT] Connection reset by server.")
    finally:
        running = False
        sock.close()

def send_input(sock):
    msg = {
        "type": "input",
        "keys": keys_state
    }
    try:
        sock.sendall((json.dumps(msg) + "\n").encode())
    except:
        pass

def draw_bar(surface, x, y, w, h, value, color):
    value = max(0.0, min(1.0, value))
    pygame.draw.rect(surface, (50, 60, 70), (x, y, w, h), border_radius=4)
    if value > 0:
        pygame.draw.rect(surface, color, (x + 2, y + 2, int((w - 4) * value), h - 4), border_radius=4)


def draw_hud(screen, font, small_font, panel_img, fps, server_ip, current_player_id, current_players):
    """
    Modern HUD: glass panel, bars, and clear CTA text.
    """
    panel = panel_img.copy()

    me = current_players.get(str(current_player_id)) if current_player_id is not None else None
    weapon_name = (me.get("weapon") if me else "basic") or "basic"
    weapon_timer = me.get("weapon_timer", 0) if me else 0
    trap_cd = me.get("trap_cooldown", 0) if me else 0
    traps_active = me.get("active_traps", 0) if me else 0

    texts = [
        ("LAN TANKS", font, True),
        (f"Server {server_ip}", small_font, False),
        (f"Player {current_player_id if current_player_id else 'connecting...'} | Online {len(current_players)}", small_font, False),
        (f"FPS {int(fps)}", small_font, False),
        (f"Weapon {weapon_name}", small_font, False),
        (f"Traps {traps_active}/{TRAP_MAX_ACTIVE}", small_font, False),
    ]

    y = 14
    for text, fnt, accent in texts:
        color = (0, 200, 255) if accent else COLOR_TEXT
        panel.blit(fnt.render(text, True, color), (16, y))
        y += 26

    # bars
    panel.blit(small_font.render("Weapon timer", True, COLOR_TEXT), (16, y + 2))
    bar_val = min(1.0, weapon_timer / 12.0) if weapon_timer > 0 else 0
    draw_bar(panel, 140, y + 4, 160, 14, bar_val, (0, 200, 255))
    y += 24

    panel.blit(small_font.render("Trap cooldown", True, COLOR_TEXT), (16, y + 2))
    trap_val = min(1.0, trap_cd / 20.0) if trap_cd > 0 else 0
    draw_bar(panel, 140, y + 4, 160, 14, trap_val, (255, 120, 80))
    y += 28

    panel.blit(small_font.render("Controls", True, (0, 200, 255)), (16, y))
    y += 22
    controls = [
        "Move: WASD / Arrows",
        "Shoot: Space",
        "Trap: E",
        "Quit: Esc / Close",
    ]
    for line in controls:
        panel.blit(small_font.render(line, True, COLOR_TEXT), (22, y))
        y += 18

    screen.blit(panel, (16, 16))

    footer = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
    footer.fill((10, 10, 10, 140))
    guide_text = "Host: run server.py on LAN | Clients: run client.py <server-ip> | Grab powerups, place traps, outlast opponents."
    footer.blit(small_font.render(guide_text, True, COLOR_TEXT), (16, 10))
    screen.blit(footer, (0, SCREEN_HEIGHT - 48))

def resolve_server_ip():
    # Priority: CLI arg -> env var -> default
    if len(sys.argv) > 1:
        return sys.argv[1]
    env_ip = os.environ.get("LAN_TANK_SERVER")
    if env_ip:
        return env_ip
    return DEFAULT_SERVER_IP


def load_assets():
    # Load map background and HUD panel; fall back to solid fills if missing.
    try:
        map_bg = pygame.image.load(os.path.join("assets", "map_bg.png")).convert()
        map_bg = pygame.transform.scale(map_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
    except Exception:
        map_bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        map_bg.fill((25, 30, 40))

    try:
        hud_panel = pygame.image.load(os.path.join("assets", "hud_panel.png")).convert_alpha()
    except Exception:
        hud_panel = pygame.Surface((340, 220), pygame.SRCALPHA)
        hud_panel.fill((25, 25, 30, 200))
        pygame.draw.rect(hud_panel, (0, 180, 255), hud_panel.get_rect(), 2, border_radius=12)

    return map_bg, hud_panel

def main():
    global running, keys_state

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_ip = resolve_server_ip()
    try:
        sock.connect((server_ip, SERVER_PORT))
    except Exception as e:
        print(f"[CLIENT] Failed to connect: {e}")
        return

    threading.Thread(target=network_thread, args=(sock,), daemon=True).start()

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("LAN Tanks")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("segoeui", 22, bold=True)
    small_font = pygame.font.SysFont("segoeui", 16)
    map_bg, hud_panel = load_assets()

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_w, pygame.K_UP):
                    keys_state["up"] = True
                if event.key in (pygame.K_s, pygame.K_DOWN):
                    keys_state["down"] = True
                if event.key in (pygame.K_a, pygame.K_LEFT):
                    keys_state["left"] = True
                if event.key in (pygame.K_d, pygame.K_RIGHT):
                    keys_state["right"] = True
                if event.key == pygame.K_SPACE:
                    keys_state["shoot"] = True
                if event.key == pygame.K_e:
                    keys_state["trap"] = True

            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_w, pygame.K_UP):
                    keys_state["up"] = False
                if event.key in (pygame.K_s, pygame.K_DOWN):
                    keys_state["down"] = False
                if event.key in (pygame.K_a, pygame.K_RIGHT):
                    keys_state["left"] = False
                if event.key in (pygame.K_d, pygame.K_LEFT):
                    keys_state["right"] = False
                if event.key == pygame.K_SPACE:
                    keys_state["shoot"] = False
                if event.key == pygame.K_e:
                    keys_state["trap"] = False

        send_input(sock)

        with state_lock:
            current_players = dict(players)
            current_bullets = list(bullets)
            current_powerups = list(powerups)
            current_traps = list(traps)

        screen.blit(map_bg, (0, 0))

        # draw powerups
        for p in current_powerups:
            cx = int(p["x"] + POWERUP_SIZE // 2)
            cy = int(p["y"] + POWERUP_SIZE // 2)
            pygame.draw.circle(screen, COLOR_POWERUP, (cx, cy), POWERUP_SIZE // 2)
            label = small_font.render(p.get("type", "?")[:1].upper(), True, COLOR_BG)
            rect = label.get_rect(center=(cx, cy))
            screen.blit(label, rect)

        # draw traps
        for t in current_traps:
            pygame.draw.rect(
                screen,
                COLOR_TRAP,
                pygame.Rect(int(t["x"]), int(t["y"]), TRAP_SIZE, TRAP_SIZE),
                border_radius=4,
            )

        for b in current_bullets:
            bx = int(b["x"])
            by = int(b["y"])
            pygame.draw.rect(
                screen,
                COLOR_BULLET,
                pygame.Rect(bx - BULLET_SIZE // 2, by - BULLET_SIZE // 2, BULLET_SIZE, BULLET_SIZE)
            )

        for pid_str, p in current_players.items():
            pid = int(pid_str)
            x = int(p["x"])
            y = int(p["y"])

            # base tank color
            if player_id is not None and pid == player_id:
                color = COLOR_TANK_1
            elif pid == 1:
                color = COLOR_TANK_2
            else:
                color = COLOR_TANK_OTHER

            # tank rect
            tank_rect = pygame.Rect(x, y, TANK_SIZE, TANK_SIZE)

            # draw tank body
            pygame.draw.rect(screen, color, tank_rect, border_radius=6)

            # draw primary & secondary weapons (cosmetics)
            direction = p.get("dir", "up")

            primary_weapon = get_primary_weapon_for_player(pid, p.get("weapon"))
            if primary_weapon:
                primary_weapon.draw(screen, tank_rect, direction)

            secondary_weapons = get_secondary_weapon_for_player(pid)
            if secondary_weapons:
                # secondary_weapons can be a list
                if isinstance(secondary_weapons, list):
                    for w in secondary_weapons:
                        w.draw(screen, tank_rect, direction)
                else:
                    secondary_weapons.draw(screen, tank_rect, direction)

            # HP text
            hp_text = font.render(f"HP:{p['hp']}", True, COLOR_TEXT)
            screen.blit(hp_text, (x, y - 18))

        draw_hud(screen, font, small_font, hud_panel, clock.get_fps(), server_ip, player_id, current_players)

        pygame.display.flip()

    pygame.quit()
    try:
        sock.close()
    except:
        pass

if __name__ == "__main__":
    main()
