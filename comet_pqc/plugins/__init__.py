__all__ = ["PluginManager"]


class PluginManager:

    def __init__(self) -> None:
        self.plugins: list = []

    def register_plugin(self, plugin: object) -> None:
        self.plugins.append(plugin)

    def install_plugins(self) -> None:
        self.handle("install")

    def uninstall_plugins(self) -> None:
        self.handle("uninstall")

    def handle(self, event_name: str, *args, **kwargs) -> None:
        attr_name = f"on_{event_name}"
        for plugin in self.plugins:
            if hasattr(plugin, attr_name):
                getattr(plugin, attr_name)(*args, **kwargs)
