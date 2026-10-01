import tkinter as tk
from tkinter import ttk, messagebox
import queue
import threading
import time

from api import SonarAPI
from math_dsp import SonarProcessor


class SonarAppUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Лабораторна робота №1 Гуринчук")
        self.root.geometry("1100x780")
        self.root.minsize(980, 680)
        self.root.configure(bg="#F1F5F9")

        self.api = SonarAPI()
        self.processor = None
        self.config = None
        self.pulse = None

        self.total_steps = 100
        self.is_ready = False

        self.current_step = 0
        self.is_running = False
        self.is_paused = False

        self.rendered_single = []
        self.rendered_avg = []

        self.show_averaged = tk.BooleanVar(value=True)
        self.show_single = tk.BooleanVar(value=True)
        self.show_beam = tk.BooleanVar(value=True)
        self.beam_tick = 0

        self.data_queue = queue.Queue()

        self._build_ui()

        self.status_var.set("Підключення до сервера...")
        threading.Thread(target=self._init_connection, daemon=True).start()

        self.root.after(40, self._check_queue)

    def _build_ui(self):
        top_panel = tk.Frame(self.root, bg="#FFFFFF", bd=1, relief=tk.SOLID, padx=10, pady=8)
        top_panel.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.btn_start = tk.Button(
            top_panel, text="▶ Старт", font=("Segoe UI", 10, "bold"),
            bg="#22C55E", fg="#FFFFFF", activebackground="#16A34A",
            relief=tk.FLAT, padx=14, pady=3, cursor="hand2",
            command=self.start_scan, state=tk.DISABLED
        )
        self.btn_start.pack(side=tk.LEFT, padx=3)

        self.btn_pause = tk.Button(
            top_panel, text="⏸ Пауза", font=("Segoe UI", 10),
            bg="#E2E8F0", fg="#334155", activebackground="#CBD5E1",
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self.toggle_pause, state=tk.DISABLED
        )
        self.btn_pause.pack(side=tk.LEFT, padx=3)

        self.btn_reset = tk.Button(
            top_panel, text="🔄 Скинути", font=("Segoe UI", 10),
            bg="#E2E8F0", fg="#334155", activebackground="#CBD5E1",
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self.reset_scan
        )
        self.btn_reset.pack(side=tk.LEFT, padx=3)

        sep = ttk.Separator(top_panel, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=12)

        tk.Checkbutton(
            top_panel, text="Накопичення (істинне дно)", variable=self.show_averaged,
            font=("Segoe UI", 9, "bold"), fg="#0284C7", bg="#FFFFFF",
            activebackground="#FFFFFF", activeforeground="#0284C7",
            command=self._redraw_seabed_only
        ).pack(side=tk.LEFT, padx=5)

        tk.Checkbutton(
            top_panel, text="Одиночний вимір (шум)", variable=self.show_single,
            font=("Segoe UI", 9), fg="#DC2626", bg="#FFFFFF",
            activebackground="#FFFFFF", activeforeground="#DC2626",
            command=self._redraw_seabed_only
        ).pack(side=tk.LEFT, padx=5)

        tk.Checkbutton(
            top_panel, text="Промінь ехолота", variable=self.show_beam,
            font=("Segoe UI", 9), fg="#475569", bg="#FFFFFF",
            activebackground="#FFFFFF",
            command=self._redraw_boat_and_beam
        ).pack(side=tk.LEFT, padx=5)

        self.lbl_server = tk.Label(
            top_panel, text="● Підключення...",
            font=("Segoe UI", 9, "bold"), fg="#D97706", bg="#FFFFFF"
        )
        self.lbl_server.pack(side=tk.RIGHT, padx=5)

        hud_bar = tk.Frame(self.root, bg="#E2E8F0", bd=1, relief=tk.SOLID, padx=8, pady=4)
        hud_bar.pack(fill=tk.X, padx=10, pady=(0, 4))

        self.txt_step = self._add_hud_item(hud_bar, "Крок:", "0 / 100")
        self.txt_depth = self._add_hud_item(hud_bar, "Істинна глибина:", "0.00 м", fg="#0284C7")
        self.txt_single = self._add_hud_item(hud_bar, "Одиночна глибина:", "0.00 м", fg="#DC2626")
        self.txt_delay = self._add_hud_item(hud_bar, "Затримка відлуння:", "0 відліків (0.0 мс)")
        self.txt_hmax = self._add_hud_item(hud_bar, "H_max системи:", "360.0 м")

        center_frame = tk.Frame(self.root, bg="#FFFFFF", bd=1, relief=tk.SOLID)
        center_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)

        self.canvas = tk.Canvas(center_frame, bg="#FFFFFF", highlightthickness=0, height=360)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self._redraw_scene())

        bottom_frame = tk.Frame(self.root, bg="#F1F5F9", height=200)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(2, 4))

        box_sig = tk.LabelFrame(
            bottom_frame, text=" Вхідний оцифрований сигнал X[i] (сенсор) ",
            font=("Segoe UI", 9, "bold"), fg="#334155", bg="#FFFFFF", bd=1
        )
        box_sig.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        self.canvas_sig = tk.Canvas(box_sig, bg="#FAFAFA", highlightthickness=0, height=160)
        self.canvas_sig.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        box_corr = tk.LabelFrame(
            bottom_frame, text=" Взаємна кореляція R(k) (пошук піку затримки) ",
            font=("Segoe UI", 9, "bold"), fg="#334155", bg="#FFFFFF", bd=1
        )
        box_corr.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        self.canvas_corr = tk.Canvas(box_corr, bg="#FAFAFA", highlightthickness=0, height=160)
        self.canvas_corr.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        status_frame = tk.Frame(self.root, bg="#CBD5E1", height=22)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="Ініціалізація...")
        tk.Label(
            status_frame, textvariable=self.status_var,
            font=("Segoe UI", 8), fg="#334155", bg="#CBD5E1"
        ).pack(side=tk.LEFT, padx=10)

    def _add_hud_item(self, parent, title, val, fg="#0F172A"):
        f = tk.Frame(parent, bg="#E2E8F0")
        f.pack(side=tk.LEFT, padx=10)
        tk.Label(f, text=title, font=("Segoe UI", 8), fg="#64748B", bg="#E2E8F0").pack(side=tk.LEFT, padx=(0, 4))
        l = tk.Label(f, text=val, font=("Segoe UI", 9, "bold"), fg=fg, bg="#E2E8F0")
        l.pack(side=tk.LEFT)
        return l

    def _init_connection(self):
        try:
            cfg = self.api.get_config()
            pulse = self.api.get_pulse()
            self.config = cfg
            self.pulse = pulse
            self.total_steps = cfg.get("total_steps", 100)

            self.processor = SonarProcessor(
                sample_rate=cfg["sample_rate"],
                sound_speed=cfg["sound_speed"],
                pulse=pulse
            )

            sig0 = self.api.get_sensor_signal(0)
            self.max_metrics = self.processor.calculate_max_depth(len(sig0))
            self.h_max = self.max_metrics["h_max"]

            self.data_queue.put(("init_ok", (cfg, self.h_max)))
        except Exception as e:
            self.data_queue.put(("error", str(e)))

    def _live_fetch_worker(self):
        while self.is_running and self.current_step < self.total_steps:
            if self.is_paused:
                time.sleep(0.05)
                continue

            step = self.current_step
            try:
                sigs = self.api.get_step_signals(step, count=4)
                if not self.is_running:
                    break
                res = self.processor.process_step(sigs)
                res["step"] = step
                self.data_queue.put(("live_step", res))

                while not self.data_queue.empty() and self.is_running:
                    time.sleep(0.01)

            except Exception as ex:
                self.data_queue.put(("error", str(ex)))
                break

    def _check_queue(self):
        try:
            while not self.data_queue.empty():
                evt, payload = self.data_queue.get_nowait()
                if evt == "init_ok":
                    cfg, h_max = payload
                    self.is_ready = True
                    self.lbl_server.config(
                        text=f"● Підключено ({cfg['sample_rate']} Гц | V={cfg['sound_speed']} м/с)",
                        fg="#16A34A"
                    )
                    self.txt_hmax.config(text=f"{h_max:.1f} м")
                    self.btn_start.config(state=tk.NORMAL)
                    self.status_var.set("Готово. Натисніть 'Старт' для початку лайв-сканування.")
                    self._redraw_scene()

                elif evt == "live_step":
                    step = payload["step"]
                    single_d = payload["single"]["depth"]
                    avg_d = payload["averaged"]["depth"]

                    self.rendered_single.append(single_d)
                    self.rendered_avg.append(avg_d)
                    self.current_step = step + 1

                    self.txt_step.config(text=f"{self.current_step} / {self.total_steps}")
                    self.txt_depth.config(text=f"{avg_d:.2f} м")
                    self.txt_single.config(text=f"{single_d:.2f} м")
                    k_val = payload["averaged"]["k_max"]
                    t_ms = payload["averaged"]["delay_time"] * 1000.0
                    self.txt_delay.config(text=f"{k_val} відл. ({t_ms:.1f} мс)")

                    self._redraw_seabed_only()
                    self._redraw_boat_and_beam()
                    self._draw_oscilloscopes(payload)

                    self.beam_tick = (self.beam_tick + 1) % 4

                    if self.current_step >= self.total_steps:
                        self.is_running = False
                        self.btn_start.config(state=tk.NORMAL)
                        self.btn_pause.config(state=tk.DISABLED)
                        self.status_var.set("Сканування маршруту завершено.")

                elif evt == "error":
                    self.lbl_server.config(text="● Помилка", fg="#DC2626")
                    self.status_var.set(f"Помилка: {payload}")
                    messagebox.showerror("Помилка", f"Помилка запиту:\n{payload}")
        finally:
            self.root.after(30, self._check_queue)

    def start_scan(self):
        if not self.is_ready:
            return

        if self.current_step >= self.total_steps:
            self.reset_scan()

        self.is_running = True
        self.is_paused = False
        self.btn_start.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL, text="⏸ Пауза")
        self.status_var.set("Лайв-сканування з сервера у реальному часі...")
        threading.Thread(target=self._live_fetch_worker, daemon=True).start()

    def toggle_pause(self):
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.config(text="▶ Продовжити")
            self.status_var.set("Сканування призупинено.")
        else:
            self.btn_pause.config(text="⏸ Пауза")
            self.status_var.set("Сканування продовжено...")

    def reset_scan(self):
        self.is_running = False
        self.is_paused = False

        self.current_step = 0
        self.rendered_single.clear()
        self.rendered_avg.clear()

        while not self.data_queue.empty():
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                break

        self.btn_start.config(state=tk.NORMAL if self.is_ready else tk.DISABLED)
        self.btn_pause.config(state=tk.DISABLED, text="⏸ Пауза")

        self.txt_step.config(text="0 / 100")
        self.txt_depth.config(text="0.00 м")
        self.txt_single.config(text="0.00 м")
        self.txt_delay.config(text="0 відліків (0.0 мс)")
        self.status_var.set("Скинуто на початок маршруту.")

        self._redraw_scene()
        self.canvas_sig.delete("all")
        self.canvas_corr.delete("all")

    def _get_geom(self):
        w = max(400, self.canvas.winfo_width())
        h = max(200, self.canvas.winfo_height())
        pad_l = 65
        pad_r = 35
        water_y = 50
        bed_bottom_y = h - 25
        return w, h, pad_l, pad_r, water_y, bed_bottom_y

    def _step_to_x(self, step, w, pad_l, pad_r):
        route_w = w - pad_l - pad_r
        return pad_l + (step / (self.total_steps - 1)) * route_w

    def _depth_to_y(self, depth, water_y, bed_bottom_y):
        max_h = getattr(self, "h_max", 360.0)
        clamped = max(0.0, min(depth, max_h))
        return water_y + (clamped / max_h) * (bed_bottom_y - water_y)

    def _redraw_scene(self):
        self.canvas.delete("all")
        w, h, pad_l, pad_r, water_y, bed_bottom_y = self._get_geom()

        self.canvas.create_rectangle(0, 0, w, water_y, fill="#F8FAFC", outline="")
        self.canvas.create_rectangle(0, water_y, w, h, fill="#F0F9FF", outline="")

        for depth_m in [50, 100, 150, 200, 250, 300, 360]:
            y_m = self._depth_to_y(depth_m, water_y, bed_bottom_y)
            self.canvas.create_line(pad_l, y_m, w - pad_r, y_m, fill="#E2E8F0", dash=(2, 4))
            self.canvas.create_text(pad_l - 8, y_m, text=f"{depth_m}м", font=("Consolas", 8), fill="#94A3B8", anchor="e")

        for st in [0, 20, 40, 60, 80, 99]:
            x_st = self._step_to_x(st, w, pad_l, pad_r)
            self.canvas.create_line(x_st, bed_bottom_y, x_st, bed_bottom_y + 4, fill="#94A3B8")
            self.canvas.create_text(x_st, bed_bottom_y + 12, text=f"{st}", font=("Consolas", 8), fill="#94A3B8")

        self.canvas.create_line(0, water_y, w, water_y, fill="#38BDF8", width=2)
        self.canvas.create_text(pad_l, water_y - 12, text="Рівень води (0 м)", font=("Segoe UI", 8), fill="#64748B", anchor="w")

        self._redraw_seabed_only()
        self._redraw_boat_and_beam()

    def _redraw_seabed_only(self):
        self.canvas.delete("seabed_layer")
        count = len(self.rendered_avg)
        if count == 0:
            return

        w, h, pad_l, pad_r, water_y, bed_bottom_y = self._get_geom()

        if count >= 2 and self.show_averaged.get():
            poly = [self._step_to_x(0, w, pad_l, pad_r), bed_bottom_y]
            for i in range(count):
                poly.extend([
                    self._step_to_x(i, w, pad_l, pad_r),
                    self._depth_to_y(self.rendered_avg[i], water_y, bed_bottom_y)
                ])
            poly.extend([self._step_to_x(count - 1, w, pad_l, pad_r), bed_bottom_y])
            self.canvas.create_polygon(poly, fill="#E2E8F0", outline="", tags="seabed_layer")

        if count >= 2 and self.show_single.get():
            single_pts = []
            for i in range(count):
                single_pts.extend([
                    self._step_to_x(i, w, pad_l, pad_r),
                    self._depth_to_y(self.rendered_single[i], water_y, bed_bottom_y)
                ])
            self.canvas.create_line(single_pts, fill="#EF4444", width=1.5, dash=(4, 3), tags="seabed_layer")

        if count >= 2 and self.show_averaged.get():
            avg_pts = []
            for i in range(count):
                avg_pts.extend([
                    self._step_to_x(i, w, pad_l, pad_r),
                    self._depth_to_y(self.rendered_avg[i], water_y, bed_bottom_y)
                ])
            self.canvas.create_line(avg_pts, fill="#0284C7", width=2.5, smooth=True, tags="seabed_layer")

    def _redraw_boat_and_beam(self):
        self.canvas.delete("boat_layer")
        w, h, pad_l, pad_r, water_y, bed_bottom_y = self._get_geom()

        step_idx = max(0, min(self.current_step - 1 if self.current_step > 0 else 0, self.total_steps - 1))
        bx = self._step_to_x(step_idx, w, pad_l, pad_r)
        by = water_y

        if self.rendered_avg and self.show_beam.get():
            last_depth = self.rendered_avg[-1]
            target_y = self._depth_to_y(last_depth, water_y, bed_bottom_y)

            beam_w = 12
            self.canvas.create_polygon(
                bx, by + 4,
                bx - beam_w, target_y,
                bx + beam_w, target_y,
                fill="#BAE6FD", outline="", tags="boat_layer"
            )

            for w_idx in range(2):
                frac = ((self.beam_tick + w_idx * 2) % 4) / 4.0
                wy = by + 4 + frac * (target_y - by - 4)
                self.canvas.create_line(bx - 6, wy, bx + 6, wy, fill="#0284C7", width=1.5, tags="boat_layer")

            self.canvas.create_oval(bx - 4, target_y - 4, bx + 4, target_y + 4, fill="#16A34A", outline="#15803D", tags="boat_layer")

        self.canvas.create_polygon(
            bx - 20, by,
            bx + 18, by,
            bx + 24, by - 9,
            bx - 20, by - 9,
            fill="#EF4444", outline="#B91C1C", width=1.5, tags="boat_layer"
        )
        self.canvas.create_rectangle(
            bx - 10, by - 18,
            bx + 8, by - 9,
            fill="#FFFFFF", outline="#475569", width=1.2, tags="boat_layer"
        )
        self.canvas.create_rectangle(
            bx + 1, by - 16,
            bx + 6, by - 11,
            fill="#38BDF8", outline="#0284C7", tags="boat_layer"
        )
        self.canvas.create_line(bx - 3, by - 18, bx - 3, by - 26, fill="#475569", width=1.5, tags="boat_layer")
        self.canvas.create_oval(bx - 7, by - 29, bx + 1, by - 25, fill="#F59E0B", outline="#D97706", tags="boat_layer")
        self.canvas.create_oval(bx - 3, by, bx + 3, by + 4, fill="#0284C7", outline="#0369A1", tags="boat_layer")

    def _draw_oscilloscopes(self, item):
        self.canvas_sig.delete("all")
        w1 = max(50, self.canvas_sig.winfo_width())
        h1 = max(40, self.canvas_sig.winfo_height())
        mid1 = h1 / 2.0

        self.canvas_sig.create_line(0, mid1, w1, mid1, fill="#E2E8F0")

        sig_single = item["single_signal"]
        sig_avg = item["averaged_signal"]
        n = len(sig_single)

        s_pts = []
        for i in range(0, n, 2):
            x = (i / (n - 1)) * w1
            y = mid1 - sig_single[i] * 3.0
            s_pts.extend([x, y])
        self.canvas_sig.create_line(s_pts, fill="#FCA5A5", width=1)

        a_pts = []
        for i in range(0, n, 2):
            x = (i / (n - 1)) * w1
            y = mid1 - sig_avg[i] * 3.0
            a_pts.extend([x, y])
        self.canvas_sig.create_line(a_pts, fill="#0D9488", width=1.5)

        self.canvas_sig.create_text(8, 10, text="— Одиночний зашумлений", font=("Segoe UI", 7), fill="#EF4444", anchor="w")
        self.canvas_sig.create_text(8, 22, text="— Усереднений (4 виміри)", font=("Segoe UI", 7, "bold"), fill="#0D9488", anchor="w")

        self.canvas_corr.delete("all")
        w2 = max(50, self.canvas_corr.winfo_width())
        h2 = max(40, self.canvas_corr.winfo_height())
        mid2 = h2 / 2.0 + 10

        self.canvas_corr.create_line(0, mid2, w2, mid2, fill="#E2E8F0")

        corr_s = item["single"]["correlation"]
        corr_a = item["averaged"]["correlation"]
        k_len = len(corr_a)

        c_s_pts = []
        for k in range(0, k_len, 2):
            x = (k / (k_len - 1)) * w2
            y = mid2 - corr_s[k] * 0.65
            c_s_pts.extend([x, y])
        self.canvas_corr.create_line(c_s_pts, fill="#FCA5A5", width=1, dash=(3, 3))

        c_a_pts = []
        for k in range(0, k_len, 2):
            x = (k / (k_len - 1)) * w2
            y = mid2 - corr_a[k] * 0.65
            c_a_pts.extend([x, y])
        self.canvas_corr.create_line(c_a_pts, fill="#0284C7", width=1.8)

        true_k = item["averaged"]["k_max"]
        kx = (true_k / (k_len - 1)) * w2
        self.canvas_corr.create_line(kx, 6, kx, h2 - 6, fill="#16A34A", width=1.5, dash=(3, 2))
        self.canvas_corr.create_text(kx + 4, 14, text=f"k_max = {true_k}", font=("Consolas", 8, "bold"), fill="#16A34A", anchor="w")

        self.canvas_corr.create_text(8, 10, text="--- R(k) одиночний", font=("Segoe UI", 7), fill="#EF4444", anchor="w")
        self.canvas_corr.create_text(8, 22, text="— R(k) усереднений", font=("Segoe UI", 7, "bold"), fill="#0284C7", anchor="w")
