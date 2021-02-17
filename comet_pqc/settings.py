from comet.settings import SettingsMixin

from .utils import from_table_unit, to_table_unit
from .position import Position

from .instruments.k2410 import K2410Instrument
from .instruments.k2657a import K2657AInstrument

__all__ = ['settings']

class TablePosition(Position):

    def __init__(self, name, x, y, z, comment=None):
        super().__init__(x, y, z)
        self.name = name
        self.comment = comment

    def __str__(self):
        return f"{self.name}"

class Settings(SettingsMixin):

    @property
    def table_positions(self):
        """List of user defined table positions for movement operations."""
        positions = []
        for position in self.settings.get('table_positions') or []:
            name = position.get('name')
            x = from_table_unit(position.get('x') or 0)
            y = from_table_unit(position.get('y') or 0)
            z = from_table_unit(position.get('z') or 0)
            comment = position.get('comment')
            positions.append(TablePosition(name, x, y, z, comment))
        return positions

    @table_positions.setter
    def table_positions(self, value):
        positions = []
        for position in value:
            positions.append({
                'name': position.name,
                'x': to_table_unit(position.x),
                'y': to_table_unit(position.y),
                'z': to_table_unit(position.z),
                'comment': position.comment,
            })
        self.settings['table_positions'] = positions

    @property
    def table_z_limit(self):
        """Table Z limit in millimeters."""
        return from_table_unit(self.settings.get('z_limit_movement') or 0)

    @table_z_limit.setter
    def table_z_limit(self, value):
        self.settings['z_limit_movement'] = to_table_unit(value)

    @property
    def operators(self):
        return list(self.settings.get('operators') or [])

    @operators.setter
    def operators(self, value):
        self.settings['operators'] = list(value)

    @property
    def current_operator(self):
        try:
            index = int(self.settings.get('current_operator') or 0)
        except ValueError:
            index = 0
        operators = self.operators
        if 0 <= index < len(operators):
            return operators[index]
        return None

    @current_operator.setter
    def current_operator(self, value):
        operators = self.operators
        index = 0
        if value in operators:
            index = operators.index(value)
        self.settings['current_operator'] = index

    @property
    def output_path(self):
        output_path = self.settings.get('output_path') or []
        if isinstance(output_path, str):
            output_path = [output_path] # provide backward compatibility
        return output_path

    @output_path.setter
    def output_path(self, value):
        if isinstance(value, str):
            value = [value] # provide backward compatibility
        self.settings['output_path'] = value

    @property
    def current_output_path(self):
        try:
            index = int(self.settings.get('current_output_path') or 0)
        except ValueError:
            index = 0
        output_path = self.output_path
        if 0 <= index < len(output_path):
            return output_path[index]
        return None

    @current_output_path.setter
    def current_output_path(self, value):
        output_path = self.output_path
        index = 0
        if value in output_path:
            index = output_path.index(value)
        self.settings['current_output_path'] = index

    @property
    def vsrc_instrument(self):
        vsrc_instrument = self.settings.get('vsrc_instrument') or 'K2657A'
        return {
            'K2410': K2410Instrument,
            'K2657A': K2657AInstrument,
        }.get(vsrc_instrument)

    @property
    def hvsrc_instrument(self):
        hvsrc_instrument = self.settings.get('hvsrc_instrument') or 'K2410'
        return {
            'K2410': K2410Instrument,
            'K2657A': K2657AInstrument,
        }.get(hvsrc_instrument)

settings = Settings()
