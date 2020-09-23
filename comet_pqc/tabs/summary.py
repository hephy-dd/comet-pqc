import datetime

from comet import ui
from comet.settings import SettingsMixin

__all__ = ['SummaryTab']

class SummaryTab(ui.Tab):

    def __init__(self):
        super().__init__(title="Summary")
        self.summary_tree = SummaryTree()
        self.layout=self.summary_tree

    def header(self):
        return self.summary_tree.header_items

    def append_result(self, *args):
        return self.summary_tree.append_result(*args)

class SummaryTreeItem(ui.TreeItem):

    def __init__(self, timestamp, sample_name, sample_type, contact_name,
                 measurement_name, measurement_state):
        super().__init__([
            datetime.datetime.fromtimestamp(timestamp).isoformat(),
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

class SummaryTree(ui.Tree, SettingsMixin):

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
