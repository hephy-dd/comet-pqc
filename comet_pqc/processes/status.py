import comet
from comet.resource import ResourceMixin, ResourceError
from comet.process import ProcessMixin
from comet.driver.corvus import Venus1
from comet.driver.hephy import EnvironmentBox
from comet.driver.keithley import K707B

class StatusProcess(comet.Process, ResourceMixin, ProcessMixin):
    """Reload instruments status."""

    def __init__(self, message=None, progress=None, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.progress = progress

    def read_matrix(self):
        self.set("matrix_model", "")
        self.set("matrix_channels", "")
        try:
            with self.resources.get("matrix") as matrix_res:
                matrix = K707B(matrix_res)
                model = matrix.identification
                self.set("matrix_model", model)
                channels = matrix.channel.getclose()
                self.set("matrix_channels", ','.join(channels))
        except (ResourceError, OSError):
            pass

    def read_hvsrc(self):
        self.set("hvsrc_model", "")
        try:
            with self.resources.get("hvsrc") as hvsrc_res:
                model = hvsrc_res.query("*IDN?")
                self.set("hvsrc_model", model)
        except (ResourceError, OSError):
            pass

    def read_vsrc(self):
        self.set("vsrc_model", "")
        try:
            with self.resources.get("vsrc") as vsrc_res:
                model = vsrc_res.query("*IDN?")
                self.set("vsrc_model", model)
        except (ResourceError, OSError):
            pass

    def read_lcr(self):
        self.set("lcr_model", "")
        try:
            with self.resources.get("lcr") as lcr_res:
                model = lcr_res.query("*IDN?")
                self.set("lcr_model", model)
        except (ResourceError, OSError):
            pass

    def read_elm(self):
        self.set("elm_model", "")
        try:
            with self.resources.get("elm") as elm_res:
                model = elm_res.query("*IDN?")
                self.set("elm_model", model)
        except (ResourceError, OSError):
            pass

    def read_table(self):
        self.set("table_model", "")
        self.set("table_state", "")
        try:
            with self.resources.get("table") as table_res:
                table = Venus1(table_res)
                table.mode = 0
                model = table.identification
                self.set("table_model", model)
                caldone = (table.x.caldone, table.y.caldone, table.z.caldone)
                if caldone == (3, 3, 3):
                    state = f"CALIBRATED"
                else:
                    state = f"NOT CALIBRATED"
                self.set("table_state", state)
        except (ResourceError, OSError):
            pass

    def read_environ(self):
        self.set("env_model", "")
        self.set("env_pc_data", None)
        try:
            with self.processes.get("environ") as environment:
                model = environment.identification()
                self.set("env_model", model)
                pc_data = environment.pc_data()
                self.set("env_pc_data", pc_data)
        except (ResourceError, OSError):
            pass

    def run(self):
        self.emit("message", "Reading Matrix...")
        self.emit("progress", 0, 7)
        self.read_matrix()

        self.emit("message", "Reading HVSource...")
        self.emit("progress", 1, 7)
        self.read_hvsrc()

        self.emit("message", "Read VSource...")
        self.emit("progress", 2, 7)
        self.read_vsrc()

        self.emit("message", "Read LCRMeter...")
        self.emit("progress", 3, 7)
        self.read_lcr()

        self.emit("message", "Read Electrometer...")
        self.emit("progress", 4, 7)
        self.read_elm()

        self.emit("message", "Read Table...")
        self.emit("progress", 5, 7)
        self.read_table()

        self.emit("message", "Read Environment Box...")
        self.emit("progress", 6, 7)
        self.read_environ()

        self.emit("message", "")
        self.emit("progress", 7, 7)
