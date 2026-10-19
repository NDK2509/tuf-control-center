"""
ASUS TUF Dash F15 Control Backend
Interfaces directly with sysfs, procfs, and asusctl daemon.
"""

import glob
import json
import os
import re
import subprocess
from typing import Dict, Any, List, Optional

CONFIG_DIR = os.path.expanduser("~/.config/asus-tuf-control")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")

# On ASUS TUF laptops (e.g. Dash F15 FX517ZC), custom software fan curve tables
# trigger the TUF EC (Embedded Controller) BD PROCHOT failsafe, locking CPU clocks to 400 MHz.
# Instead, TUF hardware uses the 3 official ASUS EC Thermal Fan Policies (Overboost / Standard / Silent).
FAN_MODES = {
    "Balanced": {
        "title": "⚖️ Standard Fan Mode",
        "desc": "Balanced dynamic airflow managed safely by ASUS TUF hardware EC",
        "profile": "Balanced",
        "policy": 0,
    },
    "Turbo": {
        "title": "🌪️ Overboost / Turbo Fans",
        "desc": "High fan RPM curve with aggressive cooling to prevent heat buildup",
        "profile": "Performance",
        "policy": 1,
    },
    "Quiet": {
        "title": "🍃 Silent Fan Mode",
        "desc": "Acoustic-first low RPM fan curve for quiet environments",
        "profile": "Quiet",
        "policy": 2,
    },
}

def run_cmd(cmd: List[str]) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=3).strip()
    except Exception:
        return ""

def reset_fan_curves() -> bool:
    """Ensure custom fan curves are disabled so BD PROCHOT 400 MHz lock is cleared."""
    try:
        run_cmd(["asusctl", "fan-curve", "--default"])
        for p in ["Quiet", "Balanced", "Performance"]:
            run_cmd(["asusctl", "fan-curve", "--mod-profile", p, "--enable-fan-curves", "false"])
        return True
    except Exception:
        return False

def get_profiles() -> List[str]:
    return ["Quiet", "Balanced", "Performance"]

def get_active_profile() -> str:
    out = run_cmd(["asusctl", "profile", "get"])
    m = re.search(r"Active profile:\s*(\w+)", out)
    if m:
        return m.group(1).capitalize()
    return "Balanced"

def set_profile(profile_name: str) -> bool:
    name = profile_name.capitalize()
    if name not in ["Quiet", "Balanced", "Performance"]:
        return False
    # Ensure custom curves are off to protect CPU clocks
    run_cmd(["asusctl", "fan-curve", "--default"])
    run_cmd(["asusctl", "fan-curve", "--mod-profile", name, "--enable-fan-curves", "false"])
    run_cmd(["asusctl", "profile", "set", name])
    return True

def get_battery_limit() -> int:
    out = run_cmd(["asusctl", "battery", "info"])
    m = re.search(r"limit:\s*(\d+)%", out)
    if m:
        return int(m.group(1))
    return 100

def set_battery_limit(percent: int) -> bool:
    percent = max(20, min(100, int(percent)))
    run_cmd(["asusctl", "battery", "limit", str(percent)])
    return True

def get_led_brightness() -> str:
    out = run_cmd(["asusctl", "leds", "get"])
    m = re.search(r"brightness:\s*(\w+)", out)
    if m:
        return m.group(1).capitalize()
    return "Med"

def set_led_brightness(level: str) -> bool:
    lvl = level.capitalize()
    if lvl not in ["Off", "Low", "Med", "High"]:
        return False
    run_cmd(["asusctl", "leds", "set", lvl])
    return True

def get_aura_mode() -> str:
    """Read the active keyboard backlight mode (Static, Breathe, Pulse) from aura config."""
    try:
        if os.path.exists("/etc/asusd/aura_tuf.ron"):
            with open("/etc/asusd/aura_tuf.ron", "r") as f:
                content = f.read()
            m = re.search(r"current_mode:\s*(\w+)", content)
            if m:
                return m.group(1).capitalize()
    except Exception:
        pass
    return "Static"

def set_aura_effect(mode: str) -> bool:
    """Set keyboard lighting mode (Static, Breathe, Pulse) via asusctl."""
    m = mode.capitalize()
    try:
        if m == "Static":
            run_cmd(["asusctl", "aura", "effect", "static", "-c", "ffffff"])
            return True
        elif m == "Breathe":
            run_cmd(["asusctl", "aura", "effect", "breathe", "--colour", "ffffff", "--colour2", "000000", "--speed", "med"])
            return True
        elif m == "Pulse":
            run_cmd(["asusctl", "aura", "effect", "pulse", "-c", "ffffff"])
            return True
    except Exception:
        pass
    return False


