import json
import math
import random
from typing import Any, Dict, List, Optional, Set, Tuple


class AntColonySolver:
    def __init__(
        self,
        task: Dict[str, Any],
        algorithm: str = "MMAS",
        num_ants: int = 35,
        alpha: float = 1.0,
        beta: float = 3.0,
        gamma: float = 1.2,
        rho: float = 0.1,
        q0: float = 0.85,
        use_2opt: bool = True,
        use_relocate: bool = True,
        candidate_size: int = 15,
        seed: Optional[int] = 42,
    ):
        self.task = task
        self.algorithm = algorithm.upper()
        self.num_ants = int(num_ants)
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.gamma = float(gamma)
        self.rho = float(rho)
        self.q0 = float(q0)
        self.use_2opt = bool(use_2opt)
        self.use_relocate = bool(use_relocate)
        self.candidate_size = int(candidate_size)

        if seed is not None:
            random.seed(seed)

        self.depot = task.get("depot", {"x": 0, "y": 0})
        self.customers = task.get("customers", [])
        self.capacity = int(task.get("capacity", 21))
        self.max_vehicles = int(task.get("vehicles", 7))
        self.reference_cost = float(task.get("reference_cost", 6558.59))
        self.num_customers = len(self.customers)

        self.coords: List[Tuple[float, float]] = [(float(self.depot["x"]), float(self.depot["y"]))]
        self.demands: List[int] = [0]
        self.customer_id_map: Dict[int, int] = {0: 0}

        for idx, cust in enumerate(self.customers, start=1):
            c_id = int(cust["id"])
            self.coords.append((float(cust["x"]), float(cust["y"])))
            self.demands.append(int(cust["demand"]))
            self.customer_id_map[c_id] = idx

        total_nodes = self.num_customers + 1
        self.dist: List[List[float]] = [[0.0] * total_nodes for _ in range(total_nodes)]
        self.eta: List[List[float]] = [[0.0] * total_nodes for _ in range(total_nodes)]
        self.savings: List[List[float]] = [[0.0] * total_nodes for _ in range(total_nodes)]

        for i in range(total_nodes):
            for j in range(total_nodes):
                if i != j:
                    d = math.hypot(self.coords[i][0] - self.coords[j][0], self.coords[i][1] - self.coords[j][1])
                    self.dist[i][j] = d
                    self.eta[i][j] = 1.0 / max(d, 1e-6)

        for i in range(1, total_nodes):
            for j in range(1, total_nodes):
                if i != j:
                    s = self.dist[i][0] + self.dist[0][j] - self.dist[i][j]
                    self.savings[i][j] = max(0.001, s)

        self.candidates: List[List[int]] = [[] for _ in range(total_nodes)]
        for i in range(total_nodes):
            targets = [j for j in range(1, total_nodes) if j != i]
            targets.sort(key=lambda j: self.dist[i][j])
            self.candidates[i] = targets[: self.candidate_size]

        self.iteration = 0
        self.best_cost = float("inf")
        self.best_routes: List[List[int]] = []
        self.best_iteration = 0
        self.stagnation_counter = 0

        self.tau0 = 1.0 / max(self.rho * self.reference_cost, 1e-4)
        self.tau_max = self.tau0
        self.tau_min = self.tau_max / (2.0 * max(self.num_customers, 1))

        self.tau: List[List[float]] = [[self.tau0] * total_nodes for _ in range(total_nodes)]
        self.cost_history: List[float] = []
        self.iter_best_history: List[float] = []
        self.iter_avg_history: List[float] = []

    def route_cost(self, route: List[int]) -> float:
        if not route:
            return 0.0
        c = self.dist[0][route[0]]
        for k in range(len(route) - 1):
            c += self.dist[route[k]][route[k + 1]]
        c += self.dist[route[-1]][0]
        return c

    def total_cost(self, routes: List[List[int]]) -> float:
        return sum(self.route_cost(r) for r in routes)

    def two_opt(self, route: List[int]) -> List[int]:
        best_r = list(route)
        improved = True
        n_r = len(best_r)
        if n_r < 4:
            return best_r

        while improved:
            improved = False
            for i in range(n_r - 1):
                for j in range(i + 2, n_r):
                    if i == 0 and j == n_r - 1:
                        continue
                    a = 0 if i == 0 else best_r[i - 1]
                    b = best_r[i]
                    c = best_r[j]
                    d = 0 if j == n_r - 1 else best_r[j + 1]

                    old_d = self.dist[a][b] + self.dist[c][d]
                    new_d = self.dist[a][c] + self.dist[b][d]
                    if new_d < old_d - 1e-5:
                        best_r[i : j + 1] = reversed(best_r[i : j + 1])
                        improved = True
                        break
                if improved:
                    break
        return best_r

    def local_search(self, routes: List[List[int]]) -> List[List[int]]:
        clean_routes = [self.two_opt(r) for r in routes if r]
        if not self.use_relocate or len(clean_routes) < 2:
            return clean_routes

        routes_copy = [list(r) for r in clean_routes]
        improved = True

        while improved:
            improved = False
            for r1_idx in range(len(routes_copy)):
                for r2_idx in range(len(routes_copy)):
                    if r1_idx == r2_idx:
                        continue
                    r1 = routes_copy[r1_idx]
                    r2 = routes_copy[r2_idx]
                    load2 = sum(self.demands[c] for c in r2)

                    for i_idx, c in enumerate(r1):
                        if load2 + self.demands[c] <= self.capacity:
                            old_cost = self.route_cost(r1) + self.route_cost(r2)
                            r1_cand = r1[:i_idx] + r1[i_idx + 1 :]
                            for pos in range(len(r2) + 1):
                                r2_cand = r2[:pos] + [c] + r2[pos:]
                                new_cost = self.route_cost(r1_cand) + self.route_cost(r2_cand)
                                if new_cost < old_cost - 1e-4:
                                    routes_copy[r1_idx] = self.two_opt(r1_cand)
                                    routes_copy[r2_idx] = self.two_opt(r2_cand)
                                    routes_copy = [r for r in routes_copy if r]
                                    improved = True
                                    break
                            if improved:
                                break
                    if improved:
                        break
                if improved:
                    break

        return routes_copy

    def select_next_customer(self, current_node: int, feasible_set: Set[int]) -> int:
        filtered_candidates = [c for c in self.candidates[current_node] if c in feasible_set]
        active_pool = filtered_candidates if filtered_candidates else list(feasible_set)

        if self.algorithm == "ACS" and random.random() < self.q0:
            best_node = active_pool[0]
            best_val = -1.0
            for node in active_pool:
                t = self.tau[current_node][node] ** self.alpha
                h = self.eta[current_node][node] ** self.beta
                s = (self.savings[current_node][node] ** self.gamma) if (current_node != 0 and self.gamma > 0) else 1.0
                val = t * h * s
                if val > best_val:
                    best_val = val
                    best_node = node
            return best_node

        weights = []
        for node in active_pool:
            t = self.tau[current_node][node] ** self.alpha
            h = self.eta[current_node][node] ** self.beta
            s = (self.savings[current_node][node] ** self.gamma) if (current_node != 0 and self.gamma > 0) else 1.0
            weights.append(t * h * s)

        total_weight = sum(weights)
        if total_weight <= 0.0:
            return random.choice(active_pool)

        rnd = random.random() * total_weight
        acc = 0.0
        for idx, w in enumerate(weights):
            acc += w
            if acc >= rnd:
                return active_pool[idx]
        return active_pool[-1]

    def construct_solution(self) -> List[List[int]]:
        unvisited = set(range(1, self.num_customers + 1))
        routes: List[List[int]] = []

        while unvisited:
            curr = 0
            current_route: List[int] = []
            current_load = 0

            while unvisited:
                feasible = {c for c in unvisited if current_load + self.demands[c] <= self.capacity}
                if not feasible:
                    break

                selected = self.select_next_customer(curr, feasible)
                current_route.append(selected)
                current_load += self.demands[selected]
                unvisited.remove(selected)

                if self.algorithm == "ACS":
                    xi = 0.1
                    self.tau[curr][selected] = (1.0 - xi) * self.tau[curr][selected] + xi * self.tau0
                    self.tau[selected][curr] = self.tau[curr][selected]

                curr = selected

            if current_route:
                routes.append(current_route)

            if len(routes) >= self.max_vehicles and unvisited:
                for rem in list(unvisited):
                    min_idx = 0
                    min_added = float("inf")
                    for r_idx, r in enumerate(routes):
                        if sum(self.demands[c] for c in r) + self.demands[rem] <= self.capacity:
                            added = self.dist[r[-1]][rem] + self.dist[rem][0] - self.dist[r[-1]][0]
                            if added < min_added:
                                min_added = added
                                min_idx = r_idx
                    if min_added < float("inf"):
                        routes[min_idx].append(rem)
                        unvisited.remove(rem)
                    else:
                        routes.append([rem])
                        unvisited.remove(rem)

        if self.use_2opt:
            routes = self.local_search(routes)

        return routes

    def update_pheromones(self, iteration_best_routes: List[List[int]], iteration_best_cost: float, all_solutions: List[Tuple[List[List[int]], float]]) -> None:
        total_nodes = self.num_customers + 1

        for i in range(total_nodes):
            for j in range(total_nodes):
                self.tau[i][j] *= 1.0 - self.rho

        if self.algorithm == "AS":
            for routes, cost in all_solutions:
                deposit = 1.0 / max(cost, 1e-4)
                for r in routes:
                    if r:
                        self.tau[0][r[0]] += deposit
                        self.tau[r[0]][0] += deposit
                        for k in range(len(r) - 1):
                            self.tau[r[k]][r[k + 1]] += deposit
                            self.tau[r[k + 1]][r[k]] += deposit
                        self.tau[r[-1]][0] += deposit
                        self.tau[0][r[-1]] += deposit

        elif self.algorithm == "EAS":
            deposit_best = 5.0 / max(self.best_cost, 1e-4)
            for r in self.best_routes:
                if r:
                    self.tau[0][r[0]] += deposit_best
                    self.tau[r[0]][0] += deposit_best
                    for k in range(len(r) - 1):
                        self.tau[r[k]][r[k + 1]] += deposit_best
                        self.tau[r[k + 1]][r[k]] += deposit_best
                    self.tau[r[-1]][0] += deposit_best
                    self.tau[0][r[-1]] += deposit_best

        elif self.algorithm in ("MMAS", "ACS"):
            target_routes = self.best_routes if self.iteration % 2 == 0 or self.best_cost < iteration_best_cost else iteration_best_routes
            target_cost = self.best_cost if target_routes == self.best_routes else iteration_best_cost
            deposit = 1.0 / max(target_cost, 1e-4)

            for r in target_routes:
                if r:
                    self.tau[0][r[0]] += deposit
                    self.tau[r[0]][0] += deposit
                    for k in range(len(r) - 1):
                        self.tau[r[k]][r[k + 1]] += deposit
                        self.tau[r[k + 1]][r[k]] += deposit
                    self.tau[r[-1]][0] += deposit
                    self.tau[0][r[-1]] += deposit

        if self.algorithm == "MMAS":
            self.tau_max = 1.0 / max(self.rho * self.best_cost, 1e-4)
            self.tau_min = self.tau_max / (2.0 * max(self.num_customers, 1))

            for i in range(total_nodes):
                for j in range(total_nodes):
                    if self.tau[i][j] > self.tau_max:
                        self.tau[i][j] = self.tau_max
                    elif self.tau[i][j] < self.tau_min:
                        self.tau[i][j] = self.tau_min

            if self.stagnation_counter > 30:
                self.stagnation_counter = 0
                for i in range(total_nodes):
                    for j in range(total_nodes):
                        self.tau[i][j] = self.tau_max

    def step(self) -> Dict[str, Any]:
        self.iteration += 1
        iter_best_cost = float("inf")
        iter_best_routes: List[List[int]] = []
        ant_solutions: List[Tuple[List[List[int]], float]] = []
        cost_sum = 0.0

        for _ in range(self.num_ants):
            sol = self.construct_solution()
            cost = self.total_cost(sol)
            ant_solutions.append((sol, cost))
            cost_sum += cost

            if cost < iter_best_cost:
                iter_best_cost = cost
                iter_best_routes = sol

        avg_cost = cost_sum / max(self.num_ants, 1)

        is_new_best = False
        if iter_best_cost < self.best_cost - 1e-4:
            self.best_cost = iter_best_cost
            self.best_routes = iter_best_routes
            self.best_iteration = self.iteration
            self.stagnation_counter = 0
            is_new_best = True
        else:
            self.stagnation_counter += 1

        self.update_pheromones(iter_best_routes, iter_best_cost, ant_solutions)

        self.cost_history.append(self.best_cost)
        self.iter_best_history.append(iter_best_cost)
        self.iter_avg_history.append(avg_cost)

        gap_percent = (self.best_cost - self.reference_cost) / max(self.reference_cost, 1e-4) * 100.0

        return {
            "iteration": self.iteration,
            "best_cost": self.best_cost,
            "iter_best_cost": iter_best_cost,
            "avg_cost": avg_cost,
            "is_new_best": is_new_best,
            "gap_percent": gap_percent,
            "routes": self.best_routes,
            "num_vehicles": len(self.best_routes),
            "info": f"{self.algorithm} a={self.alpha} b={self.beta} r={self.rho}",
        }

    def get_top_pheromone_edges(self, limit: int = 70) -> List[Tuple[int, int, float]]:
        total_nodes = self.num_customers + 1
        edges = []
        for i in range(total_nodes):
            for j in range(i + 1, total_nodes):
                edges.append((i, j, self.tau[i][j]))
        edges.sort(key=lambda item: item[2], reverse=True)
        return edges[:limit]

    def reset(self) -> None:
        self.iteration = 0
        self.best_cost = float("inf")
        self.best_routes = []
        self.best_iteration = 0
        self.stagnation_counter = 0
        self.cost_history.clear()
        self.iter_best_history.clear()
        self.iter_avg_history.clear()

        total_nodes = self.num_customers + 1
        self.tau_max = self.tau0
        self.tau_min = self.tau_max / (2.0 * max(self.num_customers, 1))
        self.tau = [[self.tau0] * total_nodes for _ in range(total_nodes)]
