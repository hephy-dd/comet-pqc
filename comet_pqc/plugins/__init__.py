# TODO

import logging

logger = logging.getLogger(__name__)


class Plugin:

    def install(self, window) -> None:
        ...

    def uninstall(self, window) -> None:
        ...

    def beforePreferences(self, dialog) -> None:
        ...

    def afterPreferences(self, dialog) -> None:
        ...


class PluginManager:

    def __init__(self, window) -> None:
        self.window = window
        self.plugins = []

    def register(self, plugin: Plugin) -> None:
        if plugin not in self.plugins:
            self.plugins.append(plugin)

    def install(self) -> None:
        for plugin in self.plugins:
            try:
                plugin.install(self.window)
            except Exception as exc:
                logger.exception(exc)

    def uninstall(self) -> None:
        for plugin in self.plugins:
            try:
                plugin.uninstall(self.window)
            except Exception as exc:
                logger.exception(exc)