def get_fan_mode() -> str:
    """Get active EC thermal fan mode based on current profile and policy."""
    prof = get_active_profile()
    if prof == "Performance":
        return "Turbo"
    elif prof == "Quiet":
        return "Quiet"
    return "Balanced"

def set_fan_mode(mode_name: str) -> bool:
    """Set the EC thermal fan mode safely without tripping 400 MHz lock."""
    if mode_name not in FAN_MODES:
        return False
    target_profile = FAN_MODES[mode_name]["profile"]
    return set_profile(target_profile)

def get_cpu_telemetry() -> Dict[str, Any]:
    freqs = []
    cpu_name = "Intel Alder Lake CPU"
    try:
        with open("/proc/cpuinfo", "r") as f:
            text = f.read()
        freqs = [float(x) for x in re.findall(r"cpu MHz\s*:\s*([\d\.]+)", text)]
        m = re.search(r"model name\s*:\s*(.+)", text)
        if m:
            cpu_name = m.group(1).strip()
    except Exception:
        pass

    avg_mhz = sum(freqs) / len(freqs) if freqs else 0.0
    max_mhz = max(freqs) if freqs else 0.0
    min_mhz = min(freqs) if freqs else 0.0
    
    # Check if ALL active cores are locked at <= 450 MHz (BD PROCHOT emergency clamp)
    is_throttled = (max_mhz <= 450.0 and len(freqs) > 0)
    
    return {
        "cpu_name": cpu_name,
        "cores": len(freqs),
        "freqs": freqs,
        "avg_mhz": round(avg_mhz, 1),
        "max_mhz": round(max_mhz, 1),
        "min_mhz": round(min_mhz, 1),
        "is_throttled": is_throttled,
    }

def get_fans() -> Dict[str, int]:
    fans = {"cpu": 0, "gpu": 0}
    for p in glob.glob("/sys/devices/platform/asus-nb-wmi/hwmon/hwmon*/fan1_input"):
        try:
            with open(p) as f:
                fans["cpu"] = int(f.read().strip())
        except Exception:
            pass
    for p in glob.glob("/sys/devices/platform/asus-nb-wmi/hwmon/hwmon*/fan2_input"):
        try:
            with open(p) as f:
                fans["gpu"] = int(f.read().strip())
        except Exception:
            pass
    return fans

def get_max_temp() -> int:
    temps = []
    for p in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        try:
            with open(p) as f:
                val = int(f.read().strip())
                if val > 1000:
                    val //= 1000
                if 20 <= val <= 115:
                    temps.append(val)
        except Exception:
            pass
    return max(temps) if temps else 0

def get_battery_telemetry() -> Dict[str, Any]:
    data = {
        "capacity": 0,
        "status": "Unknown",
        "ac_online": False,
        "watts": 0.0,
    }
    try:
        if os.path.exists("/sys/class/power_supply/BAT1/capacity"):
            with open("/sys/class/power_supply/BAT1/capacity") as f:
                data["capacity"] = int(f.read().strip())
        if os.path.exists("/sys/class/power_supply/BAT1/status"):
            with open("/sys/class/power_supply/BAT1/status") as f:
                data["status"] = f.read().strip()
        v, c = 0, 0
        if os.path.exists("/sys/class/power_supply/BAT1/voltage_now"):
            with open("/sys/class/power_supply/BAT1/voltage_now") as f:
                v = int(f.read().strip())
        if os.path.exists("/sys/class/power_supply/BAT1/current_now"):
            with open("/sys/class/power_supply/BAT1/current_now") as f:
                c = int(f.read().strip())
        if v and c:
            data["watts"] = round((v * c) / 1e12, 1)
    except Exception:
        pass

    for ac in glob.glob("/sys/class/power_supply/A*/online"):
        try:
            with open(ac) as f:
                if f.read().strip() == "1":
                    data["ac_online"] = True
                    break
        except Exception:
            pass

    return data

def get_system_summary() -> Dict[str, str]:
    return {
        "model": "ASUS TUF Dash F15 (FX517ZC)",
        "cpu": "12th Gen Intel Core i5/i7 (Alder Lake-P)",
        "dgpu": "NVIDIA GeForce RTX 3050 Mobile",
        "igpu": "Intel UHD Graphics (Alder Lake-P GT1)",
    }
