import pygame
import sys
import math
import random
import numpy as np
import pygame.gfxdraw

# Detect if the game is running in debug mode from VSCode
import os

DEBUG = "TERM_PROGRAM" in os.environ.keys() and os.environ["TERM_PROGRAM"] == "vscode"

# Initialize Pygame and its mixer
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Set up the display
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Tower Defense with Enemy Spawning")

# Colors
BACKGROUND = (10, 10, 30)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
NEON_PINK = (255, 20, 147)
NEON_CYAN = (0, 255, 255)
NEON_GREEN = (57, 255, 20)

# Waypoints for the enemy path
waypoints = [(50, 50), (750, 50), (750, 550), (50, 550), (50, 300), (400, 300)]

# New constants for grid-based placement
GRID_SIZE = 40
TOWER_COST = 100

# Constants for UI
UI_HEIGHT = 60
UI_COLOR = (50, 50, 50)
TEXT_COLOR = (255, 255, 255)

# Adjust the screen size to accommodate the UI panel
width, height = 800, 600 + UI_HEIGHT
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Tower Defense Game")


# Game state
class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.resources = 500
        self.hit_points = 20
        self.game_over = False
        self.enemies_spawned = 0
        self.min_spawn_delay = 50
        self.max_spawn_delay = 180
        self.acceleration_rate = 0.95
        self.current_enemy_type = 0
        self.enemies_in_current_group = 0


game_state = GameState()


def create_explosion_sound(duration_ms=300, frequency=440):
    sample_rate = 44100
    t = np.linspace(
        0, duration_ms / 1000.0, int(duration_ms * sample_rate / 1000.0), False
    )

    # Generate a decaying sine wave
    waveform = np.sin(2 * np.pi * frequency * t) * np.exp(-t * 10)

    # Add some noise for a more "explosive" sound
    noise = np.random.rand(len(waveform)) * 0.1
    waveform = waveform + noise

    # Normalize to 16-bit range
    waveform = np.int16(waveform / np.max(np.abs(waveform)) * 32767)

    # Convert to stereo
    stereo_waveform = np.column_stack((waveform, waveform))

    return pygame.sndarray.make_sound(stereo_waveform)


# Create the explosion sound
enemy_destroy_sound = create_explosion_sound()
enemy_destroy_sound.set_volume(0.1)


def draw_neon_shape(surface, color, center, size, shape="circle"):
    x, y = map(int, center)
    base_color = pygame.Color(*color[:3])
    glow_color = base_color.lerp(pygame.Color("white"), 0.5)
    glow_color.a = 100  # Increased opacity for better visibility

    glow_sizes = [size + 4, size + 2, size]  # Multiple layers for stronger glow effect

    for glow_size in glow_sizes:
        if shape == "circle":
            pygame.gfxdraw.filled_circle(surface, x, y, glow_size, glow_color)
            pygame.gfxdraw.aacircle(surface, x, y, glow_size, glow_color)
        elif shape == "square":
            pygame.gfxdraw.box(
                surface,
                (x - glow_size, y - glow_size, glow_size * 2, glow_size * 2),
                glow_color,
            )
            pygame.gfxdraw.rectangle(
                surface,
                (x - glow_size, y - glow_size, glow_size * 2, glow_size * 2),
                glow_color,
            )
        elif shape == "triangle":
            points = [
                (x, y - glow_size),
                (x - glow_size, y + glow_size),
                (x + glow_size, y + glow_size),
            ]
            pygame.gfxdraw.filled_polygon(surface, points, glow_color)
            pygame.gfxdraw.aapolygon(surface, points, glow_color)

    # Draw the main shape
    if shape == "circle":
        pygame.gfxdraw.filled_circle(surface, x, y, size, color)
        pygame.gfxdraw.aacircle(surface, x, y, size, color)
    elif shape == "square":
        pygame.gfxdraw.box(surface, (x - size, y - size, size * 2, size * 2), color)
        pygame.gfxdraw.rectangle(
            surface, (x - size, y - size, size * 2, size * 2), color
        )
    elif shape == "triangle":
        points = [(x, y - size), (x - size, y + size), (x + size, y + size)]
        pygame.gfxdraw.filled_polygon(surface, points, color)
        pygame.gfxdraw.aapolygon(surface, points, color)


