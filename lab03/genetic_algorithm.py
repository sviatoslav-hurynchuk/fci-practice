import random
from typing import Optional
from lab03.model import BattleshipBoard


class GeneticAlgorithmSolver:
    def __init__(
        self,
        board: BattleshipBoard,
        pop_size: int = 150,
        mutation_rate: float = 0.25,
        elite_size: int = 3,
        tournament_k: int = 4,
        max_generations: int = 1500
    ):
        self.board = board
        self.pop_size = pop_size
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self.tournament_k = tournament_k
        self.max_generations = max_generations

        self.population: list[list[tuple[int, int, int]]] = []
        self.fitness_values: list[float] = []
        self.violations_values: list[int] = []

        self.generation = 0
        self.evaluations_count = 0
        self.best_chromosome: Optional[list[tuple[int, int, int]]] = None
        self.best_eval: Optional[dict] = None
        self.best_fitness = -1.0
        self.best_violations = 999999

        self.history_best_fitness: list[float] = []
        self.history_avg_fitness: list[float] = []
        self.history_best_violations: list[int] = []

        self.initialize()

    def _random_gene(self, length: int) -> tuple[int, int, int]:
        ori = 0 if length == 1 else random.choice([0, 1])
        if ori == 0:
            x = random.randint(0, self.board.field_size - length)
            y = random.randint(0, self.board.field_size - 1)
        else:
            x = random.randint(0, self.board.field_size - 1)
            y = random.randint(0, self.board.field_size - length)
        return (x, y, ori)

    def _mutate_gene(self, gene: tuple[int, int, int], length: int) -> tuple[int, int, int]:
        x, y, ori = gene
        mode = random.random()
        if mode < 0.4:
            return self._random_gene(length)
        elif mode < 0.7:
            dx = random.choice([-1, 1])
            dy = random.choice([-1, 1])
            new_x = max(0, min(self.board.field_size - (length if ori == 0 else 1), x + dx))
            new_y = max(0, min(self.board.field_size - (1 if ori == 0 else length), y + dy))
            return (new_x, new_y, ori)
        else:
            if length == 1:
                return (x, y, 0)
            new_ori = 1 - ori
            new_x = max(0, min(self.board.field_size - (length if new_ori == 0 else 1), x))
            new_y = max(0, min(self.board.field_size - (1 if new_ori == 0 else length), y))
            return (new_x, new_y, new_ori)

    def initialize(self):
        self.generation = 0
        self.evaluations_count = 0
        self.population = [
            [self._random_gene(length) for length in self.board.ships]
            for _ in range(self.pop_size)
        ]
        self.fitness_values = []
        self.violations_values = []
        self.history_best_fitness = []
        self.history_avg_fitness = []
        self.history_best_violations = []

        for ind in self.population:
            ev = self.board.evaluate(ind)
            self.evaluations_count += 1
            self.fitness_values.append(ev["fitness"])
            self.violations_values.append(ev["violations"])

        best_idx = max(range(self.pop_size), key=lambda i: self.fitness_values[i])
        self.best_chromosome = list(self.population[best_idx])
        self.best_fitness = self.fitness_values[best_idx]
        self.best_violations = self.violations_values[best_idx]
        self.best_eval = self.board.evaluate(self.best_chromosome)

        avg_fit = sum(self.fitness_values) / self.pop_size
        self.history_best_fitness.append(self.best_fitness)
        self.history_avg_fitness.append(avg_fit)
        self.history_best_violations.append(self.best_violations)

    def step(self) -> dict:
        if self.best_violations == 0 or self.generation >= self.max_generations:
            return self.get_state()

        self.generation += 1

        sorted_indices = sorted(range(self.pop_size), key=lambda i: self.fitness_values[i], reverse=True)
        new_pop = [list(self.population[i]) for i in sorted_indices[:self.elite_size]]

        while len(new_pop) < self.pop_size:
            c1 = random.sample(range(self.pop_size), self.tournament_k)
            p1 = self.population[max(c1, key=lambda i: self.fitness_values[i])]
            c2 = random.sample(range(self.pop_size), self.tournament_k)
            p2 = self.population[max(c2, key=lambda i: self.fitness_values[i])]

            child = []
            for g_idx in range(len(self.board.ships)):
                chosen = p1[g_idx] if random.random() < 0.5 else p2[g_idx]
                if random.random() < self.mutation_rate:
                    chosen = self._mutate_gene(chosen, self.board.ships[g_idx])
                child.append(chosen)

            new_pop.append(child)

        self.population = new_pop
        self.fitness_values = []
        self.violations_values = []

        for ind in self.population:
            ev = self.board.evaluate(ind)
            self.evaluations_count += 1
            self.fitness_values.append(ev["fitness"])
            self.violations_values.append(ev["violations"])

        cur_best_idx = max(range(self.pop_size), key=lambda i: self.fitness_values[i])
        if self.fitness_values[cur_best_idx] > self.best_fitness:
            self.best_fitness = self.fitness_values[cur_best_idx]
            self.best_violations = self.violations_values[cur_best_idx]
            self.best_chromosome = list(self.population[cur_best_idx])
            self.best_eval = self.board.evaluate(self.best_chromosome)

        avg_fit = sum(self.fitness_values) / self.pop_size
        self.history_best_fitness.append(self.best_fitness)
        self.history_avg_fitness.append(avg_fit)
        self.history_best_violations.append(self.best_violations)

        return self.get_state()

    def get_state(self) -> dict:
        return {
            "generation": self.generation,
            "evaluations": self.evaluations_count,
            "best_fitness": self.best_fitness,
            "best_violations": self.best_violations,
            "is_valid": (self.best_violations == 0),
            "chromosome": self.best_chromosome,
            "eval": self.best_eval
        }
