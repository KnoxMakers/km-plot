class PlotEngine:

    def __init__(self, extension):
        self.ext = extension

    def perform_cut(self, device_path):
        self.ext.debug(f"Generating HPGL and sending to {device_path}")
        hpgl = self.generate_hpgl()
        self.send_hpgl_serial(device_path, hpgl)

    def ensure_plotter_defaults(self):
        defaults = {
            "serialBaudRate": "9600",
            "serialByteSize": "eight",
            "serialStopBits": "one",
            "serialParity": "none",
            "serialFlowControl": "xonxoff",
            "resolutionX": 1016.0,
            "resolutionY": 1016.0,
            "pen": 1,
            "force": 0,
            "speed": 0,
            "orientation": "0",
            "mirrorX": False,
            "mirrorY": False,
            "center": False,
            "overcut": 1.0,
            "precut": True,
            "flat": 1.2,
            "autoAlign": True,
            "toolOffset": 0.25,
        }
        for key, value in defaults.items():
            if not hasattr(self.ext.options, key):
                setattr(self.ext.options, key, value)

    def generate_hpgl(self):
        self.ensure_plotter_defaults()
        try:
            import hpgl_encoder
        except Exception as exc:
            raise RuntimeError(f"hpgl_encoder not available: {exc}") from exc

        if self.ext.svg.xpath("//use|//flowRoot|//text") is not None:
            self.preprocess(["flowRoot", "text"])
        encoder = hpgl_encoder.hpglEncoder(self.ext)
        try:
            hpgl = encoder.getHpgl()
        except Exception as exc:
            raise RuntimeError(f"HPGL generation failed: {exc}") from exc
        return self.convert_hpgl(hpgl)

    def convert_hpgl(self, hpgl):
        init = "IN"
        return init + hpgl + ";PU0,0;SP0;IN; "

    def send_hpgl_serial(self, device_path, hpgl):
        try:
            import serial
        except Exception as exc:
            raise RuntimeError(f"pyserial not available: {exc}") from exc

        baud = int(getattr(self.ext.options, "serialBaudRate", 9600))
        byte_size = str(getattr(self.ext.options, "serialByteSize", "eight")).lower()
        stop_bits = str(getattr(self.ext.options, "serialStopBits", "one")).lower()
        parity = str(getattr(self.ext.options, "serialParity", "none")).lower()
        flow = str(getattr(self.ext.options, "serialFlowControl", "xonxoff")).lower()

        size_map = {
            "5": serial.FIVEBITS,
            "five": serial.FIVEBITS,
            "6": serial.SIXBITS,
            "six": serial.SIXBITS,
            "7": serial.SEVENBITS,
            "seven": serial.SEVENBITS,
            "8": serial.EIGHTBITS,
            "eight": serial.EIGHTBITS,
        }
        stop_map = {
            "1": serial.STOPBITS_ONE,
            "one": serial.STOPBITS_ONE,
            "1.5": serial.STOPBITS_ONE_POINT_FIVE,
            "onepointfive": serial.STOPBITS_ONE_POINT_FIVE,
            "2": serial.STOPBITS_TWO,
            "two": serial.STOPBITS_TWO,
        }
        parity_map = {
            "none": serial.PARITY_NONE,
            "even": serial.PARITY_EVEN,
            "odd": serial.PARITY_ODD,
            "mark": serial.PARITY_MARK,
            "space": serial.PARITY_SPACE,
        }

        ser = serial.Serial()
        ser.port = device_path
        ser.baudrate = baud
        ser.bytesize = size_map.get(byte_size, serial.EIGHTBITS)
        ser.stopbits = stop_map.get(stop_bits, serial.STOPBITS_ONE)
        ser.parity = parity_map.get(parity, serial.PARITY_NONE)
        ser.timeout = 1
        ser.xonxoff = flow == "xonxoff"
        ser.rtscts = flow in ("rtscts", "dsrdtrrtscts")
        ser.dsrdtr = flow == "dsrdtrrtscts"

        self.ext.debug(
            f"Opening serial port {device_path} baud={baud} size={ser.bytesize} "
            f"stop={ser.stopbits} parity={ser.parity} flow={flow}"
        )

        ser.open()
        try:
            ser.write(hpgl.encode("utf8"))
            try:
                ser.read(2)
            except Exception:
                pass
        finally:
            ser.close()

    def preprocess(self, convert):
        try:
            self.ext.svg.convert_to_paths(convert)
        except Exception as exc:
            self.ext.debug(f"Preprocess convert_to_paths failed: {exc}")
