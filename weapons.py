# weapons.py
"""
Simple weapon system for the LAN Tanks game.

- Primary + secondary weapons
- Purely visual for now (cosmetics)
- Drawn on top of the tank in client.py
"""

import pygame

# Some nice colors for weapons
COLOR_GUN_METAL = (90, 90, 100)
COLOR_LASER = (120, 200, 255)
COLOR_ROCKET = (220, 80, 60)
COLOR_MACHINE_GUN = (230, 230, 120)
COLOR_ACCENT = (180, 180, 255)


class Weapon:
    """
    Base weapon class for drawing attachments on the tank.
    """

    def __init__(self, name, color, length, width, offset=0, style="barrel"):
        """
        :param name: display name
        :param color: (R, G, B)
        :param length: weapon length (pixels)
        :param width: weapon width (pixels)
        :param offset: side offset from tank center (for twin guns, etc.)
        :param style: "barrel", "pod", "laser"
        """
        self.name = name
        self.color = color
        self.length = length
        self.width = width
        self.offset = offset
        self.style = style

    def _compute_rect(self, tank_rect: pygame.Rect, direction: str) -> pygame.Rect:
        """
        Compute weapon rectangle based on tank position + direction.
        """
        cx = tank_rect.centerx
        cy = tank_rect.centery

        if direction == "up":
            x = cx - self.width // 2 + self.offset
            y = tank_rect.top - self.length
            return pygame.Rect(x, y, self.width, self.length)

        if direction == "down":
            x = cx - self.width // 2 + self.offset
            y = tank_rect.bottom
            return pygame.Rect(x, y, self.width, self.length)

        if direction == "left":
            x = tank_rect.left - self.length
            y = cy - self.width // 2 + self.offset
            return pygame.Rect(x, y, self.length, self.width)

        # default / "right"
        x = tank_rect.right
        y = cy - self.width // 2 + self.offset
        return pygame.Rect(x, y, self.length, self.width)

    def draw(self, surface: pygame.Surface, tank_rect: pygame.Rect, direction: str):
        """
        Draw the weapon shape on the given surface.
        """
        base_rect = self._compute_rect(tank_rect, direction)

        if self.style == "barrel":
            pygame.draw.rect(surface, self.color, base_rect)

        elif self.style == "pod":
            # rocket pod = rounded box + small circles
            pygame.draw.rect(surface, self.color, base_rect, border_radius=4)

            # draw "rockets" as small circles inside
            for i in range(3):
                if base_rect.width > base_rect.height:
                    # horizontal
                    cx = base_rect.left + (i + 1) * base_rect.width // 4
                    cy = base_rect.centery
                else:
                    cx = base_rect.centerx
                    cy = base_rect.top + (i + 1) * base_rect.height // 4

                pygame.draw.circle(surface, COLOR_ROCKET, (cx, cy), max(2, self.width // 4))

        elif self.style == "laser":
            # laser emitter: thin rectangle + glow outline
            pygame.draw.rect(surface, self.color, base_rect)
            pygame.draw.rect(surface, COLOR_ACCENT, base_rect.inflate(2, 2), width=1)

        else:
            # fallback
            pygame.draw.rect(surface, self.color, base_rect)


def get_primary_weapon_for_player(player_id: int, weapon_name: str = None) -> Weapon:
    """
    Choose primary weapon based on player_id or an explicit weapon name
    (used when a powerup overrides the default).
    """
    if weapon_name:
        name = weapon_name.lower()
        if name == "basic":
            return Weapon(
                name="Basic Cannon",
                color=COLOR_GUN_METAL,
                length=26,
                width=9,
                offset=0,
                style="barrel",
            )
        if name == "rapid":
            return Weapon(
                name="Rapid Blaster",
                color=COLOR_LASER,
                length=32,
                width=7,
                offset=0,
                style="laser",
            )
        if name == "heavy":
            return Weapon(
                name="Heavy Cannon",
                color=COLOR_ROCKET,
                length=30,
                width=12,
                offset=0,
                style="pod",
            )
        if name == "spread":
            return Weapon(
                name="Spread Gun",
                color=COLOR_MACHINE_GUN,
                length=28,
                width=10,
                offset=0,
                style="barrel",
            )

    mod = player_id % 3

    if mod == 1:
        # classic heavy cannon
        return Weapon(
            name="Heavy Cannon",
            color=COLOR_GUN_METAL,
            length=30,
            width=10,
            offset=0,
            style="barrel",
        )
    elif mod == 2:
        # railgun style
        return Weapon(
            name="Railgun",
            color=COLOR_LASER,
            length=40,
            width=6,
            offset=0,
            style="laser",
        )
    else:
        # rocket pod
        return Weapon(
            name="Rocket Pod",
            color=COLOR_GUN_METAL,
            length=22,
            width=16,
            offset=0,
            style="pod",
        )


def get_secondary_weapon_for_player(player_id: int):
    """
    Secondary weapon (optional). Can be None.
    """
    mod = player_id % 3

    if mod == 1:
        # twin machine guns on the side
        return [
            Weapon(
                name="Twin MG Left",
                color=COLOR_MACHINE_GUN,
                length=18,
                width=4,
                offset=-6,
                style="barrel",
            ),
            Weapon(
                name="Twin MG Right",
                color=COLOR_MACHINE_GUN,
                length=18,
                width=4,
                offset=6,
                style="barrel",
            ),
        ]
    elif mod == 2:
        # side laser emitters
        return [
            Weapon(
                name="Side Laser Left",
                color=COLOR_LASER,
                length=16,
                width=3,
                offset=-5,
                style="laser",
            ),
            Weapon(
                name="Side Laser Right",
                color=COLOR_LASER,
                length=16,
                width=3,
                offset=5,
                style="laser",
            ),
        ]
    else:
        # no secondary weapon for this player (clean look)
        return None
