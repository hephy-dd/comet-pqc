__all__ = ["Plugin", "PluginSystem"]


class Plugin:

    def install(self, window):
        ...

    def uninstall(self, window):
        ...


class PluginSystem:

    def __init__(self, window):
        self.window = window
        self.plugins = []

    def addPlugin(self, plugin):
        self.plugins.append(plugin)

    def installPlugins(self):
        for plugin in self.plugins:
            plugin.install(self.window)

    def uninstallPlugins(self):
        for plugin in self.plugins:
            plugin.uninstall(self.window)
