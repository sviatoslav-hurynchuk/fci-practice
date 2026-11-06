import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from lab03.model import BattleshipBoard
from lab03.genetic_algorithm import GeneticAlgorithmSolver
from lab03.simulated_annealing import SimulatedAnnealingSolver


class BattleshipUI:
    def __init__(self, board: BattleshipBoard, variant_number: int = 2, student_name: str = "Гуринчук Святослав"):
        self.board = board
        self.variant_number = variant_number
        self.student_name = student_name

        self.root = tk.Tk()
        short_name = self.student_name.split()[0]
        self.root.title(f"Лабораторна робота №3 {short_name}")
        self.root.geometry("1180x800")
        self.root.minsize(1050, 700)
        self.root.configure(bg="#F1F5F9")

        self.current_algo_name = tk.StringVar(value="GA")
        self.show_reefs = tk.BooleanVar(value=True)
        self.show_ships = tk.BooleanVar(value=True)
        self.show_violations = tk.BooleanVar(value=True)

        self.ga_solver = GeneticAlgorithmSolver(self.board)
        self.sa_solver = SimulatedAnnealingSolver(self.board)
        self.active_solver = self.ga_solver

        self.is_running = False
        self.cell_size = 62.0
        self.grid_size = self.board.field_size
        self.canvas_w = int(self.grid_size * self.cell_size)
        self.canvas_h = int(self.grid_size * self.cell_size)

        self.ship_colors = [
            "#0284C7", "#0D9488", "#6366F1", "#8B5CF6", "#EC4899",
            "#F97316", "#14B8A6", "#3B82F6", "#10B981", "#EAB308"
        ]

        self._build_ui()
        self._redraw_board()

    def _build_ui(self):
        top_panel = tk.Frame(self.root, bg="#FFFFFF", bd=1, relief=tk.SOLID, padx=10, pady=8)
        top_panel.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.btn_start = tk.Button(
            top_panel,
            text="▶ Старт",
            font=("Segoe UI", 10, "bold"),
            bg="#22C55E",
            fg="#FFFFFF",
            activebackground="#16A34A",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=14,
            pady=3,
            cursor="hand2",
            command=self.toggle_run
        )
        self.btn_start.pack(side=tk.LEFT, padx=3)

        self.btn_pause = tk.Button(
            top_panel,
            text="⏸ Пауза",
            font=("Segoe UI", 10),
            bg="#E2E8F0",
            fg="#334155",
            activebackground="#CBD5E1",
            relief=tk.FLAT,
            padx=12,
            pady=3,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.toggle_pause
        )
        self.btn_pause.pack(side=tk.LEFT, padx=3)

        self.btn_reset = tk.Button(
            top_panel,
            text="🔄 Скинути",
            font=("Segoe UI", 10),
            bg="#E2E8F0",
            fg="#334155",
            activebackground="#CBD5E1",
            relief=tk.FLAT,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self.reset_all
        )
        self.btn_reset.pack(side=tk.LEFT, padx=3)

        sep1 = ttk.Separator(top_panel, orient=tk.VERTICAL)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        tk.Label(top_panel, text="Алгоритм:", font=("Segoe UI", 9, "bold"), fg="#64748B", bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 4))

        self.rb_ga = tk.Radiobutton(
            top_panel,
            text="Генетичний (GA)",
            variable=self.current_algo_name,
            value="GA",
            font=("Segoe UI", 9, "bold"),
            fg="#0284C7",
            bg="#FFFFFF",
            activebackground="#FFFFFF",
            command=self.on_algo_change
        )
        self.rb_ga.pack(side=tk.LEFT, padx=4)

        self.rb_sa = tk.Radiobutton(
            top_panel,
            text="Відпал (SA)",
            variable=self.current_algo_name,
            value="SA",
            font=("Segoe UI", 9, "bold"),
            fg="#EA580C",
            bg="#FFFFFF",
            activebackground="#FFFFFF",
            command=self.on_algo_change
        )
        self.rb_sa.pack(side=tk.LEFT, padx=4)

        sep2 = ttk.Separator(top_panel, orient=tk.VERTICAL)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        tk.Checkbutton(
            top_panel,
            text="Рифи",
            variable=self.show_reefs,
            font=("Segoe UI", 9),
            fg="#334155",
            bg="#FFFFFF",
            command=self._redraw_board
        ).pack(side=tk.LEFT, padx=3)

        tk.Checkbutton(
            top_panel,
            text="Кораблі",
            variable=self.show_ships,
            font=("Segoe UI", 9, "bold"),
            fg="#0284C7",
            bg="#FFFFFF",
            command=self._redraw_board
        ).pack(side=tk.LEFT, padx=3)

        tk.Checkbutton(
            top_panel,
            text="Порушення",
            variable=self.show_violations,
            font=("Segoe UI", 9),
            fg="#DC2626",
            bg="#FFFFFF",
            command=self._redraw_board
        ).pack(side=tk.LEFT, padx=3)

        self.lbl_header_info = tk.Label(
            top_panel,
            text=f"● Варіант {self.variant_number} (Поле {self.grid_size}×{self.grid_size} | 10 кораблів)",
            font=("Segoe UI", 9, "bold"),
            fg="#16A34A",
            bg="#FFFFFF"
        )
        self.lbl_header_info.pack(side=tk.RIGHT, padx=5)

        hud_bar = tk.Frame(self.root, bg="#E2E8F0", bd=1, relief=tk.SOLID, padx=8, pady=4)
        hud_bar.pack(fill=tk.X, padx=10, pady=(0, 4))

        self.txt_iter = self._add_hud_item(hud_bar, "Ітерація / Покоління:", "0")
        self.txt_violations = self._add_hud_item(hud_bar, "Помилок (штраф):", "...", fg="#DC2626")
        self.txt_metric = self._add_hud_item(hud_bar, "Якість (F / E):", "...", fg="#0284C7")
        self.txt_evals = self._add_hud_item(hud_bar, "Обчислень функції:", "0")
        self.txt_status = self._add_hud_item(hud_bar, "Статус:", "Готово до оптимізації", fg="#16A34A")

        main_box = tk.Frame(self.root, bg="#F1F5F9")
        main_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)

        left_card = tk.Frame(main_box, bg="#FFFFFF", bd=1, relief=tk.SOLID)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 6))

        lbl_map = tk.Label(
            left_card,
            text=f" Поле розміщення флоту {self.grid_size}×{self.grid_size} з рифами ",
            font=("Segoe UI", 9, "bold"),
            fg="#334155",
            bg="#FFFFFF"
        )
        lbl_map.pack(anchor="w", padx=8, pady=(6, 2))

        self.canvas_board = tk.Canvas(
            left_card,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#FFFFFF",
            highlightthickness=0
        )
        self.canvas_board.pack(padx=8, pady=(2, 8))

        right_frame = tk.Frame(main_box, bg="#F1F5F9")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        self.box_chart1 = tk.LabelFrame(
            right_frame,
            text=" Динаміка збіжності цільової функції ",
            font=("Segoe UI", 9, "bold"),
            fg="#334155",
            bg="#FFFFFF",
            bd=1
        )
        self.box_chart1.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.canvas_chart1 = tk.Canvas(self.box_chart1, bg="#FAFAFA", highlightthickness=0, height=210)
        self.canvas_chart1.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas_chart1.bind("<Configure>", lambda e: self._redraw_charts())

        self.box_chart2 = tk.LabelFrame(
            right_frame,
            text=" Параметри збіжності та дослідження простору ",
            font=("Segoe UI", 9, "bold"),
            fg="#334155",
            bg="#FFFFFF",
            bd=1
        )
        self.box_chart2.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.canvas_chart2 = tk.Canvas(self.box_chart2, bg="#FAFAFA", highlightthickness=0, height=210)
        self.canvas_chart2.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas_chart2.bind("<Configure>", lambda e: self._redraw_charts())

        status_frame = tk.Frame(self.root, bg="#CBD5E1", height=22)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="Готово. Виберіть алгоритм і натисніть '▶ Старт'.")
        tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 8),
            fg="#334155",
            bg="#CBD5E1"
        ).pack(side=tk.LEFT, padx=10)

        self._update_hud_with_state(self.active_solver.get_state())

    def _add_hud_item(self, parent, title, val, fg="#0F172A"):
        f = tk.Frame(parent, bg="#E2E8F0")
        f.pack(side=tk.LEFT, padx=8)
        tk.Label(f, text=title, font=("Segoe UI", 8), fg="#64748B", bg="#E2E8F0").pack(side=tk.LEFT, padx=(0, 4))
        lbl = tk.Label(f, text=val, font=("Segoe UI", 9, "bold"), fg=fg, bg="#E2E8F0")
        lbl.pack(side=tk.LEFT)
        return lbl

    def on_algo_change(self):
        if self.is_running:
            self.toggle_pause()
        algo = self.current_algo_name.get()
        if algo == "GA":
            self.active_solver = self.ga_solver
            self.box_chart1.config(text=" Динаміка пристосованості ГА (Best & Average Fitness) ")
            self.box_chart2.config(text=" Динаміка штрафу порушень обмежень (Violations) ")
        else:
            self.active_solver = self.sa_solver
            self.box_chart1.config(text=" Динаміка енергії відпалу SA (Energy E) ")
            self.box_chart2.config(text=" Зниження температури T(k) та частка переходів ")

        st = self.active_solver.get_state()
        self._update_hud_with_state(st)
        self._redraw_board()
        self._redraw_charts()

    def toggle_run(self):
        if not self.is_running:
            self.is_running = True
            self.btn_start.config(text="▶ Працює...", state=tk.DISABLED, bg="#94A3B8")
            self.btn_pause.config(state=tk.NORMAL, text="⏸ Пауза", bg="#E2E8F0")
            self.rb_ga.config(state=tk.DISABLED)
            self.rb_sa.config(state=tk.DISABLED)
            self.txt_status.config(text="Оптимізація триває...", fg="#0284C7")
            self.status_var.set("Йде процес стохастичного пошуку розв'язку...")
            self._loop_step()

    def toggle_pause(self):
        if self.is_running:
            self.is_running = False
            self.btn_start.config(text="▶ Продовжити", state=tk.NORMAL, bg="#22C55E")
            self.btn_pause.config(state=tk.DISABLED)
            self.rb_ga.config(state=tk.NORMAL)
            self.rb_sa.config(state=tk.NORMAL)
            self.txt_status.config(text="Призупинено", fg="#D97706")
            self.status_var.set("Пошук призупинено. Натисніть 'Продовжити'.")
        else:
            self.toggle_run()

    def reset_all(self):
        self.is_running = False
        self.btn_start.config(text="▶ Старт", state=tk.NORMAL, bg="#22C55E")
        self.btn_pause.config(state=tk.DISABLED)
        self.rb_ga.config(state=tk.NORMAL)
        self.rb_sa.config(state=tk.NORMAL)

        self.ga_solver.initialize()
        self.sa_solver.initialize()

        st = self.active_solver.get_state()
        self._update_hud_with_state(st)
        self.txt_status.config(text="Скинуто", fg="#64748B")
        self.status_var.set("Алгоритм скинуто до початкового стану.")
        self._redraw_board()
        self._redraw_charts()

    def _loop_step(self):
        if not self.is_running:
            return

        st = self.active_solver.step()
        self._update_hud_with_state(st)
        self._redraw_board()
        self._redraw_charts()

        if st["is_valid"]:
            self.is_running = False
            self.btn_start.config(text="✔ Розв'язано", state=tk.DISABLED, bg="#16A34A")
            self.btn_pause.config(state=tk.DISABLED)
            self.rb_ga.config(state=tk.NORMAL)
            self.rb_sa.config(state=tk.NORMAL)
            self.txt_status.config(text="УСПІШНО РОЗВ'ЯЗАНО!", fg="#16A34A")
            self.status_var.set(f"Знайдено допустиму розстановку без жодних порушень! Обчислень: {st['evaluations']}.")
            messagebox.showinfo("Успіх", f"Успішно знайдено правильну розстановку кораблів!\nПомилок: 0\nОбчислень: {st['evaluations']}")
            return

        delay = 20 if self.current_algo_name.get() == "GA" else 10
        self.root.after(delay, self._loop_step)

    def _update_hud_with_state(self, st: dict):
        algo = self.current_algo_name.get()
        if algo == "GA":
            it_val = str(st["generation"])
            met_val = f"F = {st['best_fitness']:.2f}"
        else:
            it_val = str(st["iteration"])
            met_val = f"E = {st['best_energy']:.1f} (T={st.get('temperature', 0):.2f}°)"

        v = st["best_violations"]
        self.txt_iter.config(text=it_val)
        self.txt_violations.config(
            text=f"{v} (" + ("0 - ПРАВИЛЬНО" if v == 0 else f"{v} порушень") + ")",
            fg="#16A34A" if v == 0 else "#DC2626"
        )
        self.txt_metric.config(text=met_val)
        self.txt_evals.config(text=str(st["evaluations"]))

    def _redraw_board(self):
        c = self.canvas_board
        c.delete("all")
        cs = self.cell_size

        for i in range(self.grid_size + 1):
            c.create_line(i * cs, 0, i * cs, self.canvas_h, fill="#E2E8F0", width=1)
            c.create_line(0, i * cs, self.canvas_w, i * cs, fill="#E2E8F0", width=1)

        if self.show_reefs.get():
            for rx, ry in self.board.reefs:
                x0, y0 = rx * cs, ry * cs
                x1, y1 = x0 + cs, y0 + cs
                c.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1, fill="#334155", outline="#1E293B", width=1)
                c.create_text(x0 + cs / 2, y0 + cs / 2, text="▲\nРИФ", fill="#94A3B8", font=("Segoe UI", 7, "bold"), justify=tk.CENTER)

        st = self.active_solver.get_state()
        chromosome = st.get("chromosome")
        eval_data = st.get("eval")

        if self.show_ships.get() and chromosome:
            for s_idx, (x, y, ori) in enumerate(chromosome):
                L = self.board.ships[s_idx]
                color = self.ship_colors[s_idx % len(self.ship_colors)]
                cells = self.board.get_ship_cells(x, y, ori, L)

                for c_idx, (cx, cy) in enumerate(cells):
                    if 0 <= cx < self.grid_size and 0 <= cy < self.grid_size:
                        x0, y0 = cx * cs, cy * cs
                        x1, y1 = x0 + cs, y0 + cs

                        c.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, fill=color, outline="#FFFFFF", width=1.5)
                        if c_idx == 0:
                            label = f"#{s_idx + 1}"
                            c.create_text(x0 + cs / 2, y0 + cs / 2, text=label, fill="#FFFFFF", font=("Segoe UI", 9, "bold"))
                        else:
                            c.create_oval(x0 + cs / 2 - 3, y0 + cs / 2 - 3, x0 + cs / 2 + 3, y0 + cs / 2 + 3, fill="#FFFFFF", outline="")

        if self.show_violations.get() and eval_data and (eval_data["reef_hits"] > 0 or eval_data["overlaps"] > 0 or eval_data["touches"] > 0):
            ship_cells = eval_data["ship_cells"]
            k = len(ship_cells)
            conflict_cells = set()

            for i in range(k):
                for cx, cy in ship_cells[i]:
                    if (cx, cy) in self.board.reefs:
                        conflict_cells.add((cx, cy))

            for i in range(k):
                for j in range(i + 1, k):
                    for xi, yi in ship_cells[i]:
                        for xj, yj in ship_cells[j]:
                            if max(abs(xi - xj), abs(yi - yj)) <= 1:
                                conflict_cells.add((xi, yi))
                                conflict_cells.add((xj, yj))

            for cx, cy in conflict_cells:
                if 0 <= cx < self.grid_size and 0 <= cy < self.grid_size:
                    x0, y0 = cx * cs, cy * cs
                    x1, y1 = x0 + cs, y0 + cs
                    c.create_rectangle(x0 + 3, y0 + 3, x1 - 3, y1 - 3, outline="#EF4444", width=2.5, dash=(4, 2))

    def _redraw_charts(self):
        algo = self.current_algo_name.get()
        if algo == "GA":
            self._draw_ga_charts()
        else:
            self._draw_sa_charts()

    def _draw_ga_charts(self):
        c1 = self.canvas_chart1
        c1.delete("all")
        w1, h1 = c1.winfo_width(), c1.winfo_height()
        if w1 > 20 and h1 > 20 and len(self.ga_solver.history_best_fitness) >= 2:
            pad_l, pad_r, pad_t, pad_b = 45, 20, 15, 25
            pw, ph = w1 - pad_l - pad_r, h1 - pad_t - pad_b
            c1.create_line(pad_l, pad_t, pad_l, h1 - pad_b, fill="#CBD5E1", width=1.5)
            c1.create_line(pad_l, h1 - pad_b, w1 - pad_r, h1 - pad_b, fill="#CBD5E1", width=1.5)

            c1.create_text(pad_l + 10, pad_t - 5, text="Фітнес F", fill="#0284C7", font=("Segoe UI", 8, "bold"))
            c1.create_text(w1 - pad_r, h1 - pad_b + 12, text="Покоління", fill="#64748B", font=("Segoe UI", 8), anchor="e")

            bf = self.ga_solver.history_best_fitness
            af = self.ga_solver.history_avg_fitness
            n = len(bf)
            max_f = max(max(bf), 10.0)
            step_x = pw / max(n - 1, 1)

            pts_b = []
            pts_a = []
            for i in range(n):
                px = pad_l + i * step_x
                py_b = (h1 - pad_b) - (bf[i] / max_f) * ph
                py_a = (h1 - pad_b) - (af[i] / max_f) * ph
                pts_b.extend([px, py_b])
                pts_a.extend([px, py_a])

            if len(pts_a) >= 4:
                c1.create_line(*pts_a, fill="#94A3B8", width=1.2, dash=(3, 2))
            if len(pts_b) >= 4:
                c1.create_line(*pts_b, fill="#0284C7", width=2.0)

        c2 = self.canvas_chart2
        c2.delete("all")
        w2, h2 = c2.winfo_width(), c2.winfo_height()
        if w2 > 20 and h2 > 20 and len(self.ga_solver.history_best_violations) >= 2:
            pad_l, pad_r, pad_t, pad_b = 45, 20, 15, 25
            pw, ph = w2 - pad_l - pad_r, h2 - pad_t - pad_b
            c2.create_line(pad_l, pad_t, pad_l, h2 - pad_b, fill="#CBD5E1", width=1.5)
            c2.create_line(pad_l, h2 - pad_b, w2 - pad_r, h2 - pad_b, fill="#CBD5E1", width=1.5)

            c2.create_text(pad_l + 10, pad_t - 5, text="Порушення", fill="#DC2626", font=("Segoe UI", 8, "bold"))
            c2.create_text(w2 - pad_r, h2 - pad_b + 12, text="Покоління", fill="#64748B", font=("Segoe UI", 8), anchor="e")

            bv = self.ga_solver.history_best_violations
            n = len(bv)
            max_v = max(max(bv), 10)
            step_x = pw / max(n - 1, 1)

            pts_v = []
            for i in range(n):
                px = pad_l + i * step_x
                py_v = (h2 - pad_b) - (bv[i] / max_v) * ph
                pts_v.extend([px, py_v])

            if len(pts_v) >= 4:
                c2.create_line(*pts_v, fill="#DC2626", width=2.0)

    def _draw_sa_charts(self):
        c1 = self.canvas_chart1
        c1.delete("all")
        w1, h1 = c1.winfo_width(), c1.winfo_height()
        if w1 > 20 and h1 > 20 and len(self.sa_solver.history_best_energy) >= 2:
            pad_l, pad_r, pad_t, pad_b = 45, 20, 15, 25
            pw, ph = w1 - pad_l - pad_r, h1 - pad_t - pad_b
            c1.create_line(pad_l, pad_t, pad_l, h1 - pad_b, fill="#CBD5E1", width=1.5)
            c1.create_line(pad_l, h1 - pad_b, w1 - pad_r, h1 - pad_b, fill="#CBD5E1", width=1.5)

            c1.create_text(pad_l + 10, pad_t - 5, text="Енергія E", fill="#EA580C", font=("Segoe UI", 8, "bold"))
            c1.create_text(w1 - pad_r, h1 - pad_b + 12, text="Ітерація", fill="#64748B", font=("Segoe UI", 8), anchor="e")

            be = self.sa_solver.history_best_energy
            ce = self.sa_solver.history_current_energy
            n = len(be)
            max_e = max(max(ce), 10.0)
            step_x = pw / max(n - 1, 1)

            pts_c = []
            pts_b = []
            for i in range(n):
                px = pad_l + i * step_x
                py_c = (h1 - pad_b) - (ce[i] / max_e) * ph
                py_b = (h1 - pad_b) - (be[i] / max_e) * ph
                pts_c.extend([px, py_c])
                pts_b.extend([px, py_b])

            if len(pts_c) >= 4:
                c1.create_line(*pts_c, fill="#94A3B8", width=1.0)
            if len(pts_b) >= 4:
                c1.create_line(*pts_b, fill="#EA580C", width=2.0)

        c2 = self.canvas_chart2
        c2.delete("all")
        w2, h2 = c2.winfo_width(), c2.winfo_height()
        if w2 > 20 and h2 > 20 and len(self.sa_solver.history_temperature) >= 2:
            pad_l, pad_r, pad_t, pad_b = 45, 20, 15, 25
            pw, ph = w2 - pad_l - pad_r, h2 - pad_t - pad_b
            c2.create_line(pad_l, pad_t, pad_l, h2 - pad_b, fill="#CBD5E1", width=1.5)
            c2.create_line(pad_l, h2 - pad_b, w2 - pad_r, h2 - pad_b, fill="#CBD5E1", width=1.5)

            c2.create_text(pad_l + 10, pad_t - 5, text="Температура T(k)", fill="#6366F1", font=("Segoe UI", 8, "bold"))
            c2.create_text(w2 - pad_r, h2 - pad_b + 12, text="Ітерація", fill="#64748B", font=("Segoe UI", 8), anchor="e")

            ht = self.sa_solver.history_temperature
            n = len(ht)
            max_t = max(max(ht), 1.0)
            step_x = pw / max(n - 1, 1)

            pts_t = []
            for i in range(n):
                px = pad_l + i * step_x
                py_t = (h2 - pad_b) - (ht[i] / max_t) * ph
                pts_t.extend([px, py_t])

            if len(pts_t) >= 4:
                c2.create_line(*pts_t, fill="#6366F1", width=1.8)

    def run(self):
        self.root.mainloop()
