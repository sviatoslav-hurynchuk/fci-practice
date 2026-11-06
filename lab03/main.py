import argparse
import os
import sys
import time
from lab03.model import BattleshipBoard
from lab03.genetic_algorithm import GeneticAlgorithmSolver
from lab03.simulated_annealing import SimulatedAnnealingSolver
from lab03.ui import BattleshipUI


def run_cli_ga(board: BattleshipBoard, max_generations: int = 500, runs: int = 1):
    for r in range(1, runs + 1):
        solver = GeneticAlgorithmSolver(board, max_generations=max_generations)
        start_time = time.perf_counter()
        found = False
        while solver.generation < max_generations:
            state = solver.step()
            if state["is_valid"]:
                found = True
                break
        elapsed = time.perf_counter() - start_time
        status_str = "ЗНАЙДЕНО 0 ПОРУШЕНЬ" if found else f"ПОРУШЕНЬ: {solver.best_violations}"
        print(f"[GA] Запуск {r}/{runs}: {status_str} | Покоління: {solver.generation} | Оцінок: {solver.evaluations_count} | Час: {elapsed:.3f} с")


def run_cli_sa(board: BattleshipBoard, max_iterations: int = 15000, runs: int = 1):
    for r in range(1, runs + 1):
        solver = SimulatedAnnealingSolver(board, max_iterations=max_iterations)
        start_time = time.perf_counter()
        found = False
        while solver.iteration < max_iterations:
            state = solver.step(batch_size=25)
            if state["is_valid"]:
                found = True
                break
        elapsed = time.perf_counter() - start_time
        status_str = "ЗНАЙДЕНО 0 ПОРУШЕНЬ" if found else f"ПОРУШЕНЬ: {solver.best_energy}"
        print(f"[SA] Запуск {r}/{runs}: {status_str} | Ітерація: {solver.iteration} | Оцінок: {solver.evaluations_count} | Час: {elapsed:.3f} с")


def main():
    parser = argparse.ArgumentParser(description="Lab 3 Combinatorial Placement Optimization")
    parser.add_argument("--variant", type=int, default=2, help="Variant number")
    parser.add_argument("--student", type=str, default="Гуринчук Святослав", help="Student name")
    parser.add_argument("--cli", action="store_true", help="Run in CLI headless mode")
    parser.add_argument("--algo", type=str, choices=["ga", "sa", "both"], default="ga", help="Algorithm for CLI mode")
    parser.add_argument("--runs", type=int, default=1, help="Number of benchmark runs for CLI mode")
    args = parser.parse_args()

    variant_file = os.path.join(os.path.dirname(__file__), f"variant{args.variant:02d}.json")
    if not os.path.exists(variant_file):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        alt_path = os.path.join(base_dir, "OneDrive", "Рабочий стол", "Політех", "ООІ Петросян", "лр3", f"variant{args.variant:02d}.json")
        if os.path.exists(alt_path):
            variant_file = alt_path
        else:
            raise FileNotFoundError(f"Variant file not found: {variant_file}")

    board = BattleshipBoard.from_json(variant_file)

    if args.cli:
        print(f"=== Лабораторна робота №3 | Варіант {args.variant} | Студент: {args.student} ===")
        print(f"Розмір поля: {board.field_size}x{board.field_size}, Кількість кораблів: {len(board.ships)}, Рифів: {len(board.reefs)}")
        if args.algo in ("ga", "both"):
            run_cli_ga(board, runs=args.runs)
        if args.algo in ("sa", "both"):
            run_cli_sa(board, runs=args.runs)
    else:
        app = BattleshipUI(
            board=board,
            variant_number=args.variant,
            student_name=args.student
        )
        app.run()


if __name__ == "__main__":
    main()
