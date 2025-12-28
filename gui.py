import time
from pathlib import Path

from inkex.gui import Gtk, GLib
from gi.repository import GdkPixbuf
from plotters import plotters


class KMPlotGUI:
    def build_window(self):
        self.window = Gtk.Window(title="KM Plot")
        self.window.set_border_width(10)
        self.window.set_default_size(500, 500)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self.status_label = Gtk.Label(label="No supported plotter detected.")
        self.status_label.set_xalign(0.5)

        self.device_label = Gtk.Label(label="Device: not connected")
        self.device_label.set_xalign(0.5)

        self.device_image = Gtk.Image()
        self.device_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        self.device_image.set_pixel_size(150)
        self.device_image.set_halign(Gtk.Align.CENTER)
        self.device_image.set_valign(Gtk.Align.CENTER)

        self.port_info_label = Gtk.Label(label="")
        self.port_info_label.set_xalign(0.5)
        self.port_info_label.set_halign(Gtk.Align.CENTER)
        self.port_info_label.set_justify(Gtk.Justification.CENTER)
        self.port_info_label.set_line_wrap(True)
        self.port_info_label.set_margin_top(14)
        self.port_info_label.set_margin_bottom(14)
        self.port_info_label.set_margin_start(12)
        self.port_info_label.set_margin_end(12)
        self.port_info_frame = Gtk.Frame(label="Driver")
        self.port_info_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.port_info_frame.set_halign(Gtk.Align.CENTER)
        self.port_info_frame.set_margin_top(12)
        self.port_info_frame.set_margin_bottom(12)
        self.port_info_frame.set_margin_start(12)
        self.port_info_frame.set_margin_end(12)
        self.port_info_frame.set_size_request(250, -1)
        self.port_info_frame.add(self.port_info_label)

        self.port_store = Gtk.ListStore(str, str, str)  # device, vidpid, display
        self.port_combo = Gtk.ComboBox.new_with_model(self.port_store)
        port_renderer = Gtk.CellRendererText()
        self.port_combo.pack_start(port_renderer, True)
        self.port_combo.add_attribute(port_renderer, "text", 2)
        self.port_combo.set_sensitive(False)
        self.port_combo.connect("changed", self.on_port_changed)
        self.port_combo.set_halign(Gtk.Align.CENTER)

        self.cut_button = Gtk.Button(label="Send to plotter")
        self.cut_button.set_sensitive(False)
        self.cut_button.connect("clicked", self.on_cut_clicked)

        self.status_bar = Gtk.Label(label="Searching for devices...")
        self.status_bar.set_xalign(0)

        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)

        # Main tab
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)
        main_box.set_valign(Gtk.Align.CENTER)
        main_box.set_halign(Gtk.Align.CENTER)
        port_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        port_row.set_halign(Gtk.Align.CENTER)
        port_row.pack_start(self.port_combo, False, False, 0)
        main_box.pack_start(port_row, False, False, 0)
        main_box.pack_start(self.port_info_frame, False, False, 10)
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 12)
        main_box.pack_start(self.device_image, False, False, 6)

        notebook.append_page(main_box, Gtk.Label(label="Device"))

        # Connection settings tab
        conn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        conn_box.set_hexpand(True)
        conn_box.set_vexpand(True)
        conn_box.set_halign(Gtk.Align.CENTER)
        conn_box.set_margin_top(12)
        conn_box.set_margin_bottom(12)
        conn_grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        conn_grid.set_column_homogeneous(False)
        conn_grid.set_halign(Gtk.Align.CENTER)

        # Plot settings tab
        plot_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        plot_box.set_hexpand(True)
        plot_box.set_vexpand(True)
        plot_box.set_halign(Gtk.Align.CENTER)
        plot_box.set_margin_top(12)
        plot_box.set_margin_bottom(12)
        plot_grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        plot_grid.set_column_homogeneous(False)
        plot_grid.set_halign(Gtk.Align.CENTER)

        self.adv_controls = {}

        conn_row = 0
        plot_row = 0

        def add_conn_row(label_text, widget):
            nonlocal conn_row
            label = Gtk.Label(label=label_text)
            label.set_xalign(0)
            conn_grid.attach(label, 0, conn_row, 1, 1)
            conn_grid.attach(widget, 1, conn_row, 1, 1)
            conn_row += 1

        def add_plot_row(label_text, widget):
            nonlocal plot_row
            label = Gtk.Label(label=label_text)
            label.set_xalign(0)
            plot_grid.attach(label, 0, plot_row, 1, 1)
            plot_grid.attach(widget, 1, plot_row, 1, 1)
            plot_row += 1

        # Dropdown helpers
        def combo(options, active_value):
            store = Gtk.ListStore(str, str)
            for key, text in options:
                store.append([key, text])
            combo_box = Gtk.ComboBox.new_with_model(store)
            renderer_text = Gtk.CellRendererText()
            combo_box.pack_start(renderer_text, True)
            combo_box.add_attribute(renderer_text, "text", 1)
            # set active
            for i, row_data in enumerate(store):
                if row_data[0] == active_value:
                    combo_box.set_active(i)
                    break
            return combo_box

        # Spin helpers
        def spin_int(value, min_val, max_val, step):
            adj = Gtk.Adjustment(value=value, lower=min_val, upper=max_val, step_increment=step)
            return Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)

        def spin_float(value, min_val, max_val, step, digits=1):
            adj = Gtk.Adjustment(value=value, lower=min_val, upper=max_val, step_increment=step)
            return Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=digits)

        # Build widgets using current options/defaults
        baud_spin = spin_int(int(getattr(self.options, "serialBaudRate", 9600)), 1200, 115200, 100)
        bytesize_combo = combo(
            [("five", "5"), ("six", "6"), ("seven", "7"), ("eight", "8")],
            str(getattr(self.options, "serialByteSize", "eight")).lower(),
        )
        stopbits_combo = combo(
            [("one", "1"), ("onepointfive", "1.5"), ("two", "2")],
            str(getattr(self.options, "serialStopBits", "one")).lower(),
        )
        parity_combo = combo(
            [("none", "None"), ("even", "Even"), ("odd", "Odd"), ("mark", "Mark"), ("space", "Space")],
            str(getattr(self.options, "serialParity", "none")).lower(),
        )
        flow_combo = combo(
            [("xonxoff", "XON/XOFF"), ("rtscts", "RTS/CTS"), ("dsrdtrrtscts", "DSR/DTR+RTS/CTS"), ("none", "None")],
            str(getattr(self.options, "serialFlowControl", "xonxoff")).lower(),
        )
        resx_spin = spin_float(float(getattr(self.options, "resolutionX", 1016.0)), 10, 5000, 10, digits=1)
        resy_spin = spin_float(float(getattr(self.options, "resolutionY", 1016.0)), 10, 5000, 10, digits=1)
        pen_spin = spin_int(int(getattr(self.options, "pen", 1)), 0, 10, 1)
        force_spin = spin_int(int(getattr(self.options, "force", 0)), 0, 1000, 1)
        speed_spin = spin_int(int(getattr(self.options, "speed", 0)), 0, 1000, 1)
        orientation_combo = combo(
            [("0", "0°"), ("90", "90°"), ("180", "180°"), ("270", "270°")],
            str(getattr(self.options, "orientation", "0")),
        )
        mirrorx_check = Gtk.CheckButton(label="Mirror X")
        mirrorx_check.set_active(bool(getattr(self.options, "mirrorX", False)))
        mirrory_check = Gtk.CheckButton(label="Mirror Y")
        mirrory_check.set_active(bool(getattr(self.options, "mirrorY", False)))
        center_check = Gtk.CheckButton(label="Center zero point")
        center_check.set_active(bool(getattr(self.options, "center", False)))
        precut_check = Gtk.CheckButton(label="Use precut")
        precut_check.set_active(bool(getattr(self.options, "precut", True)))
        autoalign_check = Gtk.CheckButton(label="Auto align")
        autoalign_check.set_active(bool(getattr(self.options, "autoAlign", True)))
        overcut_spin = spin_float(float(getattr(self.options, "overcut", 1.0)), 0, 10, 0.1, digits=2)
        flat_spin = spin_float(float(getattr(self.options, "flat", 1.2)), 0.1, 10, 0.1, digits=2)
        tool_spin = spin_float(float(getattr(self.options, "toolOffset", 0.25)), 0, 10, 0.05, digits=2)

        def set_tip(widget, text):
            try:
                widget.set_tooltip_text(text)
            except Exception:
                pass

        # Tooltips for plot settings to guide users.
        set_tip(resx_spin, "Horizontal resolution in dots per inch (higher is finer).")
        set_tip(resy_spin, "Vertical resolution in dots per inch (higher is finer).")
        set_tip(pen_spin, "Pen number to use when cutting/drawing.")
        set_tip(force_spin, "Downward force in grams; higher presses harder.")
        set_tip(speed_spin, "Movement speed in cm/s; higher is faster.")
        set_tip(orientation_combo, "Rotate the plot by the selected angle.")
        set_tip(mirrorx_check, "Flip the design horizontally.")
        set_tip(mirrory_check, "Flip the design vertically.")
        set_tip(center_check, "Center the zero point on the page.")
        set_tip(precut_check, "Use a small precut to help corners release cleanly.")
        set_tip(autoalign_check, "Attempt to auto-align the plot to the material.")
        set_tip(overcut_spin, "Extend cuts past corners to ensure complete separation.")
        set_tip(flat_spin, "Flatness compensation factor.")
        set_tip(tool_spin, "Offset distance for the tool tip (in mm).")

        add_conn_row("Baud rate", baud_spin); self.adv_controls["serialBaudRate"] = baud_spin
        add_conn_row("Byte size", bytesize_combo); self.adv_controls["serialByteSize"] = bytesize_combo
        add_conn_row("Stop bits", stopbits_combo); self.adv_controls["serialStopBits"] = stopbits_combo
        add_conn_row("Parity", parity_combo); self.adv_controls["serialParity"] = parity_combo
        add_conn_row("Flow control", flow_combo); self.adv_controls["serialFlowControl"] = flow_combo
        add_plot_row("Resolution X (dpi)", resx_spin); self.adv_controls["resolutionX"] = resx_spin
        add_plot_row("Resolution Y (dpi)", resy_spin); self.adv_controls["resolutionY"] = resy_spin
        add_plot_row("Pen number", pen_spin); self.adv_controls["pen"] = pen_spin
        add_plot_row("Force (g)", force_spin); self.adv_controls["force"] = force_spin
        add_plot_row("Speed (cm/s)", speed_spin); self.adv_controls["speed"] = speed_spin
        add_plot_row("Orientation", orientation_combo); self.adv_controls["orientation"] = orientation_combo
        add_plot_row("Mirror X", mirrorx_check); self.adv_controls["mirrorX"] = mirrorx_check
        add_plot_row("Mirror Y", mirrory_check); self.adv_controls["mirrorY"] = mirrory_check
        add_plot_row("Center", center_check); self.adv_controls["center"] = center_check
        add_plot_row("Precut", precut_check); self.adv_controls["precut"] = precut_check
        add_plot_row("Auto align", autoalign_check); self.adv_controls["autoAlign"] = autoalign_check
        add_plot_row("Overcut (mm)", overcut_spin); self.adv_controls["overcut"] = overcut_spin
        add_plot_row("Flatness", flat_spin); self.adv_controls["flat"] = flat_spin
        add_plot_row("Tool offset (mm)", tool_spin); self.adv_controls["toolOffset"] = tool_spin

        # Connect change handlers to keep self.options in sync.
        baud_spin.connect("value-changed", lambda w: self.update_option("serialBaudRate", int(w.get_value())))
        resx_spin.connect("value-changed", lambda w: self.update_option("resolutionX", float(w.get_value())))
        resy_spin.connect("value-changed", lambda w: self.update_option("resolutionY", float(w.get_value())))
        pen_spin.connect("value-changed", lambda w: self.update_option("pen", int(w.get_value())))
        force_spin.connect("value-changed", lambda w: self.update_option("force", int(w.get_value())))
        speed_spin.connect("value-changed", lambda w: self.update_option("speed", int(w.get_value())))
        overcut_spin.connect("value-changed", lambda w: self.update_option("overcut", float(w.get_value())))
        flat_spin.connect("value-changed", lambda w: self.update_option("flat", float(w.get_value())))
        tool_spin.connect("value-changed", lambda w: self.update_option("toolOffset", float(w.get_value())))

        bytesize_combo.connect(
            "changed",
            lambda w: self.update_option_from_combo("serialByteSize", w, default="eight"),
        )
        stopbits_combo.connect(
            "changed",
            lambda w: self.update_option_from_combo("serialStopBits", w, default="one"),
        )
        parity_combo.connect(
            "changed", lambda w: self.update_option_from_combo("serialParity", w, default="none")
        )
        flow_combo.connect(
            "changed",
            lambda w: self.update_option_from_combo("serialFlowControl", w, default="xonxoff"),
        )
        orientation_combo.connect(
            "changed", lambda w: self.update_option_from_combo("orientation", w, default="0")
        )

        mirrorx_check.connect("toggled", lambda w: self.update_option("mirrorX", w.get_active()))
        mirrory_check.connect("toggled", lambda w: self.update_option("mirrorY", w.get_active()))
        center_check.connect("toggled", lambda w: self.update_option("center", w.get_active()))
        precut_check.connect("toggled", lambda w: self.update_option("precut", w.get_active()))
        autoalign_check.connect("toggled", lambda w: self.update_option("autoAlign", w.get_active()))

        conn_box.pack_start(conn_grid, False, False, 0)
        conn_scroller = Gtk.ScrolledWindow()
        conn_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        conn_scroller.set_hexpand(True)
        conn_scroller.set_vexpand(True)
        conn_scroller.add(conn_box)

        plot_box.pack_start(plot_grid, False, False, 0)
        plot_scroller = Gtk.ScrolledWindow()
        plot_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        plot_scroller.set_hexpand(True)
        plot_scroller.set_vexpand(True)
        plot_scroller.add(plot_box)

        notebook.append_page(conn_scroller, Gtk.Label(label="Connection Settings"))
        notebook.append_page(plot_scroller, Gtk.Label(label="Plot Settings"))

        # Footer with status and send button at the bottom.
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        footer.pack_start(self.status_bar, True, True, 0)
        footer.pack_end(self.cut_button, False, False, 0)

        root.pack_start(notebook, True, True, 0)
        root.pack_end(footer, False, False, 0)

        self.window.add(root)
        self.window.connect("destroy", self.on_window_close)
        self.window.show_all()

    def poll_devices(self):
        if getattr(self, "sending", False):
            return True
        self.debug("Polling for devices...")
        self.update_status_bar("Searching for devices...")
        devices = list(self.enumerate_with_serial())
        self.port_entries = []
        for device_entry in devices:
            device_path = device_entry["device"]
            vidpid = device_entry["vidpid"]
            info_text = device_entry["info"]
            plotter_info = plotters.get(vidpid)
            if isinstance(plotter_info, dict):
                name = plotter_info.get("name", vidpid)
                icon_key = plotter_info.get("icon")
            elif plotter_info:
                name = str(plotter_info)
                icon_key = None
            else:
                name = "Unknown device"
                icon_key = None
            display = f"{device_path} ({vidpid})" if vidpid else device_path
            self.port_entries.append(
                {
                    "device": device_path,
                    "vidpid": vidpid,
                    "name": name,
                    "display": display,
                    "info": info_text,
                    "icon": icon_key,
                    "supported": plotter_info is not None,
                }
            )

        if self.port_store:
            self.port_store.clear()
            for entry in self.port_entries:
                self.port_store.append([entry["device"], entry["vidpid"] or "", entry["display"]])

        if not self.port_entries:
            self.debug("No ports detected this cycle.")
            if self.port_combo:
                self.port_combo.set_sensitive(False)
                self.port_combo.hide()
            self.current_device = None
            self.current_vidpid = None
            if self.port_info_label:
                self.port_info_label.set_text("No Serial Devices Found")
                self.port_info_frame.set_visible(True)
            self.set_device_icon(None, fallback="noport")
            self.cut_button.set_sensitive(False)
            self.update_status_bar("Waiting for a supported plotter...")
            return True

        if self.port_combo:
            self.port_combo.set_sensitive(True)
            self.port_combo.show()
        if self.port_info_frame:
            self.port_info_frame.set_visible(True)

        active_idx = 0
        if self.current_device:
            for idx, entry in enumerate(self.port_entries):
                if entry["device"] == self.current_device:
                    active_idx = idx
                    break

        if self.port_combo:
            self.port_combo.handler_block_by_func(self.on_port_changed)
            self.port_combo.set_active(active_idx)
            self.port_combo.handler_unblock_by_func(self.on_port_changed)

        self.apply_port_entry(self.port_entries[active_idx], update_status=not getattr(self, "sending", False))
        return True

    def apply_port_entry(self, entry, update_status=False):
        self.current_device = entry["device"]
        self.current_vidpid = entry["vidpid"]
        detail = entry["vidpid"] or "unknown VID/PID"
        if self.port_info_label:
            info_text = entry.get("info") or ""
            self.port_info_label.set_text(info_text)
        self.set_device_icon(entry.get("icon"))
        self.cut_button.set_sensitive(True)
        if update_status:
            self.update_status_bar("Ready")

    def on_port_changed(self, _combo):
        idx = self.port_combo.get_active() if self.port_combo else -1
        if idx is None or idx < 0 or idx >= len(self.port_entries):
            return
        self.apply_port_entry(self.port_entries[idx], update_status=True)

    def on_window_close(self, *_args):
        if self.poll_id:
            GLib.source_remove(self.poll_id)
        Gtk.main_quit()

    def on_cut_clicked(self, _button):
        if not self.current_device:
            self.show_dialog("No plotter detected yet.", Gtk.MessageType.ERROR)
            self.update_status_bar("No plotter detected.", error=True)
            return
        try:
            self.sending = True
            self.update_status_bar("Sending to plotter...")
            self.flush_gui()
            time.sleep(0.05)
            self.perform_cut(self.current_device)
            self.show_dialog(
                f"Sent the document to {self.current_device}.", Gtk.MessageType.INFO
            )
            self.update_status_bar("Sent")
        except Exception as exc:  # pylint: disable=broad-except
            self.show_dialog(f"Cut failed: {exc}", Gtk.MessageType.ERROR)
            self.update_status_bar(f"Cut failed: {exc}", error=True)
        finally:
            self.sending = False

    def show_dialog(self, message, level):
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=level,
            buttons=Gtk.ButtonsType.OK,
            text=message,
        )
        dialog.run()
        dialog.destroy()

    def update_status_bar(self, message, error=False):
        if not self.status_bar:
            return
        prefix = "Error: " if error else ""
        self.status_bar.set_text(f"{prefix}{message}")

    def set_device_icon(self, icon_key, fallback=None):
        if not self.device_image:
            return
        target_px = 150
        base_dir = getattr(self, "icons_dir", None)
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent / "icons"

        def load_icon(name):
            icon_path = base_dir / f"{name}.png"
            if icon_path.exists():
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        str(icon_path), width=target_px, height=target_px, preserve_aspect_ratio=True
                    )
                    self.device_image.set_from_pixbuf(pixbuf)
                    return True
                except Exception as exc:
                    try:
                        self.debug(f"Failed to load icon {icon_path}: {exc}")
                    except Exception:
                        pass
            return False

        if icon_key and load_icon(icon_key):
            return
        if fallback and load_icon(fallback):
            return
        if load_icon("unknown"):
            return
        self.device_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        self.device_image.set_pixel_size(target_px)

    def flush_gui(self):
        """Process pending GTK events so label updates are shown before blocking work."""
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
