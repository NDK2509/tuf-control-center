# ASUS TUF Control Center (ASUS TUF Dash F15 - FX517ZC)

A lightweight, native Linux desktop GUI application designed specifically for the **ASUS TUF Dash F15 (FX517ZC)** laptop. Built with Python and Tkinter using a custom TUF gaming dark theme, providing zero-latency control and real-time hardware telemetry.

---

## Features

1. **🌪️ Dual Arc Flow Fan Control & Custom Curves**:
   - 🔄 **Auto (Factory)**: Uses the ASUS Embedded Controller firmware curve.
   - 🍃 **Quiet Curve**: Delays fan spin-up until 70°C+ for whisper-quiet acoustics.
   - ⚡ **Aggressive**: Kicks fans into gear early to maintain low temperatures during gaming / compiling.
   - 🌪️ **Max Turbo (100%)**: Instant 100% full airflow for fast cool-down or render tasks.
   - Real-time fan speed telemetry for both **CPU Fan** and **GPU Fan** in RPM.

2. **⚡ Performance Profiles (via `asusctl`)**:
   - 🍃 **Quiet**: Low acoustic fan profile, power conservation.
   - ⚖️ **Balanced**: Dynamic balance of cooling, acoustics, and performance.
   - 🚀 **Performance**: Maximum power limit and fan curves.

3. **🔋 Battery Health Care (Charge Limit)**:
   - **60% (Lifespan)**: Ideal for permanent desk / gaming setup plugged into AC power.
   - **80% (Balanced)**: Balances battery longevity and daily mobility.
   - **100% (Maximum)**: Full battery capacity for travel.

4. **⌨️ Keyboard Backlight Control**:
   - 4-level brightness: `Off`, `Low`, `Med`, `High`.

5. **📊 Real-time Hardware Telemetry & Live Visualizers**:
   - **📈 30s Dual-Wave Real-Time Telemetry Chart**: Continuous rolling graph tracking live CPU Clock (GHz in Cyan) and Package Temperature (°C in TUF Gold).
   - **⚡ 12-Core CPU Spectrum Equalizer**: Live individual frequency bars for each of the 12 Alder Lake-P cores with dynamic color bands and peak indicators.
   - **🌪️ Dual Arc Flow Fan Virtualizer**: Real-time circular arc tachometers with animated rotating 5-blade fan rotors spinning proportionally to CPU/GPU RPM.
   - **🔋 Cyber Segmented Battery Meter**: 10-block illuminated status bar with charging pulse animation and visible charge limit threshold marker.
   - **⚠️ 400 MHz Throttling Alert**: Emergency watchdog banner if BD PROCHOT asserts, with a one-click unthrottle fix.

6. **🖥️ System Info**:
   - Intel Alder Lake-P (12 Cores)
   - NVIDIA GeForce RTX 3050 Mobile
   - Intel UHD Graphics

---

## How to Launch

### 1. From Terminal
```bash
asus-tuf-control
```

### 2. From XFCE Application Menu
Search for **ASUS TUF Control Center** in your application launcher (under *Settings* or *System*), or pin it directly to your panel/desktop.
