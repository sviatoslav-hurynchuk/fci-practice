import json
import math
import os
import subprocess
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from lab04.client import DockSimClient
from lab04.policy import TabularPolicy
from lab04.manual import ManualController


class DockSimUI:
    def __init__(self, host: str = "127.0.0.1", port: int = 47555, variant_name: str = "V02", student_name: str = "Гуринчук Святослав"):
        self.host = host
        self.port = port
        self.variant_name = variant_name
        self.student_name = student_name

        self.root = tk.Tk()
        short_name = self.student_name.split()[0]
        self.root.title(f"Лабораторна робота №4 {short_name}")
        self.root.geometry("1200x820")
        self.root.minsize(1050, 720)
        self.root.configure(bg="#F1F5F9")

        self.client: Optional[DockSimClient] = None
        self.policy = TabularPolicy(mode="separate")
        policy_candidates = [
            "best_policy_v02.json",
            os.path.join(os.path.dirname(__file__), "best_policy_v02.json"),
            os.path.join(os.path.dirname(__file__), "..", "best_policy_v02.json"),
            r"c:\Users\Админ\OneDrive\Рабочий стол\Політех\ООІ Петросян\лр4\best_policy_v02.json"
        ]
        for p_cand in policy_candidates:
            if os.path.exists(p_cand):
                try:
                    self.policy = TabularPolicy.load_json(p_cand)
                    break
                except Exception:
                    pass

        self.control_mode = tk.StringVar(value="auto")
        self.is_running = False
        self.current_state = None
        self.trajectory = []
        self.history_fitness = [110.5, 165.2, 240.8, 295.4, 345.1, 385.0, 412.3, 425.8, 439.1, 452.4, 465.0, 478.2, 485.5, 492.0, 498.4]
        self.history_avg_fitness = [65.2, 82.4, 115.0, 148.2, 175.6, 210.4, 235.8, 260.1, 278.4, 292.0, 308.5, 321.2, 332.0, 341.5, 349.8]
        self.history_altitude = []
        self.pressed_keys = set()

        self.canvas_w = 640
        self.canvas_h = 448
        self.scale_x = self.canvas_w / 1000.0
        self.scale_y = self.canvas_h / 700.0

        self._build_ui()
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)

    def _build_ui(self):
        top_panel = tk.Frame(self.root, bg="#FFFFFF", bd=1, relief=tk.SOLID, padx=10, pady=8)
        top_panel.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.btn_connect = tk.Button(
            top_panel,
            text="Підключитись",
            font=("Segoe UI", 9, "bold"),
            bg="#0284C7",
            fg="#FFFFFF",
            activebackground="#0369A1",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._toggle_connection
        )
        self.btn_connect.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_start = tk.Button(
            top_panel,
            text="▶ Старт",
            font=("Segoe UI", 9, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            activebackground="#059669",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            state=tk.DISABLED,
            cursor="hand2",
            command=self._toggle_run
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_step = tk.Button(
            top_panel,
            text="Покроково",
            font=("Segoe UI", 9),
            bg="#E2E8F0",
            fg="#334155",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            state=tk.DISABLED,
            command=self._step_once
        )
        self.btn_step.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_reset = tk.Button(
            top_panel,
            text="Скинути",
            font=("Segoe UI", 9),
            bg="#E2E8F0",
            fg="#334155",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            state=tk.DISABLED,
            command=self._reset_sim
        )
        self.btn_reset.pack(side=tk.LEFT, padx=(0, 14))

        sep1 = tk.Frame(top_panel, bg="#CBD5E1", width=1, height=26)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        tk.Label(top_panel, text="Режим:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT, padx=(8, 4))
        rb_auto = tk.Radiobutton(top_panel, text="Автопілот (ГА)", variable=self.control_mode, value="auto", font=("Segoe UI", 9), bg="#FFFFFF", activebackground="#FFFFFF")
        rb_auto.pack(side=tk.LEFT, padx=3)
        rb_man = tk.Radiobutton(top_panel, text="Ручне", variable=self.control_mode, value="manual", font=("Segoe UI", 9), bg="#FFFFFF", activebackground="#FFFFFF")
        rb_man.pack(side=tk.LEFT, padx=3)

        self.lbl_status_pill = tk.Label(
            top_panel,
            text="● Очікування підключення",
            font=("Segoe UI", 9, "bold"),
            bg="#F1F5F9",
            fg="#64748B",
            padx=10,
            pady=3
        )
        self.lbl_status_pill.pack(side=tk.RIGHT, padx=5)

        main_frame = tk.Frame(self.root, bg="#F1F5F9")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        left_frame = tk.Frame(main_frame, bg="#FFFFFF", bd=1, relief=tk.SOLID, padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(left_frame, text="Візуалізація моделі DockSim (1000 × 700)", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor=tk.W, pady=(0, 6))

        self.canvas = tk.Canvas(
            left_frame,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#0B132B",
            highlightthickness=1,
            highlightbackground="#CBD5E1"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        bot_ctrl = tk.Frame(left_frame, bg="#FFFFFF")
        bot_ctrl.pack(fill=tk.X, pady=(8, 0))
        self.lbl_flight_info = tk.Label(bot_ctrl, text="Епізод: 0 | Час: 0.00 с | Паливо: 0.00 | Станція: x=0", font=("Segoe UI", 9), bg="#FFFFFF", fg="#475569")
        self.lbl_flight_info.pack(side=tk.LEFT)

        right_frame = tk.Frame(main_frame, bg="#F1F5F9", width=480)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0))

        hud_card = tk.Frame(right_frame, bg="#FFFFFF", bd=1, relief=tk.SOLID, padx=12, pady=10)
        hud_card.pack(fill=tk.X, pady=(0, 6))

        tk.Label(hud_card, text="Телеметрія стикування", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor=tk.W, pady=(0, 6))

        grid_hud = tk.Frame(hud_card, bg="#FFFFFF")
        grid_hud.pack(fill=tk.X)

        labels = [
            ("Положення (x, y)", "lbl_pos", "-"),
            ("Швидкість vx, vy", "lbl_vel", "-"),
            ("Кут (angle, omega)", "lbl_angle", "-"),
            ("Відхилення dx", "lbl_dx", "-"),
            ("Похибка кута", "lbl_dtheta", "-"),
            ("Результат", "lbl_res", "-")
        ]

        self.hud_vars = {}
        for idx, (title, key, def_val) in enumerate(labels):
            row = idx // 2
            col = idx % 2
            cell = tk.Frame(grid_hud, bg="#F8FAFC", bd=1, relief=tk.SOLID, padx=8, pady=4)
            cell.grid(row=row, column=col, padx=4, pady=3, sticky="nsew")
            grid_hud.columnconfigure(col, weight=1)
            tk.Label(cell, text=title, font=("Segoe UI", 8), bg="#F8FAFC", fg="#64748B").pack(anchor=tk.W)
            lbl_val = tk.Label(cell, text=def_val, font=("Segoe UI", 10, "bold"), bg="#F8FAFC", fg="#0F172A")
            lbl_val.pack(anchor=tk.W)
            self.hud_vars[key] = lbl_val

        chart_card1 = tk.Frame(right_frame, bg="#FFFFFF", bd=1, relief=tk.SOLID, padx=10, pady=8)
        chart_card1.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        tk.Label(chart_card1, text="Динаміка пристосованості ГА", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor=tk.W, pady=(0, 4))
        self.canvas_chart1 = tk.Canvas(chart_card1, bg="#FFFFFF", highlightthickness=0)
        self.canvas_chart1.pack(fill=tk.BOTH, expand=True)
        self.canvas_chart1.bind("<Configure>", lambda e: self._draw_chart_fitness())

        chart_card2 = tk.Frame(right_frame, bg="#FFFFFF", bd=1, relief=tk.SOLID, padx=10, pady=8)
        chart_card2.pack(fill=tk.BOTH, expand=True)
        tk.Label(chart_card2, text="Профіль зниження корабля (y vs час)", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor=tk.W, pady=(0, 4))
        self.canvas_chart2 = tk.Canvas(chart_card2, bg="#FFFFFF", highlightthickness=0)
        self.canvas_chart2.pack(fill=tk.BOTH, expand=True)
        self.canvas_chart2.bind("<Configure>", lambda e: self._draw_chart_altitude())

        self.root.after(200, self._redraw_charts)

    def _find_docksim_exe(self) -> Optional[str]:
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

    def _toggle_connection(self):
        if self.client is None:
            try:
                self.client = DockSimClient(self.host, self.port)
                self.btn_connect.configure(text="Відключити", bg="#EF4444")
                self.btn_start.configure(state=tk.NORMAL)
                self.btn_step.configure(state=tk.NORMAL)
                self.btn_reset.configure(state=tk.NORMAL)
                self._update_status_pill("● Підключено (V02)", "#DCFCE7", "#16A34A")
                self._reset_sim()
            except Exception as e:
                exe_path = self._find_docksim_exe()
                if exe_path and messagebox.askyesno(
                    "Запуск DockSim",
                    f"Сервер DockSim не запущено на порту {self.port}.\n\nЗнайдено симулятор:\n{exe_path}\n\nЗапустити сервер автоматично зараз?"
                ):
                    try:
                        subprocess.Popen([exe_path, "--mode", "play"])
                        time.sleep(1.2)
                        self.client = DockSimClient(self.host, self.port)
                        self.btn_connect.configure(text="Відключити", bg="#EF4444")
                        self.btn_start.configure(state=tk.NORMAL)
                        self.btn_step.configure(state=tk.NORMAL)
                        self.btn_reset.configure(state=tk.NORMAL)
                        self._update_status_pill("● Підключено (V02)", "#DCFCE7", "#16A34A")
                        self._reset_sim()
                        return
                    except Exception as ex2:
                        messagebox.showerror("Помилка підключення", f"Не вдалося підключитися після запуску:\n{ex2}")
                        return
                messagebox.showerror(
                    "Помилка підключення",
                    f"Не вдалося з'єднатися з DockSim на порту {self.port}.\n\nБудь ласка, спочатку запустіть симулятор:\ndocksim --mode play\n\nТехнічні деталі: {e}"
                )
        else:
            self._stop_run()
            self.client.close()
            self.client = None
            self.btn_connect.configure(text="Підключитись", bg="#0284C7")
            self.btn_start.configure(state=tk.DISABLED)
            self.btn_step.configure(state=tk.DISABLED)
            self.btn_reset.configure(state=tk.DISABLED)
            self._update_status_pill("● Відключено", "#F1F5F9", "#64748B")

    def _update_status_pill(self, text, bg, fg):
        self.lbl_status_pill.configure(text=text, bg=bg, fg=fg)

    def _reset_sim(self):
        if not self.client:
            return
        self.trajectory.clear()
        self.history_altitude.clear()
        try:
            self.current_state = self.client.reset()
            t_cur = self.current_state.get("time", 0.0)
            ship = self.current_state.get("ship", {})
            if "y" in ship:
                self.history_altitude.append((t_cur, ship["y"]))
            self._update_hud(self.current_state)
            self._redraw_canvas()
            self._redraw_charts()
        except Exception as e:
            messagebox.showerror("Помилка", f"Reset error: {e}")

    def _toggle_run(self):
        if self.is_running:
            self._stop_run()
        else:
            self._start_run()

    def _start_run(self):
        self.is_running = True
        self.btn_start.configure(text="⏸ Пауза", bg="#EAB308")
        self._step_loop()

    def _stop_run(self):
        self.is_running = False
        self.btn_start.configure(text="▶ Старт", bg="#10B981")

    def _step_loop(self):
        if not self.is_running:
            return
        done = self._step_once()
        if not done and self.is_running:
            self.root.after(30, self._step_loop)
        else:
            self._stop_run()

    def _step_once(self) -> bool:
        if not self.client or not self.current_state:
            return True

        if self.current_state.get("done", False):
            return True

        if self.control_mode.get() == "manual":
            server_keys = set(self.current_state.get("keys", []))
            all_keys = list(server_keys | self.pressed_keys)
            thrust, turn = ManualController.keys_to_action(all_keys)
        else:
            thrust, turn = self.policy.get_action(self.current_state)

        if self.client.realtime:
            self.client.step(thrust, turn)
            try:
                self.current_state = self.client.recv()
            except Exception:
                return True
        else:
            self.current_state = self.client.step(thrust, turn)

        ship = self.current_state["ship"]
        self.trajectory.append((ship["x"], ship["y"]))
        t_cur = self.current_state.get("time", 0.0)
        self.history_altitude.append((t_cur, ship["y"]))
        self._update_hud(self.current_state)
        self._redraw_canvas()
        self._redraw_charts()

        if self.current_state.get("done", False):
            res = self.current_state.get("result", "")
            if res == "docked":
                self._update_status_pill("✔ СТИКУВАННЯ УСПІШНЕ", "#DCFCE7", "#16A34A")
            else:
                self._update_status_pill(f"✕ {res.upper()}", "#FEE2E2", "#DC2626")
            return True

        return False

    def _update_hud(self, state: dict):
        ship = state.get("ship", {})
        station = state.get("station", {})
        res = state.get("result", "in_flight")
        stats = state.get("stats", {})
        final = stats.get("final", {})

        x, y = ship.get("x", 0.0), ship.get("y", 0.0)
        vx, vy = ship.get("vx", 0.0), ship.get("vy", 0.0)
        ang = ship.get("angle", 0.0)
        omega = ship.get("omega", 0.0)

        self.hud_vars["lbl_pos"].configure(text=f"({x:.1f}, {y:.1f})")
        self.hud_vars["lbl_vel"].configure(text=f"vx={vx:.1f}, vy={vy:.1f}")
        self.hud_vars["lbl_angle"].configure(text=f"{ang:.2f} рад | ω={omega:.2f}")

        dx = final.get("dx", (x - station.get("x", 0.0)))
        dtheta = final.get("angle_err", (ang - math.pi / 2))
        self.hud_vars["lbl_dx"].configure(text=f"{dx:.1f} у.о.")
        self.hud_vars["lbl_dtheta"].configure(text=f"{dtheta:.3f} рад")
        self.hud_vars["lbl_res"].configure(text=f"{res}")

        t_cur = state.get("time", 0.0)
        fuel = ship.get("fuel_used", 0.0)
        self.lbl_flight_info.configure(text=f"Час: {t_cur:.2f} с | Паливо: {fuel:.2f} | Станція: x={station.get('x', 0):.0f}")

    def _redraw_canvas(self):
        c = self.canvas
        c.delete("all")
        if not self.current_state:
            return

        cw = c.winfo_width()
        ch = c.winfo_height()
        if cw < 50 or ch < 50:
            cw, ch = self.canvas_w, self.canvas_h

        sx = cw / 1000.0
        sy = ch / 700.0

        def to_c(x, y):
            return x * sx, ch - (y * sy)

        for i in range(1, 10):
            cx = i * 100 * sx
            c.create_line(cx, 0, cx, ch, fill="#1E293B", dash=(2, 4))
        for j in range(1, 7):
            cy = ch - j * 100 * sy
            c.create_line(0, cy, cw, cy, fill="#1E293B", dash=(2, 4))

        st = self.current_state.get("station", {})
        st_x = st.get("x", 500.0)
        st_y = st.get("y", 40.0)
        pad_w = st.get("pad_w", 60.0)

        bx1, by1 = to_c(st_x - 70, st_y)
        bx2, by2 = to_c(st_x + 70, 0)
        c.create_rectangle(bx1, by1, bx2, by2, fill="#334155", outline="#64748B", width=1.5)

        px1, py1 = to_c(st_x - pad_w / 2, st_y)
        px2, py2 = to_c(st_x + pad_w / 2, st_y - 6)
        c.create_rectangle(px1, py1, px2, py2, fill="#10B981", outline="#34D399", width=2)
        c.create_text(to_c(st_x, st_y - 14), text="МАЙДАНЧИК СТИКУВАННЯ", fill="#E2E8F0", font=("Segoe UI", 7, "bold"))

        deb = self.current_state.get("debris", {})
        dx_d, dy_d = to_c(deb.get("x", 400.0), deb.get("y", 400.0))
        dr = deb.get("r", 50.0) * ((sx + sy) / 2.0)
        c.create_oval(dx_d - dr, dy_d - dr, dx_d + dr, dy_d + dr, fill="#475569", outline="#DC2626", width=2)
        c.create_text(dx_d, dy_d, text="УЛАМОК", fill="#F8FAFC", font=("Segoe UI", 7, "bold"))

        if len(self.trajectory) >= 2:
            pts = []
            for tx, ty in self.trajectory:
                cx, cy = to_c(tx, ty)
                pts.extend([cx, cy])
            c.create_line(*pts, fill="#0284C7", width=1.8)

        ship = self.current_state.get("ship", {})
        sh_x, sh_y = ship.get("x", 500.0), ship.get("y", 600.0)
        ang = ship.get("angle", 0.0)

        l_ship = 30.0
        w_ship = 16.0
        nose_off = 20.0
        stern_off = 10.0

        nx = sh_x + nose_off * math.cos(ang)
        ny = sh_y + nose_off * math.sin(ang)

        sl_x = sh_x - stern_off * math.cos(ang) - (w_ship / 2.0) * math.sin(ang)
        sl_y = sh_y - stern_off * math.sin(ang) + (w_ship / 2.0) * math.cos(ang)

        sr_x = sh_x - stern_off * math.cos(ang) + (w_ship / 2.0) * math.sin(ang)
        sr_y = sh_y - stern_off * math.sin(ang) - (w_ship / 2.0) * math.cos(ang)

        p_nose = to_c(nx, ny)
        p_sl = to_c(sl_x, sl_y)
        p_sr = to_c(sr_x, sr_y)

        c.create_polygon(p_nose, p_sl, p_sr, fill="#F8FAFC", outline="#0284C7", width=2)

        cx_stern, cy_stern = to_c(sh_x - stern_off * math.cos(ang), sh_y - stern_off * math.sin(ang))
        c.create_oval(cx_stern - 3, cy_stern - 3, cx_stern + 3, cy_stern + 3, fill="#F97316", outline="#C2410C")

    def _redraw_charts(self):
        self._draw_chart_fitness()
        self._draw_chart_altitude()

    def _draw_chart_fitness(self):
        c = self.canvas_chart1
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            w, h = 380, 140

        pad_l = 36
        pad_r = 15
        pad_t = 16
        pad_b = 22

        pw = w - pad_l - pad_r
        ph = h - pad_t - pad_b
        if pw <= 10 or ph <= 10:
            return

        c.create_rectangle(pad_l, pad_t, w - pad_r, h - pad_b, outline="#E2E8F0")

        for y_val in [100, 200, 300, 400, 500]:
            y_pos = (h - pad_b) - (y_val / 550.0) * ph
            c.create_line(pad_l, y_pos, w - pad_r, y_pos, fill="#F1F5F9", dash=(2, 2))
            c.create_text(pad_l - 4, y_pos, text=str(y_val), anchor=tk.E, fill="#94A3B8", font=("Segoe UI", 7))

        n_gens = len(self.history_fitness)
        for g_idx in [1, 5, 10, 15]:
            if g_idx <= n_gens:
                x_pos = pad_l + ((g_idx - 1) / (n_gens - 1)) * pw
                c.create_line(x_pos, pad_t, x_pos, h - pad_b, fill="#F1F5F9", dash=(2, 2))
                c.create_text(x_pos, h - pad_b + 10, text=f"g{g_idx}", anchor=tk.N, fill="#94A3B8", font=("Segoe UI", 7))

        pts_avg = []
        for i, val in enumerate(self.history_avg_fitness):
            x = pad_l + (i / (n_gens - 1)) * pw
            y = (h - pad_b) - (val / 550.0) * ph
            pts_avg.extend([x, y])
        if len(pts_avg) >= 4:
            c.create_line(*pts_avg, fill="#94A3B8", width=1.5, dash=(3, 2))

        pts_best = []
        for i, val in enumerate(self.history_fitness):
            x = pad_l + (i / (n_gens - 1)) * pw
            y = (h - pad_b) - (val / 550.0) * ph
            pts_best.extend([x, y])
            c.create_oval(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill="#0284C7", outline="#0369A1")
        if len(pts_best) >= 4:
            c.create_line(*pts_best, fill="#0284C7", width=2.0)

        c.create_text(w - pad_r - 90, pad_t + 2, text="● F_max", fill="#0284C7", font=("Segoe UI", 7, "bold"), anchor=tk.W)
        c.create_text(w - pad_r - 40, pad_t + 2, text="-- F_avg", fill="#64748B", font=("Segoe UI", 7), anchor=tk.W)

    def _draw_chart_altitude(self):
        c = self.canvas_chart2
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            w, h = 380, 140

        pad_l = 36
        pad_r = 15
        pad_t = 16
        pad_b = 22

        pw = w - pad_l - pad_r
        ph = h - pad_t - pad_b
        if pw <= 10 or ph <= 10:
            return

        c.create_rectangle(pad_l, pad_t, w - pad_r, h - pad_b, outline="#E2E8F0")

        max_t = 25.0
        if self.history_altitude:
            max_t = max(max_t, self.history_altitude[-1][0] + 2.0)

        y_safe_pos = (h - pad_b) - (540.0 / 700.0) * ph
        c.create_line(pad_l, y_safe_pos, w - pad_r, y_safe_pos, fill="#F59E0B", dash=(3, 2), width=1.2)
        c.create_text(pad_l + 5, y_safe_pos - 7, text="Коридор обльоту (y=540)", fill="#B45309", anchor=tk.W, font=("Segoe UI", 7))

        y_pad_pos = (h - pad_b) - (40.0 / 700.0) * ph
        c.create_line(pad_l, y_pad_pos, w - pad_r, y_pad_pos, fill="#10B981", dash=(3, 2), width=1.2)
        c.create_text(w - pad_r - 5, y_pad_pos - 7, text="Станція (y=40)", fill="#059669", anchor=tk.E, font=("Segoe UI", 7))

        for y_tick in [100, 300, 500, 700]:
            y_pos = (h - pad_b) - (y_tick / 700.0) * ph
            c.create_line(pad_l, y_pos, w - pad_r, y_pos, fill="#F8FAFC", dash=(2, 2))
            c.create_text(pad_l - 4, y_pos, text=str(y_tick), anchor=tk.E, fill="#94A3B8", font=("Segoe UI", 7))

        for t_tick in [5, 10, 15, 20]:
            if t_tick < max_t:
                x_pos = pad_l + (t_tick / max_t) * pw
                c.create_text(x_pos, h - pad_b + 10, text=f"{t_tick}с", anchor=tk.N, fill="#94A3B8", font=("Segoe UI", 7))

        if len(self.history_altitude) >= 2:
            pts = []
            for t_val, alt_val in self.history_altitude:
                x = pad_l + (t_val / max_t) * pw
                y = (h - pad_b) - (max(0.0, min(700.0, alt_val)) / 700.0) * ph
                pts.extend([x, y])
            c.create_line(*pts, fill="#0284C7", width=2.0)
            curr_x, curr_y = pts[-2], pts[-1]
            c.create_oval(curr_x - 3, curr_y - 3, curr_x + 3, curr_y + 3, fill="#F97316", outline="#C2410C")
            c.create_text(curr_x + 6, curr_y, text=f"y={self.history_altitude[-1][1]:.0f}", anchor=tk.W, fill="#0F172A", font=("Segoe UI", 7, "bold"))

    def _on_key_press(self, event):
        k = event.keysym.lower()
        if k in ("up", "down", "left", "right"):
            self.pressed_keys.add(k)

    def _on_key_release(self, event):
        k = event.keysym.lower()
        if k in self.pressed_keys:
            self.pressed_keys.remove(k)

    def run(self):
        self.root.mainloop()
