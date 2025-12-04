# client.py
import socket
import threading
import json
import pygame
import sys

from game_config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    TANK_SIZE,
    BULLET_SIZE,
    COLOR_BG,
    COLOR_TANK_1, COLOR_TANK_2, COLOR_TANK_OTHER,
    COLOR_BULLET, COLOR_TEXT,
    SERVER_PORT
)

SERVER_IP = "192.168.0.136"  # for testing sa iisang laptop muna

player_id = None
players = {}
bullets = []

keys_state = {
    "up": False,
    "down": False,
    "left": False,
    "right": False,
    "shoot": False,
    "shoot_handled": False
}

running = True

def network_thread(sock):
    global player_id, players, bullets, running

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
                    players = msg["players"]
                    bullets = msg["bullets"]
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

def main():
    global running, keys_state

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((SERVER_IP, SERVER_PORT))
    except Exception as e:
        print(f"[CLIENT] Failed to connect: {e}")
        return

    threading.Thread(target=network_thread, args=(sock,), daemon=True).start()

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("LAN Tanks")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
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
                    keys_state["shoot_handled"] = False

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
                    keys_state["shoot_handled"] = False

        send_input(sock)

        screen.fill(COLOR_BG)

        for b in bullets:
            bx = int(b["x"])
            by = int(b["y"])
            pygame.draw.rect(
                screen,
                COLOR_BULLET,
                pygame.Rect(bx - BULLET_SIZE // 2, by - BULLET_SIZE // 2, BULLET_SIZE, BULLET_SIZE)
            )

        for pid_str, p in players.items():
            pid = int(pid_str)
            x = int(p["x"])
            y = int(p["y"])

            if player_id is not None and pid == player_id:
                color = COLOR_TANK_1
            elif pid == 1:
                color = COLOR_TANK_2
            else:
                color = COLOR_TANK_OTHER

            pygame.draw.rect(
                screen,
                color,
                pygame.Rect(x, y, TANK_SIZE, TANK_SIZE)
            )

            hp_text = font.render(f"HP:{p['hp']}", True, COLOR_TEXT)
            screen.blit(hp_text, (x, y - 18))

        info = font.render(f"Player ID: {player_id}", True, COLOR_TEXT)
        screen.blit(info, (10, 10))

        pygame.display.flip()

    pygame.quit()
    try:
        sock.close()
    except:
        pass

if __name__ == "__main__":
    main()
