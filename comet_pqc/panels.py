import comet

class Panel(comet.Widget):
    """Base class for measurement panels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class IVRamp(Panel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = comet.Column(
            comet.Label("IV Ramp"),
            comet.Plot(),
            comet.Stretch()
        )

class BiasIVRamp(Panel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = comet.Column(
            comet.Label("Bias + IV Ramp"),
            comet.Stretch()
        )

class CVRamp(Panel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = comet.Column(
            comet.Label("CV Ramp (1 SMU)"),
            comet.Plot(),
            comet.Stretch()
        )

class CVRampAlt(Panel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = comet.Column(
            comet.Label("CV Ramp (2 SMU)"),
            comet.Plot(),
            comet.Stretch()
        )

class FourWireIVRamp(Panel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = comet.Column(
            comet.Label("4 Wire IV Ramp"),
            comet.Stretch()
        )
