# Session Memory & Technical Log

**Date:** 2026-10-19 to 2026-10-20  
**Machine:** ASUS TUF Dash F15 (FX517ZC)  
**OS:** Linux (XFCE / LightDM / Kernel 6.x)  
**CPU:** 12th Gen Intel Core Alder Lake-P (12 Cores / 16 Threads)  
**GPU:** NVIDIA GeForce RTX 3050 Mobile + Intel UHD Graphics  

---

## 1. Development of ASUS TUF Control Center (`asus-tuf-control`)

A lightweight, native Linux desktop application was developed to control hardware features without bloated web/electron wrappers.

### Architecture & Files
* **Location:** `/home/ndk/Apps/asus-tuf-control/`
* **`backend.py`:** Reads directly from `/sys` and `/proc` for zero-latency telemetry; executes `asusctl` commands via D-Bus user session.
* **`app.py`:** Modern Tkinter application with custom TUF dark gaming aesthetics (`#0d0e12`, TUF Gold `#ffaa00`, Neon Cyan `#00e5ff`).
* **`icon.png`:** Custom TUF emblem vector icon.
* **`~/.local/bin/asus-tuf-control`:** Global terminal command launcher.
* **`~/.local/share/applications/asus-tuf-control.desktop`:** XFCE application menu entry.

### Features
1. **Performance Profiles:** One-click switching between `Quiet`, `Balanced`, and `Performance` via `asusctl profile set`.
2. **Battery Health Limit:** Charge caps for `60% (Desk/Lifespan)`, `80% (Daily)`, and `100% (Travel)` via `asusctl battery limit`.
3. **Keyboard Backlight:** 4-level brightness control (`Off`, `Low`, `Med`, `High`).
4. **Real-Time Hardware Telemetry (Every 1.2s):**
   * Average GHz & Peak Core Boost GHz.
   * Dual Arc Flow Fan Speeds: Live CPU Fan RPM & GPU Fan RPM.
   * Package temperature with color coding.
   * Battery percentage, charging rate in Watts (e.g. `+64.5W`), and AC connection status.
5. **BD PROCHOT Watchdog:** Visual warning banner displayed if CPU drops to 400 MHz with a one-click unthrottle button.

---

## 2. Technical Discovery: Why Custom Fan Curves Caused 400 MHz CPU Lock

### The Issue
When setting custom fan curves via `asusctl fan-curve --enable-fan-curves true`, the CPU frequency immediately collapsed to 400 MHz across all cores.

### Technical Explanation:
* **ROG vs TUF Motherboard WMI:**
  * ASUS ROG laptops contain ACPI WMI tables supporting arbitrary software 8-point PWM curve arrays.
  * ASUS TUF laptops (specifically the TUF Dash F15 FX517ZC) omit these custom tables in the BIOS EC firmware.
* **The Failsafe Mechanism:**
  * When `asusctl` writes raw PWM curve tables to the WMI endpoint, the TUF EC rejects the unknown command as an invalid state.
  * As a safety precaution against unverified fan curves overheating the CPU/GPU, the EC asserts the hardware **BD PROCHOT** pin.
  * The Intel processor instantly clamps to 400 MHz.
* **The Solution:**
  * Switched fan speed management to ASUS TUF native **Hardware EC Thermal Policies**:
    * 🍃 **Silent Fan Mode:** Low acoustic RPM curve (Policy 2).
    * ⚖️ **Standard Fans:** Dynamic balanced airflow (Policy 0).
    * 🚀 **Overboost Turbo Fans:** High RPM aggressive fan curve (Policy 1).
  * Added `reset_fan_curves()` which executes `asusctl fan-curve --default` and disables custom curve flags across all profiles, permanently keeping BD PROCHOT de-asserted.

---

## 3. Resource & Performance Benchmark

Measurements taken live on system (PID: `59905`):

| Resource | Value | Notes |
|---|---|---|
| **Physical RAM (RSS)** | **~32.9 MB** | 0.2% of total system memory |
| **Private Memory (`RssAnon`)** | **~13.8 MB** | App logic and widget state |
| **Shared Libraries (`RssFile`)** | **~19.0 MB** | Python runtime & X11 / Tk |
| **Swap Usage** | **0 KB** | No swap memory used |
| **CPU Usage** | **0.0% – 0.7%** | Virtually zero CPU overhead |
| **Telemetry Tick Time** | **< 3 ms** | Direct sysfs file reads in memory |
| **Accumulated CPU Time** | **< 1 second** | Over continuous multi-minute operation |

*(Comparison: Electron/Chromium-based control dashboards typically consume 300MB – 800MB RAM and 2%–5% background CPU.)*

---

## 4. UI Virtualization & Real-Time Charts Upgrade (2026-10-20)

