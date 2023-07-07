class Plugin:

    def install(self):
        ...

    def uninstall(self):
        ...


class PluginManager:

    def __init__(self):
        self.plugins = []

    def register_pugin(self, plugin):
        self.plugins.append(plugin)

    def install_plugins(self):
        for plugin in self.plugins:
            plugin.install()

    def uninstall_plugins(self):
        for plugin in self.plugins:
            plugin.uninstall()

    def handle(self, event, *args, **kwargs):
        attr_name = f"handle_{event}"
        for plugin in self.plugins:
            if hasattr(plugin, attr_name):
                getattr(plugin, attr_name)(*args, **kwargs)
