import json
import math
import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional, Tuple

from lab05.aco import AntColonySolver
from lab05.client import VRPSimClient


class VRPSimUI:
    ROUTE_COLORS = [
        "#38BDF8",
        "#34D399",
        "#F43F5E",
        "#A855F7",
        "#FBBF24",
        "#2DD4BF",
        "#FB923C",
        "#818CF8",
        "#E879F9",
    ]

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 47560,
        variant_seed: int = 2,
        student_name: str = "Гуринчук Святослав",
    ):
        self.host = host
        self.port = port
        self.variant_seed = variant_seed
        self.student_name = student_name

        self.root = tk.Tk()
        short_name = self.student_name.split()[0]
        self.root.title(f"Лабораторна робота №5 {short_name}")
        self.root.geometry("1240x840")
        self.root.minsize(1080, 720)
        self.root.configure(bg="#F1F5F9")

        self.client: Optional[VRPSimClient] = None
        self.solver: Optional[AntColonySolver] = None
        self.task: Dict[str, Any] = {}
        self.reference_cost = 6558.59

        self.is_connected = False
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_requested = False

        self.algo_var = tk.StringVar(value="MMAS")
        self.ants_var = tk.IntVar(value=35)
        self.alpha_var = tk.DoubleVar(value=1.0)
        self.beta_var = tk.DoubleVar(value=3.0)
        self.gamma_var = tk.DoubleVar(value=1.2)
        self.rho_var = tk.DoubleVar(value=0.1)
        self.two_opt_var = tk.BooleanVar(value=True)
        self.relocate_var = tk.BooleanVar(value=True)
        self.show_pheromone_var = tk.BooleanVar(value=True)

        self.status_var = tk.StringVar(value="● Очікування підключення")
        self.cost_var = tk.StringVar(value="-")
        self.ref_cost_var = tk.StringVar(value="6558.59")
        self.gap_var = tk.StringVar(value="-")
        self.iter_var = tk.StringVar(value="0")
        self.vehicles_var = tk.StringVar(value="- / 7")
        self.valid_var = tk.StringVar(value="Очікування")

        self.build_ui()
        self.try_preload_offline_task()

    def build_ui(self) -> None:
        top_bar = tk.Frame(self.root, bg="#FFFFFF", padx=14, pady=10, relief=tk.FLAT, bd=0)
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(10, 6))

        title_lbl = tk.Label(top_bar, text="CVRP Ant Colony Optimizer (V02)", font=("Arial", 12, "bold"), bg="#FFFFFF", fg="#0F172A")
        title_lbl.pack(side=tk.LEFT, padx=(0, 14))

        self.btn_connect = tk.Button(top_bar, text="Підключитись", bg="#0284C7", fg="#FFFFFF", font=("Arial", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.toggle_connection)
        self.btn_connect.pack(side=tk.LEFT, padx=3)

        self.btn_start = tk.Button(top_bar, text="▶ Старт", bg="#059669", fg="#FFFFFF", font=("Arial", 9, "bold"), relief=tk.FLAT, padx=10, pady=4, cursor="hand2", state=tk.DISABLED, command=self.toggle_start)
        self.btn_start.pack(side=tk.LEFT, padx=3)

        self.btn_step = tk.Button(top_bar, text="Покроково", bg="#F8FAFC", fg="#334155", font=("Arial", 9), relief=tk.SOLID, bd=1, padx=8, pady=4, cursor="hand2", state=tk.DISABLED, command=self.run_single_step)
        self.btn_step.pack(side=tk.LEFT, padx=3)

        self.btn_reset = tk.Button(top_bar, text="Скинути", bg="#F8FAFC", fg="#334155", font=("Arial", 9), relief=tk.SOLID, bd=1, padx=8, pady=4, cursor="hand2", state=tk.DISABLED, command=self.reset_optimizer)
        self.btn_reset.pack(side=tk.LEFT, padx=3)

        sep1 = tk.Frame(top_bar, width=1, height=24, bg="#E2E8F0")
        sep1.pack(side=tk.LEFT, padx=8)

        tk.Label(top_bar, text="Алгоритм:", font=("Arial", 9), bg="#FFFFFF", fg="#64748B").pack(side=tk.LEFT, padx=2)
        algo_combo = ttk.Combobox(top_bar, textvariable=self.algo_var, values=["MMAS", "ACS", "EAS", "AS"], width=6, state="readonly")
        algo_combo.pack(side=tk.LEFT, padx=3)
        algo_combo.bind("<<ComboboxSelected>>", self.on_algo_change)

        tk.Label(top_bar, text="m:", font=("Arial", 9), bg="#FFFFFF", fg="#64748B").pack(side=tk.LEFT, padx=(6, 1))
        tk.Spinbox(top_bar, from_=5, to=100, increment=5, textvariable=self.ants_var, width=3, font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        tk.Label(top_bar, text="α:", font=("Arial", 9), bg="#FFFFFF", fg="#64748B").pack(side=tk.LEFT, padx=(4, 1))
        tk.Spinbox(top_bar, from_=0.0, to=5.0, increment=0.2, textvariable=self.alpha_var, width=3, font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        tk.Label(top_bar, text="β:", font=("Arial", 9), bg="#FFFFFF", fg="#64748B").pack(side=tk.LEFT, padx=(4, 1))
        tk.Spinbox(top_bar, from_=0.5, to=10.0, increment=0.5, textvariable=self.beta_var, width=3, font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        tk.Label(top_bar, text="ρ:", font=("Arial", 9), bg="#FFFFFF", fg="#64748B").pack(side=tk.LEFT, padx=(4, 1))
        tk.Spinbox(top_bar, from_=0.02, to=0.5, increment=0.02, textvariable=self.rho_var, width=4, font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        chk_opt = tk.Checkbutton(top_bar, text="2-opt", variable=self.two_opt_var, bg="#FFFFFF", font=("Arial", 8), activebackground="#FFFFFF")
        chk_opt.pack(side=tk.LEFT, padx=(6, 2))

        chk_ph = tk.Checkbutton(top_bar, text="Феромон", variable=self.show_pheromone_var, bg="#FFFFFF", font=("Arial", 8), activebackground="#FFFFFF", command=self.redraw_map)
        chk_ph.pack(side=tk.LEFT, padx=2)

        self.lbl_status = tk.Label(top_bar, textvariable=self.status_var, font=("Arial", 9, "bold"), fg="#64748B", bg="#F1F5F9", padx=8, pady=3)
        self.lbl_status.pack(side=tk.RIGHT, padx=4)

        main_pane = tk.Frame(self.root, bg="#F1F5F9")
        main_pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        map_card = tk.Frame(main_pane, bg="#FFFFFF", relief=tk.FLAT, bd=0)
        map_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        map_header = tk.Frame(map_card, bg="#FFFFFF", padx=12, pady=6)
        map_header.pack(side=tk.TOP, fill=tk.X)
        tk.Label(map_header, text="Карта маршрутизації CVRP (1000 × 1000)", font=("Arial", 10, "bold"), bg="#FFFFFF", fg="#1E293B").pack(side=tk.LEFT)

        self.canvas_map = tk.Canvas(map_card, bg="#0F172A", highlightthickness=0)
        self.canvas_map.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.canvas_map.bind("<Configure>", lambda e: self.redraw_map())

        right_panel = tk.Frame(main_pane, bg="#F1F5F9", width=420)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(6, 0))
        right_panel.pack_propagate(False)

        telemetry_card = tk.Frame(right_panel, bg="#FFFFFF", relief=tk.FLAT, bd=0, padx=10, pady=8)
        telemetry_card.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))

        tk.Label(telemetry_card, text="Телеметрія оптимізації", font=("Arial", 10, "bold"), bg="#FFFFFF", fg="#1E293B").pack(side=tk.TOP, anchor="w", pady=(0, 6))

        metrics_grid = tk.Frame(telemetry_card, bg="#FFFFFF")
        metrics_grid.pack(side=tk.TOP, fill=tk.X)

        self.add_metric_box(metrics_grid, 0, 0, "Найкраща довжина", self.cost_var, "#0284C7")
        self.add_metric_box(metrics_grid, 0, 1, "Еталон (reference)", self.ref_cost_var, "#64748B")
        self.add_metric_box(metrics_grid, 1, 0, "Відхилення (gap)", self.gap_var, "#059669")
        self.add_metric_box(metrics_grid, 1, 1, "Ітерація пошуку", self.iter_var, "#0F172A")
        self.add_metric_box(metrics_grid, 2, 0, "Машин використано", self.vehicles_var, "#7C3AED")
        self.add_metric_box(metrics_grid, 2, 1, "Статус розв'язку", self.valid_var, "#059669")

        chart_card = tk.Frame(right_panel, bg="#FFFFFF", relief=tk.FLAT, bd=0, padx=10, pady=8)
        chart_card.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 6))

        tk.Label(chart_card, text="Динаміка збіжності колонії (довжина vs ітерації)", font=("Arial", 10, "bold"), bg="#FFFFFF", fg="#1E293B").pack(side=tk.TOP, anchor="w", pady=(0, 4))

        self.canvas_chart = tk.Canvas(chart_card, bg="#F8FAFC", highlightthickness=1, highlightbackground="#E2E8F0")
        self.canvas_chart.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas_chart.bind("<Configure>", lambda e: self.redraw_chart())

        routes_card = tk.Frame(right_panel, bg="#FFFFFF", relief=tk.FLAT, bd=0, padx=10, pady=8)
        routes_card.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Label(routes_card, text="Відомість завантаження машин (routes)", font=("Arial", 10, "bold"), bg="#FFFFFF", fg="#1E293B").pack(side=tk.TOP, anchor="w", pady=(0, 4))

        self.tree_routes = ttk.Treeview(routes_card, columns=("vehicle", "load", "length", "stops"), show="headings", height=5)
        self.tree_routes.heading("vehicle", text="Машина")
        self.tree_routes.heading("load", text="Вантаж")
        self.tree_routes.heading("length", text="Довжина")
        self.tree_routes.heading("stops", text="Клієнтів")
        self.tree_routes.column("vehicle", width=65, anchor="center")
        self.tree_routes.column("load", width=75, anchor="center")
        self.tree_routes.column("length", width=80, anchor="center")
        self.tree_routes.column("stops", width=65, anchor="center")
        self.tree_routes.pack(side=tk.TOP, fill=tk.X)

    def add_metric_box(self, parent: tk.Frame, r: int, c: int, title: str, var: tk.StringVar, color: str) -> None:
        box = tk.Frame(parent, bg="#F8FAFC", relief=tk.SOLID, bd=1, padx=6, pady=4)
        box.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
        parent.grid_columnconfigure(c, weight=1)

        t_lbl = tk.Label(box, text=title, font=("Arial", 8), bg="#F8FAFC", fg="#64748B")
        t_lbl.pack(side=tk.TOP, anchor="w")

        v_lbl = tk.Label(box, textvariable=var, font=("Arial", 10, "bold"), bg="#F8FAFC", fg=color)
        v_lbl.pack(side=tk.TOP, anchor="w")

    def on_algo_change(self, event=None) -> None:
        if self.solver:
            self.solver.algorithm = self.algo_var.get().upper()

    def try_preload_offline_task(self) -> None:
        candidates = [
            "task_v02.json",
            os.path.join(os.path.dirname(__file__), "task_v02.json"),
            os.path.join(os.path.dirname(__file__), "..", "task_v02.json"),
            r"c:\Users\Админ\OneDrive\Рабочий стол\Політех\ООІ Петросян\лр5\task_v02.json",
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        self.task = json.load(f)
                    self.init_solver_from_task()
                    self.redraw_map()
                    self.btn_start.configure(state=tk.NORMAL)
                    self.btn_step.configure(state=tk.NORMAL)
                    self.btn_reset.configure(state=tk.NORMAL)
                    break
                except Exception:
                    pass

    def init_solver_from_task(self) -> None:
        if not self.task:
            return
        self.reference_cost = float(self.task.get("reference_cost", 6558.59))
        self.ref_cost_var.set(f"{self.reference_cost:.2f}")

        self.solver = AntColonySolver(
            task=self.task,
            algorithm=self.algo_var.get(),
            num_ants=self.ants_var.get(),
            alpha=self.alpha_var.get(),
            beta=self.beta_var.get(),
            gamma=self.gamma_var.get(),
            rho=self.rho_var.get(),
            use_2opt=self.two_opt_var.get(),
            use_relocate=self.relocate_var.get(),
        )

    def locate_vrpsim_executable(self) -> Optional[str]:
        candidates = [
            r"c:\Users\Админ\OneDrive\Рабочий стол\Політех\ООІ Петросян\лр5\vrpsim\vrpsim_windows_x86_64.exe",
            r"c:\Users\Админ\OneDrive\Рабочий стол\Політех\ООІ Петросян\лр5\vrpsim_windows_x86_64.exe",
            os.path.join(os.path.dirname(__file__), "vrpsim_windows_x86_64.exe"),
            os.path.join(os.path.dirname(__file__), "..", "vrpsim_windows_x86_64.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def toggle_connection(self) -> None:
        if not self.is_connected:
            self.connect_to_server()
        else:
            self.disconnect_from_server()

    def connect_to_server(self) -> None:
        try:
            self.client = VRPSimClient(host=self.host, port=self.port, timeout=3.0)
            hello = self.client.connect()
            self.is_connected = True
            self.task = hello.get("task", {})
            self.reference_cost = float(hello.get("reference_cost", 6558.59))

            self.init_solver_from_task()
            self.btn_connect.configure(text="Відключити", bg="#DC2626")
            self.btn_start.configure(state=tk.NORMAL)
            self.btn_step.configure(state=tk.NORMAL)
            self.btn_reset.configure(state=tk.NORMAL)
            self.status_var.set("● Підключено (V02)")
            self.lbl_status.configure(fg="#059669")
            self.redraw_map()

        except Exception as e:
            exe = self.locate_vrpsim_executable()
            if exe:
                if messagebox.askyesno("VRPSim не знайдено", f"Не вдалося з'єднатися на порту {self.port}.\n\nЗапустити середовище VRPSim автоматично?"):
                    try:
                        subprocess.Popen([exe, "-seed", str(self.variant_seed), "-port", str(self.port)])
                        time.sleep(1.2)
                        self.connect_to_server()
                    except Exception as ex:
                        messagebox.showerror("Помилка запуску", f"Не вдалося запустити VRPSim: {ex}")
            else:
                messagebox.showerror("Помилка підключення", f"Не вдалося з'єднатися з VRPSim: {e}")

    def disconnect_from_server(self) -> None:
        self.stop_optimizer()
        if self.client:
            self.client.close()
            self.client = None
        self.is_connected = False
        self.btn_connect.configure(text="Підключитись", bg="#0284C7")
        self.status_var.set("● Відключено")
        self.lbl_status.configure(fg="#64748B")

    def toggle_start(self) -> None:
        if self.is_running:
            self.stop_optimizer()
        else:
            self.start_optimizer()

    def start_optimizer(self) -> None:
        if not self.solver:
            self.init_solver_from_task()
        if not self.solver:
            return

        self.solver.algorithm = self.algo_var.get().upper()
        self.solver.num_ants = self.ants_var.get()
        self.solver.alpha = self.alpha_var.get()
        self.solver.beta = self.beta_var.get()
        self.solver.gamma = self.gamma_var.get()
        self.solver.rho = self.rho_var.get()
        self.solver.use_2opt = self.two_opt_var.get()
        self.solver.use_relocate = self.relocate_var.get()

        self.is_running = True
        self.stop_requested = False
        self.btn_start.configure(text="⏸ Пауза", bg="#D97706")
        self.btn_step.configure(state=tk.DISABLED)

        self.worker_thread = threading.Thread(target=self.optimization_loop, daemon=True)
        self.worker_thread.start()

    def stop_optimizer(self) -> None:
        self.stop_requested = True
        self.is_running = False
        self.btn_start.configure(text="▶ Старт", bg="#059669")
        self.btn_step.configure(state=tk.NORMAL)

    def reset_optimizer(self) -> None:
        self.stop_optimizer()
        if self.solver:
            self.solver.reset()
        self.cost_var.set("-")
        self.gap_var.set("-")
        self.iter_var.set("0")
        self.vehicles_var.set("- / 7")
        self.valid_var.set("Скинуто")
        for item in self.tree_routes.get_children():
            self.tree_routes.delete(item)
        self.redraw_map()
        self.redraw_chart()

    def run_single_step(self) -> None:
        if not self.solver:
            self.init_solver_from_task()
        if not self.solver:
            return
        res = self.solver.step()
        self.handle_step_result(res)

    def optimization_loop(self) -> None:
        while not self.stop_requested:
            if not self.solver:
                break
            res = self.solver.step()
            self.root.after(0, self.handle_step_result, res)
            time.sleep(0.02)

    def handle_step_result(self, res: Dict[str, Any]) -> None:
        routes = res["routes"]
        best_cost = res["best_cost"]
        gap = res["gap_percent"]
        iteration = res["iteration"]

        self.cost_var.set(f"{best_cost:.2f}")
        self.gap_var.set(f"{gap:+.2f}%")
        self.iter_var.set(str(iteration))
        self.vehicles_var.set(f"{len(routes)} / {self.solver.max_vehicles if self.solver else 7}")

        if self.is_connected and self.client:
            try:
                server_res = self.client.send_solution(routes=routes, iteration=iteration, info=res.get("info"))
                is_valid = server_res.get("valid", False)
                self.valid_var.set("✔ Допустимий" if is_valid else "✕ Помилка")
                if iteration % 6 == 0:
                    top_edges = self.solver.get_top_pheromone_edges(limit=60)
                    self.client.send_pheromone(top_edges)
            except Exception:
                pass
        else:
            self.valid_var.set("Локальний")

        self.update_routes_tree(routes)
        self.redraw_map()
        self.redraw_chart()

    def update_routes_tree(self, routes: List[List[int]]) -> None:
        for item in self.tree_routes.get_children():
            self.tree_routes.delete(item)

        if not self.solver:
            return

        for idx, r in enumerate(routes, start=1):
            load = sum(self.solver.demands[c] for c in r)
            length = self.solver.route_cost(r)
            stops = len(r)
            self.tree_routes.insert("", tk.END, values=(f"№{idx}", f"{load}/{self.solver.capacity}", f"{length:.1f}", stops))

    def redraw_map(self) -> None:
        self.canvas_map.delete("all")
        w = self.canvas_map.winfo_width()
        h = self.canvas_map.winfo_height()
        if w < 20 or h < 20:
            return

        margin = 35.0
        scale_x = (w - 2.0 * margin) / 1000.0
        scale_y = (h - 2.0 * margin) / 1000.0

        def to_canvas(x: float, y: float) -> Tuple[float, float]:
            cx = margin + x * scale_x
            cy = h - margin - y * scale_y
            return cx, cy

        for gx in range(0, 1001, 200):
            x1, y1 = to_canvas(gx, 0)
            x2, y2 = to_canvas(gx, 1000)
            self.canvas_map.create_line(x1, y1, x2, y2, fill="#1E293B", dash=(2, 4))
            self.canvas_map.create_text(x1, h - 14, text=str(gx), fill="#475569", font=("Arial", 7))

        for gy in range(0, 1001, 200):
            x1, y1 = to_canvas(0, gy)
            x2, y2 = to_canvas(1000, gy)
            self.canvas_map.create_line(x1, y1, x2, y2, fill="#1E293B", dash=(2, 4))
            self.canvas_map.create_text(16, y1, text=str(gy), fill="#475569", font=("Arial", 7))

        if self.show_pheromone_var.get() and self.solver:
            edges = self.solver.get_top_pheromone_edges(limit=80)
            if edges:
                max_tau = edges[0][2]
                for u, v, tau in edges:
                    ratio = tau / max(max_tau, 1e-6)
                    if ratio > 0.15:
                        x1, y1 = to_canvas(self.solver.coords[u][0], self.solver.coords[u][1])
                        x2, y2 = to_canvas(self.solver.coords[v][0], self.solver.coords[v][1])
                        lw = 1 + int(ratio * 3)
                        self.canvas_map.create_line(x1, y1, x2, y2, fill="#F59E0B", width=lw)

        if self.solver and self.solver.best_routes:
            for r_idx, route in enumerate(self.solver.best_routes):
                if not route:
                    continue
                color = self.ROUTE_COLORS[r_idx % len(self.ROUTE_COLORS)]
                full_path = [0] + route + [0]
                pts = []
                for node_id in full_path:
                    nx, ny = to_canvas(self.solver.coords[node_id][0], self.solver.coords[node_id][1])
                    pts.extend([nx, ny])
                self.canvas_map.create_line(pts, fill=color, width=2.2, joinstyle=tk.ROUND, capstyle=tk.ROUND)

        if self.solver:
            for idx in range(1, self.solver.num_customers + 1):
                cx, cy = to_canvas(self.solver.coords[idx][0], self.solver.coords[idx][1])
                demand = self.solver.demands[idx]
                r = 4.0 + demand * 1.5
                self.canvas_map.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#38BDF8", outline="#0284C7", width=1.5)
                self.canvas_map.create_text(cx, cy, text=str(idx), fill="#0F172A", font=("Arial", 7, "bold"))

            depot_x, depot_y = to_canvas(self.solver.coords[0][0], self.solver.coords[0][1])
            ds = 8.0
            self.canvas_map.create_rectangle(depot_x - ds, depot_y - ds, depot_x + ds, depot_y + ds, fill="#FFFFFF", outline="#DC2626", width=2.5)
            self.canvas_map.create_text(depot_x, depot_y - 14, text="ДЕПО (0)", fill="#FFFFFF", font=("Arial", 8, "bold"))

    def redraw_chart(self) -> None:
        self.canvas_chart.delete("all")
        w = self.canvas_chart.winfo_width()
        h = self.canvas_chart.winfo_height()
        if w < 20 or h < 20 or not self.solver or len(self.solver.cost_history) < 2:
            self.canvas_chart.create_text(w / 2, h / 2, text="Очікування даних збіжності...", fill="#94A3B8", font=("Arial", 9))
            return

        pad_l = 48.0
        pad_r = 16.0
        pad_t = 16.0
        pad_b = 26.0

        history = self.solver.cost_history
        iter_bests = self.solver.iter_best_history
        iter_avgs = self.solver.iter_avg_history
        n_pts = len(history)

        all_vals = history + iter_bests + iter_avgs + [self.reference_cost]
        min_v = min(all_vals) * 0.98
        max_v = max(all_vals) * 1.02

        def val_to_y(v: float) -> float:
            ratio = (v - min_v) / max(max_v - min_v, 1e-4)
            return h - pad_b - ratio * (h - pad_t - pad_b)

        def idx_to_x(i: int) -> float:
            return pad_l + (i / max(n_pts - 1, 1)) * (w - pad_l - pad_r)

        ref_y = val_to_y(self.reference_cost)
        self.canvas_chart.create_line(pad_l, ref_y, w - pad_r, ref_y, fill="#10B981", dash=(3, 3), width=1.5)
        self.canvas_chart.create_text(w - pad_r - 28, ref_y - 8, text=f"Еталон: {self.reference_cost:.1f}", fill="#059669", font=("Arial", 7, "bold"))

        for i in range(4):
            val = min_v + (i / 3.0) * (max_v - min_v)
            y = val_to_y(val)
            self.canvas_chart.create_line(pad_l, y, w - pad_r, y, fill="#E2E8F0", dash=(1, 3))
            self.canvas_chart.create_text(pad_l - 6, y, text=f"{int(val)}", fill="#64748B", font=("Arial", 7), anchor="e")

        avg_pts = []
        for i in range(n_pts):
            avg_pts.extend([idx_to_x(i), val_to_y(iter_avgs[i])])
        self.canvas_chart.create_line(avg_pts, fill="#94A3B8", dash=(2, 2), width=1.2)

        iter_pts = []
        for i in range(n_pts):
            iter_pts.extend([idx_to_x(i), val_to_y(iter_bests[i])])
        self.canvas_chart.create_line(iter_pts, fill="#F59E0B", width=1.4)

        best_pts = []
        for i in range(n_pts):
            best_pts.extend([idx_to_x(i), val_to_y(history[i])])
        self.canvas_chart.create_line(best_pts, fill="#0284C7", width=2.2)

        self.canvas_chart.create_text(pad_l + 10, h - 10, text="1", fill="#64748B", font=("Arial", 7))
        self.canvas_chart.create_text(w - pad_r, h - 10, text=str(n_pts), fill="#64748B", font=("Arial", 7), anchor="e")

    def run(self) -> None:
        self.root.mainloop()
