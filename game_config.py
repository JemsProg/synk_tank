# game_config.py
SCREEN_WIDTH = 1820
SCREEN_HEIGHT = 1080


TANK_SIZE = 40
TANK_SPEED = 3
BULLET_SPEED = 7
BULLET_SIZE = 8
TANK_HP = 3
POWERUP_SIZE = 20
POWERUP_RESPAWN_TIME = 6
POWERUP_MAX = 3
POWERUP_DURATION = 12  # seconds the temporary weapon lasts
TRAP_SIZE = 18
TRAP_DAMAGE = 2
TRAP_COOLDOWN = 20  # seconds
TRAP_MAX_ACTIVE = 2

SERVER_TICK_RATE = 60  # updates per second

SERVER_HOST = "0.0.0.0"  # for server bind
SERVER_PORT = 5000       # port for all clients

# Colors (R, G, B)
COLOR_BG = (30, 30, 30)
COLOR_TANK_1 = (0, 200, 0)
COLOR_TANK_2 = (0, 0, 200)
COLOR_TANK_OTHER = (200, 200, 0)
COLOR_BULLET = (255, 255, 255)
COLOR_TEXT = (255, 255, 255)
COLOR_POWERUP = (255, 140, 0)
COLOR_TRAP = (220, 60, 60)
COLOR_WALL = (70, 80, 90)

# Static obstacles (x, y, width, height)
OBSTACLES = [
    {"x": SCREEN_WIDTH // 2 - 100, "y": SCREEN_HEIGHT // 2 - 30, "w": 200, "h": 60},
    {"x": SCREEN_WIDTH // 4 - 150, "y": SCREEN_HEIGHT // 3 - 20, "w": 300, "h": 40},
    {"x": 3 * SCREEN_WIDTH // 4 - 150, "y": SCREEN_HEIGHT // 3 - 20, "w": 300, "h": 40},
    {"x": SCREEN_WIDTH // 4 - 150, "y": 2 * SCREEN_HEIGHT // 3 - 20, "w": 300, "h": 40},
    {"x": 3 * SCREEN_WIDTH // 4 - 150, "y": 2 * SCREEN_HEIGHT // 3 - 20, "w": 300, "h": 40},
    {"x": SCREEN_WIDTH // 2 - 30, "y": SCREEN_HEIGHT // 4 - 100, "w": 60, "h": 200},
    {"x": SCREEN_WIDTH // 2 - 30, "y": 3 * SCREEN_HEIGHT // 4 - 100, "w": 60, "h": 200},
]
