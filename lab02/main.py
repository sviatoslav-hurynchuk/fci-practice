import argparse
import sys
from lab02.api import FoxHuntAPI
from lab02.simulated_annealing import SimulatedAnnealingHunter
from lab02.ui import FoxHuntUI


def main():
    parser = argparse.ArgumentParser(description="Fox Hunt Simulated Annealing Client")
    parser.add_argument("--variant", type=int, default=2, help="Variant number")
    parser.add_argument("--student", type=str, default="Гуринчук Святослав", help="Student name")
    parser.add_argument("--cli", action="store_true", help="Run in CLI headless mode")
    args = parser.parse_args()

    api = FoxHuntAPI()
    data = api.start_session(args.student, args.variant)

    grid = data["map"]
    w = data["map_size"]["width"]
    h = data["map_size"]["height"]
    sx = data["start_position"]["x"]
    sy = data["start_position"]["y"]

    hunter = SimulatedAnnealingHunter(
        grid=grid,
        width=w,
        height=h,
        start_x=sx,
        start_y=sy,
        move_fn=api.make_move
    )

    if args.cli:
        print(f"Старт полювання: варіант {args.variant}, студент {args.student}")
        while True:
            st = hunter.run_step()
            if st.get("fox_caught"):
                print(f"Лисицю знайдено! Залишилося: {st['remaining_foxes']}, крок {st['step']}")
            if st["status"] == "completed":
                print(f"Полювання успішно завершено за {st['step']} кроків!")
                break
            if st["status"] == "stuck":
                print("Пошук застряг.")
                break
    else:
        app = FoxHuntUI(
            grid=grid,
            width=w,
            height=h,
            step_callback=hunter.run_step,
            variant_number=args.variant,
            student_name=args.student
        )
        app.run()


if __name__ == "__main__":
    main()
