from .standard_name import StandardName
from .transformation import derivative_of_X_wrt_to_Y


class StandardNameTable:
    """Standard Name Table class

    Examples
    --------
    >>> from h5rdmtoolbox.conventions.standard_names import StandardNameTable
    >>> table = StandardNameTable.from_yaml('standard_name_table.yaml')
    >>> # check a standard name
    >>> table.check('x_velocity')
    True
    >>> # check a transformed standard name
    >>> table.check('derivative_of_x_velocity_wrt_to_x_coordinate')
    True
    """
    __slots__ = ('table', 'meta', 'transformations')

    def __init__(self, table, **meta):
        self.table = table
        self.meta = meta
        self.transformations = (derivative_of_X_wrt_to_Y,)

    def __repr__(self):
        meta_str = ', '.join([f'{key}: {value}' for key, value in self.meta.items()])
        return f'<StandardNameTable: ({meta_str})>'

    def __contains__(self, standard_name):
        return standard_name in self.table

    def __getitem__(self, standard_name: str) -> StandardName:
        """Return table entry"""
        if standard_name in self.table:
            entry = self.table[standard_name]
            return StandardName(standard_name, entry['canonical_units'], entry['description'], self)
        for transformation in self.transformations:
            sn = transformation(standard_name, self)
            if sn:
                return sn

    def check(self, standard_name: str) -> bool:
        """check the standard name against the table. If the name is not
        exactly in the table, check if it is a transformed standard name"""
        if standard_name in self.table:
            return True
        for transformation in self.transformations:
            if transformation(standard_name, self):
                return True
        return False

    # Loader:
    @staticmethod
    def from_yaml(yaml_filename):
        """Initialize a StandardNameTable from a YAML file"""
        import yaml
        with open(yaml_filename, 'r') as f:
            _dict = {}
            for d in yaml.full_load_all(f):
                _dict.update(d)
            table = _dict.pop('table')
            return StandardNameTable(table=table, **_dict)
