#!/usr/bin/env python3
"""
TUF Control Center - ASUS TUF Dash F15 (FX517ZC)
A modern desktop control panel for performance profiles, safe EC fan controls,
battery charging caps, keyboard backlight, and real-time hardware telemetry.
Features rich live charts, per-core frequency visualizer, and dual rotating fan tachometers.
"""

import math
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any

# Add current folder to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backend

# Theme & Palette
BG_MAIN = "#0d0e12"
BG_CARD = "#161820"
BG_CARD_HOVER = "#1c1f2b"
BG_ACTIVE = "#252836"
BORDER_COLOR = "#2a2d3d"
BORDER_ACTIVE = "#ffaa00"
TUF_GOLD = "#ffaa00"
TUF_GOLD_HOVER = "#ffbe33"
TUF_CYAN = "#00e5ff"
TUF_CYAN_DIM = "#007a8a"
TUF_PURPLE = "#c084fc"
ACCENT_GREEN = "#10b981"
ACCENT_RED = "#ff3b57"
TEXT_WHITE = "#ffffff"
TEXT_MUTED = "#8b90a0"
TEXT_SUB = "#b3b7c6"

# ---------------------------------------------------------
# Custom Canvas Widgets for Visualization
# ---------------------------------------------------------

class CoreEqualizerCanvas(tk.Canvas):
    """Visualizes live clock speeds across all 12 CPU cores as an animated equalizer."""
    def __init__(self, parent, width=250, height=52, **kwargs):
        super().__init__(parent, width=width, height=height, bg=BG_CARD,
                         highlightthickness=0, bd=0, **kwargs)
        self.w = width
        self.h = height
        self.freqs: List[float] = [800.0] * 12
        self.draw()

    def update_freqs(self, freqs: List[float]):
        if freqs:
            self.freqs = freqs
            self.draw()

    def draw(self):
        self.delete("all")
        n = len(self.freqs) if self.freqs else 12
        if n == 0:
            return

        pad_x = 6
        pad_y = 6
        avail_w = self.w - (pad_x * 2)
        avail_h = self.h - (pad_y * 2) - 10  # leave room for core labels

        gap = 4
        bar_w = max(4, int((avail_w - (n - 1) * gap) / n))

        # Max frequency scale: 4.6 GHz (boost limit of 12450H)
        max_scale = 4600.0

        for i in range(n):
            freq = self.freqs[i] if i < len(self.freqs) else 400.0
            x0 = pad_x + i * (bar_w + gap)
            x1 = x0 + bar_w
            y_base = self.h - pad_y - 10

            # Background slot
            self.create_rectangle(x0, pad_y, x1, y_base, fill="#1e2230", outline="", width=0)

            # Bar height
            ratio = min(1.0, max(0.08, freq / max_scale))
            bar_h = ratio * avail_h
            y_top = y_base - bar_h

            # Dynamic color gradient according to frequency
            if freq < 1200:
                bar_color = TUF_CYAN
                cap_color = "#80f2ff"
            elif freq < 2800:
                bar_color = ACCENT_GREEN
                cap_color = "#6ee7b7"
            elif freq < 3800:
                bar_color = TUF_GOLD
                cap_color = "#ffe066"
            else:
                bar_color = ACCENT_RED
                cap_color = "#ff94a2"

            # Filled bar
            self.create_rectangle(x0, y_top, x1, y_base, fill=bar_color, outline="", width=0)
            # Glowing peak line
            self.create_line(x0, y_top, x1, y_top, fill=cap_color, width=2)

            # Core index label
            self.create_text(x0 + bar_w / 2, self.h - 4, text=f"{i+1}",
                             fill=TEXT_MUTED, font=("Noto Sans", 6, "bold"))


class GpuVirtualizerCanvas(tk.Canvas):
    """Virtualizes Intel UHD iGPU clock/load and NVIDIA RTX 3050 dGPU power state."""
    def __init__(self, parent, width=200, height=52, **kwargs):
        super().__init__(parent, width=width, height=height, bg=BG_CARD,
                         highlightthickness=0, bd=0, **kwargs)
        self.w = width
        self.h = height
        self.igpu_freq = 0
        self.igpu_usage = 0
        self.vram_mb = 0.0
        self.dgpu_active = False
        self.dgpu_status = "Sleep (0W)"
        self.draw()

    def update_gpu(self, igpu_freq: int, igpu_usage: int, vram_mb: float, dgpu_active: bool, dgpu_status: str):
        self.igpu_freq = igpu_freq
        self.igpu_usage = igpu_usage
        self.vram_mb = vram_mb
        self.dgpu_active = dgpu_active
        self.dgpu_status = dgpu_status
        self.draw()

    def draw(self):
        self.delete("all")
        pad_x = 8
        avail_w = self.w - (pad_x * 2)

        # 1. iGPU Section (Top)
        y_top = 3
        self.create_text(pad_x, y_top + 4, text="iGPU (Intel UHD)", fill=TUF_CYAN,
                         font=("Noto Sans", 7, "bold"), anchor="w")
        freq_str = f"{self.igpu_freq} MHz" if self.igpu_freq > 0 else "0 MHz (Idle)"
        self.create_text(self.w - pad_x, y_top + 4, text=freq_str, fill=TEXT_MUTED,
                         font=("Noto Sans", 7), anchor="e")

        # iGPU meter bar
        bar_y = y_top + 13
        bar_h = 5
        self.create_rectangle(pad_x, bar_y, pad_x + avail_w, bar_y + bar_h, fill="#202434", outline="")
        ratio = min(1.0, max(0.04, self.igpu_usage / 100.0))
        fill_w = ratio * avail_w
        self.create_rectangle(pad_x, bar_y, pad_x + fill_w, bar_y + bar_h, fill=TUF_CYAN, outline="")

        # 2. dGPU Section (Bottom)
        y_bot = 27
        self.create_text(pad_x, y_bot + 4, text="dGPU (RTX 3050)", fill=TUF_PURPLE,
                         font=("Noto Sans", 7, "bold"), anchor="w")

        if self.dgpu_active:
            status_text = "● ACTIVE 3D"
            pill_col = ACCENT_RED
        else:
            status_text = "● SLEEP (0W)"
            pill_col = ACCENT_GREEN

        self.create_text(self.w - pad_x, y_bot + 4, text=status_text, fill=pill_col,
                         font=("Noto Sans", 7, "bold"), anchor="e")

        vram_text = f"VRAM: {self.vram_mb} MB Allocated" if self.vram_mb > 0 else "Optimus Hybrid Power-Save"
        self.create_text(pad_x, self.h - 4, text=vram_text, fill=TEXT_MUTED,
                         font=("Noto Sans", 6), anchor="w")


