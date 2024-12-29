import pygame
import sys
import random
import time
import math
from concurrent.futures import ThreadPoolExecutor

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
use_ai = True  # Set to False to play manually
num_threads = 8  # Number of threads for MCTS

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
pygame.display.set_caption("2048 but with a twist")
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

def display_game_over(score):
    screen.fill(BACKGROUND_COLOR)
    text = font.render(f"Game Over! Score: {score}", True, TEXT_COLOR)
    text_rect = text.get_rect(center=(SCREEN_SIZE // 2, SCREEN_SIZE // 2))
    screen.blit(text, text_rect)
    pygame.display.flip()
    wait_for_key(pygame.K_RETURN)

def wait_for_key(key):
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == key:
                return

class MCTSNode:
    def __init__(self, grid, parent=None, move=None):
        self.grid = grid
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.total_score = 0

    def expand(self):
        moves = [(move_left, "left"), (move_right, "right"), (move_up, "up"), (move_down, "down")]
        for move_func, move_name in moves:
            new_grid = move_func(self.grid)
            if new_grid != self.grid:
                child_node = MCTSNode(new_grid, parent=self, move=move_func)
                self.children.append(child_node)

    def is_fully_expanded(self):
        return len(self.children) > 0

    def best_child(self, exploration_weight=1.4):
        return max(
            self.children,
            key=lambda child: child.total_score / (child.visits + 1) + exploration_weight * math.sqrt(math.log(self.visits + 1) / (child.visits + 1))
        )

def mcts_worker(root, iterations):
    for _ in range(iterations):
        node = root
        # Selection
        while node.is_fully_expanded() and node.children:
            node = node.best_child()
        # Expansion
        if not node.is_fully_expanded():
            node.expand()
            if node.children:
                node = random.choice(node.children)
        # Simulation
        score = simulate(node.grid)
        # Backpropagation
        while node is not None:
            node.visits += 1
            node.total_score += score
            node = node.parent

def mcts(root, iterations=1000):
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(mcts_worker, root, iterations // num_threads) for _ in range(num_threads)]
        for future in futures:
            future.result()

    return root.best_child(exploration_weight=0).move

def simulate(grid):
    simulation_grid = [row[:] for row in grid]
    while not is_game_over(simulation_grid):
        moves = [move_left, move_right, move_up, move_down]
        random_move = random.choice(moves)
        new_grid = random_move(simulation_grid)
        if new_grid != simulation_grid:
            add_new_tile(new_grid)
            simulation_grid = new_grid
    return calculate_score(simulation_grid)

def ai_move(grid):
    root = MCTSNode(grid)
    root.expand()
    best_move = mcts(root)
    return best_move

def main():
    global use_ai
    grid = create_grid()
    clock = pygame.time.Clock()
    while True:
        if use_ai:
            best_move = ai_move(grid)
            if best_move:
                grid = best_move(grid)
                add_new_tile(grid)
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
                        grid = move_left(grid)
                    elif event.key == pygame.K_RIGHT:
                        grid = move_right(grid)
                    elif event.key == pygame.K_UP:
                        grid = move_up(grid)
                    elif event.key == pygame.K_DOWN:
                        grid = move_down(grid)
                    add_new_tile(grid)
                    grid = check_and_expand(grid)
                    if is_game_over(grid):
                        display_game_over(calculate_score(grid))
                        return
        draw_grid(grid)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
