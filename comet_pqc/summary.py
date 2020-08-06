import qutie as ui

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
        if "Success" in item[5].value:
            item[5].color = "green"
        else:
            item[5].color = "red"

class SummaryTree(ui.Tree):

    def __init__(self):
        super().__init__()
        self.header = "Time", "Sample", "Type", "Contact", "Measurement", "Result"
        self.indentation = 0

    def append_result(self, *args):
        item = SummaryTreeItem(*args)
        self.append(item)
        self.fit()
        self.scroll_to(item)
