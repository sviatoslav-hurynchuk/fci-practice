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
        variant_number: int = 2,
        student_name: str = "Гуринчук Святослав"
    ):
        self.grid = grid
        self.grid_w = width
        self.grid_h = height
        self.step_callback = step_callback
        self.variant_number = variant_number
        self.student_name = student_name

        self.root = tk.Tk()
        short_name = self.student_name.split()[0]
        self.root.title(f"Лабораторна робота №2 {short_name}")
        self.root.geometry("1100x780")
        self.root.minsize(980, 680)
        self.root.configure(bg="#F1F5F9")

        self.is_running = False
        self.cell_size = 5.2
        self.canvas_w = int(self.grid_w * self.cell_size)
        self.canvas_h = int(self.grid_h * self.cell_size)

        self.show_trajectory = tk.BooleanVar(value=True)
        self.show_foxes = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=True)

        self.trajectory_points: list[tuple[float, float]] = []
        self.fox_coords: list[tuple[float, float, int, float]] = []
        self.temp_history: list[float] = []
        self.signal_history: list[float] = []
        self.fox_events: list[tuple[int, float]] = []

        self._build_ui()
        self._draw_grid_static()

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
            command=self.reset_view
        )
        self.btn_reset.pack(side=tk.LEFT, padx=3)

        sep = ttk.Separator(top_panel, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=12)

        tk.Checkbutton(
            top_panel,
            text="Траєкторія агента",
            variable=self.show_trajectory,
            font=("Segoe UI", 9, "bold"),
            fg="#0284C7",
            bg="#FFFFFF",
            activebackground="#FFFFFF",
            activeforeground="#0284C7",
            command=self._redraw_trajectory_and_foxes
        ).pack(side=tk.LEFT, padx=5)

        tk.Checkbutton(
            top_panel,
            text="Позначки об'єктів",
            variable=self.show_foxes,
            font=("Segoe UI", 9),
            fg="#DC2626",
            bg="#FFFFFF",
            activebackground="#FFFFFF",
            activeforeground="#DC2626",
            command=self._redraw_trajectory_and_foxes
        ).pack(side=tk.LEFT, padx=5)

        tk.Checkbutton(
            top_panel,
            text="Координатна сітка",
            variable=self.show_grid,
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#FFFFFF",
            activebackground="#FFFFFF",
            command=self._draw_grid_static
        ).pack(side=tk.LEFT, padx=5)

        self.lbl_server = tk.Label(
            top_panel,
            text=f"● Підключено (Варіант {self.variant_number} | Сервер активний)",
            font=("Segoe UI", 9, "bold"),
            fg="#16A34A",
            bg="#FFFFFF"
        )
        self.lbl_server.pack(side=tk.RIGHT, padx=5)

        hud_bar = tk.Frame(self.root, bg="#E2E8F0", bd=1, relief=tk.SOLID, padx=8, pady=4)
        hud_bar.pack(fill=tk.X, padx=10, pady=(0, 4))

        self.txt_step = self._add_hud_item(hud_bar, "Крок:", "0")
        self.txt_foxes = self._add_hud_item(hud_bar, "Лисиць лишилось:", "3", fg="#DC2626")
        self.txt_pos = self._add_hud_item(hud_bar, "Координати:", "(0, 0)")
        self.txt_temp = self._add_hud_item(hud_bar, "Температура T:", "40.00°", fg="#EA580C")
        self.txt_signal = self._add_hud_item(hud_bar, "Рівень сигналу S:", "0.0000", fg="#0284C7")
        self.txt_radius = self._add_hud_item(hud_bar, "Радіус R:", "25 кл.", fg="#475569")
        self.txt_status = self._add_hud_item(hud_bar, "Статус:", "Готово до пошуку", fg="#16A34A")

        main_box = tk.Frame(self.root, bg="#F1F5F9")
        main_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)

        left_card = tk.Frame(main_box, bg="#FFFFFF", bd=1, relief=tk.SOLID)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 6))

        lbl_map = tk.Label(
            left_card,
            text=" Топологічна карта пошуку 100×100 (Перешкоди, Траєкторія, Об'єкти) ",
            font=("Segoe UI", 9, "bold"),
            fg="#334155",
            bg="#FFFFFF"
        )
        lbl_map.pack(anchor="w", padx=8, pady=(6, 2))

        self.canvas = tk.Canvas(
            left_card,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#FFFFFF",
            highlightthickness=0
        )
        self.canvas.pack(padx=8, pady=(2, 8))

        right_frame = tk.Frame(main_box, bg="#F1F5F9")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        box_temp = tk.LabelFrame(
            right_frame,
            text=" Динаміка зміни температури T(k) (охолодження та Reheating) ",
            font=("Segoe UI", 9, "bold"),
            fg="#334155",
            bg="#FFFFFF",
            bd=1
        )
        box_temp.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.canvas_temp = tk.Canvas(box_temp, bg="#FAFAFA", highlightthickness=0, height=220)
        self.canvas_temp.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas_temp.bind("<Configure>", lambda e: self._draw_temp_chart())

        box_sig = tk.LabelFrame(
            right_frame,
            text=" Потенціал сигналу сервера S(k) (сходження на екстремуми) ",
            font=("Segoe UI", 9, "bold"),
            fg="#334155",
            bg="#FFFFFF",
            bd=1
        )
        box_sig.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.canvas_sig = tk.Canvas(box_sig, bg="#FAFAFA", highlightthickness=0, height=220)
        self.canvas_sig.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas_sig.bind("<Configure>", lambda e: self._draw_sig_chart())

        status_frame = tk.Frame(self.root, bg="#CBD5E1", height=22)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="Готово. Натисніть '▶ Старт' для початку пошуку.")
        tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 8),
            fg="#334155",
            bg="#CBD5E1"
        ).pack(side=tk.LEFT, padx=10)

    def _add_hud_item(self, parent, title, val, fg="#0F172A"):
        f = tk.Frame(parent, bg="#E2E8F0")
        f.pack(side=tk.LEFT, padx=8)
        tk.Label(f, text=title, font=("Segoe UI", 8), fg="#64748B", bg="#E2E8F0").pack(side=tk.LEFT, padx=(0, 4))
        lbl = tk.Label(f, text=val, font=("Segoe UI", 9, "bold"), fg=fg, bg="#E2E8F0")
        lbl.pack(side=tk.LEFT)
        return lbl

    def _draw_grid_static(self):
        self.canvas.delete("all")

        if self.show_grid.get():
            step_grid = 10 * self.cell_size
            for i in range(11):
                pos = i * step_grid
                self.canvas.create_line(pos, 0, pos, self.canvas_h, fill="#F1F5F9", width=1)
                self.canvas.create_line(0, pos, self.canvas_w, pos, fill="#F1F5F9", width=1)

        for y in range(self.grid_h):
            for x in range(self.grid_w):
                if self.grid[y][x] == 1:
                    x0 = x * self.cell_size
                    y0 = y * self.cell_size
                    x1 = x0 + self.cell_size
                    y1 = y0 + self.cell_size
                    self.canvas.create_rectangle(x0, y0, x1, y1, fill="#334155", outline="")

        sx = 0.5 * self.cell_size
        sy = 0.5 * self.cell_size
        self.canvas.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill="#10B981", outline="#FFFFFF", width=1.5)
        self.canvas.create_text(sx + 10, sy + 7, text="(0,0)", fill="#0F172A", font=("Segoe UI", 7, "bold"))

        self._redraw_trajectory_and_foxes()

    def _redraw_trajectory_and_foxes(self):
        self.canvas.delete("trajectory")
        self.canvas.delete("fox")
        self.canvas.delete("agent")

        if self.show_trajectory.get() and len(self.trajectory_points) >= 2:
            pts = []
            for px, py in self.trajectory_points:
                pts.extend([px, py])
            self.canvas.create_line(*pts, fill="#0284C7", width=1.5, tags="trajectory")

        if self.show_foxes.get():
            for fx, fy, step, _ in self.fox_coords:
                self.canvas.create_oval(fx - 6, fy - 6, fx + 6, fy + 6, fill="#EF4444", outline="#F59E0B", width=2, tags="fox")
                self.canvas.create_text(fx, fy - 10, text=f"#{step}", fill="#DC2626", font=("Segoe UI", 7, "bold"), tags="fox")

        if self.trajectory_points:
            cx, cy = self.trajectory_points[-1]
            r = 4.0
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#22C55E", outline="#0F172A", width=1.5, tags="agent")

    def toggle_run(self):
        if not self.is_running:
            self.is_running = True
            self.btn_start.config(text="▶ Пошук...", state=tk.DISABLED, bg="#94A3B8")
            self.btn_pause.config(state=tk.NORMAL, text="⏸ Пауза", bg="#E2E8F0")
            self.txt_status.config(text="Пошук триває...", fg="#0284C7")
            self.status_var.set("Йде процес стохастичної оптимізації імітацією відпалу...")
            self._loop_step()

    def toggle_pause(self):
        if self.is_running:
            self.is_running = False
            self.btn_start.config(text="▶ Продовжити", state=tk.NORMAL, bg="#22C55E")
            self.btn_pause.config(text="▶ Пауза", state=tk.DISABLED, bg="#E2E8F0")
            self.txt_status.config(text="Призупинено", fg="#D97706")
            self.status_var.set("Пошук тимчасово призупинено. Натисніть 'Продовжити'.")
        else:
            self.toggle_run()

    def reset_view(self):
        self.is_running = False
        self.trajectory_points.clear()
        self.fox_coords.clear()
        self.temp_history.clear()
        self.signal_history.clear()
        self.fox_events.clear()

        self.txt_step.config(text="0")
        self.txt_foxes.config(text="3", fg="#DC2626")
        self.txt_pos.config(text="(0, 0)")
        self.txt_temp.config(text="40.00°")
        self.txt_signal.config(text="0.0000")
        self.txt_radius.config(text="25 кл.")
        self.txt_status.config(text="Скинуто", fg="#64748B")

        self.btn_start.config(text="▶ Старт", state=tk.NORMAL, bg="#22C55E")
        self.btn_pause.config(text="⏸ Пауза", state=tk.DISABLED)
        self.status_var.set("Вигляд скинуто.")
        self._draw_grid_static()
        self._draw_temp_chart()
        self._draw_sig_chart()

    def _loop_step(self):
        if not self.is_running:
            return

        state = self.step_callback()
        self._update_state(state)

        if state["status"] == "completed":
            self.is_running = False
            self.btn_start.config(text="✔ Завершено", state=tk.DISABLED, bg="#16A34A")
            self.btn_pause.config(state=tk.DISABLED)
            self.txt_status.config(text="УСПІШНО ЗАВЕРШЕНО", fg="#16A34A")
            self.status_var.set(f"Всі 3 об'єкти виявлено! Загальна к-сть кроків: {state.get('step', state.get('steps', 0))}.")
            return

        if state["status"] == "stuck":
            self.is_running = False
            self.btn_start.config(text="Застряг", state=tk.DISABLED, bg="#DC2626")
            self.txt_status.config(text="Застряг у глухому куті", fg="#DC2626")
            self.status_var.set("Помилка пошуку: агент застряг.")
            return

        self.root.after(20, self._loop_step)

    def _update_state(self, state: dict):
        x = state["x"]
        y = state["y"]
        cx = (x + 0.5) * self.cell_size
        cy = (y + 0.5) * self.cell_size

        if self.show_trajectory.get() and self.trajectory_points:
            px, py = self.trajectory_points[-1]
            self.canvas.create_line(px, py, cx, cy, fill="#0284C7", width=1.5, tags="trajectory")
        self.trajectory_points.append((cx, cy))

        self.canvas.delete("agent")
        r = 4.0
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#22C55E", outline="#0F172A", width=1.5, tags="agent")

        step_num = state["step"]
        sig_val = state["signal"]
        temp_val = state["temperature"]

        if state.get("fox_caught"):
            fx, fy = cx, cy
            self.fox_coords.append((fx, fy, step_num, sig_val))
            self.fox_events.append((step_num, sig_val))
            if self.show_foxes.get():
                self.canvas.create_oval(fx - 6, fy - 6, fx + 6, fy + 6, fill="#EF4444", outline="#F59E0B", width=2, tags="fox")
                self.canvas.create_text(fx, fy - 10, text=f"#{step_num}", fill="#DC2626", font=("Segoe UI", 7, "bold"), tags="fox")

        rem = state["remaining_foxes"]
        self.txt_step.config(text=str(step_num))
        self.txt_foxes.config(text=f"{rem} ({3 - rem} знайдено)", fg="#16A34A" if rem == 0 else "#DC2626")
        self.txt_pos.config(text=f"({x}, {y})")
        self.txt_temp.config(text=f"{temp_val:.2f}°")
        self.txt_signal.config(text=f"{sig_val:.4f}")
        self.txt_radius.config(text=f"{state['radius']} кл.")

        self.temp_history.append(temp_val)
        self.signal_history.append(sig_val)

        self._draw_temp_chart()
        self._draw_sig_chart()

    def _draw_temp_chart(self):
        c = self.canvas_temp
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20 or h < 20:
            return

        pad_l, pad_r, pad_t, pad_b = 40, 20, 15, 25
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        for i in range(4):
            y_val = pad_t + i * (plot_h / 3)
            c.create_line(pad_l, y_val, w - pad_r, y_val, fill="#E2E8F0", width=1)
            t_label = 40.0 - i * (40.0 / 3)
            c.create_text(pad_l - 6, y_val, text=f"{t_label:.0f}°", fill="#94A3B8", font=("Segoe UI", 7), anchor="e")

        c.create_line(pad_l, pad_t, pad_l, h - pad_b, fill="#CBD5E1", width=1.5)
        c.create_line(pad_l, h - pad_b, w - pad_r, h - pad_b, fill="#CBD5E1", width=1.5)

        c.create_text(pad_l + 10, pad_t - 5, text="T(°C)", fill="#EA580C", font=("Segoe UI", 8, "bold"))
        c.create_text(w - pad_r, h - pad_b + 12, text="Крок", fill="#64748B", font=("Segoe UI", 8), anchor="e")

        n = len(self.temp_history)
        if n < 2:
            return

        max_t = max(max(self.temp_history), 40.0)
        step_x = plot_w / max(n - 1, 1)

        pts = []
        for i in range(n):
            px = pad_l + i * step_x
            py = (h - pad_b) - (self.temp_history[i] / max_t) * plot_h
            pts.extend([px, py])

        c.create_line(*pts, fill="#EA580C", width=1.8)

        for step_ev, _ in self.fox_events:
            if step_ev < n:
                ev_x = pad_l + step_ev * step_x
                c.create_line(ev_x, pad_t, ev_x, h - pad_b, fill="#DC2626", dash=(3, 2), width=1.5)
                c.create_text(ev_x, pad_t + 8, text=f"Reheating\n#{step_ev}", fill="#DC2626", font=("Segoe UI", 7, "bold"), anchor="s")

    def _draw_sig_chart(self):
        c = self.canvas_sig
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 20 or h < 20:
            return

        pad_l, pad_r, pad_t, pad_b = 40, 20, 15, 25
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        for i in range(4):
            y_val = pad_t + i * (plot_h / 3)
            c.create_line(pad_l, y_val, w - pad_r, y_val, fill="#E2E8F0", width=1)
            s_label = 100.0 - i * (100.0 / 3)
            c.create_text(pad_l - 6, y_val, text=f"{s_label:.0f}", fill="#94A3B8", font=("Segoe UI", 7), anchor="e")

        c.create_line(pad_l, pad_t, pad_l, h - pad_b, fill="#CBD5E1", width=1.5)
        c.create_line(pad_l, h - pad_b, w - pad_r, h - pad_b, fill="#CBD5E1", width=1.5)

        c.create_text(pad_l + 10, pad_t - 5, text="S(x,y)", fill="#0284C7", font=("Segoe UI", 8, "bold"))
        c.create_text(w - pad_r, h - pad_b + 12, text="Крок", fill="#64748B", font=("Segoe UI", 8), anchor="e")

        n = len(self.signal_history)
        if n < 2:
            return

        max_s = max(max(self.signal_history), 105.0)
        step_x = plot_w / max(n - 1, 1)

        pts = []
        for i in range(n):
            px = pad_l + i * step_x
            py = (h - pad_b) - (self.signal_history[i] / max_s) * plot_h
            pts.extend([px, py])

        c.create_line(*pts, fill="#0284C7", width=1.8)

        for step_ev, sig_val in self.fox_events:
            if step_ev < n:
                ev_x = pad_l + step_ev * step_x
                c.create_line(ev_x, pad_t, ev_x, h - pad_b, fill="#16A34A", dash=(3, 2), width=1.5)
                c.create_text(ev_x, pad_t + 8, text=f"S={sig_val:.1f}\n#{step_ev}", fill="#16A34A", font=("Segoe UI", 7, "bold"), anchor="s")

    def run(self):
        self.root.mainloop()
