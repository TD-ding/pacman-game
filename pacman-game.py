#!/usr/bin/env python3
"""Pac-Man game implemented with pygame."""

import pygame
import sys
import math
import random
import array

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CELL = 28
COLS = 21
ROWS = 22
WIDTH = CELL * COLS
HEIGHT = CELL * ROWS + 40  # extra space for HUD

FPS = 60
PAC_SPEED = 2
BASE_GHOST_SPEED = 1.8
GHOST_RESPAWN_TIME = 300  # frames (~5 seconds)
DEATH_ANIM_FRAMES = 60

BLACK  = (0, 0, 0)
YELLOW = (255, 255, 0)
WHITE  = (255, 255, 255)
BLUE   = (33, 33, 222)
RED    = (255, 0, 0)
PINK   = (255, 184, 255)
CYAN   = (0, 255, 255)
ORANGE = (255, 184, 82)
DOT_CLR = (255, 183, 174)
GREEN  = (0, 255, 0)

# 1 = wall, 0 = dot, 2 = empty, 3 = power pellet
MAZE_TEMPLATE = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,1,0,1,1,1,0,1,0,1,1,1,0,1,1,1,0,1],
    [1,3,1,1,1,0,1,1,1,0,1,0,1,1,1,0,1,1,1,3,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,1,0,1,0,1,1,1,1,1,0,1,0,1,1,1,0,1],
    [1,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,1],
    [1,1,1,1,1,0,1,1,1,2,1,2,1,1,1,0,1,1,1,1,1],
    [1,1,1,1,1,0,1,2,2,2,2,2,2,2,1,0,1,1,1,1,1],
    [1,1,1,1,1,0,1,2,1,1,2,1,1,2,1,0,1,1,1,1,1],
    [2,2,2,2,2,0,2,2,1,2,2,2,1,2,2,0,2,2,2,2,2],
    [1,1,1,1,1,0,1,2,1,1,1,1,1,2,1,0,1,1,1,1,1],
    [1,1,1,1,1,0,1,2,2,2,2,2,2,2,1,0,1,1,1,1,1],
    [1,1,1,1,1,0,1,2,1,1,1,1,1,2,1,0,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,1,0,1,1,1,0,1,0,1,1,1,0,1,1,1,0,1],
    [1,3,0,0,1,0,0,0,0,0,2,0,0,0,0,0,1,0,0,3,1],
    [1,1,1,0,1,0,1,0,1,1,1,1,1,0,1,0,1,0,1,1,1],
    [1,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,1],
    [1,0,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

# Fruit types: (name, color, points)
FRUIT_TYPES = [
    ("Cherry",     RED,    100),
    ("Strawberry", PINK,   300),
    ("Orange",     ORANGE, 500),
    ("Apple",      GREEN,  700),
    ("Melon",      CYAN,   1000),
]

# Score popups for eating ghosts in combo
GHOST_EAT_SCORES = [200, 400, 800, 1600]

# ---------------------------------------------------------------------------
# Sound FX
# ---------------------------------------------------------------------------

class SoundFX:
    """Generates square-wave sound effects using pygame.mixer + array module."""

    SR = 22050

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.SR, size=-16, channels=1, buffer=512)
            self._generate()
            self.enabled = True
        except pygame.error:
            pass

    def _square(self, freq, dur, vol=0.3):
        n = int(self.SR * dur)
        buf = array.array('h')
        amp = int(32767 * vol)
        hp = self.SR / (2 * freq)
        for i in range(n):
            buf.append(amp if int(i / hp) % 2 == 0 else -amp)
        return buf

    def _generate(self):
        self.sounds['chomp'] = pygame.mixer.Sound(buffer=self._square(600, 0.05, 0.2))
        buf = self._square(400, 0.08) + self._square(800, 0.08)
        self.sounds['power'] = pygame.mixer.Sound(buffer=buf)
        buf = self._square(500, 0.1) + self._square(400, 0.1) + self._square(300, 0.1) + self._square(200, 0.15)
        self.sounds['death'] = pygame.mixer.Sound(buffer=buf)
        buf = self._square(523, 0.08) + self._square(659, 0.08) + self._square(784, 0.08) + self._square(1047, 0.12)
        self.sounds['start'] = pygame.mixer.Sound(buffer=buf)
        # ghost eat – quick rising blip
        buf = self._square(800, 0.04) + self._square(1200, 0.06)
        self.sounds['eat_ghost'] = pygame.mixer.Sound(buffer=buf)
        # fruit – happy two-note
        buf = self._square(880, 0.06) + self._square(1320, 0.08)
        self.sounds['fruit'] = pygame.mixer.Sound(buffer=buf)
        # level up – ascending scale
        buf = (self._square(523, 0.06) + self._square(659, 0.06) +
               self._square(784, 0.06) + self._square(1047, 0.1) +
               self._square(1319, 0.15))
        self.sounds['level_up'] = pygame.mixer.Sound(buffer=buf)

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cell_center(col, row):
    return col * CELL + CELL // 2, row * CELL + CELL // 2 + 40


