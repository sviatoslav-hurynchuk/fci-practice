import concurrent.futures
import math
import random
from lab04.client import DockSimClient
from lab04.policy import TabularPolicy


def compute_episode_score(result: str, stats: dict, final_state: dict, tolerances: dict) -> float:
    final = stats.get("final", {})

    if result == "docked":
        fuel = stats.get("fuel_used", 15.0)
        t_ep = stats.get("time", 30.0)
        return 1000.0 + max(0.0, 100.0 - 4.0 * fuel) + max(0.0, 80.0 - 1.5 * t_ep)

    if result == "crash_station":
        tol_angle = tolerances.get("angle", 0.1745)
        tol_vx = tolerances.get("vx", 8.0)
        tol_vy = tolerances.get("vy", 12.0)
        tol_omega = tolerances.get("omega", 0.2618)

        dx = abs(final.get("dx", 50.0))
        a_err = abs(final.get("angle_err", 0.5))
        vx = abs(final.get("vx", 20.0))
        vy = abs(final.get("vy", 20.0))
        om = abs(final.get("omega", 1.0))

        q_dx = 1.0 / (1.0 + max(0.0, dx / 30.0 - 1.0))
        q_ang = 1.0 / (1.0 + max(0.0, a_err / tol_angle - 1.0))
        q_vx = 1.0 / (1.0 + max(0.0, vx / tol_vx - 1.0))
        q_vy = 1.0 / (1.0 + max(0.0, vy / tol_vy - 1.0))
        q_om = 1.0 / (1.0 + max(0.0, om / tol_omega - 1.0))

        q_tot = q_dx * q_ang * q_vx * q_vy * q_om
        return 400.0 + 500.0 * q_tot

    if result == "crash_debris":
        return 50.0

    ship = final_state.get("ship", {})
    station = final_state.get("station", {})
    dx_st = abs(ship.get("x", 500.0) - station.get("x", 500.0))
    dy_st = abs(ship.get("y", 350.0) - station.get("y", 40.0))
    dist = math.hypot(dx_st, dy_st)
    return max(0.0, 300.0 / (1.0 + dist / 150.0))


def evaluate_individual_client(client: DockSimClient, policy: TabularPolicy, seeds: list[int], max_steps: int = 900) -> dict:
    total_score = 0.0
    docked_count = 0
    crashes_debris = 0
    crashes_station = 0
    other_ends = 0
    total_fuel = 0.0
    total_time = 0.0

    tolerances = client.hello.get("tolerances", {
        "angle": 0.1745,
        "vx": 8.0,
        "vy": 12.0,
        "omega": 0.2618
    })

    for seed in seeds:
        st = client.reset(seed=seed)
        step_n = 0

        while not st.get("done", False) and step_n < max_steps:
            step_n += 1
            th, tu = policy.get_action(st)
            st = client.step(th, tu)

        res = st.get("result", "timeout")
        stats = st.get("stats", {})
        score = compute_episode_score(res, stats, st, tolerances)

        total_score += score
        total_fuel += stats.get("fuel_used", 0.0)
        total_time += stats.get("time", 0.0)

        if res == "docked":
            docked_count += 1
        elif res == "crash_debris":
            crashes_debris += 1
        elif res == "crash_station":
            crashes_station += 1
        else:
            other_ends += 1

    n_seeds = max(len(seeds), 1)
    return {
        "fitness": total_score / n_seeds,
        "docked_rate": (docked_count / n_seeds) * 100.0,
        "docked_count": docked_count,
        "crashes_debris": crashes_debris,
        "crashes_station": crashes_station,
        "other_ends": other_ends,
        "avg_fuel": total_fuel / n_seeds,
        "avg_time": total_time / n_seeds
    }


