#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>
#include <cuda_runtime.h>

#define GRID_SIZE 4

// Weights for monte carlo simulations and the steps :
#define EMPTY_CELLS_WEIGHT 50000
#define TOTAL_SUM_WEIGHT 1
#define SMOOTHNESS_WEIGHT 100
#define MAX_TILE_WEIGHT 20

#define STEPS 5  // Number of Monte Carlo simulations

// Uncomment the following macros to enable specific features
#define USE_AI    // Enable AI to play the game
// #define AZERTY    // Set player controls to AZERTY (ZQSD)

using namespace std;

// CUDA kernel to move left
__global__ void move_left(int* grid, int size) {
    int row = blockIdx.x;
    for (int col = 0; col < size; ++col) {
        if (grid[row * size + col] == 0) {
            for (int k = col + 1; k < size; ++k) {
                if (grid[row * size + k] != 0) {
                    grid[row * size + col] = grid[row * size + k];
                    grid[row * size + k] = 0;
                    break;
                }
            }
        }
    }
    for (int col = 0; col < size - 1; ++col) {
        if (grid[row * size + col] == grid[row * size + col + 1] && grid[row * size + col] != 0) {
            grid[row * size + col] *= 2;
            grid[row * size + col + 1] = 0;
        }
    }
    for (int col = 0; col < size; ++col) {
        if (grid[row * size + col] == 0) {
            for (int k = col + 1; k < size; ++k) {
                if (grid[row * size + k] != 0) {
                    grid[row * size + col] = grid[row * size + k];
                    grid[row * size + k] = 0;
                    break;
                }
            }
        }
    }
}

// CUDA kernel to move right
__global__ void move_right(int* grid, int size) {
    int row = blockIdx.x;
    for (int col = size - 1; col >= 0; --col) {
        if (grid[row * size + col] == 0) {
            for (int k = col - 1; k >= 0; --k) {
                if (grid[row * size + k] != 0) {
                    grid[row * size + col] = grid[row * size + k];
                    grid[row * size + k] = 0;
                    break;
                }
            }
        }
    }
    for (int col = size - 1; col > 0; --col) {
        if (grid[row * size + col] == grid[row * size + col - 1] && grid[row * size + col] != 0) {
            grid[row * size + col] *= 2;
            grid[row * size + col - 1] = 0;
        }
    }
    for (int col = size - 1; col >= 0; --col) {
        if (grid[row * size + col] == 0) {
            for (int k = col - 1; k >= 0; --k) {
                if (grid[row * size + k] != 0) {
                    grid[row * size + col] = grid[row * size + k];
                    grid[row * size + k] = 0;
                    break;
                }
            }
        }
    }
}

// CUDA kernel to transpose the grid
__global__ void transpose(int* grid, int size) {
    int idx = threadIdx.x + blockIdx.x * blockDim.x;
    int row = idx / size;
    int col = idx % size;

    if (row < col) {
        int tmp = grid[row * size + col];
        grid[row * size + col] = grid[col * size + row];
        grid[col * size + row] = tmp;
    }
}

// CPU function to add a new tile
void add_new_tile(vector<int>& grid) {
    vector<int> empty_positions;
    for (int i = 0; i < grid.size(); ++i) {
        if (grid[i] == 0) empty_positions.push_back(i);
    }
    if (!empty_positions.empty()) {
        int pos = empty_positions[rand() % empty_positions.size()];
        grid[pos] = (rand() % 10 == 0) ? 4 : 2;
    }
}

// Calculate the score for a grid
__host__ int total_score(const vector<int>& grid) {
    int total_sum = 0;
    for (int value : grid) {
        total_sum += value;
    }
    return total_sum;
}

// Evaluate the score for a grid
__host__ int evaluate_grid(const vector<int>& grid) {
    int empty_cells = 0, total_sum = 0, smoothness = 0;
    int max_tile = 0;

    // Check for empty cells and calculate total sum
    for (int i = 0; i < grid.size(); ++i) {
        int value = grid[i];
        if (value == 0) {
            ++empty_cells;
        }
        else {
            total_sum += value;
            max_tile = max(max_tile, value);

            // Calculate smoothness (penalize big differences between neighbors)
            if (i % GRID_SIZE != GRID_SIZE - 1) { // Right neighbor
                int neighbor = grid[i + 1];
                if (neighbor != 0) {
                    smoothness -= abs(value - neighbor);
                }
            }
            if (i < GRID_SIZE * (GRID_SIZE - 1)) { // Downward neighbor
                int neighbor = grid[i + GRID_SIZE];
                if (neighbor != 0) {
                    smoothness -= abs(value - neighbor);
                }
            }
        }
    }

    // Weighted score
    return (empty_cells * EMPTY_CELLS_WEIGHT) +
        (total_sum * TOTAL_SUM_WEIGHT) +
        (smoothness * SMOOTHNESS_WEIGHT) +
        (max_tile * MAX_TILE_WEIGHT);
}


