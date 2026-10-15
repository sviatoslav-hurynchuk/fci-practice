import math
import tkinter as tk
from tkinter import ttk
from typing import Callable


class FoxHuntUI:
    def __init__(
        self,
        grid: list[list[int]],
        width: int,
        height: int,
        step_callback: Callable[[], dict],
        variant_number: int,
        student_name: str = "Гуринчук С. М."
    ):
        self.grid = grid
        self.grid_w = width
        self.grid_h = height
        self.step_callback = step_callback
        self.variant_number = variant_number
        self.student_name = student_name

        self.root = tk.Tk()
        self.root.title(f"Лабораторна робота №2 {self.student_name.split()[0]}")
        self.root.geometry("1100x700")
        self.root.configure(bg="#0F172A")
        self.root.minsize(1000, 650)

        self.is_running = False
        self.cell_size = 5.2
        self.canvas_w = int(self.grid_w * self.cell_size)
        self.canvas_h = int(self.grid_h * self.cell_size)

        self.fox_coords: list[tuple[int, int, int]] = []
        self.trajectory_points: list[tuple[float, float]] = []
        self.temp_history: list[float] = []
        self.signal_history: list[float] = []

        self._build_ui()
        self._draw_grid_static()

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#1E293B", height=50)
        header.pack(fill=tk.X, side=tk.TOP)

        lbl_title = tk.Label(
            header,
            text=f"Оптимізація імітацією відпалу (Simulated Annealing) — Варіант {self.variant_number}",
            font=("Segoe UI", 12, "bold"),
            bg="#1E293B",
            fg="#F8FAFC"
        )
        lbl_title.pack(side=tk.LEFT, padx=16, pady=10)

        lbl_author = tk.Label(
            header,
            text=f"Студент: {self.student_name}",
            font=("Segoe UI", 10),
            bg="#1E293B",
            fg="#94A3B8"
        )
        lbl_author.pack(side=tk.RIGHT, padx=16, pady=10)

        main_box = tk.Frame(self.root, bg="#0F172A")
        main_box.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        left_frame = tk.Frame(main_box, bg="#1E293B", bd=1, relief=tk.SOLID)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        lbl_map = tk.Label(
            left_frame,
            text="Карта пошуку 100x100 (Перешкоди, Траєкторія, Об'єкти)",
            font=("Segoe UI", 9, "bold"),
            bg="#1E293B",
            fg="#CBD5E1"
        )
        lbl_map.pack(anchor="w", padx=8, pady=(6, 2))

        self.canvas = tk.Canvas(
            left_frame,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#020617",
            highlightthickness=0
        )
        self.canvas.pack(padx=8, pady=8)

        right_frame = tk.Frame(main_box, bg="#0F172A")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        telemetry_box = tk.LabelFrame(
            right_frame,
            text=" Телеметрія та стан пошуку ",
            font=("Segoe UI", 10, "bold"),
            bg="#1E293B",
            fg="#38BDF8",
            bd=1,
            relief=tk.SOLID
        )
        telemetry_box.pack(fill=tk.X, pady=(0, 10))

        grid_t = tk.Frame(telemetry_box, bg="#1E293B")
        grid_t.pack(fill=tk.X, padx=10, pady=8)

        self.var_step = tk.StringVar(value="0")
        self.var_foxes = tk.StringVar(value="3")
        self.var_pos = tk.StringVar(value="(0, 0)")
        self.var_signal = tk.StringVar(value="0.0000")
        self.var_temp = tk.StringVar(value="50.00°")
        self.var_radius = tk.StringVar(value="30 кл.")

        params = [
            ("Крок:", self.var_step, "#FFFFFF"),
            ("Лисиць лишилось:", self.var_foxes, "#F87171"),
            ("Координати:", self.var_pos, "#FCD34D"),
            ("Рівень сигналу S:", self.var_signal, "#34D399"),
            ("Температура T:", self.var_temp, "#60A5FA"),
            ("Радіус пошуку R:", self.var_radius, "#A78BFA"),
        ]

        for i, (label, s_var, color) in enumerate(params):
            r = i // 2
            c = (i % 2) * 2
            tk.Label(grid_t, text=label, font=("Segoe UI", 9), bg="#1E293B", fg="#94A3B8").grid(
                row=r, column=c, sticky="w", padx=6, pady=3
            )
            tk.Label(grid_t, textvariable=s_var, font=("Consolas", 10, "bold"), bg="#1E293B", fg=color).grid(
                row=r, column=c + 1, sticky="w", padx=6, pady=3
            )

        chart_box = tk.LabelFrame(
            right_frame,
            text=" Динаміка охолодження та сигналу ",
            font=("Segoe UI", 10, "bold"),
            bg="#1E293B",
            fg="#38BDF8",
            bd=1,
            relief=tk.SOLID
        )
        chart_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.chart_canvas = tk.Canvas(
            chart_box,
            bg="#020617",
            highlightthickness=0,
            height=200
        )
        self.chart_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ctrl_frame = tk.Frame(right_frame, bg="#0F172A")
        ctrl_frame.pack(fill=tk.X)

        self.btn_run = tk.Button(
            ctrl_frame,
            text="Запустити пошук",
            command=self._toggle_run,
            font=("Segoe UI", 10, "bold"),
            bg="#0284C7",
            fg="#FFFFFF",
            activebackground="#0369A1",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2"
        )
        self.btn_run.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_status = tk.Label(
            ctrl_frame,
            text="Готовий до запуску",
            font=("Segoe UI", 9, "italic"),
            bg="#0F172A",
            fg="#94A3B8"
        )
        self.lbl_status.pack(side=tk.LEFT, padx=8)

    def _draw_grid_static(self):
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                if self.grid[y][x] == 1:
                    x0 = x * self.cell_size
                    y0 = y * self.cell_size
                    x1 = x0 + self.cell_size
                    y1 = y0 + self.cell_size
                    self.canvas.create_rectangle(x0, y0, x1, y1, fill="#334155", outline="")

    def _toggle_run(self):
        if self.is_running:
            self.is_running = False
            self.btn_run.config(text="Продовжити", bg="#0284C7")
            self.lbl_status.config(text="Пошук призупинено")
        else:
            self.is_running = True
            self.btn_run.config(text="Пауза", bg="#D97706")
            self.lbl_status.config(text="Йде процес полювання...")
            self._loop_step()

    def _loop_step(self):
        if not self.is_running:
            return

        state = self.step_callback()
        self._update_state(state)

        if state["status"] == "completed":
            self.is_running = False
            self.btn_run.config(text="Завершено", state=tk.DISABLED, bg="#16A34A")
            self.lbl_status.config(text=f"Усіх лисиць знайдено за {state['step']} кроків!")
            return

        self.root.after(20, self._loop_step)

    def _update_state(self, state: dict):
        x = state["x"]
        y = state["y"]
        cx = (x + 0.5) * self.cell_size
        cy = (y + 0.5) * self.cell_size

        if self.trajectory_points:
            px, py = self.trajectory_points[-1]
            self.canvas.create_line(px, py, cx, cy, fill="#0284C7", width=1.5)
        self.trajectory_points.append((cx, cy))

        self.canvas.delete("agent")
        r = 3.5
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#38BDF8", outline="#FFFFFF", tags="agent")

        if state.get("fox_caught"):
            fx, fy = cx, cy
            self.canvas.create_oval(fx - 5, fy - 5, fx + 5, fy + 5, fill="#EF4444", outline="#FDE047", width=2)
            self.canvas.create_text(fx, fy - 8, text=f"#{state['step']}", fill="#FDE047", font=("Segoe UI", 7, "bold"))

        self.var_step.set(str(state["step"]))
        self.var_foxes.set(str(state["remaining_foxes"]))
        self.var_pos.set(f"({x}, {y})")
        self.var_signal.set(f"{state['signal']:.4f}")
        self.var_temp.set(f"{state['temperature']:.2f}°")
        self.var_radius.set(f"{state['radius']} кл.")

        self.temp_history.append(state["temperature"])
        self.signal_history.append(state["signal"])
        self._draw_charts()

    def _draw_charts(self):
        c = self.chart_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10 or len(self.temp_history) < 2:
            return

        c.create_line(35, 10, 35, h - 20, fill="#475569")
        c.create_line(35, h - 20, w - 10, h - 20, fill="#475569")

        c.create_text(20, 15, text="T, S", fill="#94A3B8", font=("Segoe UI", 8))
        c.create_text(w - 20, h - 10, text="Крок", fill="#94A3B8", font=("Segoe UI", 8))

        n = len(self.temp_history)
        max_t = max(max(self.temp_history), 50.0)
        max_s = max(max(self.signal_history), 1.0)

        step_x = (w - 50) / max(n - 1, 1)

        t_coords = []
        s_coords = []
        for i in range(n):
            px = 35 + i * step_x
            py_t = (h - 20) - (self.temp_history[i] / max_t) * (h - 35)
            py_s = (h - 20) - (self.signal_history[i] / max_s) * (h - 35)
            t_coords.extend([px, py_t])
            s_coords.extend([px, py_s])

        if len(t_coords) >= 4:
            c.create_line(*t_coords, fill="#60A5FA", width=1.5)
        if len(s_coords) >= 4:
            c.create_line(*s_coords, fill="#34D399", width=1.5)

    def run(self):
        self.root.mainloop()
