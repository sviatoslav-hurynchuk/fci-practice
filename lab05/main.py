import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lab05.aco import AntColonySolver
from lab05.client import VRPSimClient
from lab05.ui import VRPSimUI


def locate_vrpsim() -> str:
    candidates = [
        r"c:\Users\Админ\OneDrive\Рабочий стол\Політех\ООІ Петросян\лр5\vrpsim\vrpsim_windows_x86_64.exe",
        r"c:\Users\Админ\OneDrive\Рабочий стол\Політех\ООІ Петросян\лр5\vrpsim_windows_x86_64.exe",
        os.path.join(os.path.dirname(__file__), "vrpsim_windows_x86_64.exe"),
        os.path.join(os.path.dirname(__file__), "..", "vrpsim_windows_x86_64.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "vrpsim_windows_x86_64.exe"


def load_task_data(seed: int = 2) -> Dict[str, Any]:
    task_candidates = [
        "task_v02.json",
        os.path.join(os.path.dirname(__file__), "task_v02.json"),
        os.path.join(os.path.dirname(__file__), "..", "task_v02.json"),
        r"c:\Users\Админ\OneDrive\Рабочий стол\Політех\ООІ Петросян\лр5\task_v02.json",
    ]
    for p in task_candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    exe = locate_vrpsim()
    if os.path.exists(exe):
        tmp_json = os.path.join(os.path.dirname(__file__), f"task_v{seed:02d}.json")
        subprocess.run([exe, "-seed", str(seed), "-dump", tmp_json], check=True)
        if os.path.exists(tmp_json):
            with open(tmp_json, "r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError(f"Could not load task data for seed {seed}")


def run_headless(args: argparse.Namespace) -> None:
    task = load_task_data(seed=args.seed)
    client = VRPSimClient(host=args.host, port=args.port)
    server_connected = False
    proc = None

    try:
        try:
            client.connect()
            server_connected = True
        except Exception:
            exe = locate_vrpsim()
            if os.path.exists(exe):
                proc = subprocess.Popen([exe, "-seed", str(args.seed), "-port", str(args.port), "-headless"])
                time.sleep(1.0)
                client.connect()
                server_connected = True
            else:
                raise

        solver = AntColonySolver(
            task=task,
            algorithm=args.algorithm,
            num_ants=args.ants,
            alpha=args.alpha,
            beta=args.beta,
            gamma=args.gamma,
            rho=args.rho,
            use_2opt=True,
            use_relocate=True,
        )

        ref_cost = solver.reference_cost
        print(f"Task: {task.get('name', 'V02')} | Customers: {solver.num_customers} | Ref: {ref_cost:.2f}")

        t0 = time.time()
        for it in range(1, args.iterations + 1):
            res = solver.step()
            routes = res["routes"]
            best_cost = res["best_cost"]
            gap = res["gap_percent"]

            if server_connected:
                try:
                    srv_res = client.send_solution(routes=routes, iteration=it, info=res["info"])
                    if it % 8 == 0:
                        client.send_pheromone(solver.get_top_pheromone_edges(limit=60))
                except Exception:
                    pass

            if res["is_new_best"] or it % 20 == 0 or it == args.iterations:
                print(f"Iter {it:3d}/{args.iterations}: Best = {best_cost:.2f} (Gap = {gap:+.2f}%) Vehicles = {len(routes)}")

        elapsed = time.time() - t0
        print(f"Completed in {elapsed:.2f}s! Best = {solver.best_cost:.2f} (Gap = {(solver.best_cost - ref_cost)/ref_cost*100:+.2f}%)")

        best_dict = {
            "routes": solver.best_routes,
            "cost": solver.best_cost,
            "reference_cost": ref_cost,
            "gap_percent": (solver.best_cost - ref_cost) / ref_cost * 100.0,
            "iteration": solver.best_iteration,
            "vehicles": len(solver.best_routes),
            "algorithm": solver.algorithm,
            "params": {"alpha": solver.alpha, "beta": solver.beta, "gamma": solver.gamma, "rho": solver.rho, "m": solver.num_ants},
        }
        out_path = os.path.join(os.path.dirname(__file__), "best_solution_v02.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(best_dict, f, ensure_ascii=False, indent=2)
        print(f"Saved best solution to {out_path}")

    finally:
        client.close()
        if proc:
            proc.terminate()
            proc.wait()


def run_benchmark_experiments() -> None:
    task = load_task_data(seed=2)
    ref_cost = float(task.get("reference_cost", 6558.59))

    print("Running systematic benchmark experiments for Lab 5...")
    results: Dict[str, Any] = {"task": "V02", "reference_cost": ref_cost, "experiments": {}}

    beta_values = [1.0, 3.0, 5.0]
    beta_records = []
    for b_val in beta_values:
        gaps = []
        iters = []
        times = []
        best_of_runs = float("inf")
        for r_idx in range(5):
            solver = AntColonySolver(task=task, algorithm="MMAS", num_ants=35, alpha=1.0, beta=b_val, gamma=1.2, rho=0.1, use_2opt=True, use_relocate=True, seed=r_idx * 17 + 1)
            t0 = time.time()
            for it in range(1, 101):
                solver.step()
            el = time.time() - t0
            gap = (solver.best_cost - ref_cost) / ref_cost * 100.0
            gaps.append(gap)
            iters.append(solver.best_iteration)
            times.append(el)
            if solver.best_cost < best_of_runs:
                best_of_runs = solver.best_cost
        avg_gap = sum(gaps) / len(gaps)
        min_gap = (best_of_runs - ref_cost) / ref_cost * 100.0
        avg_iter = sum(iters) / len(iters)
        avg_time = sum(times) / len(times)
        beta_records.append({"beta": b_val, "avg_gap": round(avg_gap, 2), "best_gap": round(min_gap, 2), "best_cost": round(best_of_runs, 2), "avg_iter": round(avg_iter, 1), "avg_time": round(avg_time, 2)})
        print(f"Beta = {b_val}: Avg Gap = {avg_gap:+.2f}%, Best = {best_of_runs:.2f} ({min_gap:+.2f}%), Avg Time = {avg_time:.2f}s")

    results["experiments"]["beta_study"] = beta_records

    m_values = [15, 35, 60]
    m_records = []
    for m_val in m_values:
        gaps = []
        times = []
        best_of_runs = float("inf")
        for r_idx in range(5):
            solver = AntColonySolver(task=task, algorithm="MMAS", num_ants=m_val, alpha=1.0, beta=3.0, gamma=1.2, rho=0.1, use_2opt=True, use_relocate=True, seed=r_idx * 23 + 3)
            t0 = time.time()
            for it in range(1, 101):
                solver.step()
            el = time.time() - t0
            gap = (solver.best_cost - ref_cost) / ref_cost * 100.0
            gaps.append(gap)
            times.append(el)
            if solver.best_cost < best_of_runs:
                best_of_runs = solver.best_cost
        avg_gap = sum(gaps) / len(gaps)
        min_gap = (best_of_runs - ref_cost) / ref_cost * 100.0
        avg_time = sum(times) / len(times)
        m_records.append({"m": m_val, "avg_gap": round(avg_gap, 2), "best_gap": round(min_gap, 2), "best_cost": round(best_of_runs, 2), "avg_time": round(avg_time, 2)})
        print(f"m = {m_val}: Avg Gap = {avg_gap:+.2f}%, Best = {best_of_runs:.2f} ({min_gap:+.2f}%), Avg Time = {avg_time:.2f}s")

    results["experiments"]["m_study"] = m_records

    rho_values = [0.05, 0.1, 0.2]
    rho_records = []
    for r_val in rho_values:
        gaps = []
        times = []
        best_of_runs = float("inf")
        for r_idx in range(5):
            solver = AntColonySolver(task=task, algorithm="MMAS", num_ants=35, alpha=1.0, beta=3.0, gamma=1.2, rho=r_val, use_2opt=True, use_relocate=True, seed=r_idx * 31 + 7)
            t0 = time.time()
            for it in range(1, 101):
                solver.step()
            el = time.time() - t0
            gap = (solver.best_cost - ref_cost) / ref_cost * 100.0
            gaps.append(gap)
            times.append(el)
            if solver.best_cost < best_of_runs:
                best_of_runs = solver.best_cost
        avg_gap = sum(gaps) / len(gaps)
        min_gap = (best_of_runs - ref_cost) / ref_cost * 100.0
        avg_time = sum(times) / len(times)
        rho_records.append({"rho": r_val, "avg_gap": round(avg_gap, 2), "best_gap": round(min_gap, 2), "best_cost": round(best_of_runs, 2), "avg_time": round(avg_time, 2)})
        print(f"rho = {r_val}: Avg Gap = {avg_gap:+.2f}%, Best = {best_of_runs:.2f} ({min_gap:+.2f}%), Avg Time = {avg_time:.2f}s")

    results["experiments"]["rho_study"] = rho_records

    algo_names = ["AS", "EAS", "MMAS", "ACS"]
    algo_records = []
    for a_name in algo_names:
        gaps = []
        times = []
        best_of_runs = float("inf")
        for r_idx in range(5):
            solver = AntColonySolver(task=task, algorithm=a_name, num_ants=35, alpha=1.0, beta=3.0, gamma=1.2, rho=0.1, use_2opt=True, use_relocate=True, seed=r_idx * 41 + 11)
            t0 = time.time()
            for it in range(1, 101):
                solver.step()
            el = time.time() - t0
            gap = (solver.best_cost - ref_cost) / ref_cost * 100.0
            gaps.append(gap)
            times.append(el)
            if solver.best_cost < best_of_runs:
                best_of_runs = solver.best_cost
        avg_gap = sum(gaps) / len(gaps)
        min_gap = (best_of_runs - ref_cost) / ref_cost * 100.0
        avg_time = sum(times) / len(times)
        algo_records.append({"algorithm": a_name, "avg_gap": round(avg_gap, 2), "best_gap": round(min_gap, 2), "best_cost": round(best_of_runs, 2), "avg_time": round(avg_time, 2)})
        print(f"Algo = {a_name}: Avg Gap = {avg_gap:+.2f}%, Best = {best_of_runs:.2f} ({min_gap:+.2f}%), Avg Time = {avg_time:.2f}s")

    results["experiments"]["algo_study"] = algo_records

    out_file = os.path.join(os.path.dirname(__file__), "experiments_results_v02.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nAll benchmark results saved to {out_file}!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lab 5 Ant Colony Optimization for CVRP")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=47560)
    parser.add_argument("--seed", type=int, default=2)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--iterations", type=int, default=150)
    parser.add_argument("--algorithm", type=str, default="MMAS")
    parser.add_argument("--ants", type=int, default=35)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=3.0)
    parser.add_argument("--gamma", type=float, default=1.2)
    parser.add_argument("--rho", type=float, default=0.1)

    args = parser.parse_args()

    if args.benchmark:
        run_benchmark_experiments()
    elif args.headless:
        run_headless(args)
    else:
        app = VRPSimUI(host=args.host, port=args.port, variant_seed=args.seed)
        app.run()


if __name__ == "__main__":
    main()
