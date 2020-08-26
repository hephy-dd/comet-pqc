import comet
from comet import ui

__all__ = [
    'SummaryTreeItem'
    'SummaryTree',
]

class SummaryTreeItem(ui.TreeItem):

    def __init__(self, timestamp, sample_name, sample_type, contact_name,
                 measurement_name, measurement_state):
        super().__init__([
            timestamp.isoformat(),
            sample_name,
            sample_type,
            contact_name,
            measurement_name,
            measurement_state
        ])
        # TODO
        if "Success" in self[5].value:
            self[5].color = "green"
        else:
            self[5].color = "red"

class SummaryTree(ui.Tree, comet.SettingsMixin):

    header_items = "Time", "Sample", "Type", "Contact", "Measurement", "Result"

    def __init__(self):
        super().__init__()
        self.header = self.header_items
        self.indentation = 0

    def append_result(self, *args):
        item = SummaryTreeItem(*args)
        self.append(item)
        self.fit()
        self.scroll_to(item)
        return item
