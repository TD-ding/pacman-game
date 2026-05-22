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
ROWS = 23
WIDTH = CELL * COLS
HEIGHT = CELL * ROWS + 40  # extra space for HUD

FPS = 60
PAC_SPEED = 2
GHOST_SPEED = 1.8
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
        # chomp – short blip when eating a dot
        self.sounds['chomp'] = pygame.mixer.Sound(buffer=self._square(600, 0.05, 0.2))
        # power – two-note ascending when eating a power pellet
        buf = self._square(400, 0.08) + self._square(800, 0.08)
        self.sounds['power'] = pygame.mixer.Sound(buffer=buf)
        # death – descending tones
        buf = self._square(500, 0.1) + self._square(400, 0.1) + self._square(300, 0.1) + self._square(200, 0.15)
        self.sounds['death'] = pygame.mixer.Sound(buffer=buf)
        # start – four-note ascending jingle
        buf = self._square(523, 0.08) + self._square(659, 0.08) + self._square(784, 0.08) + self._square(1047, 0.12)
        self.sounds['start'] = pygame.mixer.Sound(buffer=buf)

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
        # clamp col into valid range after wrap
        if self.col < 0:
            self.col += COLS
        elif self.col >= COLS:
            self.col -= COLS

    def draw(self, screen, death_frame=0):
        r = CELL // 2 - 2
        ix, iy = int(self.x), int(self.y)

        if not self.alive:
            # death animation: pac-man shrinks into nothing
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

    def update(self, maze, pacman):
        # handle respawn countdown
        if self.eaten:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.respawn()
            return

        if self.scared:
            self.scared_timer -= 1
            if self.scared_timer <= 0:
                self.scared = False

        speed = GHOST_SPEED * 0.6 if self.scared else GHOST_SPEED

        # snap to cell center and choose direction when close enough
        cx, cy = cell_center(self.col, self.row)
        dist_to_center = math.hypot(self.x - cx, self.y - cy)

        if dist_to_center < speed + 0.5:
            self.x, self.y = float(cx), float(cy)
            self.col, self.row = pixel_to_cell(self.x, self.y)
            if self.col < 0:
                self.col += COLS
            elif self.col >= COLS:
                self.col -= COLS
            self._choose_direction(maze, pacman)

        # validate current direction before moving
        dx, dy = self.direction
        if dx == 0 and dy == 0:
            self._choose_direction(maze, pacman)
            dx, dy = self.direction
            if dx == 0 and dy == 0:
                return

        nc = self.col + dx
        nr = self.row + dy
        if not is_passable(maze, nc, nr):
            # re-snap and re-choose
            self.x, self.y = float(cx), float(cy)
            self._choose_direction(maze, pacman)
            dx, dy = self.direction
            if dx == 0 and dy == 0:
                return
            nc = self.col + dx
            nr = self.row + dy
            if not is_passable(maze, nc, nr):
                return  # truly stuck, wait

        self.x += dx * speed
        self.y += dy * speed
        self.x = wrap_x(self.x)

        self.col, self.row = pixel_to_cell(self.x, self.y)
        if self.col < 0:
            self.col += COLS
        elif self.col >= COLS:
            self.col -= COLS

    def _choose_direction(self, maze, pacman):
        dx, dy = self.direction
        opposite = (-dx, -dy) if (dx, dy) != (0, 0) else None
        options = []
        for d in [(1,0),(-1,0),(0,1),(0,-1)]:
            if d == opposite:
                continue
            nc = self.col + d[0]
            nr = self.row + d[1]
            if is_passable(maze, nc, nr):
                options.append(d)

        if not options:
            if opposite and is_passable(maze, self.col + opposite[0], self.row + opposite[1]):
                options = [opposite]
            else:
                # try all 4 directions as last resort
                for d in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nc = self.col + d[0]
                    nr = self.row + d[1]
                    if is_passable(maze, nc, nr):
                        options.append(d)
                if not options:
                    return

        if self.scared:
            self.direction = random.choice(options)
            return

        best = options[0]
        best_dist = float('inf')
        for d in options:
            nc = self.col + d[0]
            nr = self.row + d[1]
            nccx, nccy = cell_center(nc, nr)
            dist = math.hypot(nccx - pacman.x, nccy - pacman.y)
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
        self.sfx = SoundFX()
        self.state = "start"  # start | playing | paused | dying | won | gameover
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
        self.death_frame = 0
        self.ghost_eat_combo = 0
        self.ready_timer = 120  # brief "READY!" countdown after death/respawn

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

    def update(self):
        if self.state == "dying":
            self.death_frame += 1
            if self.death_frame >= DEATH_ANIM_FRAMES:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "gameover"
                else:
                    self.pacman.reset()
                    for g in self.ghosts:
                        g.reset()
                    self.state = "playing"
                    self.ready_timer = 120
            return

        if self.state == "playing":
            if self.ready_timer > 0:
                self.ready_timer -= 1
                return

            self.pacman.update(self.maze)

            c, r = self.pacman.col, self.pacman.row
            if 0 <= r < ROWS and 0 <= c < COLS:
                cell = self.maze[r][c]
                if cell == 0:
                    self.maze[r][c] = 2
                    self.score += 10
                    self.dots_left -= 1
                    self.sfx.play('chomp')
                elif cell == 3:
                    self.maze[r][c] = 2
                    self.score += 50
                    self.dots_left -= 1
                    self.ghost_eat_combo = 0
                    for g in self.ghosts:
                        if not g.eaten:
                            g.scared = True
                            g.scared_timer = 360
                    self.sfx.play('power')

            if self.dots_left <= 0:
                self.state = "won"
                return

            for g in self.ghosts:
                g.update(self.maze, self.pacman)

            for g in self.ghosts:
                if g.eaten:
                    continue
                if math.hypot(self.pacman.x - g.x, self.pacman.y - g.y) < CELL * 0.7:
                    if g.scared:
                        g.eaten = True
                        g.respawn_timer = GHOST_RESPAWN_TIME
                        self.ghost_eat_combo += 1
                        self.score += 200 * self.ghost_eat_combo
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
        for g in self.ghosts:
            g.draw(self.screen)

        if self.state == "dying":
            self.pacman.draw(self.screen, death_frame=self.death_frame)
        else:
            self.pacman.draw(self.screen)

        self._draw_hud()

        if self.state == "paused":
            self._draw_overlay("PAUSED", WHITE, "Press P or ESC to resume")
        elif self.state == "won":
            self._draw_overlay("YOU WIN!", YELLOW, "Press ENTER or SPACE to restart")
        elif self.state == "gameover":
            self._draw_overlay("GAME OVER", RED, "Press ENTER or SPACE to restart")
        elif self.ready_timer > 0:
            self._draw_overlay("READY!", YELLOW, "")

        pygame.display.flip()

    def _draw_start_screen(self):
        # animated pac-man logo
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

        # draw sample ghosts
        gx = WIDTH // 2 - 70
        for i, color in enumerate(GHOST_COLORS):
            gr = 14
            gix = gx + i * 40
            giy = HEIGHT // 2 + 30
            pygame.draw.circle(self.screen, color, (gix, giy - 3), gr)
            pygame.draw.rect(self.screen, color, (gix - gr, giy - 3, gr * 2, gr))

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
        for i in range(self.lives):
            pygame.draw.circle(self.screen, YELLOW, (WIDTH - 30 - i * 28, 20), 10)
        txt2 = self.font.render(f"Dots: {self.dots_left}", True, DOT_CLR)
        self.screen.blit(txt2, (WIDTH // 2 - txt2.get_width() // 2, 8))

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