// Monte Carlo function to choose the best move
int monte_carlo_move(const vector<int>& grid, int* d_grid) {
    int best_move = -1;
    double best_score = -1;

    for (int move = 0; move < 4; ++move) {
        double total_score = 0;
        bool valid_move = false;

        for (int step = 0; step < STEPS; ++step) {
            vector<int> temp_grid(grid);
            cudaMemcpy(d_grid, temp_grid.data(), GRID_SIZE * GRID_SIZE * sizeof(int), cudaMemcpyHostToDevice);

            // Apply the move
            switch (move) {
            case 0: move_left << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE); break;
            case 1: move_right << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE); break;
            case 2:
                transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
                move_left << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE);
                transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
                break;
            case 3:
                transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
                move_right << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE);
                transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
                break;
            }

            // Copy back and check validity
            cudaMemcpy(temp_grid.data(), d_grid, GRID_SIZE * GRID_SIZE * sizeof(int), cudaMemcpyDeviceToHost);
            if (temp_grid != grid) {
                valid_move = true;
            }
            else {
                break; // No need to continue for an invalid move
            }

            // Add a random tile and evaluate the grid
            add_new_tile(temp_grid);
            total_score += evaluate_grid(temp_grid);
        }

        // Skip invalid moves
        if (!valid_move) continue;

        // Calculate average score for this move
        double average_score = total_score / STEPS;
        if (average_score > best_score) {
            best_score = average_score;
            best_move = move;
        }
    }

    return best_move;
}


// Check if the game is over
bool is_game_over(const vector<int>& grid) {
    // Check for empty cells
    for (int value : grid) {
        if (value == 0) {
            return false;
        }
    }

    // Check for possible horizontal merges
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE - 1; ++j) {
            int idx = i * GRID_SIZE + j;
            if (grid[idx] == grid[idx + 1]) {
                return false;
            }
        }
    }

    // Check for possible vertical merges
    for (int j = 0; j < GRID_SIZE; ++j) {
        for (int i = 0; i < GRID_SIZE - 1; ++i) {
            int idx = i * GRID_SIZE + j;
            if (grid[idx] == grid[idx + GRID_SIZE]) {
                return false;
            }
        }
    }

    // No empty cells and no possible merges
    return true;
}

// Main function
int main() {
    srand(time(0));

    vector<int> grid(GRID_SIZE * GRID_SIZE, 0);
    int* d_grid;
    cudaMalloc(&d_grid, GRID_SIZE * GRID_SIZE * sizeof(int));

    add_new_tile(grid);
    add_new_tile(grid);

    while (!is_game_over(grid)) {
        cout << "Current grid:\n";
        for (int i = 0; i < GRID_SIZE; ++i) {
            for (int j = 0; j < GRID_SIZE; ++j) {
                cout << grid[i * GRID_SIZE + j] << "\t";
            }
            cout << endl;
        }

#ifdef USE_AI
        // AI determines the best move
        int move = monte_carlo_move(grid, d_grid);
        if (move == -1) {
            cout << "No valid moves. Game over." << endl;
            break;
        }

        switch (move) {
        case 0: move_left << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE); break;
        case 1: move_right << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE); break;
        case 2:
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            move_left << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE);
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            break;
        case 3:
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            move_right << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE);
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            break;
        }
#else
        // Player input for manual moves
        char input;
#ifdef AZERTY
        cout << "Enter move (Z=Up, Q=Left, S=Down, D=Right): ";
#else
        cout << "Enter move (W=Up, A=Left, S=Down, D=Right): ";
#endif
        cin >> input;

        bool valid_move = false;
        switch (input) {
#ifdef AZERTY
        case 'Q': case 'q': move_left << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE); valid_move = true; break;
        case 'D': case 'd': move_right << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE); valid_move = true; break;
        case 'Z': case 'z':
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            move_left << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE);
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            valid_move = true;
            break;
        case 'S': case 's':
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            move_right << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE);
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            valid_move = true;
            break;
#else
        case 'A': case 'a': move_left << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE); valid_move = true; break;
        case 'D': case 'd': move_right << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE); valid_move = true; break;
        case 'W': case 'w':
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            move_left << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE);
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            valid_move = true;
            break;
        case 'S': case 's':
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            move_right << <GRID_SIZE, 1 >> > (d_grid, GRID_SIZE);
            transpose << <1, GRID_SIZE* GRID_SIZE >> > (d_grid, GRID_SIZE);
            valid_move = true;
            break;
#endif
        default:
            cout << "Invalid input. Try again.\n";
            break;
        }

        if (!valid_move) continue;
#endif

        cudaMemcpy(grid.data(), d_grid, GRID_SIZE * GRID_SIZE * sizeof(int), cudaMemcpyDeviceToHost);
        add_new_tile(grid);
    }

    cout << "Game over!" << endl;

    // Print the grid one last time
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            cout << grid[i * GRID_SIZE + j] << "\t";
        }
        cout << endl;
    }
    fprintf(stdout, "Score : ");
    cout << total_score(grid) << endl;
    cudaFree(d_grid);


    return 0;
}
