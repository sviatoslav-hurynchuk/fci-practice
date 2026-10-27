import math
import random
from typing import Optional
from lab03.model import BattleshipBoard


class SimulatedAnnealingSolver:
    def __init__(
        self,
        board: BattleshipBoard,
        t_start: float = 25.0,
        t_min: float = 0.0005,
        alpha: float = 0.9995,
        max_iterations: int = 60000
    ):
        self.board = board
        self.t_start = t_start
        self.t_min = t_min
        self.alpha = alpha
        self.max_iterations = max_iterations

        self.current_temp = t_start
        self.iteration = 0
        self.evaluations_count = 0
        self.accepted_moves = 0
        self.recent_accepted = 0

        self.current_chromosome: list[tuple[int, int, int]] = []
        self.current_energy = 999999.0
        self.best_chromosome: Optional[list[tuple[int, int, int]]] = None
        self.best_energy = 999999.0
        self.best_eval: Optional[dict] = None

        self.history_current_energy: list[float] = []
        self.history_best_energy: list[float] = []
        self.history_temperature: list[float] = []
        self.history_acceptance_rate: list[float] = []

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
        if mode < 0.35:
            return self._random_gene(length)
        elif mode < 0.70:
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
        self.iteration = 0
        self.evaluations_count = 0
        self.accepted_moves = 0
        self.recent_accepted = 0
        self.current_temp = self.t_start

        self.current_chromosome = [
            self._random_gene(length) for length in self.board.ships
        ]
        ev = self.board.evaluate(self.current_chromosome)
        self.evaluations_count += 1
        self.current_energy = ev["energy"]

        self.best_chromosome = list(self.current_chromosome)
        self.best_energy = self.current_energy
        self.best_eval = ev

        self.history_current_energy = [self.current_energy]
        self.history_best_energy = [self.best_energy]
        self.history_temperature = [self.current_temp]
        self.history_acceptance_rate = [1.0]

    def step(self, batch_size: int = 50) -> dict:
        for _ in range(batch_size):
            if self.best_energy == 0 or self.current_temp < self.t_min or self.iteration >= self.max_iterations:
                break

            self.iteration += 1

            ship_idx = random.randint(0, len(self.board.ships) - 1)
            old_gene = self.current_chromosome[ship_idx]
            self.current_chromosome[ship_idx] = self._mutate_gene(old_gene, self.board.ships[ship_idx])

            ev = self.board.evaluate(self.current_chromosome)
            self.evaluations_count += 1
            new_energy = ev["energy"]
            delta_e = new_energy - self.current_energy

            accepted = False
            if delta_e <= 0:
                accepted = True
            else:
                prob = math.exp(-delta_e / max(self.current_temp, 1e-6))
                if random.random() < prob:
                    accepted = True

            if accepted:
                self.current_energy = new_energy
                self.accepted_moves += 1
                self.recent_accepted += 1
                if self.current_energy < self.best_energy:
                    self.best_energy = self.current_energy
                    self.best_chromosome = list(self.current_chromosome)
                    self.best_eval = ev
            else:
                self.current_chromosome[ship_idx] = old_gene

            self.current_temp = max(self.t_min, self.current_temp * self.alpha)

        acc_rate = (self.recent_accepted / max(batch_size, 1))
        self.recent_accepted = 0

        self.history_current_energy.append(self.current_energy)
        self.history_best_energy.append(self.best_energy)
        self.history_temperature.append(self.current_temp)
        self.history_acceptance_rate.append(acc_rate)

        return self.get_state()

    def get_state(self) -> dict:
        return {
            "iteration": self.iteration,
            "evaluations": self.evaluations_count,
            "temperature": self.current_temp,
            "current_energy": self.current_energy,
            "best_energy": self.best_energy,
            "best_violations": int(self.best_energy),
            "is_valid": (self.best_energy == 0),
            "chromosome": self.best_chromosome,
            "eval": self.best_eval
        }
