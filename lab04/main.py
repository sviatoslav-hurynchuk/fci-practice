import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lab04.client import DockSimClient
from lab04.policy import TabularPolicy
from lab04.manual import ManualController
from lab04.genetic_algorithm import GeneticAlgorithmTrainer, evaluate_individual_client
from lab04.ui import DockSimUI


def find_docksim_exe():
    candidates = [
        r"c:\Users\Админ\OneDrive\Рабочий стол\Політех\ООІ Петросян\лр4\V02\docksim_V02_windows_amd64.exe",
        os.path.join(os.path.dirname(__file__), "..", "..", "OneDrive", "Рабочий стол", "Політех", "ООІ Петросян", "лр4", "V02", "docksim_V02_windows_amd64.exe"),
        os.path.join(os.path.dirname(__file__), "V02", "docksim_V02_windows_amd64.exe"),
        os.path.join(os.path.dirname(__file__), "..", "V02", "docksim_V02_windows_amd64.exe"),
        os.path.join("V02", "docksim_V02_windows_amd64.exe"),
        "docksim_V02_windows_amd64.exe"
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None


def run_cli_train(port: int = 47555, generations: int = 15, pop_size: int = 30, workers: int = 1, out_file: str = "best_policy_v02.json"):
    server_proc = None
    try:
        c = DockSimClient(port=port)
        c.close()
    except Exception:
        exe = find_docksim_exe()
        if exe:
            print(f"Запуск сервера DockSim у режимі train на порту {port}...")
            server_proc = subprocess.Popen([exe, "--mode", "train", "--port", str(port)])
            time.sleep(1.2)

    print(f"=== Початок навчання генетичного алгоритму (GA) | Популяція: {pop_size}, Поколінь: {generations} ===")
    try:
        trainer = GeneticAlgorithmTrainer(pop_size=pop_size, port=port, workers=workers)
        t0 = time.perf_counter()

        for gen in range(1, generations + 1):
            st = trainer.step()
            b_ev = st["best_eval"]
            dock_cnt = b_ev.get("docked_count", 0)
            fit = st["best_fitness"]
            avg_fit = st["avg_fitness"]
            rate = st["best_dock_rate"]
            print(f"Покоління {gen:2d}/{generations:2d} | Фітнес: {fit:6.1f} (сер: {avg_fit:6.1f}) | Стикування: {rate:5.1f}% ({dock_cnt} шт) | Час: {time.perf_counter()-t0:.1f}с")

        elapsed = time.perf_counter() - t0
        best_policy = TabularPolicy(chromosome=trainer.best_individual)
        best_policy.save_json(out_file)
        print(f"=== Навчання завершено за {elapsed:.2f} с! Найкращу політику збережено у: {out_file} ===")
        return best_policy
    finally:
        if server_proc:
            server_proc.terminate()


def run_cli_evaluate_auto(port: int = 47555, policy_file: str = "best_policy_v02.json"):
    if not os.path.exists(policy_file):
        pol = TabularPolicy(mode="separate")
    else:
        pol = TabularPolicy.load_json(policy_file)

    client = DockSimClient(port=port)
    print(f"=== Підключено до режиму оцінювання (Evaluate Auto) | Варіант: {client.hello.get('variant')} ===")
    try:
        seeds_count = 10
        docked = 0
        for ep in range(1, seeds_count + 1):
            st = client.reset()
            step_n = 0
            while not st.get("done", False):
                step_n += 1
                th, tu = pol.get_action(st)
                st = client.step(th, tu)

            res = st.get("result")
            stats = st.get("stats", {})
            if res == "docked":
                docked += 1
            print(f"Епізод {ep:2d}/10: {res:14s} | Час: {stats.get('time', 0):.1f} с | Паливо: {stats.get('fuel_used', 0):.1f} | Final: {stats.get('final')}")

        print(f"\nПідсумок заліку: {docked}/10 успішних стикувань!")
        if client.last_report:
            print("Збережено офіційний підписаний звіт!")
    finally:
        client.close()


def run_cli_evaluate_manual(port: int = 47555):
    client = DockSimClient(port=port)
    print(f"=== Підключено до режиму ручного оцінювання (Evaluate Manual) | Варіант: {client.hello.get('variant')} ===")
    try:
        def on_event(ev_type, data):
            if ev_type == "episode_end":
                st = data["state"]
                ep = data["episode"]
                print(f"Епізод {ep:2d}/10: {st.get('result'):14s} | Stats: {st.get('stats')}")

        ManualController.run_session(client, max_episodes=10, callback=on_event)
        if client.last_report:
            print("Збережено офіційний підписаний звіт ручного заліку!")
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Lab 4 DockSim Spacecraft Docking Control")
    parser.add_argument("--port", type=int, default=47555, help="DockSim port")
    parser.add_argument("--cli", action="store_true", help="Run in CLI headless mode")
    parser.add_argument("--train", action="store_true", help="Run GA training in CLI")
    parser.add_argument("--eval-auto", action="store_true", help="Run official evaluate with trained policy")
    parser.add_argument("--eval-manual", action="store_true", help="Run official evaluate with manual keyboard control")
    parser.add_argument("--generations", type=int, default=15, help="Number of GA generations")
    parser.add_argument("--pop-size", type=int, default=30, help="GA population size")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers for training")
    parser.add_argument("--policy", type=str, default="best_policy_v02.json", help="Path to policy JSON")
    args = parser.parse_args()

    if args.train:
        run_cli_train(port=args.port, generations=args.generations, pop_size=args.pop_size, workers=args.workers, out_file=args.policy)
    elif args.eval_auto:
        run_cli_evaluate_auto(port=args.port, policy_file=args.policy)
    elif args.eval_manual:
        run_cli_evaluate_manual(port=args.port)
    elif args.cli:
        print("DockSim CLI Client ready. Use --train, --eval-auto or --eval-manual.")
    else:
        app = DockSimUI(port=args.port)
        app.run()


if __name__ == "__main__":
    main()
