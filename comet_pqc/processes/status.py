import comet
from comet.driver.keithley import K707B
from comet.process import ProcessMixin
from comet.resource import ResourceError, ResourceMixin

__all__ = ["StatusProcess"]


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
                self.set("matrix_channels", ",".join(channels))
        except (ResourceError, OSError):
            ...

    def read_hvsrc(self):
        self.set("hvsrc_model", "")
        try:
            with self.resources.get("hvsrc") as hvsrc_res:
                model = hvsrc_res.query("*IDN?")
                self.set("hvsrc_model", model)
        except (ResourceError, OSError):
            ...

    def read_vsrc(self):
        self.set("vsrc_model", "")
        try:
            with self.resources.get("vsrc") as vsrc_res:
                model = vsrc_res.query("*IDN?")
                self.set("vsrc_model", model)
        except (ResourceError, OSError):
            ...

    def read_lcr(self):
        self.set("lcr_model", "")
        try:
            with self.resources.get("lcr") as lcr_res:
                model = lcr_res.query("*IDN?")
                self.set("lcr_model", model)
        except (ResourceError, OSError):
            ...

    def read_elm(self):
        self.set("elm_model", "")
        try:
            with self.resources.get("elm") as elm_res:
                model = elm_res.query("*IDN?")
                self.set("elm_model", model)
        except (ResourceError, OSError):
            ...

    def read_table(self):
        self.set("table_model", "")
        self.set("table_state", "")
        if not self.get("use_table", False):
            return
        try:
            table_process = self.processes.get("table")
            model = table_process.get_identification().get(timeout=5.0)
            caldone = table_process.get_caldone().get(timeout=5.0)
            self.set("table_model", model)
            if caldone == (3, 3, 3):
                state = "CALIBRATED"
            else:
                state = "NOT CALIBRATED"
            self.set("table_state", state)
        except (ResourceError, OSError):
            ...

    def read_environ(self):
        self.set("env_model", "")
        self.set("env_pc_data", None)
        if not self.get("use_environ", False):
            return
        try:
            with self.processes.get("environ") as environment:
                model = environment.identification()
                self.set("env_model", model)
                pc_data = environment.pc_data()
                self.set("env_pc_data", pc_data)
        except (ResourceError, OSError):
            ...

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