class Enemy:
    def __init__(self, path):
        self.path = path
        self.path_index = 0
        self.x, self.y = self.path[0]
        self.size = 12  # Slightly increased size for better visibility
        self.color = (255, 0, 0, 255)  # Full opacity for the main shape
        self.health = 100
        self.max_health = 100
        self.speed = 2
        self.resource_reward = 10
        self.shape = "circle"  # Default shape
        self.glow_offset = 0
        self.glow_direction = 1

    def move(self):
        if self.path_index < len(self.path) - 1:
            target_x, target_y = self.path[self.path_index + 1]
            dx = target_x - self.x
            dy = target_y - self.y
            distance = math.sqrt(dx**2 + dy**2)

            if distance < self.speed:
                self.path_index += 1
            else:
                move_ratio = self.speed / distance
                self.x += dx * move_ratio
                self.y += dy * move_ratio

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            enemy_destroy_sound.play()
        return self.health <= 0

    def draw(self, surface):
        # Pulsing glow effect
        self.glow_offset += 0.2 * self.glow_direction
        if self.glow_offset > 2 or self.glow_offset < 0:
            self.glow_direction *= -1

        draw_neon_shape(
            surface,
            self.color,
            (self.x, self.y),
            self.size + int(self.glow_offset),
            self.shape,
        )

        # Health bar
        health_bar_width = 20  # Reduced width
        health_bar_height = 3  # Reduced height
        health_bar_y_offset = 15  # Increased offset to separate from sprite

        health_ratio = self.health / self.max_health

        # Background of health bar (red)
        pygame.draw.rect(
            surface,
            (255, 0, 0, 180),
            (
                self.x - health_bar_width // 2,
                self.y - self.size - health_bar_y_offset,
                health_bar_width,
                health_bar_height,
            ),
        )

        # Foreground of health bar (green)
        pygame.draw.rect(
            surface,
            (0, 255, 0, 180),
            (
                self.x - health_bar_width // 2,
                self.y - self.size - health_bar_y_offset,
                int(health_bar_width * health_ratio),
                health_bar_height,
            ),
        )

    def get_resource_reward(self):
        return self.resource_reward


class SquareEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.color = (255, 0, 0, 255)  # Red
        self.shape = "square"


class TriangleEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.color = (0, 255, 0, 255)  # Green
        self.speed = 3
        self.health = 75
        self.max_health = 75
        self.resource_reward = 15
        self.shape = "triangle"


class CircleEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.color = (0, 0, 255, 255)  # Blue
        self.health = 150
        self.max_health = 150
        self.speed = 1.5
        self.resource_reward = 20
        self.shape = "circle"