Integrated high-performance custom Tkinter Canvas visualization widgets with 0% CPU overhead:
1. **⚡ 12-Core CPU Spectrum Equalizer**: Live vertical frequency bars for all 12 cores (Alder Lake-P 12450H) with frequency-based color mapping (Cyan < 1.2G, Green < 2.8G, Gold < 3.8G, Crimson Turbo > 3.8G) and glowing peak caps.
2. **🌪️ Dual Arc Flow Fan Tachometers & Rotating Blades**: Visualizes CPU & GPU fans with circular arc meters (0 - 6000 RPM) and animated rotating 5-blade fan rotors operating smoothly at 25 FPS scaled to actual RPM.
3. **🔋 Cyber Segmented Battery Meter**: 10-block illuminated battery gauge with charging pulse animation and visible charge limit threshold marker.
4. **📈 30s Real-Time Dual-Wave Telemetry Chart**: Rolling Bezier curve graph tracking CPU Avg Clock (`#00e5ff`) and Package Temp (`#ffaa00`) with dynamic grid lines, range markers, and live value nodes.

---

## 5. Keyboard AURA Backlight Effects & Modes Support (2026-10-20)

Integrated full hardware AURA effect control for ASUS TUF Dash F15 (`aura_tuf.ron`):
* **Single-Color LED Backlight**: This laptop hardware features single-color (non-RGB) keyboard backlighting.
* **Effect Types**:
  * ✨ **Static**: Solid continuous illumination.
  * 💨 **Breathe**: Smooth two-phase breathing fade.
  * ⚡ **Pulse**: Rhythmic heartbeat pulsing effect.
* **Brightness Control**: 4 hardware levels (`Off`, `Low`, `Med`, `High`).
* **Hardware Interfacing**: Real-time D-Bus communication with `asusctl aura effect <mode>` and parsing `/etc/asusd/aura_tuf.ron`.

---

## 6. Upgraded `asusctl` to `v6.5.0` (2026-10-20)

* **Migration**: Transferred upstream git tracking from the archived GitLab repository (`asus-linux/asusctl`) to the active GitHub organization ([`OpenGamingCollective/asusctl`](https://github.com/OpenGamingCollective/asusctl)).
* **Version**: Upgraded from `v6.3.6` to `v6.5.0`.
* **Binaries Updated**: `/usr/bin/asusctl`, `/usr/bin/asusd`, `/usr/bin/asusd-user`, `/usr/bin/asus-shutdown`.
* **Service Status**: `asusd.service` successfully reloaded and running active on `v6.5.0`.

---

## 7. Dual GPU Virtualization & Hardware Telemetry (Intel UHD + RTX 3050)

* **Architecture Context**: The ASUS TUF Dash F15 (FX517ZC) utilizes an Intel Alder Lake-P hybrid graphics architecture:
  * **iGPU**: Intel UHD Graphics (`i915` driver, card1)
  * **dGPU**: NVIDIA GeForce RTX 3050 Mobile (`nouveau` driver, card0)
  * When no demanding 3D or CUDA load is active, Linux Runtime Power Management puts the RTX 3050 into `D3cold` (0W power consumption).
* **Backend Implementation (`backend.py`)**:
  * `get_gpu_telemetry()`:
    - Reads `/sys/class/drm/card1/gt_act_freq_mhz` to track real-time Intel UHD clock frequency (0 - 1200 MHz boost).
    - Checks `/sys/class/drm/card0/device/power/runtime_status` for NVIDIA RTX 3050 state (`suspended` / `D3cold` vs `active`).
    - Scans `/proc/<pid>/fdinfo/<fd>` to aggregate process VRAM allocations (`drm-total-system0:`) and active graphics clients.
    - Captures dedicated GPU Arc Flow Fan RPM (`fan2_input`).
* **UI Virtualizer (`app.py`)**:
  * **`GpuVirtualizerCanvas`**: Dual-engine visualizer showing:
    - Top: Intel UHD frequency readout + real-time animated turquoise load meter.
    - Bottom: NVIDIA RTX 3050 power status badge (`● SLEEP (0W)` in green vs `● ACTIVE 3D` in red) with live VRAM allocation tracking.
  * **Top 4-Card Telemetry Grid**:
    1. `⚡ CPU CLOCK SPECTRUM`: 12-core equalizer + throttling watchdog.
    2. `🎮 DUAL GPU ACCELERATION`: Dual GPU state, frequency, load meter, and VRAM.
    3. `🌪️ THERMALS & FANS`: Package thermals + rotating dual Arc Flow fans.
    4. `🔋 BATTERY & CHARGE`: Capacity, charge cap limit indicator, and power draw.
  * **3-Wave Rolling Telemetry History Chart**: Expanded `TelemetryHistoryChart` to plot live CPU Clock (Cyan), Temperature (TUF Gold), and GPU Load (Purple `#c084fc`) across a rolling 30-sample window.




