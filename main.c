#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>
#include <string.h>

#define GRID_SIZE 4
#define EMPTY_CELL 0
#define START_TILES 2
#define PROBABILITY_4 0.1
#define STEPS 1

#ifdef AZERTY
#define MOVE_UP 'z'
#define MOVE_LEFT 'q'
#define MOVE_DOWN 's'
#define MOVE_RIGHT 'd'
#else
#define MOVE_UP 'w'
#define MOVE_LEFT 'a'
#define MOVE_DOWN 's'
#define MOVE_RIGHT 'd'
#endif

#define WEIGHT_EMPTY_CELLS 5.0
#define WEIGHT_CLUSTERING 3.0
#define WEIGHT_MAX_TILE 2.0

int grid[GRID_SIZE][GRID_SIZE];

void initialize_grid() {
    memset(grid, 0, sizeof(grid));
    for (int i = 0; i < START_TILES; i++) {
        int r = rand() % GRID_SIZE;
        int c = rand() % GRID_SIZE;
        while (grid[r][c] != EMPTY_CELL) {
            r = rand() % GRID_SIZE;
            c = rand() % GRID_SIZE;
        }
        grid[r][c] = (rand() < PROBABILITY_4 * RAND_MAX) ? 4 : 2;
    }
}

void print_grid() {
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            printf("%4d", grid[r][c]);
        }
        printf("\n");
    }
    printf("\n");
}

bool slide_and_merge_row(int* row) {
    bool moved = false;
    int temp[GRID_SIZE] = { 0 };
    int write_index = 0;

    for (int i = 0; i < GRID_SIZE; i++) {
        if (row[i] != EMPTY_CELL) {
            if (write_index > 0 && temp[write_index - 1] == row[i]) {
                temp[write_index - 1] *= 2;
                moved = true;
            }
            else {
                temp[write_index++] = row[i];
            }
        }
    }

    for (int i = 0; i < GRID_SIZE; i++) {
        if (row[i] != temp[i]) {
            row[i] = temp[i];
            moved = true;
        }
    }

    return moved;
}

bool move_left() {
    bool moved = false;
    for (int r = 0; r < GRID_SIZE; r++) {
        if (slide_and_merge_row(grid[r])) {
            moved = true;
        }
    }
    return moved;
}

bool move_right() {
    bool moved = false;
    for (int r = 0; r < GRID_SIZE; r++) {
        int temp[GRID_SIZE];
        for (int c = 0; c < GRID_SIZE; c++) {
            temp[c] = grid[r][GRID_SIZE - 1 - c];
        }
        if (slide_and_merge_row(temp)) {
            moved = true;
        }
        for (int c = 0; c < GRID_SIZE; c++) {
            grid[r][GRID_SIZE - 1 - c] = temp[c];
        }
    }
    return moved;
}

bool move_up() {
    bool moved = false;
    for (int c = 0; c < GRID_SIZE; c++) {
        int temp[GRID_SIZE];
        for (int r = 0; r < GRID_SIZE; r++) {
            temp[r] = grid[r][c];
        }
        if (slide_and_merge_row(temp)) {
            moved = true;
        }
        for (int r = 0; r < GRID_SIZE; r++) {
            grid[r][c] = temp[r];
        }
    }
    return moved;
}

bool move_down() {
    bool moved = false;
    for (int c = 0; c < GRID_SIZE; c++) {
        int temp[GRID_SIZE];
        for (int r = 0; r < GRID_SIZE; r++) {
            temp[r] = grid[GRID_SIZE - 1 - r][c];
        }
        if (slide_and_merge_row(temp)) {
            moved = true;
        }
        for (int r = 0; r < GRID_SIZE; r++) {
            grid[GRID_SIZE - 1 - r][c] = temp[r];
        }
    }
    return moved;
}

void add_new_tile() {
    int empty_cells[GRID_SIZE * GRID_SIZE][2];
    int empty_count = 0;

    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c] == EMPTY_CELL) {
                empty_cells[empty_count][0] = r;
                empty_cells[empty_count][1] = c;
                empty_count++;
            }
        }
    }

    if (empty_count > 0) {
        int idx = rand() % empty_count;
        int r = empty_cells[idx][0];
        int c = empty_cells[idx][1];
        grid[r][c] = (rand() < PROBABILITY_4 * RAND_MAX) ? 4 : 2;
    }
}

bool can_move() {
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c] == EMPTY_CELL) {
                return true;
            }
            if (c < GRID_SIZE - 1 && grid[r][c] == grid[r][c + 1]) {
                return true;
            }
            if (r < GRID_SIZE - 1 && grid[r][c] == grid[r + 1][c]) {
                return true;
            }
        }
    }
    return false;
}

double evaluate_grid() {
    double score = 0.0;
    int empty_cells = 0;
    int max_tile = 0;

    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c] == EMPTY_CELL) {
                empty_cells++;
            }
            if (grid[r][c] > max_tile) {
                max_tile = grid[r][c];
            }
        }
    }

    score += WEIGHT_EMPTY_CELLS * empty_cells;
    score += WEIGHT_MAX_TILE * max_tile;

    return score;
}

void ai_make_move() {
    double best_score = -1;
    char best_move = '\0';

    int backup[GRID_SIZE][GRID_SIZE];
    memcpy(backup, grid, sizeof(grid));

    char moves[] = { MOVE_UP, MOVE_LEFT, MOVE_DOWN, MOVE_RIGHT };
    for (int i = 0; i < 4; i++) {
        bool moved = false;
        switch (moves[i]) {
        case MOVE_UP:
            moved = move_up();
            break;
        case MOVE_LEFT:
            moved = move_left();
            break;
        case MOVE_DOWN:
            moved = move_down();
            break;
        case MOVE_RIGHT:
            moved = move_right();
            break;
        }

        if (moved) {
            double score = evaluate_grid();
            if (score > best_score) {
                best_score = score;
                best_move = moves[i];
            }
        }

        memcpy(grid, backup, sizeof(grid));
    }

    switch (best_move) {
    case MOVE_UP:
        move_up();
        break;
    case MOVE_LEFT:
        move_left();
        break;
    case MOVE_DOWN:
        move_down();
        break;
    case MOVE_RIGHT:
        move_right();
        break;
    default:
        break;
    }

    add_new_tile();
}

void ai_play() {
    for (int i = 0; i < STEPS; i++) {
        if (can_move()) {
            ai_make_move();
        }
        else {
            break;
        }
    }
}

int calculate_score() {
    int score = 0;
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            score += grid[r][c];
        }
    }
    return score;
}

int main() {
    srand(time(NULL));
    initialize_grid();

    while (true) {
        print_grid();

        if (!can_move()) {
            printf("Game Over!\n");
            print_grid();
            printf("Final Score: %d\n", calculate_score());
            break;
        }

#ifdef AI_PLAY
        ai_play();
#else
        printf("Enter move (%c/%c/%c/%c): ", MOVE_UP, MOVE_LEFT, MOVE_DOWN, MOVE_RIGHT);

        char move;
        scanf(" %c", &move);

        bool moved = false;
        switch (move) {
        case MOVE_UP:
            moved = move_up();
            break;
        case MOVE_LEFT:
            moved = move_left();
            break;
        case MOVE_DOWN:
            moved = move_down();
            break;
        case MOVE_RIGHT:
            moved = move_right();
            break;
        default:
            printf("Invalid move!\n");
            break;
        }

        if (moved) {
            add_new_tile();
        }
#endif
    }

    return 0;
}
