import math
import random
from typing import Callable


class SimulatedAnnealingHunter:
    def __init__(
        self,
        grid: list[list[int]],
        width: int,
        height: int,
        start_x: int,
        start_y: int,
        move_fn: Callable[[int, int], dict],
        t_start: float = 40.0,
        t_min: float = 0.02,
        alpha: float = 0.91,
        r_max: int = 25,
        max_steps: int = 1000
    ):
        self.grid = grid
        self.width = width
        self.height = height
        self.curr_x = start_x
        self.curr_y = start_y
        self.move_fn = move_fn
        self.t_start = t_start
        self.t_min = t_min
        self.alpha = alpha
        self.r_max = r_max
        self.max_steps = max_steps

        self.t = t_start
        self.step_count = 0
        self.remaining_foxes = 3
        self.curr_signal = 0.0
        self.caught_foxes: list[tuple[int, int, int]] = []
        self.history_trajectory: list[tuple[int, int]] = [(start_x, start_y)]
        self.history_temperature: list[float] = [t_start]
        self.history_signal: list[float] = [0.0]

    def run_step(self) -> dict:
        if self.remaining_foxes == 0:
            return {"status": "completed", "steps": self.step_count}

        if self.curr_signal < 0.02:
            r = self.r_max
            self.t = self.t_start
        else:
            r = max(1, round(self.r_max * (self.t / self.t_start)))

        candidate = self._generate_candidate(r)
        if not candidate:
            candidate = self._generate_fallback_neighbor()

        if not candidate:
            return {"status": "stuck", "steps": self.step_count}

        nx, ny = candidate
        res = self.move_fn(nx, ny)
        self.step_count = res.get("steps_made", self.step_count + 1)
        new_signal = res.get("signal_level", 0.0)
        fox_caught = res.get("fox_caught", False)
        self.remaining_foxes = res.get("remaining_foxes", self.remaining_foxes)

        accepted = False
        if fox_caught:
            accepted = True
            self.curr_x, self.curr_y = nx, ny
            self.curr_signal = 0.0
            self.caught_foxes.append((nx, ny, self.step_count))
            self.t = self.t_start
        else:
            delta_s = new_signal - self.curr_signal
            if delta_s > 0:
                accepted = True
            else:
                prob = math.exp(delta_s / max(self.t, 1e-6))
                accepted = random.random() < prob

            if accepted:
                self.curr_x, self.curr_y = nx, ny
                self.curr_signal = new_signal

            if self.curr_signal >= 0.02:
                self.t = max(self.t_min, self.t * self.alpha)

        self.history_trajectory.append((self.curr_x, self.curr_y))
        self.history_temperature.append(self.t)
        self.history_signal.append(self.curr_signal)

        return {
            "status": "in_progress" if self.remaining_foxes > 0 else "completed",
            "step": self.step_count,
            "x": self.curr_x,
            "y": self.curr_y,
            "signal": self.curr_signal,
            "temperature": self.t,
            "radius": r,
            "fox_caught": fox_caught,
            "remaining_foxes": self.remaining_foxes,
            "accepted": accepted
        }

    def _generate_candidate(self, r: int) -> tuple[int, int] | None:
        for _ in range(35):
            dx = random.randint(-r, r)
            dy = random.randint(-r, r)
            if dx == 0 and dy == 0:
                continue
            nx = self.curr_x + dx
            ny = self.curr_y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.grid[ny][nx] == 0:
                    return nx, ny
        return None

    def _generate_fallback_neighbor(self) -> tuple[int, int] | None:
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx = self.curr_x + dx
            ny = self.curr_y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.grid[ny][nx] == 0:
                    return nx, ny
        return None