class DualFanVisualizerCanvas(tk.Canvas):
    """Virtualizes the dual Arc Flow fans with arc tachometers and live rotating rotor blades."""
    def __init__(self, parent, width=250, height=65, **kwargs):
        super().__init__(parent, width=width, height=height, bg=BG_CARD,
                         highlightthickness=0, bd=0, **kwargs)
        self.w = width
        self.h = height
        self.cpu_rpm = 0
        self.gpu_rpm = 0
        self.fan_angle_cpu = 0.0
        self.fan_angle_gpu = 0.0
        self.draw_gauges()

    def update_rpms(self, cpu_rpm: int, gpu_rpm: int):
        self.cpu_rpm = cpu_rpm
        self.gpu_rpm = gpu_rpm
        self.draw_gauges()

    def advance_animation(self):
        """Called periodically by animation timer to spin rotor blades proportional to RPM."""
        if self.cpu_rpm > 0:
            self.fan_angle_cpu = (self.fan_angle_cpu + (self.cpu_rpm / 6000.0) * 0.45) % (2 * math.pi)
        if self.gpu_rpm > 0:
            self.fan_angle_gpu = (self.fan_angle_gpu + (self.gpu_rpm / 6000.0) * 0.45) % (2 * math.pi)
        self.draw_gauges()

    def draw_gauges(self):
        self.delete("all")
        # Layout: two circular tachometers side by side
        cx1 = self.w * 0.28
        cx2 = self.w * 0.74
        cy = self.h * 0.42
        r = 22

        # 1. CPU Fan (Left)
        self._draw_single_fan(cx1, cy, r, self.cpu_rpm, self.fan_angle_cpu,
                              label=f"CPU: {self.cpu_rpm} RPM", arc_color=TUF_CYAN)

        # 2. GPU Fan (Right)
        self._draw_single_fan(cx2, cy, r, self.gpu_rpm, self.fan_angle_gpu,
                              label=f"GPU: {self.gpu_rpm} RPM", arc_color=TUF_GOLD)

    def _draw_single_fan(self, cx, cy, r, rpm, angle, label, arc_color):
        # Outer track arc (240 degrees from 150 to 390)
        track_color = "#202434"
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=210, extent=-240,
                        outline=track_color, width=4, style="arc")

        # Active fill arc proportional to 6000 RPM
        pct = min(1.0, max(0.0, rpm / 6000.0))
        if pct > 0:
            self.create_arc(cx - r, cy - r, cx + r, cy + r, start=210, extent=-int(240 * pct),
                            outline=arc_color, width=4, style="arc")

        # Rotating 5-blade fan rotor inside
        rotor_r = r - 5
        num_blades = 5
        for b in range(num_blades):
            theta = angle + b * (2 * math.pi / num_blades)
            p1 = (cx, cy)
            p2 = (cx + rotor_r * math.cos(theta), cy + rotor_r * math.sin(theta))
            p3 = (cx + rotor_r * 0.75 * math.cos(theta + 0.45), cy + rotor_r * 0.75 * math.sin(theta + 0.45))
            self.create_polygon([p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]],
                                fill=arc_color if rpm > 0 else "#40465c", outline="", width=0)

        # Center hub cap
        self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#12141c", outline=arc_color, width=1.5)

        # Label under fan
        self.create_text(cx, self.h - 7, text=label, fill=TEXT_SUB, font=("Noto Sans", 7, "bold"))


class CyberBatteryCanvas(tk.Canvas):
    """Segmented cyber battery bar with active charge limit marker."""
    def __init__(self, parent, width=250, height=48, **kwargs):
        super().__init__(parent, width=width, height=height, bg=BG_CARD,
                         highlightthickness=0, bd=0, **kwargs)
        self.w = width
        self.h = height
        self.capacity = 100
        self.limit = 100
        self.ac_online = True
        self.pulse_phase = 0.0
        self.draw()

    def update_state(self, capacity: int, limit: int, ac_online: bool):
        self.capacity = capacity
        self.limit = limit
        self.ac_online = ac_online
        self.draw()

    def advance_pulse(self):
        if self.ac_online:
            self.pulse_phase = (self.pulse_phase + 0.25) % (2 * math.pi)
            self.draw()

    def draw(self):
        self.delete("all")
        pad_x = 8
        pad_y = 12
        avail_w = self.w - pad_x * 2 - 14  # space for battery terminal cap
        bar_h = 16

        # Terminal cap on right
        cap_x0 = pad_x + avail_w + 3
        cap_y0 = pad_y + 4
        cap_x1 = cap_x0 + 4
        cap_y1 = pad_y + bar_h - 4
        self.create_rectangle(cap_x0, cap_y0, cap_x1, cap_y1, fill="#40465c", outline="")

        # 10 segments
        num_segments = 10
        gap = 3
        seg_w = (avail_w - (num_segments - 1) * gap) / num_segments

        lit_segments = int(round((self.capacity / 100.0) * num_segments))

        for s in range(num_segments):
            sx0 = pad_x + s * (seg_w + gap)
            sx1 = sx0 + seg_w

            if s < lit_segments:
                if self.capacity <= 20:
                    fill_col = ACCENT_RED
                elif self.capacity <= 50:
                    fill_col = TUF_GOLD
                else:
                    fill_col = ACCENT_GREEN

                # Pulse effect on highest lit segment when charging
                if s == lit_segments - 1 and self.ac_online:
                    glow = (math.sin(self.pulse_phase) + 1.0) / 2.0
                    fill_col = "#7df7be" if glow > 0.5 else ACCENT_GREEN

                self.create_rectangle(sx0, pad_y, sx1, pad_y + bar_h, fill=fill_col, outline="")
            else:
                self.create_rectangle(sx0, pad_y, sx1, pad_y + bar_h, fill="#202434", outline="")

        # Limit marker line
        if self.limit < 100:
            lim_ratio = self.limit / 100.0
            lim_x = pad_x + lim_ratio * avail_w
            self.create_line(lim_x, pad_y - 4, lim_x, pad_y + bar_h + 4,
                             fill=TUF_GOLD, width=2, dash=(2, 2))
            self.create_text(lim_x, pad_y + bar_h + 10, text=f"CAP {self.limit}%",
                             fill=TUF_GOLD, font=("Noto Sans", 6, "bold"))
        else:
            self.create_text(pad_x + avail_w / 2, pad_y + bar_h + 10, text="CHARGE CAP: 100% (FULL)",
                             fill=TEXT_MUTED, font=("Noto Sans", 6, "bold"))


