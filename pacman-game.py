#!/usr/bin/env python3
"""Pac-Man game implemented with pygame."""

import pygame
import sys
import math
import random
from collections import deque

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CELL = 28
COLS = 21
ROWS = 23
WIDTH = CELL * COLS
HEIGHT = CELL * ROWS + 40  # extra space for HUD

FPS = 60
PAC_SPEED = 2
GHOST_SPEED = 1.8

BLACK  = (0, 0, 0)
YELLOW = (255, 255, 0)
WHITE  = (255, 255, 255)
BLUE   = (33, 33, 222)
RED    = (255, 0, 0)
PINK   = (255, 184, 255)
CYAN   = (0, 255, 255)
ORANGE = (255, 184, 82)
DOT_CLR = (255, 183, 174)

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cell_center(col, row):
    return col * CELL + CELL // 2, row * CELL + CELL // 2 + 40


def pixel_to_cell(x, y):
    return (x - CELL // 2) // CELL, (y - 40 - CELL // 2) // CELL


def is_passable(maze, col, row):
    if row < 0 or row >= ROWS:
        return False
    c = col % COLS  # wrap horizontally for tunnel
    return maze[row][c] != 1


# ---------------------------------------------------------------------------
# Pac-Man
# ---------------------------------------------------------------------------

class PacMan:
    def __init__(self, col, row):
        self.sx, self.sy = cell_center(col, row)
        self.x, self.y = float(self.sx), float(self.sy)
        self.col, self.row = col, row
        self.direction = (0, 0)
        self.next_dir = (0, 0)
        self.mouth_angle = 0
        self.mouth_open = True
        self.alive = True

    def reset(self):
        self.x, self.y = float(self.sx), float(self.sy)
        self.direction = (0, 0)
        self.next_dir = (0, 0)
        self.alive = True

    def set_direction(self, dx, dy):
        self.next_dir = (dx, dy)

    def update(self, maze):
        if not self.alive:
            return

        # animate mouth
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

        # try switching to queued direction at cell center
        if dist_to_center < PAC_SPEED + 0.5 and self.next_dir != (0, 0):
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
        if not is_passable(maze, nc, nr) and dist_to_center < PAC_SPEED + 0.5:
            self.x, self.y = float(cx), float(cy)
            self.direction = (0, 0)
            return

        self.x += dx * PAC_SPEED
        self.y += dy * PAC_SPEED

        # wrap tunnel
        if self.x < 0:
            self.x += COLS * CELL
        elif self.x >= COLS * CELL:
            self.x -= COLS * CELL

        self.col, self.row = pixel_to_cell(self.x, self.y)

    def draw(self, screen):
        if not self.alive:
            return
        r = CELL // 2 - 2
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
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), r)
        pygame.draw.polygon(screen, BLACK, [
            (int(self.x), int(self.y)),
            (int(self.x + r * math.cos(math.radians(start - mouth))),
             int(self.y - r * math.sin(math.radians(start - mouth)))),
            (int(self.x + r * math.cos(math.radians(start + mouth))),
             int(self.y - r * math.sin(math.radians(start + mouth)))),
        ])


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
        self.direction = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.scared = False
        self.scared_timer = 0
        self.eaten = False

    def reset(self):
        self.x, self.y = float(self.sx), float(self.sy)
        self.col, self.row = self.start_col, self.start_row
        self.direction = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.scared = False
        self.scared_timer = 0
        self.eaten = False

    def update(self, maze, pacman):
        if self.eaten:
            return

        if self.scared:
            self.scared_timer -= 1
            if self.scared_timer <= 0:
                self.scared = False

        speed = GHOST_SPEED * 0.6 if self.scared else GHOST_SPEED
        cx, cy = cell_center(self.col, self.row)
        dist_to_center = math.hypot(self.x - cx, self.y - cy)

        if dist_to_center < speed + 0.5:
            self.x, self.y = float(cx), float(cy)
            self._choose_direction(maze, pacman)

        dx, dy = self.direction
        nc = self.col + dx
        nr = self.row + dy
        if not is_passable(maze, nc, nr) and dist_to_center < speed + 0.5:
            self._choose_direction(maze, pacman)
            dx, dy = self.direction

        self.x += dx * speed
        self.y += dy * speed

        if self.x < 0:
            self.x += COLS * CELL
        elif self.x >= COLS * CELL:
            self.x -= COLS * CELL

        self.col, self.row = pixel_to_cell(self.x, self.y)

    def _choose_direction(self, maze, pacman):
        dx, dy = self.direction
        opposite = (-dx, -dy)
        options = []
        for d in [(1,0),(-1,0),(0,1),(0,-1)]:
            if d == opposite:
                continue
            nc = self.col + d[0]
            nr = self.row + d[1]
            if is_passable(maze, nc, nr):
                options.append(d)

        if not options:
            if is_passable(maze, self.col + opposite[0], self.row + opposite[1]):
                options = [opposite]
            else:
                return

        if self.scared:
            self.direction = random.choice(options)
            return

        # chase: pick direction that minimises distance to pac-man
        best = options[0]
        best_dist = float('inf')
        for d in options:
            nc = self.col + d[0]
            nr = self.row + d[1]
            nccx, nccy = cell_center(nc, nr)
            dist = math.hypot(nccx - pacman.x, nccy - pacman.y)
            # add small random factor for variety
            dist += random.random() * 20
            if dist < best_dist:
                best_dist = dist
                best = d
        self.direction = best

    def draw(self, screen):
        if self.eaten:
            return
        r = CELL // 2 - 2
        ix, iy = int(self.x), int(self.y)

        if self.scared:
            color = (33, 33, 222) if self.scared_timer > 90 or self.scared_timer % 12 < 6 else WHITE
        else:
            color = self.color

        # body
        pygame.draw.circle(screen, color, (ix, iy - 3), r)
        pygame.draw.rect(screen, color, (ix - r, iy - 3, r * 2, r))
        # wavy bottom
        for i in range(3):
            bx = ix - r + i * (r * 2 // 3) + r * 2 // 6
            pygame.draw.circle(screen, BLACK, (bx, iy - 3 + r), r // 4)

        # eyes
        if not self.scared:
            for ex in (ix - r // 3, ix + r // 3):
                pygame.draw.circle(screen, WHITE, (ex, iy - 5), r // 3)
                ddx, ddy = self.direction
                pygame.draw.circle(screen, BLUE, (ex + ddx * 2, iy - 5 + ddy * 2), r // 5)
        else:
            # scared face
            for ex in (ix - r // 3, ix + r // 3):
                pygame.draw.circle(screen, WHITE, (ex, iy - 5), r // 4)


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Pac-Man")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20, bold=True)
        self.big_font = pygame.font.SysFont("arial", 36, bold=True)
        self.reset()

    def reset(self):
        self.maze = [row[:] for row in MAZE_TEMPLATE]
        self.pacman = PacMan(10, 16)
        self.ghosts = [
            Ghost(10, 9, 0),
            Ghost(9, 9, 1),
            Ghost(11, 9, 2),
            Ghost(10, 7, 3),
        ]
        self.score = 0
        self.lives = 3
        self.dots_left = sum(1 for r in self.maze for c in r if c in (0, 3))
        self.state = "playing"  # playing | dying | won | gameover
        self.death_timer = 0
        self.ghost_eat_combo = 0

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.state in ("won", "gameover"):
                    if event.key == pygame.K_RETURN:
                        self.reset()
                    continue
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.pacman.set_direction(0, -1)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.pacman.set_direction(0, 1)
                elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    self.pacman.set_direction(-1, 0)
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    self.pacman.set_direction(1, 0)

    def update(self):
        if self.state == "dying":
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "gameover"
                else:
                    self.pacman.reset()
                    for g in self.ghosts:
                        g.reset()
                    self.state = "playing"
            return

        if self.state != "playing":
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
            elif cell == 3:
                self.maze[r][c] = 2
                self.score += 50
                self.dots_left -= 1
                self.ghost_eat_combo = 0
                for g in self.ghosts:
                    if not g.eaten:
                        g.scared = True
                        g.scared_timer = 360  # ~6 seconds

        if self.dots_left <= 0:
            self.state = "won"
            return

        for g in self.ghosts:
            g.update(self.maze, self.pacman)

        # collision with ghosts
        for g in self.ghosts:
            if g.eaten:
                continue
            if math.hypot(self.pacman.x - g.x, self.pacman.y - g.y) < CELL * 0.7:
                if g.scared:
                    g.eaten = True
                    self.ghost_eat_combo += 1
                    self.score += 200 * self.ghost_eat_combo
                else:
                    self.state = "dying"
                    self.death_timer = 60
                    self.pacman.alive = False

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self):
        self.screen.fill(BLACK)
        self._draw_maze()
        self._draw_dots()
        for g in self.ghosts:
            g.draw(self.screen)
        self.pacman.draw(self.screen)
        self._draw_hud()

        if self.state == "won":
            self._draw_overlay("YOU WIN!", YELLOW)
        elif self.state == "gameover":
            self._draw_overlay("GAME OVER", RED)

        pygame.display.flip()

    def _draw_maze(self):
        for row in range(ROWS):
            for col in range(COLS):
                if self.maze[row][col] == 1:
                    x, y = col * CELL, row * CELL + 40
                    pygame.draw.rect(self.screen, BLUE, (x, y, CELL, CELL))
                    # inner darkening for style
                    pygame.draw.rect(self.screen, (15, 15, 100),
                                     (x + 2, y + 2, CELL - 4, CELL - 4), 1)

    def _draw_dots(self):
        for row in range(ROWS):
            for col in range(COLS):
                cx, cy = cell_center(col, row)
                if self.maze[row][col] == 0:
                    pygame.draw.circle(self.screen, DOT_CLR, (cx, cy), 3)
                elif self.maze[row][col] == 3:
                    pygame.draw.circle(self.screen, DOT_CLR, (cx, cy), 7)

    def _draw_hud(self):
        # score
        txt = self.font.render(f"SCORE: {self.score}", True, WHITE)
        self.screen.blit(txt, (10, 8))
        # lives
        for i in range(self.lives):
            pygame.draw.circle(self.screen, YELLOW, (WIDTH - 30 - i * 28, 20), 10)
        # dots left
        txt2 = self.font.render(f"Dots: {self.dots_left}", True, DOT_CLR)
        self.screen.blit(txt2, (WIDTH // 2 - txt2.get_width() // 2, 8))

    def _draw_overlay(self, message, color):
        surf = self.big_font.render(message, True, color)
        rect = surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        bg = pygame.Surface((rect.width + 40, rect.height + 20), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.screen.blit(bg, (rect.x - 20, rect.y - 10))
        self.screen.blit(surf, rect)
        hint = self.font.render("Press ENTER to restart", True, WHITE)
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))

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
