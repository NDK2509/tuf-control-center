# ASUS TUF Control Center (ASUS TUF Dash F15 - FX517ZC)

A lightweight, native Linux desktop GUI application designed specifically for the **ASUS TUF Dash F15 (FX517ZC)** laptop. Built with Python and Tkinter using a custom TUF gaming dark theme, providing zero-latency control and real-time hardware telemetry.

---

## Features

1. **🌪️ Hardware EC Thermal Profiles & Fan Control**:
   - 🚀 **Overboost Turbo Fans (`Performance`)**: Maximizes CPU/GPU power limit and applies the aggressive high-RPM cooling curve (up to 5500-6000 RPM) to keep temperatures low under heavy loads.
   - ⚖️ **Standard Fans (`Balanced`)**: Dynamic balance of cooling airflow, acoustics, and clock speeds for daily tasks.
   - 🍃 **Silent / Quiet Fans (`Quiet`)**: Acoustic-first low-RPM fan profile, prioritizing silent operation and power efficiency.
   - *Note on Custom Curves:* On ASUS TUF laptops (FX517ZC), arbitrary software fan curves trigger the hardware EC's **BD PROCHOT** safety lock (clamping CPU to 400 MHz). The application uses the laptop's official hardware EC thermal policies to guarantee full boost clocks with zero throttling risk.
   - Real-time telemetry for both **CPU Fan** and **GPU Fan** in RPM.

3. **🔋 Battery Health Care (Charge Limit)**:
   - **60% (Lifespan)**: Ideal for permanent desk / gaming setup plugged into AC power.
   - **80% (Balanced)**: Balances battery longevity and daily mobility.
   - **100% (Maximum)**: Full battery capacity for travel.

4. **⌨️ Keyboard Backlight & Lighting Effects**:
   - **Effect Types**: `✨ Static`, `💨 Breathe`, and `⚡ Pulse`.
   - **4-Level Brightness**: `Off`, `Low`, `Med`, and `High`.
   - Native single-color LED hardware support.

5. **📊 Real-time Hardware Telemetry & Live Visualizers**:
   - **📈 30s 3-Wave Real-Time Telemetry Chart**: Continuous rolling graph tracking live CPU Clock (GHz in Cyan), Package Temperature (°C in TUF Gold), and Dual GPU Activity (% in Purple).
   - **🎮 Dual GPU Acceleration Virtualizer**: Real-time telemetry for hybrid GPU architecture:
     * **Intel UHD iGPU**: Live frequency monitoring (0 - 1200 MHz boost clock) with an active load meter.
     * **NVIDIA RTX 3050 Mobile dGPU**: Real-time PCI runtime power state tracking (`D3cold` 0W sleep vs `Active 3D`), DRM VRAM allocation tracking, and active graphics client process detection.
   - **⚡ 12-Core CPU Spectrum Equalizer**: Live individual frequency bars for each of the 12 Alder Lake-P cores with dynamic color bands and peak indicators.
   - **🌪️ Dual Arc Flow Fan Virtualizer**: Real-time circular arc tachometers with animated rotating 5-blade fan rotors spinning proportionally to CPU/GPU RPM.
   - **🔋 Cyber Segmented Battery Meter**: 10-block illuminated status bar with charging pulse animation and visible charge limit threshold marker.
   - **⚠️ 400 MHz Throttling Alert**: Emergency watchdog banner if BD PROCHOT asserts, with a one-click unthrottle fix.

6. **🖥️ System Info**:
   - Intel Alder Lake-P (12 Cores)
   - NVIDIA GeForce RTX 3050 Mobile
   - Intel UHD Graphics

---

## Prerequisites: Installing `asusctl`

This application interfaces directly with the `asusd` system daemon and `asusctl` CLI tool for profile, battery limit, and keyboard backlight management. Ensure `asusctl` (v6.5.0+) is installed and running on your system:

### 1. Install Build Dependencies & Rust Toolchain
On Debian / Ubuntu:
```bash
sudo apt update
sudo apt install -y build-essential cmake libclang-dev libudev-dev libfontconfig-dev libxkbcommon-dev git
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
```

*(On Fedora: `sudo dnf install git make cmake clang-devel libxkbcommon-devel systemd-devel expat-devel pcre2-devel libzstd-devel rust cargo`)*  
*(On Arch Linux: `sudo pacman -S --needed git cmake clang pkg-config libzip rust openssl`)*

### 2. Clone the Upstream Repository & Compile
```bash
git clone https://github.com/OpenGamingCollective/asusctl.git
cd asusctl
git checkout 6.5.0
make
sudo make install
```

### 3. Enable and Start the `asusd` Daemon
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now asusd
```

### 4. Verify Installation
```bash
asusctl info
```
Output should confirm:
```text
asusctl v6.5.0
Software version: 6.5.0
  Product family: ASUS TUF Dash F15
      Board name: FX517ZC
```

---

## How to Launch

### 1. From Terminal
```bash
asus-tuf-control
```

### 2. From Application Menu
Search for **ASUS TUF Control Center** in your application launcher (under *Settings* or *System*), or pin it directly to your panel/desktop.