class GeneticAlgorithmTrainer:
    def __init__(
        self,
        pop_size: int = 40,
        mutation_rate: float = 0.18,
        elite_size: int = 2,
        tournament_k: int = 3,
        mode: str = "separate",
        port: int = 47555,
        workers: int = 1
    ):
        self.pop_size = pop_size
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self.tournament_k = tournament_k
        self.mode = mode
        self.port = port
        self.workers = max(1, min(workers, 8))

        self.population: list[list] = []
        self.fitness_scores: list[float] = []
        self.eval_details: list[dict] = []

        self.generation = 0
        self.best_individual: list = None
        self.best_fitness = -1.0
        self.best_eval: dict = None

        self.history_best_fitness: list[float] = []
        self.history_avg_fitness: list[float] = []
        self.history_dock_rate: list[float] = []

        self._init_population()

    def _init_population(self):
        self.population = []
        default_chrom = TabularPolicy.get_default_chromosome(self.mode)
        self.population.append(list(default_chrom))

        for _ in range(self.pop_size - 1):
            ind = list(default_chrom)
            if self.mode == "separate":
                for i in range(15):
                    if random.random() < 0.35:
                        ind[i] = random.choice([-1, 0, 1])
                ind[15] = max(0.02, min(0.15, ind[15] + random.gauss(0, 0.02)))
                ind[16] = max(0.04, min(0.25, ind[16] + random.gauss(0, 0.02)))
                ind[17] = max(1.0, min(5.0, ind[17] + random.gauss(0, 0.5)))
                ind[18] = max(6.0, min(18.0, ind[18] + random.gauss(0, 1.5)))
                ind[19] = max(0.10, min(0.55, ind[19] + random.gauss(0, 0.05)))
                ind[20] = max(0.20, min(0.60, ind[20] + random.gauss(0, 0.05)))
            else:
                for i in range(54):
                    if random.random() < 0.35:
                        ind[i] = random.randint(0, 8)
                for r in range(54, 60):
                    ind[r] = max(0.01, ind[r] + random.gauss(0, 0.05))
            self.population.append(ind)

    def _crossover(self, parent1: list, parent2: list) -> list:
        child = []
        split_idx = 15 if self.mode == "separate" else 54

        for i in range(split_idx):
            gene = parent1[i] if random.random() < 0.5 else parent2[i]
            child.append(gene)

        for i in range(split_idx, len(parent1)):
            lam = random.random()
            child.append(lam * parent1[i] + (1.0 - lam) * parent2[i])

        return child

    def _mutate(self, ind: list) -> list:
        mutated = list(ind)
        split_idx = 15 if self.mode == "separate" else 54

        if self.mode == "separate":
            for i in range(split_idx):
                if random.random() < self.mutation_rate:
                    mutated[i] = random.choice([-1, 0, 1])

            if random.random() < self.mutation_rate * 1.5:
                mutated[15] = max(0.02, min(0.15, mutated[15] + random.gauss(0, 0.015)))
            if random.random() < self.mutation_rate * 1.5:
                mutated[16] = max(0.04, min(0.25, mutated[16] + random.gauss(0, 0.02)))
            if random.random() < self.mutation_rate * 1.5:
                mutated[17] = max(1.0, min(5.0, mutated[17] + random.gauss(0, 0.4)))
            if random.random() < self.mutation_rate * 1.5:
                mutated[18] = max(6.0, min(18.0, mutated[18] + random.gauss(0, 1.0)))
            if random.random() < self.mutation_rate * 1.5:
                mutated[19] = max(0.10, min(0.55, mutated[19] + random.gauss(0, 0.04)))
            if random.random() < self.mutation_rate * 1.5:
                mutated[20] = max(0.20, min(0.60, mutated[20] + random.gauss(0, 0.04)))
        else:
            for i in range(split_idx):
                if random.random() < self.mutation_rate:
                    mutated[i] = random.randint(0, 8)
            for i in range(split_idx, len(mutated)):
                if random.random() < self.mutation_rate * 1.5:
                    mutated[i] = max(0.01, mutated[i] + random.gauss(0, 0.05))

        return mutated

    def _tournament(self) -> list:
        candidates = random.sample(range(self.pop_size), self.tournament_k)
        best_idx = max(candidates, key=lambda idx: self.fitness_scores[idx])
        return self.population[best_idx]

    def evaluate_population(self, seeds: list[int]):
        def eval_single(ind):
            cl = DockSimClient(port=self.port)
            pol = TabularPolicy(chromosome=ind, mode=self.mode)
            try:
                res = evaluate_individual_client(cl, pol, seeds)
            finally:
                cl.close()
            return res

        if self.workers > 1 and len(self.population) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
                results = list(executor.map(eval_single, self.population))
        else:
            cl = DockSimClient(port=self.port)
            try:
                results = []
                for ind in self.population:
                    pol = TabularPolicy(chromosome=ind, mode=self.mode)
                    results.append(evaluate_individual_client(cl, pol, seeds))
            finally:
                cl.close()

        self.eval_details = results
        self.fitness_scores = [r["fitness"] for r in results]

        best_idx = max(range(self.pop_size), key=lambda i: self.fitness_scores[i])
        if self.fitness_scores[best_idx] > self.best_fitness:
            self.best_fitness = self.fitness_scores[best_idx]
            self.best_individual = list(self.population[best_idx])
            self.best_eval = dict(self.eval_details[best_idx])

    def step(self, seeds: list[int] = None) -> dict:
        if seeds is None:
            base_s = (self.generation * 7 + 13) % 1000
            seeds = [base_s + i * 23 for i in range(5)]

        self.evaluate_population(seeds)
        self.generation += 1

        avg_fit = sum(self.fitness_scores) / self.pop_size
        best_dock = max(r["docked_rate"] for r in self.eval_details)

        self.history_best_fitness.append(self.best_fitness)
        self.history_avg_fitness.append(avg_fit)
        self.history_dock_rate.append(best_dock)

        elite_indices = sorted(range(self.pop_size), key=lambda i: self.fitness_scores[i], reverse=True)[:self.elite_size]
        new_pop = [list(self.population[idx]) for idx in elite_indices]

        while len(new_pop) < self.pop_size:
            p1 = self._tournament()
            p2 = self._tournament()
            child = self._crossover(p1, p2)
            child = self._mutate(child)
            new_pop.append(child)

        self.population = new_pop

        return {
            "generation": self.generation,
            "best_fitness": self.best_fitness,
            "avg_fitness": avg_fit,
            "best_dock_rate": best_dock,
            "best_eval": self.best_eval
        }
