#!/usr/bin/env python3
import glob
import os
import platform
import subprocess
import sys
from pathlib import Path
import ctypes

# Make bundled deps (e.g., pyserial) importable before loading inkex.
BASE_DIR = Path(__file__).resolve().parent
DEPS_DIR = BASE_DIR / "deps"
if DEPS_DIR.exists():
    sys.path.insert(0, str(DEPS_DIR))

# Enable stderr logging when set True (or via KM_PLOT_DEBUG=1 environment variable).
DEBUG = os.environ.get("KM_PLOT_DEBUG", "").lower() in {"1", "true", "yes"}

# Hide the transient console window that appears on Windows.
if os.name == "nt":  # pragma: win32-only
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass

import inkex
from gui import KMPlotGUI, Gtk, GLib
from plot import PlotEngine
from plotters import plotters

try:
    import serial.tools.list_ports  # type: ignore
except Exception as exc:  # pragma: no cover
    serial_ports = None
    serial_import_error = repr(exc)
else:
    serial_ports = serial.tools.list_ports
    serial_import_error = None


class KMPlot(KMPlotGUI, inkex.EffectExtension):
    def __init__(self):
        super().__init__()
        self.window = None
        self.status_label = None
        self.device_label = None
        self.port_info_label = None
        self.port_combo = None
        self.port_store = None
        self.cut_button = None
        self.status_bar = None
        self.current_device = None
        self.current_vidpid = None
        self.poll_id = None
        self.port_entries = []
        self.sending = False
        self.device_image = None
        self.icons_dir = BASE_DIR / "icons"
        self.plot_engine = PlotEngine(self)

    def effect(self):
        self.debug("KM Plot extension starting; setting up window.")
        self.build_window()
        interval = 2
        self.debug(f"Using poll interval: {interval} seconds")
        self.update_status_bar("Searching for devices...")
        self.poll_id = GLib.timeout_add_seconds(interval, self.poll_devices)
        self.poll_devices()
        Gtk.main()

    def find_matching_device(self):
        devices = list(self.enumerate_with_serial())
        if not devices:
            self.debug("pyserial enumeration returned no devices.")
        for entry in devices:
            vidpid = entry["vidpid"]
            if vidpid in plotters:
                return entry["device"], vidpid, plotters[vidpid]
        return None

    def enumerate_with_serial(self):
        if not serial_ports:
            reason = (
                f" import error: {serial_import_error}"
                if serial_import_error
                else ""
            )
            self.debug(
                f"pyserial not available; skipping VID/PID enumeration.{reason}"
            )
            return []
        devices = []
        try:
            ports = list(serial_ports.comports())
        except Exception as exc:
            self.debug(f"serial.tools.list_ports.comports() failed: {exc!r}")
            return []

        if not ports:
            self.debug("serial.tools.list_ports reported no ports; retrying with links.")
            try:
                ports = list(serial_ports.comports(include_links=True))
            except Exception as exc:
                self.debug(
                    f"serial.tools.list_ports(include_links=True) failed: {exc!r}"
                )
                ports = []

        if not ports:
            self.debug("serial.tools.list_ports still returned no ports.")
            return []

        for port in ports:
            device = (
                getattr(port, "device", None)
                or getattr(port, "name", None)
                or getattr(port, "path", None)
                or getattr(port, "port", None)
                or (port if isinstance(port, str) else None)
            )
            vid = getattr(port, "vid", None) or getattr(port, "vendor_id", None)
            pid = getattr(port, "pid", None) or getattr(port, "product_id", None)
            vidpid = getattr(port, "vidpid", None)
            manufacturer = getattr(port, "manufacturer", None)
            product = getattr(port, "product", None)

            if vidpid:
                vidpid = str(vidpid).lower()
            elif vid is not None and pid is not None:
                try:
                    vidpid = f"{int(vid):04x}:{int(pid):04x}".lower()
                except Exception:
                    vidpid = f"{str(vid).lower()}:{str(pid).lower()}"

            self.debug(
                f"Serial port candidate: device={device}, vid={vid}, pid={pid}, vidpid={vidpid}"
            )
            if device and vid is not None and pid is not None and vidpid:
                info_lines = []
                if manufacturer:
                    info_lines.append(str(manufacturer))
                if product:
                    info_lines.append(str(product))
                devices.append(
                    {
                        "device": device,
                        "vidpid": vidpid,
                        "info": "\n".join(info_lines),
                    }
                )
        return devices

    def perform_cut(self, device_path):
        return self.plot_engine.perform_cut(device_path)

    def update_option(self, key, value):
        setattr(self.options, key, value)

    def update_option_from_combo(self, key, combo, default):
        model = combo.get_model()
        active_iter = combo.get_active_iter()
        if active_iter:
            value = model[active_iter][0]
        else:
            value = default
        setattr(self.options, key, value)

    def debug(self, message):
        text = f"[KMPlot] {message}"
        if DEBUG:
            print(text, file=sys.stderr, flush=True)


if __name__ == "__main__":
    KMPlot().run()
