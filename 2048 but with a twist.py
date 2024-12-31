import pygame
import sys
import random
import time
import math

# Constants
SCREEN_SIZE = 1000
BACKGROUND_COLOR = (187, 173, 160)
TILE_COLORS = {
    0: (205, 193, 180),
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
    4096: (60, 58, 50),
    8192: (40, 40, 40),
    16384: (20, 20, 20),
    32768: (10, 10, 10),
    65536: (5, 5, 5)
}
TEXT_COLOR = (119, 110, 101)

# Variables
GRID_SIZE = 4
TILE_SIZE = SCREEN_SIZE // GRID_SIZE
FONT_SIZE = max(20, TILE_SIZE // 4)
next_upgrade = 2048
STEPS = 3  # Number of steps ahead for AI to simulate
use_ai = True

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
pygame.display.set_caption("2048 but with a Twist")
font = pygame.font.Font(None, FONT_SIZE)

def create_grid():
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    add_new_tile(grid)
    add_new_tile(grid)
    return grid

def add_new_tile(grid):
    empty_cells = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if grid[r][c] == 0]
    if empty_cells:
        r, c = random.choice(empty_cells)
        grid[r][c] = 2 if random.random() < 0.9 else 4

def draw_grid(grid):
    global TILE_SIZE, FONT_SIZE, font
    screen.fill(BACKGROUND_COLOR)
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            tile_value = grid[r][c]
            tile_color = TILE_COLORS.get(tile_value, (0, 0, 0))  # Default color for very high values
            pygame.draw.rect(screen, tile_color, (c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            if tile_value != 0:
                text = font.render(str(tile_value), True, TEXT_COLOR)
                text_rect = text.get_rect(center=(c * TILE_SIZE + TILE_SIZE // 2, r * TILE_SIZE + TILE_SIZE // 2))
                screen.blit(text, text_rect)

def slide_and_merge(row):
    new_row = [value for value in row if value != 0]
    merged_row = []
    skip = False
    for i in range(len(new_row)):
        if skip:
            skip = False
            continue
        if i + 1 < len(new_row) and new_row[i] == new_row[i + 1]:
            merged_row.append(new_row[i] * 2)
            skip = True
        else:
            merged_row.append(new_row[i])
    merged_row.extend([0] * (GRID_SIZE - len(merged_row)))
    return merged_row

def move_left(grid):
    return [slide_and_merge(row) for row in grid]

def move_right(grid):
    return [slide_and_merge(row[::-1])[::-1] for row in grid]

def move_up(grid):
    transposed = list(zip(*grid))
    moved = move_left([list(row) for row in transposed])
    return [list(row) for row in zip(*moved)]

def move_down(grid):
    transposed = list(zip(*grid))
    moved = move_right([list(row) for row in transposed])
    return [list(row) for row in zip(*moved)]

def is_game_over(grid):
    for row in grid:
        if 0 in row:
            return False
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE - 1):
            if grid[r][c] == grid[r][c + 1]:
                return False
    for c in range(GRID_SIZE):
        for r in range(GRID_SIZE - 1):
            if grid[r][c] == grid[r + 1][c]:
                return False
    return True

def calculate_score(grid):
    return sum(sum(row) for row in grid)

def expand_grid(grid):
    global GRID_SIZE, TILE_SIZE, FONT_SIZE, font
    GRID_SIZE += 1
    TILE_SIZE = SCREEN_SIZE // GRID_SIZE
    FONT_SIZE = max(20, TILE_SIZE // 4)
    font = pygame.font.Font(None, FONT_SIZE)

    new_grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    for r in range(len(grid)):
        for c in range(len(grid[r])):
            new_grid[r][c] = grid[r][c]
    add_new_tile(new_grid)
    return new_grid

def check_and_expand(grid):
    global next_upgrade
    for row in grid:
        for value in row:
            if value >= next_upgrade:
                next_upgrade *= 2
                return expand_grid(grid)
    return grid

def evaluate_grid(grid):
    """
    Évalue une grille en prenant en compte :
    - le nombre de cases vides,
    - la plus grande valeur,
    - le regroupement des nombres identiques (ou proches).
    """
    # Pondérations
    empty_cell_weight = 5000
    max_tile_weight = 10
    grouping_weight = 200

    # Nombre de cases vides
    empty_cells = sum(1 for row in grid for cell in row if cell == 0)

    # Plus grande valeur
    max_tile = max(max(row) for row in grid)

    # Regroupement des nombres proches (fusion possible)
    def calculate_grouping_score(grid):
        score = 0
        for r in range(len(grid)):
            for c in range(len(grid[0])):
                if grid[r][c] == 0:
                    continue
                # Vérifie les voisins (droite et bas uniquement pour éviter les doublons)
                if c + 1 < len(grid) and abs(grid[r][c] - grid[r][c + 1]) <= grid[r][c] // 2:
                    score += 1
                if r + 1 < len(grid) and abs(grid[r][c] - grid[r + 1][c]) <= grid[r][c] // 2:
                    score += 1
        return score

    grouping_score = calculate_grouping_score(grid)

    # Évaluation finale
    score = (empty_cells * empty_cell_weight +
             max_tile * max_tile_weight +
             grouping_score * grouping_weight)

    return score



def simulate_move(grid, move_func):
    new_grid = move_func(grid)
    if new_grid != grid:
        add_new_tile(new_grid)
    return new_grid

def ai_play(grid, steps):
    moves = [move_left, move_right, move_up, move_down]
    best_move = None
    best_score = -float('inf')

    for move_func in moves:
        simulation_grid = simulate_move(grid, move_func)
        if simulation_grid == grid:
            continue

        score = simulate_future(simulation_grid, steps - 1)
        if score > best_score:
            best_score = score
            best_move = move_func

    return best_move

def simulate_future(grid, steps):
    if steps == 0 or is_game_over(grid):
        return evaluate_grid(grid)

    moves = [move_left, move_right, move_up, move_down]
    scores = []
    for move_func in moves:
        simulation_grid = simulate_move(grid, move_func)
        if simulation_grid != grid:
            scores.append(simulate_future(simulation_grid, steps - 1))

    return max(scores) if scores else evaluate_grid(grid)

def display_game_over(score):
    screen.fill(BACKGROUND_COLOR)
    text = font.render(f"Game Over! Score: {score}", True, TEXT_COLOR)
    text_rect = text.get_rect(center=(SCREEN_SIZE // 2, SCREEN_SIZE // 2))
    screen.blit(text, text_rect)
    pygame.display.flip()
    pygame.time.wait(3000)

def main():
    global use_ai
    grid = create_grid()
    clock = pygame.time.Clock()

    while True:
        if use_ai:
            best_move = ai_play(grid, STEPS)
            if best_move:
                grid = simulate_move(grid, best_move)
                grid = check_and_expand(grid)
            if is_game_over(grid):
                display_game_over(calculate_score(grid))
                return
        else:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        grid = simulate_move(grid, move_left)
                    elif event.key == pygame.K_RIGHT:
                        grid = simulate_move(grid, move_right)
                    elif event.key == pygame.K_UP:
                        grid = simulate_move(grid, move_up)
                    elif event.key == pygame.K_DOWN:
                        grid = simulate_move(grid, move_down)
                    grid = check_and_expand(grid)
                    if is_game_over(grid):
                        display_game_over(calculate_score(grid))
                        return

        draw_grid(grid)
        pygame.display.flip()
        clock.tick(0)

if __name__ == "__main__":
    main()