class TelemetryHistoryChart(tk.Canvas):
    """Rolling 30-sample real-time history wave chart for CPU Clock, Temp, and GPU Load."""
    def __init__(self, parent, height=105, **kwargs):
        super().__init__(parent, height=height, bg=BG_CARD, highlightthickness=0, bd=0, **kwargs)
        self.h = height
        self.max_pts = 30
        self.cpu_history: List[float] = []
        self.temp_history: List[float] = []
        self.gpu_history: List[float] = []
        self.bind("<Configure>", lambda e: self.draw())

    def push_data(self, ghz: float, temp: float, gpu_pct: float):
        self.cpu_history.append(ghz)
        self.temp_history.append(temp)
        self.gpu_history.append(gpu_pct)
        if len(self.cpu_history) > self.max_pts:
            self.cpu_history.pop(0)
        if len(self.temp_history) > self.max_pts:
            self.temp_history.pop(0)
        if len(self.gpu_history) > self.max_pts:
            self.gpu_history.pop(0)
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 100:
            w = 840
        h = self.h

        pad_left = 38
        pad_right = 65
        pad_top = 16
        pad_bot = 22
        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bot

        # Background Grid & Guide Lines
        grid_color = "#202434"
        for frac, label in [(0.25, "75%"), (0.5, "50%"), (0.75, "25%")]:
            gy = pad_top + frac * plot_h
            self.create_line(pad_left, gy, pad_left + plot_w, gy, fill=grid_color, dash=(3, 3))

        # Time labels
        self.create_text(pad_left, h - 9, text="-30s", fill=TEXT_MUTED, font=("Noto Sans", 7))
        self.create_text(pad_left + plot_w / 2, h - 9, text="-15s", fill=TEXT_MUTED, font=("Noto Sans", 7))
        self.create_text(pad_left + plot_w, h - 9, text="NOW", fill=TUF_CYAN, font=("Noto Sans", 7, "bold"))

        # Axis scales: Left = CPU GHz (0 - 4.5 GHz), Right = Temp °C (20 - 100 °C)
        self.create_text(pad_left - 18, pad_top + 4, text="4.5G", fill=TUF_CYAN, font=("Noto Sans", 6, "bold"))
        self.create_text(pad_left - 18, pad_top + plot_h, text="0.4G", fill=TUF_CYAN, font=("Noto Sans", 6))

        self.create_text(w - pad_right + 32, pad_top + 4, text="100°C", fill=TUF_GOLD, font=("Noto Sans", 6, "bold"))
        self.create_text(w - pad_right + 32, pad_top + plot_h, text="30°C", fill=TUF_GOLD, font=("Noto Sans", 6))

        n = len(self.cpu_history)
        if n < 2:
            return

        pts_cpu = []
        pts_temp = []
        pts_gpu = []

        step_x = plot_w / (self.max_pts - 1)
        start_idx = self.max_pts - n

        for i in range(n):
            x = pad_left + (start_idx + i) * step_x

            # CPU: 0.4 GHz to 4.5 GHz scale
            val_cpu = self.cpu_history[i]
            ratio_cpu = min(1.0, max(0.0, (val_cpu - 0.4) / (4.5 - 0.4)))
            y_cpu = pad_top + (1.0 - ratio_cpu) * plot_h
            pts_cpu.extend([x, y_cpu])

            # Temp: 30°C to 100°C scale
            val_temp = self.temp_history[i]
            ratio_temp = min(1.0, max(0.0, (val_temp - 30.0) / (100.0 - 30.0)))
            y_temp = pad_top + (1.0 - ratio_temp) * plot_h
            pts_temp.extend([x, y_temp])

            # GPU: 0 to 100% scale
            val_gpu = self.gpu_history[i] if i < len(self.gpu_history) else 0.0
            ratio_gpu = min(1.0, max(0.0, val_gpu / 100.0))
            y_gpu = pad_top + (1.0 - ratio_gpu) * plot_h
            pts_gpu.extend([x, y_gpu])

        # Draw GPU Line (Purple with glow)
        if len(pts_gpu) >= 4:
            self.create_line(pts_gpu, fill=TUF_PURPLE, width=1.8, smooth=True)
            gx, gy = pts_gpu[-2], pts_gpu[-1]
            self.create_oval(gx - 3, gy - 3, gx + 3, gy + 3, fill=TUF_PURPLE, outline="#ffffff", width=1)

        # Draw CPU Line (Cyan with glow)
        if len(pts_cpu) >= 4:
            self.create_line(pts_cpu, fill=TUF_CYAN, width=2, smooth=True)
            # Latest point glowing dot
            lx, ly = pts_cpu[-2], pts_cpu[-1]
            self.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, fill=TUF_CYAN, outline="#ffffff", width=1.5)

        # Draw Temp Line (Gold with glow)
        if len(pts_temp) >= 4:
            self.create_line(pts_temp, fill=TUF_GOLD, width=2, smooth=True)
            # Latest point glowing dot
            tx, ty = pts_temp[-2], pts_temp[-1]
            self.create_oval(tx - 4, ty - 4, tx + 4, ty + 4, fill=TUF_GOLD, outline="#ffffff", width=1.5)