def pixel_to_cell(x, y):
    c = int((x - CELL // 2) // CELL)
    r = int((y - 40 - CELL // 2) // CELL)
    return c, r


def is_passable(maze, col, row):
    if row < 0 or row >= ROWS:
        return False
    c = col % COLS
    if c < 0:
        c += COLS
    return maze[row][c] != 1


def wrap_x(x):
    if x < 0:
        return x + COLS * CELL
    if x >= COLS * CELL:
        return x - COLS * CELL
    return x


# ---------------------------------------------------------------------------
# Pac-Man
# ---------------------------------------------------------------------------

class PacMan:
    def __init__(self, col, row):
        self.start_col, self.start_row = col, row
        self.sx, self.sy = cell_center(col, row)
        self.x, self.y = float(self.sx), float(self.sy)
        self.col, self.row = col, row
        self.direction = (0, 0)
        self.next_dir = (0, 0)
        self.mouth_angle = 0
        self.mouth_open = True
        self.alive = True
        self.death_frame = 0

    def reset(self):
        self.x, self.y = float(self.sx), float(self.sy)
        self.col, self.row = self.start_col, self.start_row
        self.direction = (0, 0)
        self.next_dir = (0, 0)
        self.alive = True
        self.death_frame = 0

    def set_direction(self, dx, dy):
        self.next_dir = (dx, dy)

    def update(self, maze):
        if not self.alive:
            return

        if self.mouth_open:
            self.mouth_angle += 4
            if self.mouth_angle >= 45:
                self.mouth_open = False
        else:
            self.mouth_angle -= 4
            if self.mouth_angle <= 5:
                self.mouth_open = True

        cx, cy = cell_center(self.col, self.row)
        dist_to_center = math.hypot(self.x - cx, self.y - cy)

        if dist_to_center < PAC_SPEED * 2 and self.next_dir != (0, 0):
            nc = self.col + self.next_dir[0]
            nr = self.row + self.next_dir[1]
            if is_passable(maze, nc, nr):
                self.direction = self.next_dir
                self.x, self.y = float(cx), float(cy)

        dx, dy = self.direction
        if dx == 0 and dy == 0:
            return

        nc = self.col + dx
        nr = self.row + dy
        if not is_passable(maze, nc, nr) and dist_to_center < PAC_SPEED * 2:
            self.x, self.y = float(cx), float(cy)
            self.direction = (0, 0)
            return

        self.x += dx * PAC_SPEED
        self.y += dy * PAC_SPEED
        self.x = wrap_x(self.x)

        self.col, self.row = pixel_to_cell(self.x, self.y)
        if self.col < 0:
            self.col += COLS
        elif self.col >= COLS:
            self.col -= COLS

    def draw(self, screen, death_frame=0):
        r = CELL // 2 - 2
        ix, iy = int(self.x), int(self.y)

        if not self.alive:
            progress = death_frame / DEATH_ANIM_FRAMES
            angle = int(360 * progress)
            if angle >= 360:
                return
            half = max(1, 180 - angle)
            pygame.draw.circle(screen, YELLOW, (ix, iy), r)
            pygame.draw.polygon(screen, BLACK, [
                (ix, iy),
                (ix + int(r * math.cos(math.radians(0 - half))),
                 iy - int(r * math.sin(math.radians(0 - half)))),
                (ix + int(r * math.cos(math.radians(0 + half))),
                 iy - int(r * math.sin(math.radians(0 + half)))),
            ])
            return

        if self.direction == (1, 0):
            start = 0
        elif self.direction == (-1, 0):
            start = 180
        elif self.direction == (0, -1):
            start = 90
        elif self.direction == (0, 1):
            start = 270
        else:
            start = 0
        mouth = max(self.mouth_angle, 1)
        pygame.draw.circle(screen, YELLOW, (ix, iy), r)
        pygame.draw.polygon(screen, BLACK, [
            (ix, iy),
            (ix + int(r * math.cos(math.radians(start - mouth))),
             iy - int(r * math.sin(math.radians(start - mouth)))),
            (ix + int(r * math.cos(math.radians(start + mouth))),
             iy - int(r * math.sin(math.radians(start + mouth)))),
        ])


# ---------------------------------------------------------------------------
# Ghost AI strategies
# ---------------------------------------------------------------------------

class GhostAI:
    """Base class providing shared logic for ghost targeting."""

    @staticmethod
    def _get_options(maze, col, row, direction):
        dx, dy = direction
        opposite = (-dx, -dy) if (dx, dy) != (0, 0) else None
        options = []
        for d in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            if d == opposite:
                continue
            nc = col + d[0]
            nr = row + d[1]
            if is_passable(maze, nc, nr):
                options.append(d)
        if not options:
            if opposite and is_passable(maze, col + opposite[0], row + opposite[1]):
                options = [opposite]
            else:
                for d in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    if is_passable(maze, col + d[0], row + d[1]):
                        options.append(d)
        return options

    @staticmethod
    def _pick_closest(options, col, row, tx, ty, jitter=20):
        best = options[0]
        best_dist = float('inf')
        for d in options:
            nc = col + d[0]
            nr = row + d[1]
            nccx, nccy = cell_center(nc, nr)
            dist = math.hypot(nccx - tx, nccy - ty) + random.random() * jitter
            if dist < best_dist:
                best_dist = dist
                best = d
        return best

    @staticmethod
    def _pick_farthest(options, col, row, tx, ty, jitter=10):
        best = options[0]
        best_dist = -1
        for d in options:
            nc = col + d[0]
            nr = row + d[1]
            nccx, nccy = cell_center(nc, nr)
            dist = math.hypot(nccx - tx, nccy - ty) + random.random() * jitter
            if dist > best_dist:
                best_dist = dist
                best = d
        return best


class BlinkyAI(GhostAI):
    """Red ghost – directly targets Pac-Man's current position."""
    name = "Blinky"

    @staticmethod
    def choose(maze, col, row, direction, pacman, blinky=None):
        options = GhostAI._get_options(maze, col, row, direction)
        if not options:
            return direction
        return GhostAI._pick_closest(options, col, row, pacman.x, pacman.y)


class PinkyAI(GhostAI):
    """Pink ghost – targets 4 cells ahead of Pac-Man's facing direction."""
    name = "Pinky"

    @staticmethod
    def choose(maze, col, row, direction, pacman, blinky=None):
        options = GhostAI._get_options(maze, col, row, direction)
        if not options:
            return direction
        offset = 4
        pdx, pdy = pacman.direction if pacman.direction != (0, 0) else (0, -1)
        tx = pacman.x + pdx * CELL * offset
        ty = pacman.y + pdy * CELL * offset
        return GhostAI._pick_closest(options, col, row, tx, ty)


class InkyAI(GhostAI):
    """Cyan ghost – uses Blinky's position to determine a flanking target."""
    name = "Inky"

    @staticmethod
    def choose(maze, col, row, direction, pacman, blinky=None):
        options = GhostAI._get_options(maze, col, row, direction)
        if not options:
            return direction
        pdx, pdy = pacman.direction if pacman.direction != (0, 0) else (0, -1)
        pivot_x = pacman.x + pdx * CELL * 2
        pivot_y = pacman.y + pdy * CELL * 2
        if blinky is None:
            tx, ty = pivot_x, pivot_y
        else:
            tx = pivot_x + (pivot_x - blinky.x)
            ty = pivot_y + (pivot_y - blinky.y)
        return GhostAI._pick_closest(options, col, row, tx, ty)


class ClydeAI(GhostAI):
    """Orange ghost – chases when far (>8 cells), scatters when close."""
    name = "Clyde"

    SCATTER_TARGET = (1, ROWS - 2)  # bottom-left corner
    CHASE_DIST = 8 * CELL

    @staticmethod
    def choose(maze, col, row, direction, pacman, blinky=None):
        options = GhostAI._get_options(maze, col, row, direction)
        if not options:
            return direction
        dist = math.hypot(cell_center(col, row)[0] - pacman.x,
                          cell_center(col, row)[1] - pacman.y)
        if dist > ClydeAI.CHASE_DIST:
            return GhostAI._pick_closest(options, col, row, pacman.x, pacman.y)
        else:
            sx, sy = cell_center(*ClydeAI.SCATTER_TARGET)
            return GhostAI._pick_closest(options, col, row, sx, sy)


GHOST_AI_LIST = [BlinkyAI, PinkyAI, InkyAI, ClydeAI]

# ---------------------------------------------------------------------------
# Ghost
# ---------------------------------------------------------------------------

GHOST_COLORS = [RED, PINK, CYAN, ORANGE]

class Ghost:
    def __init__(self, col, row, color_idx):
        self.start_col, self.start_row = col, row
        self.sx, self.sy = cell_center(col, row)
        self.x, self.y = float(self.sx), float(self.sy)
        self.col, self.row = col, row
        self.color = GHOST_COLORS[color_idx % len(GHOST_COLORS)]
        self.color_idx = color_idx
        self.ai = GHOST_AI_LIST[color_idx % len(GHOST_AI_LIST)]
        self.direction = (0, 0)
        self.scared = False
        self.scared_timer = 0
        self.eaten = False
        self.respawn_timer = 0

    def reset(self):
        self.x, self.y = float(self.sx), float(self.sy)
        self.col, self.row = self.start_col, self.start_row
        self.direction = (0, -1)
        self.scared = False
        self.scared_timer = 0
        self.eaten = False
        self.respawn_timer = 0

    def respawn(self):
        self.x, self.y = float(self.sx), float(self.sy)
        self.col, self.row = self.start_col, self.start_row
        self.direction = (0, -1)
        self.scared = False
        self.scared_timer = 0
        self.eaten = False
        self.respawn_timer = 0

    def update(self, maze, pacman, blinky, ghost_speed):
        if self.eaten:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.respawn()
            return

        if self.scared:
            self.scared_timer -= 1
            if self.scared_timer <= 0:
                self.scared = False

        speed = ghost_speed * 0.6 if self.scared else ghost_speed

        cx, cy = cell_center(self.col, self.row)
        dist_to_center = math.hypot(self.x - cx, self.y - cy)

        if dist_to_center < speed + 0.5:
            self.x, self.y = float(cx), float(cy)
            self.col, self.row = pixel_to_cell(self.x, self.y)
            if self.col < 0:
                self.col += COLS
            elif self.col >= COLS:
                self.col -= COLS
            self._choose_direction(maze, pacman, blinky)

        dx, dy = self.direction
        if dx == 0 and dy == 0:
            self._choose_direction(maze, pacman, blinky)
            dx, dy = self.direction
            if dx == 0 and dy == 0:
                return

        nc = self.col + dx
        nr = self.row + dy
        if not is_passable(maze, nc, nr):
            self.x, self.y = float(cx), float(cy)
            self._choose_direction(maze, pacman, blinky)
            dx, dy = self.direction
            if dx == 0 and dy == 0:
                return
            nc = self.col + dx
            nr = self.row + dy
            if not is_passable(maze, nc, nr):
                return

        self.x += dx * speed
        self.y += dy * speed
        self.x = wrap_x(self.x)

        self.col, self.row = pixel_to_cell(self.x, self.y)
        if self.col < 0:
            self.col += COLS
        elif self.col >= COLS:
            self.col -= COLS

    def _choose_direction(self, maze, pacman, blinky):
        if self.scared:
            options = GhostAI._get_options(maze, self.col, self.row, self.direction)
            if options:
                self.direction = random.choice(options)
            return

        self.direction = self.ai.choose(
            maze, self.col, self.row, self.direction, pacman, blinky
        )

    def draw(self, screen):
        if self.eaten:
            # draw just eyes heading back to spawn
            r = CELL // 2 - 2
            ix, iy = int(self.x), int(self.y)
            for ex in (ix - r // 3, ix + r // 3):
                pygame.draw.circle(screen, WHITE, (ex, iy - 5), r // 3)
                ddx, ddy = self.direction
                pygame.draw.circle(screen, BLUE, (ex + ddx * 2, iy - 5 + ddy * 2), r // 5)
            return
        r = CELL // 2 - 2
        ix, iy = int(self.x), int(self.y)

        if self.scared:
            color = (33, 33, 222) if self.scared_timer > 90 or self.scared_timer % 12 < 6 else WHITE
        else:
            color = self.color

        pygame.draw.circle(screen, color, (ix, iy - 3), r)
        pygame.draw.rect(screen, color, (ix - r, iy - 3, r * 2, r))
        for i in range(3):
            bx = ix - r + i * (r * 2 // 3) + r * 2 // 6
            pygame.draw.circle(screen, BLACK, (bx, iy - 3 + r), r // 4)

        if not self.scared:
            for ex in (ix - r // 3, ix + r // 3):
                pygame.draw.circle(screen, WHITE, (ex, iy - 5), r // 3)
                ddx, ddy = self.direction
                pygame.draw.circle(screen, BLUE, (ex + ddx * 2, iy - 5 + ddy * 2), r // 5)
        else:
            for ex in (ix - r // 3, ix + r // 3):
                pygame.draw.circle(screen, WHITE, (ex, iy - 5), r // 4)


# ---------------------------------------------------------------------------
# Score Popup
# ---------------------------------------------------------------------------

class ScorePopup:
    """Floating score text that appears when eating a ghost or fruit."""

    def __init__(self, x, y, points, color=WHITE):
        self.x = x
        self.y = y
        self.points = points
        self.color = color
        self.timer = 60  # 1 second at 60 FPS
        self.active = True

    def update(self):
        self.timer -= 1
        self.y -= 0.5  # float upward
        if self.timer <= 0:
            self.active = False

    def draw(self, screen, font):
        if not self.active:
            return
        alpha = min(255, self.timer * 6)
        surf = font.render(str(self.points), True, self.color)
        if alpha < 255:
            tmp = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            tmp.blit(surf, (0, 0))
            tmp.set_alpha(alpha)
            screen.blit(tmp, (int(self.x) - surf.get_width() // 2, int(self.y)))
        else:
            screen.blit(surf, (int(self.x) - surf.get_width() // 2, int(self.y)))


# ---------------------------------------------------------------------------
# Fruit
# ---------------------------------------------------------------------------

class Fruit:
    """Bonus fruit that appears near map center for a limited time."""

    def __init__(self, fruit_type=0):
        self.name, self.color, self.points = FRUIT_TYPES[fruit_type % len(FRUIT_TYPES)]
        self.col = 10
        self.row = 16
        self.x, self.y = cell_center(self.col, self.row)
        self.x = float(self.x)
        self.y = float(self.y)
        self.timer = 600  # 10 seconds at 60 FPS
        self.active = True

    def update(self):
        if not self.active:
            return
        self.timer -= 1
        if self.timer <= 0:
            self.active = False

    def check_eaten(self, pacman):
        if not self.active:
            return False
        if math.hypot(pacman.x - self.x, pacman.y - self.y) < CELL * 0.8:
            self.active = False
            return True
        return False

    def draw(self, screen):
        if not self.active:
            return
        ix, iy = int(self.x), int(self.y)
        r = CELL // 2 - 2
        if self.timer < 120 and (self.timer // 10) % 2 == 0:
            return
        pygame.draw.circle(screen, self.color, (ix, iy), r - 2)
        pygame.draw.circle(screen, WHITE, (ix - 2, iy - 3), 2)
        pygame.draw.line(screen, (0, 180, 0), (ix, iy - r + 2), (ix + 3, iy - r - 2), 2)


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Pac-Man")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20, bold=True)
        self.big_font = pygame.font.SysFont("arial", 36, bold=True)
        self.title_font = pygame.font.SysFont("arial", 48, bold=True)
        self.small_font = pygame.font.SysFont("arial", 14, bold=True)
        self.popup_font = pygame.font.SysFont("arial", 16, bold=True)
        self.sfx = SoundFX()
        self.state = "start"
        self.level = 1
        self.reset()

    def _ghost_speed(self):
        return BASE_GHOST_SPEED + min(self.level * 0.15, 1.2)

    def _scare_duration(self):
        return max(360 - self.level * 30, 120)

    def _fruit_type(self):
        return min(self.level - 1, len(FRUIT_TYPES) - 1)

    def reset(self):
        self.maze = [row[:] for row in MAZE_TEMPLATE]
        self.pacman = PacMan(10, 16)
        self.ghosts = [
            Ghost(10, 9, 0),
            Ghost(9, 8, 1),
            Ghost(11, 8, 2),
            Ghost(10, 8, 3),
        ]
        self.score = 0
        self.lives = 3
        self.level = 1
        self.dots_left = sum(1 for r in self.maze for c in r if c in (0, 3))
        self.death_frame = 0
        self.ghost_eat_combo = 0
        self.ready_timer = 120
        self.popups = []
        self.fruit = None
        self.fruit_dots_counter = 0
        self.levelup_timer = 0

    def _next_level(self):
        self.level += 1
        if self.level > 10:
            self.state = "won"
            self.sfx.play('level_up')
            return
        self.maze = [row[:] for row in MAZE_TEMPLATE]
        self.pacman.reset()
        for g in self.ghosts:
            g.reset()
        self.dots_left = sum(1 for r in self.maze for c in r if c in (0, 3))
        self.ghost_eat_combo = 0
        self.ready_timer = 120
        self.popups = []
        self.fruit = None
        self.fruit_dots_counter = 0
        self.state = "levelup"
        self.levelup_timer = 180
        self.sfx.play('level_up')

    def _soft_reset(self):
        self.pacman.reset()
        for g in self.ghosts:
            g.reset()
        self.ghost_eat_combo = 0
        self.ready_timer = 120
        self.popups = []
        self.fruit = None
        self.fruit_dots_counter = 0

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.state == "start":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "playing"
                        self.sfx.play('start')
                    continue

                if self.state in ("won", "gameover"):
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.reset()
                        self.state = "playing"
                        self.sfx.play('start')
                    continue

                if self.state == "paused":
                    if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                        self.state = "playing"
                    continue

                if self.state == "playing":
                    if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                        self.state = "paused"
                        continue
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.pacman.set_direction(0, -1)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.pacman.set_direction(0, 1)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.pacman.set_direction(-1, 0)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.pacman.set_direction(1, 0)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self):
        # update popups regardless of state
        for p in self.popups:
            p.update()
        self.popups = [p for p in self.popups if p.active]

        if self.state == "dying":
            self.death_frame += 1
            if self.death_frame >= DEATH_ANIM_FRAMES:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "gameover"
                else:
                    self._soft_reset()
                    self.state = "playing"
            return

        if self.state == "levelup":
            self.levelup_timer -= 1
            if self.levelup_timer <= 0:
                self.state = "playing"
            return

        if self.state == "playing":
            if self.ready_timer > 0:
                self.ready_timer -= 1
                return

            self.pacman.update(self.maze)

            # eat dots / power pellets
            c, r = self.pacman.col, self.pacman.row
            if 0 <= r < ROWS and 0 <= c < COLS:
                cell = self.maze[r][c]
                if cell == 0:
                    self.maze[r][c] = 2
                    self.score += 10
                    self.dots_left -= 1
                    self.fruit_dots_counter += 1
                    self.sfx.play('chomp')
                elif cell == 3:
                    self.maze[r][c] = 2
                    self.score += 50
                    self.dots_left -= 1
                    self.fruit_dots_counter += 1
                    self.ghost_eat_combo = 0
                    scare = self._scare_duration()
                    for g in self.ghosts:
                        if not g.eaten:
                            g.scared = True
                            g.scared_timer = scare
                    self.sfx.play('power')

            # spawn fruit after eating enough dots
            if self.fruit is None and self.fruit_dots_counter >= 40:
                self.fruit_dots_counter = 0
                self.fruit = Fruit(self._fruit_type())

            # update fruit
            if self.fruit is not None:
                self.fruit.update()
                if self.fruit.check_eaten(self.pacman):
                    self.score += self.fruit.points
                    self.popups.append(ScorePopup(self.fruit.x, self.fruit.y, self.fruit.points, self.fruit.color))
                    self.sfx.play('fruit')
                    self.fruit = None
                elif self.fruit is not None and not self.fruit.active:
                    self.fruit = None

            # check win
            if self.dots_left <= 0:
                self._next_level()
                return

            # update ghosts
            blinky = self.ghosts[0]
            gs = self._ghost_speed()
            for g in self.ghosts:
                g.update(self.maze, self.pacman, blinky, gs)

            # collision with ghosts
            for g in self.ghosts:
                if g.eaten:
                    continue
                if math.hypot(self.pacman.x - g.x, self.pacman.y - g.y) < CELL * 0.7:
                    if g.scared:
                        g.eaten = True
                        g.respawn_timer = GHOST_RESPAWN_TIME
                        idx = min(self.ghost_eat_combo, len(GHOST_EAT_SCORES) - 1)
                        pts = GHOST_EAT_SCORES[idx]
                        self.score += pts
                        self.popups.append(ScorePopup(g.x, g.y - 10, pts, CYAN))
                        self.ghost_eat_combo += 1
                        self.sfx.play('eat_ghost')
                    else:
                        self.state = "dying"
                        self.death_frame = 0
                        self.pacman.alive = False
                        self.sfx.play('death')

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self):
        self.screen.fill(BLACK)

        if self.state == "start":
            self._draw_start_screen()
            pygame.display.flip()
            return

        self._draw_maze()
        self._draw_dots()

        # draw fruit
        if self.fruit is not None:
            self.fruit.draw(self.screen)

        for g in self.ghosts:
            g.draw(self.screen)

        if self.state == "dying":
            self.pacman.draw(self.screen, death_frame=self.death_frame)
        else:
            self.pacman.draw(self.screen)

        # draw score popups
        for p in self.popups:
            p.draw(self.screen, self.popup_font)

        self._draw_hud()

        if self.state == "paused":
            self._draw_overlay("PAUSED", WHITE, "Press P or ESC to resume")
        elif self.state == "won":
            self._draw_overlay("YOU WIN!", YELLOW, "Press ENTER or SPACE to restart")
        elif self.state == "gameover":
            self._draw_overlay("GAME OVER", RED, "Press ENTER or SPACE to restart")
        elif self.state == "levelup":
            self._draw_levelup_screen()
        elif self.ready_timer > 0:
            self._draw_overlay("READY!", YELLOW, "")

        pygame.display.flip()

    def _draw_start_screen(self):
        t = pygame.time.get_ticks()
        mouth = abs(math.sin(t * 0.005)) * 40 + 5
        cx, cy = WIDTH // 2, HEIGHT // 2 - 80
        r = 40
        pygame.draw.circle(self.screen, YELLOW, (cx, cy), r)
        pygame.draw.polygon(self.screen, BLACK, [
            (cx, cy),
            (cx + int(r * math.cos(math.radians(-mouth))),
             cy - int(r * math.sin(math.radians(-mouth)))),
            (cx + int(r * math.cos(math.radians(mouth))),
             cy - int(r * math.sin(math.radians(mouth)))),
        ])

        title = self.title_font.render("PAC-MAN", True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))

        # draw sample ghosts with names
        ghost_names = ["Blinky", "Pinky", "Inky", "Clyde"]
        gx = WIDTH // 2 - 90
        for i, color in enumerate(GHOST_COLORS):
            gr = 12
            gix = gx + i * 50
            giy = HEIGHT // 2 + 30
            pygame.draw.circle(self.screen, color, (gix, giy - 3), gr)
            pygame.draw.rect(self.screen, color, (gix - gr, giy - 3, gr * 2, gr))
            name_surf = self.small_font.render(ghost_names[i], True, color)
            self.screen.blit(name_surf, (gix - name_surf.get_width() // 2, giy + 12))

        if (t // 500) % 2 == 0:
            hint = self.font.render("Press ENTER or SPACE to start", True, WHITE)
            self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80)))

        ctrl = self.font.render("Arrow Keys / WASD to move   P / ESC to pause", True, (150, 150, 150))
        self.screen.blit(ctrl, ctrl.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120)))

    def _draw_maze(self):
        for row in range(ROWS):
            for col in range(COLS):
                if self.maze[row][col] == 1:
                    x, y = col * CELL, row * CELL + 40
                    pygame.draw.rect(self.screen, BLUE, (x, y, CELL, CELL))
                    pygame.draw.rect(self.screen, (15, 15, 100),
                                     (x + 2, y + 2, CELL - 4, CELL - 4), 1)

    def _draw_dots(self):
        t = pygame.time.get_ticks() / 200.0
        for row in range(ROWS):
            for col in range(COLS):
                cx, cy = cell_center(col, row)
                if self.maze[row][col] == 0:
                    pygame.draw.circle(self.screen, DOT_CLR, (cx, cy), 3)
                elif self.maze[row][col] == 3:
                    radius = int(5 + 3 * math.sin(t + col * 0.7 + row * 1.3))
                    pygame.draw.circle(self.screen, DOT_CLR, (cx, cy), max(radius, 2))

    def _draw_hud(self):
        txt = self.font.render(f"SCORE: {self.score}", True, WHITE)
        self.screen.blit(txt, (10, 8))
        level_txt = self.font.render(f"LV {self.level}", True, YELLOW)
        self.screen.blit(level_txt, (WIDTH // 2 - level_txt.get_width() // 2, 8))
        for i in range(self.lives):
            pygame.draw.circle(self.screen, YELLOW, (WIDTH - 30 - i * 28, 20), 10)

    def _draw_overlay(self, message, color, hint_text):
        surf = self.big_font.render(message, True, color)
        rect = surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        bg = pygame.Surface((rect.width + 40, rect.height + 20), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.screen.blit(bg, (rect.x - 20, rect.y - 10))
        self.screen.blit(surf, rect)
        if hint_text:
            hint = self.font.render(hint_text, True, WHITE)
            self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))

    def _draw_levelup_screen(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        lvl_txt = self.big_font.render(f"LEVEL {self.level}", True, YELLOW)
        self.screen.blit(lvl_txt, lvl_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))

        if (self.levelup_timer // 20) % 2 == 0:
            ready_txt = self.big_font.render("READY!", True, WHITE)
            self.screen.blit(ready_txt, ready_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))

        gs = self._ghost_speed()
        sd = self._scare_duration()
        info = self.small_font.render(
            f"Ghost Speed: {gs:.1f}   Scare Time: {sd / 60:.1f}s", True, DOT_CLR
        )
        self.screen.blit(info, info.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60)))

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