class Tower:
    def __init__(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.x = grid_x * GRID_SIZE + GRID_SIZE // 2
        self.y = grid_y * GRID_SIZE + GRID_SIZE // 2
        self.range = 150
        self.damage = 20
        self.color = NEON_CYAN
        self.size = 30
        self.target = None
        self.attack_cooldown = 45
        self.attack_timer = 0
        self.attack_duration = 5  # Number of frames to show the attack line
        self.current_attack_duration = 0

    def detect_enemies(self, enemies):
        self.target = None
        for enemy in enemies:
            distance = math.sqrt((self.x - enemy.x) ** 2 + (self.y - enemy.y) ** 2)
            if distance <= self.range:
                self.target = enemy
                break

    def attack(self, enemies, game_state):
        if self.target and self.attack_timer <= 0:
            if self.target.take_damage(self.damage):
                game_state.resources += self.target.get_resource_reward()
                enemies.remove(self.target)
            self.attack_timer = self.attack_cooldown
            self.current_attack_duration = self.attack_duration
        elif self.attack_timer > 0:
            self.attack_timer -= 1

        if self.current_attack_duration > 0:
            self.current_attack_duration -= 1

    def draw(self, surface):
        pygame.draw.rect(
            surface,
            self.color,
            (self.x - self.size // 2, self.y - self.size // 2, self.size, self.size),
            2,
        )
        pygame.draw.circle(
            surface, self.color, (int(self.x), int(self.y)), self.range, 1
        )

    def draw_attack(self, surface):
        if self.target and self.current_attack_duration > 0:
            pygame.draw.line(
                surface, NEON_CYAN, (self.x, self.y), (self.target.x, self.target.y), 2
            )


def is_valid_tower_location(grid_x, grid_y, path):
    # Check if the location is on the grid
    if (
        grid_x < 0
        or grid_x >= width // GRID_SIZE
        or grid_y < 0
        or grid_y >= (height - UI_HEIGHT) // GRID_SIZE
    ):
        return False

    # Check if the location is on the path
    # Note: We don't add UI_HEIGHT here because the path coordinates should already be adjusted
    tower_rect = pygame.Rect(
        grid_x * GRID_SIZE, grid_y * GRID_SIZE, GRID_SIZE, GRID_SIZE
    )
    for i in range(len(path) - 1):
        start = path[i]
        end = path[i + 1]
        if tower_rect.clipline(start, end):
            return False

    # Check if the location overlaps with existing towers
    for tower in towers:
        if tower.grid_x == grid_x and tower.grid_y == grid_y:
            return False

    return True


# Create lists to store enemies and towers
enemies = []
towers = []

# Enemy spawning variables
spawn_timer = 0
spawn_interval = 90  # Increased from 60 to 90 frames (slower spawning)

# Font initialization
pygame.font.init()
font = pygame.font.Font(None, 36)
large_font = pygame.font.Font(None, 72)


def draw_game_over_screen(screen):
    screen.fill(BACKGROUND)
    game_over_text = large_font.render("GAME OVER", True, RED)
    restart_text = font.render("Press R to Restart", True, WHITE)
    screen.blit(
        game_over_text, (width // 2 - game_over_text.get_width() // 2, height // 2 - 50)
    )
    screen.blit(
        restart_text, (width // 2 - restart_text.get_width() // 2, height // 2 + 50)
    )


def draw_ui(surface, game_state):
    # Draw UI background
    pygame.draw.rect(surface, UI_COLOR, (0, height - UI_HEIGHT, width, UI_HEIGHT))

    # Draw Resources
    resources_text = font.render(f"Resources: {game_state.resources}", True, TEXT_COLOR)
    surface.blit(resources_text, (20, height - UI_HEIGHT + 20))

    # Draw Hit Points
    hit_points_text = font.render(
        f"Hit Points: {game_state.hit_points}", True, TEXT_COLOR
    )
    surface.blit(
        hit_points_text,
        (width // 2 - hit_points_text.get_width() // 2, height - UI_HEIGHT + 20),
    )

    # Draw debug information when in debug mode
    if DEBUG:
        debug_text = font.render(
            f"Enemies spawned: {game_state.enemies_spawned}, Min Delay: {game_state.min_spawn_delay}, Max Delay: {game_state.max_spawn_delay}",
            True,
            YELLOW,
        )
        surface.blit(
            debug_text, (width - debug_text.get_width() - 20, height - UI_HEIGHT + 5)
        )


def spawn_enemy():
    enemy_types = [SquareEnemy, TriangleEnemy, CircleEnemy]
    new_enemy = enemy_types[game_state.current_enemy_type](waypoints.copy())
    enemies.append(new_enemy)

    game_state.enemies_spawned += 1
    game_state.enemies_in_current_group += 1

    if game_state.enemies_in_current_group == 5:
        game_state.current_enemy_type = (game_state.current_enemy_type + 1) % 3
        game_state.enemies_in_current_group = 0

    if game_state.enemies_spawned % 10 == 0:
        game_state.max_spawn_delay = max(
            game_state.min_spawn_delay,
            int(game_state.max_spawn_delay * game_state.acceleration_rate),
        )


def draw_path(surface, waypoints):
    if len(waypoints) > 1:
        pygame.draw.lines(surface, NEON_GREEN, False, waypoints, 2)


# Main game loop
clock = pygame.time.Clock()
running = True

while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and not game_state.game_over:
            if event.button == 1:  # Left mouse button
                mouse_x, mouse_y = pygame.mouse.get_pos()
                # Calculate grid position
                # Subtract UI_HEIGHT from mouse_y to account for the UI bar at the bottom
                grid_x = mouse_x // GRID_SIZE
                grid_y = mouse_y // GRID_SIZE
                if (
                    is_valid_tower_location(grid_x, grid_y, waypoints)
                    and game_state.resources >= TOWER_COST
                ):
                    # Create tower at the calculated grid position
                    towers.append(Tower(grid_x, grid_y))
                    game_state.resources -= TOWER_COST
        elif event.type == pygame.KEYDOWN and game_state.game_over:
            if event.key == pygame.K_r:
                # Reset the game
                game_state.reset()
                enemies.clear()
                towers.clear()

    if not game_state.game_over:
        # Spawn enemies
        spawn_timer += 1
        if spawn_timer >= random.randint(
            game_state.min_spawn_delay, game_state.max_spawn_delay
        ):
            spawn_enemy()
            spawn_timer = 0

        # Clear the screen
        screen.fill(BACKGROUND)

        # Draw grid
        for x in range(0, width, GRID_SIZE):
            pygame.draw.line(screen, (30, 30, 50), (x, 0), (x, height))
        for y in range(0, height, GRID_SIZE):
            pygame.draw.line(screen, (30, 30, 50), (0, y), (width, y))

        draw_path(screen, waypoints)

        # Update and draw enemies
        for enemy in enemies[:]:
            enemy.move()
            enemy.draw(screen)
            if enemy.path_index == len(enemy.path) - 1:
                enemies.remove(enemy)
                game_state.hit_points -= 1
                if game_state.hit_points <= 0:
                    game_state.game_over = True

        # Update and draw towers
        for tower in towers:
            tower.detect_enemies(enemies)
            tower.attack(enemies, game_state)
            tower.draw(screen)
            tower.draw_attack(screen)

        # Draw tower placement preview
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Calculate grid position
        # Subtract UI_HEIGHT from mouse_y to account for the UI bar at the bottom
        grid_x = mouse_x // GRID_SIZE
        grid_y = mouse_y // GRID_SIZE

        # Only draw preview if mouse is in the game area (not in UI bar)
        if 0 <= grid_y < (height - UI_HEIGHT) // GRID_SIZE:
            preview_color = (
                GREEN
                if is_valid_tower_location(grid_x, grid_y, waypoints)
                and game_state.resources >= TOWER_COST
                else RED
            )
            # Draw preview rectangle
            # Multiply grid coordinates by GRID_SIZE to get pixel coordinates
            # Do NOT add UI_HEIGHT here, as we've already accounted for it in grid_y calculation
            preview_rect = pygame.Rect(
                grid_x * GRID_SIZE, grid_y * GRID_SIZE, GRID_SIZE, GRID_SIZE
            )
            pygame.draw.rect(screen, preview_color, preview_rect, 2)

        # Draw UI
        draw_ui(screen, game_state)

    else:
        draw_game_over_screen(screen)

    # Update the display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(60)

# Quit Pygame
pygame.quit()
sys.exit()