# ---------------------------------------------------------
# Main Application Class
# ---------------------------------------------------------

class TUFControlApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TUF Control Center - ASUS TUF Dash F15")
        self.root.geometry("1000x890")
        self.root.minsize(960, 820)
        self.root.configure(bg=BG_MAIN)

        self.current_profile = "Balanced"
        self.current_fan_mode = "Balanced"
        self.current_bat_limit = 100
        self.current_led = "Med"
        self.current_aura_mode = "Static"
        self.running = True

        # Try to load icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            try:
                img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(False, img)
            except Exception:
                pass

        self._build_ui()

        # Initial fetch
        self.refresh_controls_state()

        # Background thread for sysfs telemetry
        self.telemetry_thread = threading.Thread(target=self._telemetry_worker, daemon=True)
        self.telemetry_thread.start()

        # Start micro-animation loop for spinning fan rotor blades and pulse effects (25 FPS)
        self._animation_tick()

        # Handle clean exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        self.main_frame = tk.Frame(self.root, bg=BG_MAIN)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=12)

        # 1. Header
        self._build_header(self.main_frame)

        # 2. Alert Banner (Visible when BD PROCHOT / 400 MHz is asserted)
        self.alert_frame = tk.Frame(self.main_frame, bg="#3b1117", highlightbackground=ACCENT_RED, highlightthickness=1)
        self.alert_label = tk.Label(self.alert_frame,
                                    text="⚠️ WARNING: CPU is locked at 400 MHz! (BD PROCHOT / EC emergency throttling active)",
                                    bg="#3b1117", fg="#ff8090", font=("Noto Sans", 10, "bold"), padx=12, pady=7)
        self.alert_label.pack(side=tk.LEFT)

        self.btn_unthrottle = tk.Button(self.alert_frame, text="⚡ Fix & Unthrottle", font=("Noto Sans", 9, "bold"),
                                        bg=ACCENT_RED, fg=TEXT_WHITE, activebackground="#d92b45",
                                        activeforeground=TEXT_WHITE, bd=0, padx=12, pady=4, cursor="hand2",
                                        command=self.unthrottle_cpu)
        self.btn_unthrottle.pack(side=tk.RIGHT, padx=10)

        # 3. Telemetry Overview Cards (Equipped with Canvas Visualizers)
        self._build_telemetry_section(self.main_frame)

        # 4. Live 30s Real-Time History Graph
        self._build_chart_section(self.main_frame)

        # 5. Performance & Fan Profiles Section
        self._build_fan_control_section(self.main_frame)

        # 6. Controls Row: Battery Limit & Keyboard Backlight
        controls_row = tk.Frame(self.main_frame, bg=BG_MAIN)
        controls_row.pack(fill=tk.X, pady=(0, 10))

        self._build_battery_limit_card(controls_row)
        self._build_keyboard_card(controls_row)

        # 7. System Info Footer
        self._build_footer(self.main_frame)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=BG_MAIN)
        header.pack(fill=tk.X, pady=(0, 10))

        title_block = tk.Frame(header, bg=BG_MAIN)
        title_block.pack(side=tk.LEFT)

        app_title = tk.Label(title_block, text="TUF CONTROL CENTER", font=("Noto Sans", 15, "bold"), fg=TUF_GOLD, bg=BG_MAIN)
        app_title.pack(anchor="w")

        model_subtitle = tk.Label(title_block, text="ASUS TUF DASH F15 (FX517ZC) • HARDWARE CONTROLLER",
                                  font=("Noto Sans", 8, "bold"), fg=TEXT_MUTED, bg=BG_MAIN)
        model_subtitle.pack(anchor="w")

        self.status_block = tk.Frame(header, bg=BG_MAIN)
        self.status_block.pack(side=tk.RIGHT)

        self.power_pill = tk.Label(self.status_block, text="🔌 AC Connected", font=("Noto Sans", 9, "bold"),
                                   fg=ACCENT_GREEN, bg=BG_CARD, padx=12, pady=5,
                                   highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.power_pill.pack(side=tk.RIGHT, padx=4)

    def _build_telemetry_section(self, parent):
        telemetry_frame = tk.Frame(parent, bg=BG_MAIN)
        telemetry_frame.pack(fill=tk.X, pady=(0, 10))
        telemetry_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="telemetry")

        # ----------------- Card 0: CPU Speed & 12-Core Equalizer -----------------
        self.card_cpu = self._create_card(telemetry_frame, 0, "⚡ CPU CLOCK SPECTRUM")
        
        cpu_top_row = tk.Frame(self.card_cpu, bg=BG_CARD)
        cpu_top_row.pack(fill=tk.X, padx=10, pady=(2, 0))

        self.lbl_cpu_ghz = tk.Label(cpu_top_row, text="-- GHz", font=("Noto Sans", 16, "bold"), fg=TEXT_WHITE, bg=BG_CARD)
        self.lbl_cpu_ghz.pack(side=tk.LEFT)

        self.badge_cpu = tk.Label(cpu_top_row, text="NORMAL", font=("Noto Sans", 7, "bold"),
                                  fg=ACCENT_GREEN, bg="#122b1e", padx=5, pady=2)
        self.badge_cpu.pack(side=tk.RIGHT, pady=4)

        self.lbl_cpu_sub = tk.Label(self.card_cpu, text="Peak: -- GHz • 12 Cores",
                                    font=("Noto Sans", 8), fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_cpu_sub.pack(anchor="w", padx=10, pady=(0, 4))

        # Core Equalizer Canvas
        self.canvas_equalizer = CoreEqualizerCanvas(self.card_cpu, width=200, height=48)
        self.canvas_equalizer.pack(fill=tk.X, padx=6, pady=(0, 8))

        # ----------------- Card 1: Dual GPU (Intel UHD & RTX 3050) -----------------
        self.card_gpu = self._create_card(telemetry_frame, 1, "🎮 DUAL GPU ACCELERATION")

        gpu_top_row = tk.Frame(self.card_gpu, bg=BG_CARD)
        gpu_top_row.pack(fill=tk.X, padx=10, pady=(2, 0))

        self.lbl_gpu_title = tk.Label(gpu_top_row, text="RTX 3050", font=("Noto Sans", 15, "bold"), fg=TEXT_WHITE, bg=BG_CARD)
        self.lbl_gpu_title.pack(side=tk.LEFT)

        self.badge_gpu_status = tk.Label(gpu_top_row, text="SLEEP (0W)", font=("Noto Sans", 7, "bold"),
                                         fg=ACCENT_GREEN, bg="#122b1e", padx=5, pady=2)
        self.badge_gpu_status.pack(side=tk.RIGHT, pady=4)

        self.lbl_gpu_sub = tk.Label(self.card_gpu, text="UHD: 0 MHz • 0 MB",
                                    font=("Noto Sans", 8), fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_gpu_sub.pack(anchor="w", padx=10, pady=(0, 4))

        # GPU Virtualizer Canvas
        self.canvas_gpu = GpuVirtualizerCanvas(self.card_gpu, width=200, height=48)
        self.canvas_gpu.pack(fill=tk.X, padx=6, pady=(0, 8))

        # ----------------- Card 2: Cooling & Dual Arc Flow Fans -----------------
        self.card_thermal = self._create_card(telemetry_frame, 2, "🌪️ THERMALS & FANS")

        therm_top_row = tk.Frame(self.card_thermal, bg=BG_CARD)
        therm_top_row.pack(fill=tk.X, padx=10, pady=(2, 0))

        self.lbl_temp = tk.Label(therm_top_row, text="-- °C", font=("Noto Sans", 16, "bold"), fg=TUF_CYAN, bg=BG_CARD)
        self.lbl_temp.pack(side=tk.LEFT)

        self.lbl_fan_status = tk.Label(therm_top_row, text="Turbo Fans", font=("Noto Sans", 7, "bold"),
                                       fg=TUF_GOLD, bg="#262215", padx=5, pady=2)
        self.lbl_fan_status.pack(side=tk.RIGHT, pady=4)

        # Dual Rotating Fans Canvas Visualizer
        self.canvas_fans = DualFanVisualizerCanvas(self.card_thermal, width=200, height=62)
        self.canvas_fans.pack(fill=tk.X, padx=4, pady=(0, 8))

        # ----------------- Card 3: Battery & Power Flow -----------------
        self.card_bat = self._create_card(telemetry_frame, 3, "🔋 BATTERY & CHARGE")

        bat_top_row = tk.Frame(self.card_bat, bg=BG_CARD)
        bat_top_row.pack(fill=tk.X, padx=10, pady=(2, 0))

        self.lbl_bat_pct = tk.Label(bat_top_row, text="--%", font=("Noto Sans", 16, "bold"), fg=TEXT_WHITE, bg=BG_CARD)
        self.lbl_bat_pct.pack(side=tk.LEFT)

        self.lbl_bat_watts = tk.Label(bat_top_row, text="--W", font=("Noto Sans", 8, "bold"), fg=ACCENT_GREEN, bg=BG_CARD)
        self.lbl_bat_watts.pack(side=tk.RIGHT, pady=4)

        self.lbl_bat_status_detail = tk.Label(self.card_bat, text="Status: Calculating...", font=("Noto Sans", 8), fg=TEXT_MUTED, bg=BG_CARD)
        self.lbl_bat_status_detail.pack(anchor="w", padx=10, pady=(0, 4))

        # Cyber Segmented Battery Canvas
        self.canvas_battery = CyberBatteryCanvas(self.card_bat, width=200, height=48)
        self.canvas_battery.pack(fill=tk.X, padx=6, pady=(0, 8))

    def _create_card(self, parent, col, title):
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.grid(row=0, column=col, padx=4, sticky="nsew")
        lbl = tk.Label(card, text=title, font=("Noto Sans", 8, "bold"), fg=TUF_GOLD, bg=BG_CARD)
        lbl.pack(anchor="w", padx=10, pady=(8, 2))
        return card

    def _build_chart_section(self, parent):
        """Builds the dedicated real-time telemetry line wave chart."""
        chart_card = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        chart_card.pack(fill=tk.X, pady=(0, 10))

        header_bar = tk.Frame(chart_card, bg=BG_CARD)
        header_bar.pack(fill=tk.X, padx=14, pady=(8, 2))

        title = tk.Label(header_bar, text="📈 REAL-TIME HARDWARE MONITOR (30s WAVE HISTORY)",
                         font=("Noto Sans", 8, "bold"), fg=TUF_GOLD, bg=BG_CARD)
        title.pack(side=tk.LEFT)

        # Legend & Live Readouts
        legend_frame = tk.Frame(header_bar, bg=BG_CARD)
        legend_frame.pack(side=tk.RIGHT)

        tk.Label(legend_frame, text="■", fg=TUF_CYAN, bg=BG_CARD, font=("Noto Sans", 9)).pack(side=tk.LEFT)
        self.lbl_chart_cpu = tk.Label(legend_frame, text="CPU: -- GHz", font=("Noto Sans", 8, "bold"), fg=TEXT_WHITE, bg=BG_CARD)
        self.lbl_chart_cpu.pack(side=tk.LEFT, padx=(2, 10))

        tk.Label(legend_frame, text="■", fg=TUF_GOLD, bg=BG_CARD, font=("Noto Sans", 9)).pack(side=tk.LEFT)
        self.lbl_chart_temp = tk.Label(legend_frame, text="Temp: -- °C", font=("Noto Sans", 8, "bold"), fg=TEXT_WHITE, bg=BG_CARD)
        self.lbl_chart_temp.pack(side=tk.LEFT, padx=(2, 10))

        tk.Label(legend_frame, text="■", fg=TUF_PURPLE, bg=BG_CARD, font=("Noto Sans", 9)).pack(side=tk.LEFT)
        self.lbl_chart_gpu = tk.Label(legend_frame, text="GPU: --%", font=("Noto Sans", 8, "bold"), fg=TEXT_WHITE, bg=BG_CARD)
        self.lbl_chart_gpu.pack(side=tk.LEFT, padx=(2, 4))

        self.chart_canvas = TelemetryHistoryChart(chart_card, height=95)
        self.chart_canvas.pack(fill=tk.X, padx=8, pady=(0, 6))

    def _build_fan_control_section(self, parent):
        frame = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        frame.pack(fill=tk.X, pady=(0, 10))

        header_row = tk.Frame(frame, bg=BG_CARD)
        header_row.pack(fill=tk.X, padx=14, pady=(10, 4))

        title_lbl = tk.Label(header_row, text="🌪️ THERMAL PROFILES & FAN SPEED CONTROL",
                             font=("Noto Sans", 9, "bold"), fg=TUF_GOLD, bg=BG_CARD)
        title_lbl.pack(side=tk.LEFT)

        self.lbl_fan_active_badge = tk.Label(header_row, text="Active: Standard (Balanced)",
                                             font=("Noto Sans", 8, "bold"), fg=TUF_CYAN, bg="#12242c", padx=8, pady=2)
        self.lbl_fan_active_badge.pack(side=tk.RIGHT)

        note_lbl = tk.Label(frame,
                            text="Direct hardware EC control prevents BD PROCHOT 400 MHz locks while providing optimal cooling.",
                            font=("Noto Sans", 8), fg=TEXT_MUTED, bg=BG_CARD)
        note_lbl.pack(anchor="w", padx=14, pady=(0, 8))

        btn_container = tk.Frame(frame, bg=BG_CARD)
        btn_container.pack(fill=tk.X, padx=10, pady=(0, 12))
        btn_container.columnconfigure((0, 1, 2), weight=1, uniform="fanmodes")

        self.fan_buttons = {}
        modes = [
            ("Quiet", "🍃 Silent / Quiet Fans", "Low acoustic RPM curve • Power saver • Whisper-quiet"),
            ("Balanced", "⚖️ Standard Fans", "Dynamic balance of acoustics, CPU boost, and airflow"),
            ("Turbo", "🚀 Overboost Turbo Fans", "High RPM aggressive fan curves • Maximum cooling power")
        ]

        for idx, (m_id, m_title, m_desc) in enumerate(modes):
            card = tk.Frame(btn_container, bg=BG_ACTIVE, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
            card.grid(row=0, column=idx, padx=3, sticky="nsew")

            lbl_title = tk.Label(card, text=m_title, font=("Noto Sans", 9, "bold"), fg=TEXT_WHITE, bg=BG_ACTIVE)
            lbl_title.pack(anchor="w", padx=10, pady=(8, 2))

            lbl_desc = tk.Label(card, text=m_desc, font=("Noto Sans", 8), fg=TEXT_MUTED, bg=BG_ACTIVE, wraplength=210, justify="left")
            lbl_desc.pack(anchor="w", padx=10, pady=(0, 10))

            card.bind("<Button-1>", lambda e, name=m_id: self.select_fan_mode(name))
            lbl_title.bind("<Button-1>", lambda e, name=m_id: self.select_fan_mode(name))
            lbl_desc.bind("<Button-1>", lambda e, name=m_id: self.select_fan_mode(name))

            self.fan_buttons[m_id] = {
                "card": card,
                "title": lbl_title,
                "desc": lbl_desc
            }

    def _build_battery_limit_card(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        title = tk.Label(card, text="🔋 BATTERY HEALTH CARE", font=("Noto Sans", 9, "bold"), fg=TUF_GOLD, bg=BG_CARD)
        title.pack(anchor="w", padx=12, pady=(8, 2))

        sub = tk.Label(card, text="Cap maximum charge to prolong battery lifespan",
                       font=("Noto Sans", 8), fg=TEXT_MUTED, bg=BG_CARD)
        sub.pack(anchor="w", padx=12, pady=(0, 6))

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.bat_limit_buttons = {}
        presets = [
            (60, "60% (Desk)"),
            (80, "80% (Daily)"),
            (100, "100% (Travel)")
        ]
        for limit, text in presets:
            btn = tk.Label(btn_row, text=text, font=("Noto Sans", 8, "bold"), fg=TEXT_WHITE, bg=BG_ACTIVE,
                           padx=8, pady=7, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            btn.bind("<Button-1>", lambda e, val=limit: self.select_battery_limit(val))
            self.bat_limit_buttons[limit] = btn

        # Info advice block
        tip_frame = tk.Frame(card, bg="#12141c", highlightbackground=BORDER_COLOR, highlightthickness=1)
        tip_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.lbl_bat_advice = tk.Label(tip_frame,
                                       text="💡 Lifespan Tip: Setting 80% limit prevents lithium cell oxidation when AC power remains plugged in. Use 100% when traveling.",
                                       font=("Noto Sans", 7), fg=TEXT_MUTED, bg="#12141c", wraplength=380, justify="left", padx=8, pady=6)
        self.lbl_bat_advice.pack(anchor="w")

    def _build_keyboard_card(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        title_row = tk.Frame(card, bg=BG_CARD)
        title_row.pack(fill=tk.X, padx=12, pady=(8, 2))

        title = tk.Label(title_row, text="⌨️ KEYBOARD BACKLIGHT", font=("Noto Sans", 9, "bold"), fg=TUF_GOLD, bg=BG_CARD)
        title.pack(side=tk.LEFT)

        self.lbl_aura_active_badge = tk.Label(title_row, text="Static • Med", font=("Noto Sans", 7, "bold"),
                                              fg=TUF_CYAN, bg="#12242c", padx=6, pady=2)
        self.lbl_aura_active_badge.pack(side=tk.RIGHT)

        sub = tk.Label(card, text="Hardware backlight animation effect & brightness levels",
                       font=("Noto Sans", 8), fg=TEXT_MUTED, bg=BG_CARD)
        sub.pack(anchor="w", padx=12, pady=(0, 6))

        # 1. Backlight Effect Types (Static, Breathe, Pulse)
        type_row = tk.Frame(card, bg=BG_CARD)
        type_row.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.aura_mode_buttons = {}
        modes = [
            ("Static", "✨ Static"),
            ("Breathe", "💨 Breathe"),
            ("Pulse", "⚡ Pulse")
        ]
        for m_id, m_text in modes:
            btn = tk.Label(type_row, text=m_text, font=("Noto Sans", 8, "bold"), fg=TEXT_WHITE, bg=BG_ACTIVE,
                           padx=6, pady=7, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            btn.bind("<Button-1>", lambda e, name=m_id: self.select_aura_mode(name))
            self.aura_mode_buttons[m_id] = btn

        # 2. Brightness row
        b_btns = tk.Frame(card, bg=BG_CARD)
        b_btns.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.led_buttons = {}
        for level in ["Off", "Low", "Med", "High"]:
            btn = tk.Label(b_btns, text=level, font=("Noto Sans", 8, "bold"), fg=TEXT_WHITE, bg=BG_ACTIVE,
                           padx=6, pady=6, highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2")
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            btn.bind("<Button-1>", lambda e, lvl=level: self.select_led_brightness(lvl))
            self.led_buttons[level] = btn

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        footer.pack(fill=tk.X, pady=(0, 2))

        specs_left = tk.Label(footer, text="HARDWARE: Intel Alder Lake-P (12 Cores)  •  NVIDIA GeForce RTX 3050 Mobile  •  Intel UHD Graphics",
                              font=("Noto Sans", 8), fg=TEXT_MUTED, bg=BG_CARD, padx=12, pady=6)
        specs_left.pack(side=tk.LEFT)

        self.lbl_refresh_pulse = tk.Label(footer, text="● Hardware Telemetry Active",
                                          font=("Noto Sans", 8, "bold"), fg=ACCENT_GREEN, bg=BG_CARD, padx=12)
        self.lbl_refresh_pulse.pack(side=tk.RIGHT)

    def _animation_tick(self):
        """Micro-animation timer running at ~25 FPS to spin fan blades smoothly."""
        if not self.running:
            return
        try:
            self.canvas_fans.advance_animation()
            self.canvas_battery.advance_pulse()
        except Exception:
            pass
        self.root.after(40, self._animation_tick)

    def refresh_controls_state(self):
        def worker():
            prof = backend.get_active_profile()
            fan_mode = backend.get_fan_mode()
            bat_limit = backend.get_battery_limit()
            led = backend.get_led_brightness()
            aura_mode = backend.get_aura_mode()
            self.root.after(0, lambda: self._apply_controls_state(prof, fan_mode, bat_limit, led, aura_mode))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_controls_state(self, profile: str, fan_mode: str, bat_limit: int, led: str, aura_mode: str):
        self.current_profile = profile
        self.current_fan_mode = fan_mode
        self.current_bat_limit = bat_limit
        self.current_led = led
        self.current_aura_mode = aura_mode

        for m_id, item in self.fan_buttons.items():
            if m_id.lower() == fan_mode.lower():
                item["card"].configure(bg="#2d2812", highlightbackground=TUF_GOLD, highlightthickness=2)
                item["title"].configure(bg="#2d2812", fg=TUF_GOLD)
                item["desc"].configure(bg="#2d2812", fg=TEXT_WHITE)
            else:
                item["card"].configure(bg=BG_ACTIVE, highlightbackground=BORDER_COLOR, highlightthickness=1)
                item["title"].configure(bg=BG_ACTIVE, fg=TEXT_WHITE)
                item["desc"].configure(bg=BG_ACTIVE, fg=TEXT_MUTED)

        self.lbl_fan_active_badge.configure(text=f"Active: {fan_mode}")
        self.lbl_fan_status.configure(text=f"{fan_mode} Fans")

        for limit_val, btn in self.bat_limit_buttons.items():
            if abs(limit_val - bat_limit) <= 5:
                btn.configure(bg="#2d2812", fg=TUF_GOLD, highlightbackground=TUF_GOLD, highlightthickness=2)
            else:
                btn.configure(bg=BG_ACTIVE, fg=TEXT_WHITE, highlightbackground=BORDER_COLOR, highlightthickness=1)

        for lvl_name, btn in self.led_buttons.items():
            if lvl_name.lower() == led.lower():
                btn.configure(bg="#2d2812", fg=TUF_GOLD, highlightbackground=TUF_GOLD, highlightthickness=2)
            else:
                btn.configure(bg=BG_ACTIVE, fg=TEXT_WHITE, highlightbackground=BORDER_COLOR, highlightthickness=1)

        for m_id, btn in self.aura_mode_buttons.items():
            if m_id.lower() == aura_mode.lower():
                btn.configure(bg="#2d2812", fg=TUF_GOLD, highlightbackground=TUF_GOLD, highlightthickness=2)
            else:
                btn.configure(bg=BG_ACTIVE, fg=TEXT_WHITE, highlightbackground=BORDER_COLOR, highlightthickness=1)

        self.lbl_aura_active_badge.configure(text=f"{aura_mode} • {led}")

    def select_fan_mode(self, mode_name: str):
        def worker():
            backend.set_fan_mode(mode_name)
            self.root.after(0, self.refresh_controls_state)
        threading.Thread(target=worker, daemon=True).start()

    def unthrottle_cpu(self):
        def worker():
            backend.reset_fan_curves()
            backend.set_profile("Balanced")
            self.root.after(0, self.refresh_controls_state)
        threading.Thread(target=worker, daemon=True).start()

    def select_battery_limit(self, limit: int):
        def worker():
            backend.set_battery_limit(limit)
            self.root.after(0, self.refresh_controls_state)
        threading.Thread(target=worker, daemon=True).start()

    def select_led_brightness(self, level: str):
        def worker():
            backend.set_led_brightness(level)
            self.root.after(0, self.refresh_controls_state)
        threading.Thread(target=worker, daemon=True).start()

    def select_aura_mode(self, mode_name: str):
        def worker():
            backend.set_aura_effect(mode_name)
            self.root.after(0, self.refresh_controls_state)
        threading.Thread(target=worker, daemon=True).start()

    def _telemetry_worker(self):
        while self.running:
            cpu = backend.get_cpu_telemetry()
            gpu = backend.get_gpu_telemetry()
            fans = backend.get_fans()
            temp = backend.get_max_temp()
            bat = backend.get_battery_telemetry()
            self.root.after(0, lambda c=cpu, g=gpu, f=fans, t=temp, b=bat: self._update_telemetry_ui(c, g, f, t, b))
            time.sleep(1.2)

    def _update_telemetry_ui(self, cpu, gpu, fans, temp, bat):
        if not self.running:
            return

        # 1. Throttling banner
        if cpu.get("is_throttled", False):
            if not self.alert_frame.winfo_ismapped():
                self.alert_frame.pack(fill=tk.X, pady=(0, 10), before=self.card_cpu.master)
            self.badge_cpu.configure(text="⚠️ 400 MHz THROTTLED", fg="#ff4d4d", bg="#3b1117")
        else:
            if self.alert_frame.winfo_ismapped():
                self.alert_frame.pack_forget()
            self.badge_cpu.configure(text="NORMAL BOOST", fg=ACCENT_GREEN, bg="#122b1e")

        # 2. CPU GHz & Per-Core Equalizer
        avg_ghz = round(cpu.get("avg_mhz", 0) / 1000.0, 2)
        max_ghz = round(cpu.get("max_mhz", 0) / 1000.0, 2)
        cores = cpu.get("cores", 12)
        self.lbl_cpu_ghz.configure(text=f"{avg_ghz} GHz")
        self.lbl_cpu_sub.configure(text=f"Peak: {max_ghz} GHz • {cores} Cores Active")
        self.canvas_equalizer.update_freqs(cpu.get("freqs", []))

        # 3. Dual GPU (Intel UHD & NVIDIA RTX 3050)
        dgpu_active = gpu.get("dgpu_active", False)
        dgpu_status = gpu.get("dgpu_status", "Sleep (0W)")
        igpu_freq = gpu.get("igpu_freq", 0)
        igpu_usage = gpu.get("igpu_usage", 0)
        vram_mb = gpu.get("vram_mb", 0.0)

        gpu_pct = 100 if dgpu_active else igpu_usage
        if dgpu_active:
            self.lbl_gpu_title.configure(text="RTX 3050", fg="#ff6b81")
            self.badge_gpu_status.configure(text="ACTIVE 3D", fg=ACCENT_RED, bg="#3b1117")
            self.lbl_gpu_sub.configure(text=f"VRAM: {vram_mb} MB • Arc Flow Fan")
        else:
            self.lbl_gpu_title.configure(text="RTX 3050", fg=TEXT_WHITE)
            self.badge_gpu_status.configure(text="SLEEP (0W)", fg=ACCENT_GREEN, bg="#122b1e")
            self.lbl_gpu_sub.configure(text=f"UHD: {igpu_freq} MHz • {igpu_usage}%")

        self.canvas_gpu.update_gpu(igpu_freq, igpu_usage, vram_mb, dgpu_active, dgpu_status)

        # 4. Cooling & Thermals & Dual Rotating Fans
        self.lbl_temp.configure(text=f"{temp} °C")
        if temp < 55:
            self.lbl_temp.configure(fg=TUF_CYAN)
        elif temp < 75:
            self.lbl_temp.configure(fg=TUF_GOLD)
        else:
            self.lbl_temp.configure(fg=ACCENT_RED)

        cpu_fan = fans.get("cpu", 0)
        gpu_fan = fans.get("gpu", 0)
        self.canvas_fans.update_rpms(cpu_fan, gpu_fan)

        # 5. Battery & Power Flow
        cap = bat.get("capacity", 0)
        status = bat.get("status", "Unknown")
        watts = bat.get("watts", 0.0)
        ac_on = bat.get("ac_online", False)

        self.lbl_bat_pct.configure(text=f"{cap}%")
        self.canvas_battery.update_state(cap, self.current_bat_limit, ac_on)

        if ac_on:
            self.power_pill.configure(text="🔌 AC Connected", fg=ACCENT_GREEN)
            rate_str = f"+{watts}W" if watts > 0 else ""
            self.lbl_bat_watts.configure(text=rate_str, fg=ACCENT_GREEN)
            self.lbl_bat_status_detail.configure(text=f"{status} • Limit: {self.current_bat_limit}%")
        else:
            self.power_pill.configure(text="🔋 On Battery", fg=TUF_GOLD)
            rate_str = f"-{watts}W" if watts > 0 else ""
            self.lbl_bat_watts.configure(text=rate_str, fg=TUF_GOLD)
            self.lbl_bat_status_detail.configure(text=f"{status} • Limit: {self.current_bat_limit}%")

        # 6. Push data to live 30s history wave chart
        self.chart_canvas.push_data(avg_ghz, temp, gpu_pct)
        self.lbl_chart_cpu.configure(text=f"CPU: {avg_ghz} GHz")
        self.lbl_chart_temp.configure(text=f"Temp: {temp} °C")
        gpu_label_status = "RTX Active" if dgpu_active else f"UHD {igpu_usage}%"
        self.lbl_chart_gpu.configure(text=f"GPU: {gpu_pct}% ({gpu_label_status})")

    def on_close(self):
        self.running = False
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TUFControlApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
